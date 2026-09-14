from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AgentConfig
from .runtime import JarvisAgentRuntime

_RUNTIME: JarvisAgentRuntime | None = None
_INSTALLED = False


def _cockpit_dispatch(assistant: Any, callback) -> None:
    """Run a cockpit UI callback safely on the Qt GUI thread."""
    try:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, callback)
        return
    except Exception:
        pass
    try:
        callback()
    except Exception:
        pass


def _get_cockpit(assistant: Any):
    if assistant is None:
        return None
    cockpit = getattr(assistant, "_neo_cockpit", None)
    if cockpit is not None:
        return cockpit
    try:
        from ui.cockpit_hud import CockpitHud
        cockpit = CockpitHud(assistant, getattr(assistant, "JarvisWindow", None))
        assistant._neo_cockpit = cockpit
        return cockpit
    except Exception:
        return None


def _show_agent_event(assistant: Any, state: str, task: dict[str, Any]) -> None:
    """Surface autonomous work in the NEO cockpit instead of the legacy chat."""
    def render() -> None:
        cockpit = _get_cockpit(assistant)
        if cockpit is None:
            return
        try:
            if not cockpit.isVisible():
                cockpit.show()
            cockpit.raise_()
            cockpit.activateWindow()
            goal = str(task.get("goal") or "Mission autonome")
            context = task.get("context") or {}
            if state == "completed":
                result = str(context.get("result") or "Mission terminée.")
                try:
                    payload = json.loads(result)
                    if isinstance(payload, dict) and payload.get("kind"):
                        result = f"Résultat {payload.get('kind')} : {payload.get('query') or payload.get('message') or 'opération terminée'}"
                except Exception:
                    pass
                cockpit.show_dynamic_panel("agent-result", "MISSION TERMINÉE", result, "success", "neo-agent")
            elif state == "failed":
                cockpit.show_dynamic_panel("agent-result", "MISSION ÉCHOUÉE", "La mission autonome a échoué. Consultez l'historique de tâche.", "error", "neo-agent")
            elif state == "waiting_approval":
                cockpit.show_dynamic_panel("agent-result", "AUTORISATION REQUISE", "Une action nécessite une autorisation avant de poursuivre.", "warning", "neo-agent")
            else:
                cockpit.show_dynamic_panel("agent-progress", "MISSION AUTONOME", goal, "info", "neo-agent")
        except Exception:
            pass

    _cockpit_dispatch(assistant, render)


def install() -> None:
    global _RUNTIME, _INSTALLED
    if _INSTALLED:
        return
    try:
        from core import assistant_components as components
        original = components.CommandProcessor.ask_ai
    except Exception:
        return
    if getattr(original, "_neo_agent_bridge", False):
        _INSTALLED = True
        return

    original_image_search = getattr(components.CommandProcessor, "image_search", None)

    def on_event(event: str, payload: dict[str, Any]) -> None:
        task = payload.get("task", {})
        state = task.get("state")
        assistant = getattr(components, "_neo_assistant", None)
        if state:
            _show_agent_event(assistant, state, task)
        try:
            if state == "failed":
                components._signals.log_msg.emit("Jarvis", "Mission autonome échouée. Consultez l'historique de tâche.")
            elif state == "waiting_approval":
                components._signals.log_msg.emit("Jarvis", "Autorisation requise pour poursuivre la mission.")
        except Exception:
            pass

    cfg = components._cfg()
    config = AgentConfig(
        permission_mode=max(1, min(3, int(cfg.get("agent_permission_mode", 3)))),
        max_steps=80,
        max_retries_per_step=3,
        cwd=".",
        persist_tasks=True,
        state_dir=str(Path.home() / ".jarvis_neo" / "agent_tasks"),
    )
    model = str(cfg.get("model") or "llama3.2:3b")
    _RUNTIME = JarvisAgentRuntime(config=config, model=model, event=on_event)
    try:
        _RUNTIME.recover()
    except Exception:
        pass

    def ask_ai(self, text: str):
        goal = str(text).strip()
        if not goal:
            return "Directive vide."
        try:
            components._neo_assistant = getattr(self, "_neo_assistant", None)
            task = _RUNTIME.submit(goal, context={"source": "hud", "language": "fr-FR"}, background=True)
            _show_agent_event(components._neo_assistant, "running", task.to_dict())
            return f"Mission autonome lancée. ID : {task.id}"
        except Exception:
            return original(self, text)

    def image_search(self, query: str):
        """Return a media payload without opening the legacy Dynamic Space."""
        query = str(query).strip()
        if not query:
            return "Sujet de recherche d'images manquant."
        return json.dumps({"kind": "image_search", "query": query}, ensure_ascii=False)

    ask_ai._neo_agent_bridge = True
    components.CommandProcessor.ask_ai = ask_ai
    if original_image_search is not None:
        components.CommandProcessor.image_search = image_search
    _INSTALLED = True


try:
    install()
except Exception:
    pass
