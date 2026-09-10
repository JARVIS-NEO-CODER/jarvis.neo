"""Proactive presence engine for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import threading
import time
from typing import Any

import psutil


class PresenceEngine:
    """Low-cost proactive layer that can speak without a user prompt."""

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
        """Submit context. The LLM decides whether an intervention is useful."""
        if not self._enabled:
            return False
        event = str(event or "").strip()
        context = str(context or "").strip()
        if not event:
            return False
        now = time.monotonic()
        with self._lock:
            if not force and now - self._last_spoken < self.COOLDOWN_SECONDS:
                return False
        message = self._generate_message(event, context)
        if not message:
            return False
        with self._lock:
            self._last_spoken = time.monotonic()
            self._last_event = event
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

    def _mode(self) -> str:
        config = self._config()
        return str(config.get("jarvis_mode", config.get("mode", "normal"))).strip().lower()

    def _cloud_allowed(self) -> bool:
        config = self._config()
        modes = config.get("presence_cloud_modes", ["cloud", "agent"])
        if isinstance(modes, str):
            modes = [modes]
        allowed = {str(item).strip().lower() for item in modes}
        return str(config.get("ai_provider", "groq")).strip().lower() == "groq" and self._mode() in allowed

    def _generate_message(self, event: str, context: str) -> str:
        cloud = self._cloud_allowed()
        mode = "cloud" if cloud else "local"
        prompt = (
            "Tu es la présence active de J.A.R.V.I.S. NEO. Tu peux engager la "
            "conversation spontanément, mais seulement si cela apporte quelque "
            "chose à l'utilisateur. Analyse l'événement et le contexte. Si une "
            "intervention n'est pas pertinente, réponds exactement SILENCE. "
            "Sinon, écris une phrase naturelle en français, courte, sans "
            "préambule, sans liste et sans prétendre avoir effectué une action. "
            "Tu peux poser une question simple. "
            f"Événement: {event}\nContexte: {context}\nMode: {mode}"
        )
        try:
            if not cloud:
                from .conversation_ai import OllamaChatProvider
                try:
                    import ollama
                except ImportError:
                    return ""
                config = self._config()
                model = str(config.get("presence_local_model", config.get("model", "llama3.2:3b")))
                provider = OllamaChatProvider(ollama, model, config.get("ollama_base_url", "http://127.0.0.1:11434"))
                text = provider.chat([{"role": "system", "content": prompt}], temperature=0.4, max_tokens=100)
            else:
                conversation = getattr(self.assistant, "conversation_ai", None)
                if conversation is None:
                    from .conversation_ai import ConversationAI
                    conversation = ConversationAI(self._config())
                text = conversation.chat([{"role": "system", "content": prompt}], temperature=0.4, max_tokens=100)
        except Exception as exc:
            self._log(f"PRESENCE: IA {mode} indisponible : {exc}")
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
        except Exception as exc:
            self._log(f"PRESENCE: synthèse vocale indisponible : {exc}")

    def _log(self, message: str) -> None:
        try:
            self.assistant.log.info(message)
        except Exception:
            pass


__all__ = ["PresenceEngine"]
