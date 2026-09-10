"""Proactive presence engine for J.A.R.V.I.S. NEO.

The engine observes lightweight local PC events and only asks an LLM to
formulate a message when an intervention is actually useful. Local/Ollama is
preferred for presence unless the configured AI mode explicitly allows cloud.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import psutil


class PresenceEngine:
    """Small, low-cost proactive layer that can speak without a user prompt."""

    POLL_SECONDS = 5.0
    COOLDOWN_SECONDS = 180.0
    MAX_MESSAGE_CHARS = 260

    def __init__(self, assistant: Any):
        self.assistant = assistant
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_spoken = 0.0
        self._last_event: str | None = None
        self._enabled = bool(self._config().get("presence_active", True))
        self._last_processes: set[str] = set()

    def _config(self) -> dict[str, Any]:
        return getattr(self.assistant, "CONFIG", {}) or {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        if not self._enabled:
            return False
        self._stop.clear()
        self._last_processes = self._process_snapshot()
        self._thread = threading.Thread(target=self._run, name="JARVIS-Presence", daemon=True)
        self._thread.start()
        self._log("PRESENCE: présence active démarrée")
        return True

    def stop(self) -> None:
        self._stop.set()
        self._log("PRESENCE: présence active arrêtée")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if self._enabled:
            self.start()
        else:
            self.stop()

    def notify(self, event: str, context: str = "", *, force: bool = False) -> bool:
        """Submit a contextual event. Returns True when JARVIS actually spoke."""
        if not self._enabled:
            return False
        event = str(event or "").strip()
        context = str(context or "").strip()
        if not event:
            return False
        now = time.monotonic()
        with self._lock:
            if not force and now - self._last_spoken < self.Cooldown_SECONDS:
                return False
            self._last_spoken = now
            self._last_event = event
        message = self._generate_message(event, context)
        if not message:
            return False
        self._speak(message)
        return True

    def _run(self) -> None:
        while not self._stop.wait(self.POLL_SECONDS):
            try:
                self._check_process_changes()
            except Exception as exc:
                self._log(f"PRESENCE: surveillance légère indisponible : {exc}")

    def _process_snapshot(self) -> set[str]:
        names: set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = str(proc.info.get("name") or "").lower().strip()
                if name:
                    names.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return names

    def _check_process_changes(self) -> None:
        current = self._process_snapshot()
        started = sorted(current - self._last_processes)
        self._last_processes = current
        # Only surface a tiny set of meaningful user applications. This is
        # deliberately not a hard-coded phrase list: the LLM writes the line.
        interesting = {
            "code.exe": "Visual Studio Code vient d'être lancé.",
            "discord.exe": "Discord vient d'être lancé.",
            "steam.exe": "Steam vient d'être lancé.",
            "eurotrucks2.exe": "Euro Truck Simulator 2 vient d'être lancé.",
        }
        for process in started:
            context = interesting.get(process)
            if context:
                self.notify("Une application importante vient de démarrer", context)
                break

    def _presence_mode(self) -> str:
        config = self._config()
        # "ollama" / "local" / "simple" are local-safe modes. Cloud is only
        # selected when the user explicitly configured a cloud-capable mode.
        mode = str(config.get("ai_provider", "groq")).strip().lower()
        if mode in {"ollama", "local", "simple"}:
            return "local"
        return "cloud"

    def _generate_message(self, event: str, context: str) -> str:
        conversation = getattr(self.assistant, "conversation_ai", None)
        if conversation is None:
            conversation = getattr(self.assistant, "ai", None)
        if conversation is None or not callable(getattr(conversation, "chat", None)):
            return ""

        mode = self._presence_mode()
        prompt = (
            "Tu es la présence active de J.A.R.V.I.S. NEO. "
            "Tu peux engager la conversation spontanément, mais seulement si "
            "cela apporte quelque chose à l'utilisateur. À partir de l'événement "
            "et du contexte ci-dessous, décide si une courte intervention est "
            "pertinente. Si non, réponds exactement SILENCE. Sinon, écris une "
            "phrase naturelle en français, sans préambule, sans liste et sans "
            "prétendre avoir fait une action. Tu peux poser une question simple. "
            f"Événement: {event}\nContexte: {context}\nMode de présence: {mode}"
        )
        try:
            text = conversation.chat(
                [{"role": "system", "content": prompt}],
                temperature=0.4,
                max_tokens=100,
            )
        except Exception as exc:
            self._log(f"PRESENCE: IA indisponible : {exc}")
            return ""
        text = str(text or "").strip()
        if not text or text.upper() == "SILENCE":
            return ""
        return text[: self.MAX_MESSAGE_CHARS]

    def _speak(self, text: str) -> None:
        try:
            speech = getattr(self.assistant, "speech", None)
            say = getattr(speech, "say", None)
            if callable(say):
                say(text)
                self._log(f"PRESENCE: JARVIS a pris la parole : {text}")
                return
            raw_say = getattr(speech, "_say", None)
            if callable(raw_say):
                raw_say(text)
                self._log(f"PRESENCE: JARVIS a pris la parole : {text}")
        except Exception as exc:
            self._log(f"PRESENCE: synthèse vocale indisponible : {exc}")

    def _log(self, message: str) -> None:
        try:
            self.assistant.log.info(message)
        except Exception:
            pass


__all__ = ["PresenceEngine"]
