"""Safe action execution layer for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import os, platform, subprocess, webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import psutil
from .memory import NeoMemory
from .capability_registry import Capability, CapabilityRegistry
from .web_search import WebSearchProvider

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
    def __init__(self, memory: NeoMemory | None = None, event_bus: Any | None = None, capabilities: CapabilityRegistry | None = None) -> None:
        self.memory = memory or NeoMemory()
        self.mode = ControlMode.NORMAL
        self._full_control_until = None
        self._actions: dict[str, ActionDefinition] = {}
        self._event_bus = event_bus
        self.capabilities = capabilities or CapabilityRegistry()
        self.web_search = WebSearchProvider()
        self._register_safe_actions()

    @property
    def full_control_active(self):
        return self.mode is ControlMode.FULL_CONTROL and self._full_control_until is not None and datetime.now() < self._full_control_until

    def register(self, definition: ActionDefinition) -> None:
        if not definition.name or not callable(definition.handler):
            raise ValueError("Une action valide nécessite un nom et un handler callable.")
        self._actions[definition.name] = definition
        if self.capabilities.get(definition.name) is None:
            self.capabilities.register(Capability(definition.name, definition.description, permission=definition.minimum_mode.value, action=definition.name, verifier="action_result_and_handler_verification"))
        self.capabilities.bind(definition.name, definition.handler)

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

    def disable_full_control(self):
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
            if isinstance(output, tuple) and len(output) == 2 and isinstance(output[0], bool):
                success, message = output
            else:
                success, message = True, str(output) if output is not None else "Action terminée."
            result = ActionResult(action_name, bool(success), str(message), bool(success))
        except Exception as exc:
            result = ActionResult(action_name, False, f"Échec: {exc}")
        self._log_result(result)
        return result

    def attach_to_bus(self, bus): self._event_bus = bus
    def detach_from_bus(self): self._event_bus = None

    def _register_safe_actions(self):
        self.register(ActionDefinition("action.notify", self._notify, description="Publier une notification."))
        self.register(ActionDefinition("action.set_state", self._set_state, description="Mettre à jour un état interne."))
        self.register(ActionDefinition("action.publish_event", self._publish_event, description="Publier un événement interne autorisé."))
        self.register(ActionDefinition("action.show_hud", self._show_hud, description="Afficher une vue HUD."))
        self.register(ActionDefinition("action.open_url", self._open_url, description="Ouvrir une URL HTTP(S) validée."))
        self.register(ActionDefinition("action.search_web", self._search_web, description="Rechercher réellement sur le Web et retourner les résultats."))
        self.register(ActionDefinition("action.open_path", self._open_path, ControlMode.AGENT, "Ouvrir un chemin local existant."))
        self.register(ActionDefinition("action.launch_app", self._launch_app, ControlMode.AGENT, "Lancer une application locale."))
        self.register(ActionDefinition("action.close_app", self._close_app, ControlMode.AGENT, "Fermer une application et vérifier la disparition de ses processus."))
        self.register(ActionDefinition("action.create_directory", self._create_directory, ControlMode.AGENT, "Créer un dossier local."))
        self.register(ActionDefinition("action.write_text_file", self._write_text_file, ControlMode.FULL_CONTROL, "Écrire un fichier texte local."))

    def _require_bus(self):
        if self._event_bus is None: raise RuntimeError("Aucun EventBus n'est attaché à l'ActionEngine.")
        return self._event_bus
    def _notify(self, message="", level="info", **data):
        from .bus import Event
        self._require_bus().publish(Event(name="notification.show", payload={"message": message, "level": level, **data}, priority=10)); return "Notification publiée."
    def _set_state(self, key, value=None, **data):
        from .bus import Event
        self._require_bus().publish(Event(name="state.changed", payload={"key": key, "value": value, **data}, priority=10)); return f"État mis à jour: {key}"
    def _publish_event(self, event_name, payload=None):
        if not event_name or event_name.startswith("security."): raise ValueError("Nom d'événement non autorisé.")
        from .bus import Event
        self._require_bus().publish(Event(name=event_name, payload=payload or {}, priority=10)); return f"Événement publié: {event_name}"
    def _show_hud(self, target="context", **data):
        if target not in {"system_monitor", "media_player", "code_diff", "context", "none"}: raise ValueError(f"HUD target inconnu: {target}")
        if target == "none": return "HUD ignoré."
        from .bus import Event
        self._require_bus().publish(Event(name="hud.show", payload={"target": target, **data}, priority=10)); return f"HUD demandé: {target}"
    @staticmethod
    def _open_url(url):
        url = url.strip()
        if not (url.startswith("https://") or url.startswith("http://")): raise ValueError("Seules les URLs HTTP(S) sont autorisées.")
        if not webbrowser.open(url, new=2): raise RuntimeError("Le navigateur n'a pas accepté l'ouverture de l'URL.")
        return f"URL ouverte: {url}"
    def _search_web(self, query, limit=5):
        results = self.web_search.search(query, limit=limit)
        self.memory.record_event("web", f"Recherche web: {query}", source="action_engine")
        return "\n\n".join(f"{i}. {r.title}\n{r.url}\n{r.snippet}" for i, r in enumerate(results, 1))
    @staticmethod
    def _open_path(path):
        target = Path(path).expanduser().resolve()
        if not target.exists(): raise FileNotFoundError(f"Chemin introuvable: {target}")
        system = platform.system()
        if system == "Windows": os.startfile(str(target))
        elif system == "Darwin": subprocess.Popen(["open", str(target)])
        elif system == "Linux": subprocess.Popen(["xdg-open", str(target)])
        else: raise RuntimeError(f"Système non pris en charge: {system}")
        return f"Chemin ouvert: {target}"
    @staticmethod
    def _launch_app(command, args=None):
        command = command.strip()
        if not command or any(part in command for part in ("&", "|", ";", ">", "<", "`")): raise ValueError("Commande refusée.")
        subprocess.Popen([command] + [str(x) for x in (args or [])], shell=False, start_new_session=True)
        return f"Application lancée: {command}"
    @staticmethod
    def _process_matches(name: str):
        needle = name.strip().lower().removesuffix(".exe")
        return [p for p in psutil.process_iter(["pid", "name"]) if needle in (p.info.get("name") or "").lower()]
    def _close_app(self, name, force=False):
        matches = self._process_matches(name)
        if not matches: return False, f"Aucun processus actif pour '{name}'."
        for process in matches:
            try: process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
        _, alive = psutil.wait_procs(matches, timeout=3)
        if force:
            for process in alive:
                try: process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass
            _, alive = psutil.wait_procs(alive, timeout=2)
        remaining = [p for p in alive if p.is_running()]
        if remaining: return False, f"{len(remaining)} processus liés à '{name}' refusent de se fermer."
        self.memory.record_event("outil", f"Fermeture vérifiée de {len(matches)} processus {name}", source="action_engine")
        return True, f"Fermeture de {len(matches)} processus liés à '{name}', vérifiée."
    def _create_directory(self, path):
        target = Path(path).expanduser().resolve(); target.mkdir(parents=True, exist_ok=True)
        if not target.is_dir(): raise RuntimeError("Le dossier n'a pas pu être vérifié.")
        return f"Dossier prêt et vérifié: {target}"
    @staticmethod
    def _write_text_file(path, content="", encoding="utf-8"):
        target = Path(path).expanduser().resolve(); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding=encoding)
        if target.read_text(encoding=encoding) != content: raise RuntimeError("Vérification d'écriture échouée.")
        return f"Fichier écrit et vérifié: {target}"
    def _log_result(self, result):
        self.memory.record_event("action", f"{result.action}: {'success' if result.success else 'failure'} — {result.message}", source="action_engine")

__all__ = ["ActionEngine", "ActionDefinition", "ActionResult", "ControlMode"]
