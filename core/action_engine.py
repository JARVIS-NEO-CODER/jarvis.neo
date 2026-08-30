"""Safe action execution layer for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .memory import NeoMemory


class ControlMode(str, Enum):
    NORMAL = "normal"
    AGENT = "agent"
    FULL_CONTROL = "full_control"


@dataclass(frozen=True)
class ActionResult:
    action: str
    success: bool
    message: str
    verified: bool = False


@dataclass
class ActionDefinition:
    name: str
    handler: Callable[..., Any]
    minimum_mode: ControlMode = ControlMode.NORMAL
    description: str = ""


class ActionEngine:
    """Execute only registered, permission-gated and verifiable actions."""

    def __init__(self, memory: NeoMemory | None = None, event_bus: Any | None = None) -> None:
        self.memory = memory or NeoMemory()
        self.mode = ControlMode.NORMAL
        self._full_control_until: datetime | None = None
        self._actions: dict[str, ActionDefinition] = {}
        self._event_bus = event_bus
        self._register_safe_actions()

    @property
    def full_control_active(self) -> bool:
        return self.mode is ControlMode.FULL_CONTROL and self._full_control_until is not None and datetime.now() < self._full_control_until

    def register(self, definition: ActionDefinition) -> None:
        if not definition.name or not callable(definition.handler):
            raise ValueError("Une action valide nécessite un nom et un handler callable.")
        self._actions[definition.name] = definition

    def set_mode(self, mode: ControlMode) -> None:
        if mode is ControlMode.FULL_CONTROL:
            raise PermissionError("FULL_CONTROL requires explicit enable_full_control() confirmation.")
        self.mode = mode
        self._full_control_until = None

    def enable_full_control(self, *, duration_minutes: int = 30) -> None:
        duration_minutes = max(1, min(int(duration_minutes), 120))
        self.mode = ControlMode.FULL_CONTROL
        self._full_control_until = datetime.now() + timedelta(minutes=duration_minutes)
        self.memory.record_event("security", f"FULL_CONTROL enabled for {duration_minutes} minutes", source="action_engine")

    def disable_full_control(self) -> None:
        self.mode = ControlMode.NORMAL
        self._full_control_until = None
        self.memory.record_event("security", "FULL_CONTROL disabled", source="action_engine")

    def execute(self, action_name: str, **kwargs: Any) -> ActionResult:
        definition = self._actions.get(action_name)
        if definition is None:
            result = ActionResult(action_name, False, "Action inconnue.")
            self._log_result(result)
            return result
        if definition.minimum_mode is ControlMode.AGENT and self.mode is ControlMode.NORMAL:
            result = ActionResult(action_name, False, "Cette action nécessite le mode AGENT.")
            self._log_result(result)
            return result
        if definition.minimum_mode is ControlMode.FULL_CONTROL and not self.full_control_active:
            result = ActionResult(action_name, False, "Cette action nécessite le mode FULL_CONTROL.")
            self._log_result(result)
            return result
        try:
            output = definition.handler(**kwargs)
            result = ActionResult(action_name, True, str(output) if output is not None else "Action terminée.", verified=True)
        except Exception as exc:
            result = ActionResult(action_name, False, f"Échec: {exc}")
        self._log_result(result)
        return result

    def attach_to_bus(self, bus: Any) -> None:
        self._event_bus = bus

    def detach_from_bus(self) -> None:
        self._event_bus = None

    def _register_safe_actions(self) -> None:
        self.register(ActionDefinition("action.notify", self._notify, ControlMode.NORMAL, "Publish a safe notification."))
        self.register(ActionDefinition("action.set_state", self._set_state, ControlMode.NORMAL, "Publish a safe internal state update."))
        self.register(ActionDefinition("action.publish_event", self._publish_event, ControlMode.NORMAL, "Publish an explicitly named bus event."))
        self.register(ActionDefinition("action.show_hud", self._show_hud, ControlMode.NORMAL, "Request a HUD view."))
        self.register(ActionDefinition("action.open_url", self._open_url, ControlMode.NORMAL, "Open a validated HTTP(S) URL in the default browser."))
        self.register(ActionDefinition("action.open_path", self._open_path, ControlMode.AGENT, "Open an existing local file or directory."))
        self.register(ActionDefinition("action.launch_app", self._launch_app, ControlMode.AGENT, "Launch an explicitly named local application."))
        self.register(ActionDefinition("action.create_directory", self._create_directory, ControlMode.AGENT, "Create a local directory."))
        self.register(ActionDefinition("action.write_text_file", self._write_text_file, ControlMode.FULL_CONTROL, "Write UTF-8 text to a local file."))

    def _require_bus(self) -> Any:
        if self._event_bus is None:
            raise RuntimeError("Aucun EventBus n'est attaché à l'ActionEngine.")
        return self._event_bus

    def _notify(self, message: str = "", level: str = "info", **data: Any) -> str:
        bus = self._require_bus()
        from .bus import Event
        bus.publish(Event(name="notification.show", payload={"message": message, "level": level, **data}, priority=10))
        return "Notification publiée."

    def _set_state(self, key: str, value: Any = None, **data: Any) -> str:
        bus = self._require_bus()
        from .bus import Event
        bus.publish(Event(name="state.changed", payload={"key": key, "value": value, **data}, priority=10))
        return f"État mis à jour: {key}"

    def _publish_event(self, event_name: str, payload: dict[str, Any] | None = None) -> str:
        if not event_name or event_name.startswith("security."):
            raise ValueError("Nom d'événement non autorisé.")
        bus = self._require_bus()
        from .bus import Event
        bus.publish(Event(name=event_name, payload=payload or {}, priority=10))
        return f"Événement publié: {event_name}"

    def _show_hud(self, target: str = "context", **data: Any) -> str:
        allowed_targets = {"system_monitor", "media_player", "code_diff", "context", "none"}
        if target not in allowed_targets:
            raise ValueError(f"HUD target inconnu: {target}")
        if target == "none":
            return "HUD ignoré."
        bus = self._require_bus()
        from .bus import Event
        bus.publish(Event(name="hud.show", payload={"target": target, **data}, priority=10))
        return f"HUD demandé: {target}"

    @staticmethod
    def _open_url(url: str) -> str:
        url = url.strip()
        if not (url.startswith("https://") or url.startswith("http://")):
            raise ValueError("Seules les URLs HTTP(S) sont autorisées.")
        if not webbrowser.open(url, new=2):
            raise RuntimeError("Le navigateur n'a pas accepté l'ouverture de l'URL.")
        return f"URL ouverte: {url}"

    @staticmethod
    def _open_path(path: str) -> str:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"Chemin introuvable: {target}")
        system = platform.system()
        if system == "Windows":
            os.startfile(str(target))
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])
        elif system == "Linux":
            subprocess.Popen(["xdg-open", str(target)])
        else:
            raise RuntimeError(f"Système non pris en charge: {system}")
        return f"Chemin ouvert: {target}"

    @staticmethod
    def _launch_app(command: str, args: list[str] | None = None) -> str:
        command = command.strip()
        if not command:
            raise ValueError("Le nom de l'application est obligatoire.")
        if any(part in command for part in ("&", "|", ";", ">", "<", "`")):
            raise ValueError("Commande refusée: caractères shell détectés.")
        argv = [command] + [str(x) for x in (args or [])]
        subprocess.Popen(argv, shell=False, start_new_session=True)
        return f"Application lancée: {command}"

    @staticmethod
    def _create_directory(path: str) -> str:
        target = Path(path).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        if not target.is_dir():
            raise RuntimeError("Le chemin créé n'est pas un dossier.")
        return f"Dossier prêt: {target}"

    @staticmethod
    def _write_text_file(path: str, content: str = "", encoding: str = "utf-8") -> str:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        if target.read_text(encoding=encoding) != content:
            raise RuntimeError("Vérification d'écriture échouée.")
        return f"Fichier écrit et vérifié: {target}"

    def _log_result(self, result: ActionResult) -> None:
        self.memory.record_event("action", f"{result.action}: {'success' if result.success else 'failure'} — {result.message}", source="action_engine")


__all__ = ["ActionEngine", "ActionDefinition", "ActionResult", "ControlMode"]
