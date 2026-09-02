"""Objective-level verification for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
from .system_observer import SystemSnapshot

@dataclass(frozen=True)
class GoalVerification:
    achieved: bool
    confidence: float
    reason: str
    evidence: dict[str, Any]

class GoalVerifier:
    """Verify objectives using action results plus observable system evidence."""
    def verify(self, objective: str, *, before: SystemSnapshot | None, after: SystemSnapshot | None, action_success: bool, action_verified: bool) -> GoalVerification:
        text = objective.strip().lower()
        if not text:
            return GoalVerification(False, 0.0, "Objectif vide.", {})
        if not action_success or not action_verified:
            return GoalVerification(False, 0.0, "La dernière action n'a pas été vérifiée.", {"action_success": action_success, "action_verified": action_verified})

        close = re.search(r"(?:ferme|fermer|quitte|quitter|arrête|arrêter)\s+(?:le|la|les|l')?\s*(.+)", text)
        if close and after is not None:
            target = close.group(1).strip().strip(".!?")
            proc = (after.active_process or "").lower()
            window = (after.active_window or "").lower()
            tokens = [t for t in re.findall(r"[a-z0-9]+", target) if len(t) > 2]
            still_present = target in proc or target in window or (bool(tokens) and all(t in proc or t in window for t in tokens))
            return GoalVerification(not still_present, 1.0 if not still_present else 0.0, "Le programme n'est plus détecté." if not still_present else "Le programme demandé est encore détecté.", {"target": target, "active_process": after.active_process, "active_window": after.active_window})

        match = re.search(r"(?:lance|lancer|ouvre|ouvrir|démarre|démarrer)\s+(.+)", text)
        if match and after is not None:
            target = match.group(1).strip().strip(".!?")
            process = (after.active_process or "").lower()
            window = (after.active_window or "").lower()
            tokens = [t for t in re.findall(r"[a-z0-9]+", target) if len(t) > 2]
            matched = target in process or target in window or (bool(tokens) and all(t in process or t in window for t in tokens))
            return GoalVerification(matched, 1.0 if matched else 0.15, "Le programme demandé est détecté." if matched else "Le programme demandé n'est pas détecté.", {"target": target, "active_process": after.active_process, "active_window": after.active_window})

        if before is not None and after is not None:
            changed = (before.active_window, before.active_process) != (after.active_window, after.active_process)
            return GoalVerification(True, 0.7, "L'action a réussi et l'état observé a changé." if changed else "L'action a réussi; aucun changement observable n'est requis.", {"foreground_changed": changed, "active_process": after.active_process, "active_window": after.active_window})
        return GoalVerification(True, 0.5, "L'action a été exécutée et vérifiée; aucune preuve système supplémentaire n'est disponible.", {})

__all__ = ["GoalVerifier", "GoalVerification"]
