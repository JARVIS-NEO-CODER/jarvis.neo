"""Objective-level verification for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from .system_observer import SystemSnapshot


@dataclass(frozen=True)
class GoalVerification:
    achieved: bool
    confidence: float
    reason: str
    evidence: dict[str, Any]


class GoalVerifier:
    """Verify goals with capability-specific evidence before using OS observations."""

    _CLOSE_INTENT = re.compile(r"\b(?:ferme|fermer|quitte|quitter|arrête|arrêter|close|quit|stop)\b")
    _LAUNCH_INTENT = re.compile(r"\b(?:lance|lancer|ouvre|ouvrir|démarre|démarrer|launch|open|start)\b")
    _CREATE_DIR_INTENT = re.compile(
        r"\b(?:crée|créer|creer|créer|create|make)\b.*\b(?:dossier|répertoire|repertoire|folder|directory)\b"
    )
    _WRITE_FILE_INTENT = re.compile(
        r"\b(?:écris|écrire|ecris|écrit|crée|créer|creer|enregistre|enregistrer|write|create|save)\b"
        r".*\b(?:fichier|file|texte|text)\b"
    )
    _SEARCH_INTENT = re.compile(r"\b(?:cherche|recherche|rechercher|cherche|search|look up|find)\b")

    def verify(
        self,
        objective: str,
        *,
        before: SystemSnapshot | None,
        after: SystemSnapshot | None,
        action_success: bool,
        action_verified: bool,
        action_name: str | None = None,
        action_kwargs: dict[str, Any] | None = None,
        action_message: str | None = None,
    ) -> GoalVerification:
        text = objective.strip().lower()
        if not text:
            return GoalVerification(False, 0.0, "Objectif vide.", {})
        if not action_success or not action_verified:
            return GoalVerification(
                False,
                0.0,
                "La dernière action n'a pas été vérifiée.",
                {"action_success": action_success, "action_verified": action_verified},
            )

        kwargs = action_kwargs or {}
        # Prefer proof tied to the capability that actually ran. Foreground-window
        # changes alone cannot prove a file was written or a background app was closed.
        capability_result = self._verify_capability(
            text, action_name, kwargs, after, action_message
        )
        if capability_result is not None:
            return capability_result
        if action_name is not None:
            return GoalVerification(
                False,
                0.0,
                "Cette capacité ne possède pas de vérificateur adapté à cet objectif.",
                {"action_name": action_name, "action_success": action_success, "action_verified": action_verified},
            )

        close = re.search(
            r"(?:ferme|fermer|quitte|quitter|arrête|arrêter|close|quit|stop)\s+"
            r"(?:le|la|les|l')?\s*(.+)",
            text,
        )
        if close and after is not None:
            target = close.group(1).strip().strip(".!?")
            proc = (after.active_process or "").lower()
            window = (after.active_window or "").lower()
            tokens = [t for t in re.findall(r"[a-z0-9]+", target) if len(t) > 2]
            still_present = target in proc or target in window or (
                bool(tokens) and all(t in proc or t in window for t in tokens)
            )
            return GoalVerification(
                not still_present,
                1.0 if not still_present else 0.0,
                "La cible n'est plus détectée dans la fenêtre active."
                if not still_present
                else "La cible est encore détectée dans la fenêtre active.",
                {"target": target, "active_process": after.active_process, "active_window": after.active_window},
            )

        match = re.search(
            r"(?:lance|lancer|ouvre|ouvrir|démarre|démarrer|launch|open|start)\s+(.+)",
            text,
        )
        if match and after is not None:
            target = match.group(1).strip().strip(".!?")
            process = (after.active_process or "").lower()
            window = (after.active_window or "").lower()
            tokens = [t for t in re.findall(r"[a-z0-9]+", target) if len(t) > 2]
            matched = target in process or target in window or (
                bool(tokens) and all(t in process or t in window for t in tokens)
            )
            return GoalVerification(
                matched,
                1.0 if matched else 0.15,
                "Le programme demandé est détecté."
                if matched
                else "Le programme demandé n'est pas détecté.",
                {"target": target, "active_process": after.active_process, "active_window": after.active_window},
            )

        evidence = {"action_success": action_success, "action_verified": action_verified}
        if before is not None and after is not None:
            changed = (before.active_window, before.active_process) != (
                after.active_window,
                after.active_process,
            )
            evidence.update(
                {
                    "foreground_changed": changed,
                    "before_process": before.active_process,
                    "after_process": after.active_process,
                    "before_window": before.active_window,
                    "after_window": after.active_window,
                }
            )
        return GoalVerification(
            False,
            0.0,
            "Aucune règle de vérification spécifique ne permet de confirmer cet objectif.",
            evidence,
        )

    def _verify_capability(
        self,
        objective: str,
        action_name: str | None,
        kwargs: dict[str, Any],
        after: SystemSnapshot | None,
        action_message: str | None,
    ) -> GoalVerification | None:
        if action_name == "action.create_directory" and self._CREATE_DIR_INTENT.search(objective):
            raw_path = kwargs.get("path")
            path = Path(str(raw_path)).expanduser() if raw_path else None
            target_matches = bool(path is not None and self._target_mentioned(objective, path.name))
            exists = bool(target_matches and path is not None and path.is_dir())
            return GoalVerification(
                exists,
                1.0 if exists else 0.0,
                "Le dossier demandé existe et a été vérifié."
                if exists
                else "Le dossier demandé n'existe pas : création non confirmée.",
                {"capability": action_name, "path": str(path) if path else None, "target_matches_objective": target_matches, "is_directory": bool(path is not None and path.is_dir())},
            )

        if action_name == "action.write_text_file" and self._WRITE_FILE_INTENT.search(objective):
            raw_path = kwargs.get("path")
            expected = kwargs.get("content", "")
            encoding = kwargs.get("encoding", "utf-8")
            path = Path(str(raw_path)).expanduser() if raw_path else None
            target_matches = bool(path is not None and self._target_mentioned(objective, path.name))
            matches = False
            read_error = None
            if target_matches and path is not None and path.is_file():
                try:
                    matches = path.read_text(encoding=encoding) == expected
                except (OSError, UnicodeError, LookupError) as exc:
                    read_error = str(exc)
            return GoalVerification(
                matches,
                1.0 if matches else 0.0,
                "Le fichier existe et son contenu correspond exactement à la demande."
                if matches
                else "Le contenu du fichier ne peut pas être confirmé.",
                {
                    "capability": action_name,
                    "path": str(path) if path else None,
                    "file_exists": bool(path is not None and path.is_file()),
                    "target_matches_objective": target_matches,
                    "content_matches": matches,
                    "read_error": read_error,
                },
            )

        if action_name == "action.close_app" and self._CLOSE_INTENT.search(objective):
            name = str(kwargs.get("name", "")).strip().lower().replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".exe")
            if not name or not self._target_mentioned(objective, name):
                return GoalVerification(False, 0.0, "La cible de fermeture ne correspond pas explicitement à l'objectif.", {"capability": action_name, "target": name})
            running = []
            for process in psutil.process_iter(["pid", "name"]):
                try:
                    process_name = (process.info.get("name") or "").lower().removesuffix(".exe")
                    if name in process_name:
                        running.append({"pid": process.info.get("pid"), "name": process.info.get("name")})
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            closed = not running
            return GoalVerification(
                closed,
                1.0 if closed else 0.0,
                "Aucun processus correspondant n'est encore actif."
                if closed
                else "Le processus existe encore : fermeture non confirmée.",
                {"capability": action_name, "target": name, "remaining_processes": running},
            )

        if action_name == "action.launch_app" and self._LAUNCH_INTENT.search(objective):
            command = str(kwargs.get("command", "")).strip()
            target = command.replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe") if command else ""
            if not target or not self._target_mentioned(objective, target):
                return GoalVerification(False, 0.0, "La cible de lancement ne correspond pas explicitement à l'objectif.", {"capability": action_name, "target": target})
            running = []
            for process in psutil.process_iter(["pid", "name"]):
                try:
                    process_name = (process.info.get("name") or "").lower().removesuffix(".exe")
                    if process_name == target or process_name.startswith(target + "."):
                        running.append({"pid": process.info.get("pid"), "name": process.info.get("name")})
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            foreground_matches = False
            if after is not None:
                foreground_process = (after.active_process or "").lower().removesuffix(".exe")
                foreground_matches = foreground_process == target or foreground_process.startswith(target + ".")
            verified = bool(running) or foreground_matches
            return GoalVerification(
                verified,
                1.0 if verified else 0.0,
                "Le processus demandé est détecté."
                if verified
                else "Le processus demandé n'est pas détecté après le lancement.",
                {"capability": action_name, "target": target, "running_processes": running, "foreground_matches": foreground_matches},
            )

        if action_name == "action.search_web" and self._SEARCH_INTENT.search(objective):
            has_results = bool((action_message or "").strip())
            return GoalVerification(
                has_results,
                1.0 if has_results else 0.0,
                "La recherche a retourné du contenu."
                if has_results
                else "La recherche n'a retourné aucun résultat vérifiable.",
                {"capability": action_name, "has_results": has_results},
            )

        return None

    @staticmethod
    def _target_mentioned(objective: str, target: str) -> bool:
        """Require the planned target to be named in the user's goal."""
        objective_tokens = set(re.findall(r"[a-z0-9]+", objective.lower()))
        target_tokens = re.findall(r"[a-z0-9]+", target.lower())
        return bool(target_tokens) and all(token in objective_tokens for token in target_tokens)


__all__ = ["GoalVerifier", "GoalVerification"]
