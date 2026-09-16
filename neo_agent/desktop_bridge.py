from __future__ import annotations

import json
import threading
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
        parent = assistant if hasattr(assistant, "winId") else None
        cockpit = CockpitHud(assistant, parent)
        assistant._neo_cockpit = cockpit
        return cockpit
    except Exception:
        return None


def _show_agent_event(assistant: Any, state: str, task: dict[str, Any]) -> None:
    """Surface autonomous work in the NEO cockpit instead of legacy chat."""
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
                    if isinstance(payload, dict):
                        kind = str(payload.get("kind") or "").lower()
                        if kind == "image_search":
                            result = f"Recherche d'images terminée : {payload.get('query') or goal}"
                        elif payload.get("kind"):
                            result = f"Résultat {payload.get('kind')} : {payload.get('query') or payload.get('message') or 'opération terminée'}"
                except Exception:
                    pass
                cockpit.show_dynamic_panel("agent-result", "MISSION TERMINÉE", result, "success", "neo-agent")
            elif state == "failed":
                error = str(context.get("last_error") or "La mission autonome a échoué.")
                cockpit.show_dynamic_panel("agent-result", "MISSION ÉCHOUÉE", error, "error", "neo-agent")
            elif state == "waiting_approval":
                message = str(context.get("waiting_message") or "Une action nécessite une autorisation avant de poursuivre.")
                cockpit.show_dynamic_panel("agent-approval", "AUTORISATION REQUISE", message, "warning", "neo-agent")
            else:
                cockpit.show_dynamic_panel("agent-progress", "MISSION AUTONOME", goal, "info", "neo-agent")
        except Exception:
            pass

    _cockpit_dispatch(assistant, render)


def _show_image_results(assistant: Any, query: str) -> None:
    """Fetch image results off the GUI thread and display them in the cockpit."""
    def worker() -> None:
        try:
            from core.web_media import WebMediaProvider
            results = WebMediaProvider().search_images(query, limit=8)
        except Exception as exc:
            _cockpit_dispatch(assistant, lambda: _show_agent_event(assistant, "failed", {"goal": query, "context": {"last_error": str(exc)}}))
            return

        def render() -> None:
            cockpit = _get_cockpit(assistant)
            if cockpit is None:
                return
            cockpit.show()
            cockpit.raise_()
            cockpit.activateWindow()
            if not results:
                cockpit.show_dynamic_panel("image-search", "RECHERCHE D'IMAGES", f"Aucun résultat pour « {query} ».", "warning", "neo-agent")
                return
            for index, item in enumerate(results[:8]):
                cockpit.show_dynamic_panel(
                    f"image-search-{index}",
                    item.title or query,
                    "",
                    "image",
                    item.url,
                )

        _cockpit_dispatch(assistant, render)

    threading.Thread(target=worker, daemon=True, name="jarvis-image-search").start()


def _bind_active_window(components) -> None:
    """Keep the real Qt window available to background agent callbacks."""
    window_cls = getattr(components, "JarvisWindow", None)
    if window_cls is None or getattr(window_cls, "_neo_agent_window_bound", False):
        return
    original_init = window_cls.__init__

    def init_with_agent_reference(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._neo_assistant = self
        components._neo_assistant = self

    window_cls.__init__ = init_with_agent_reference
    window_cls._neo_agent_window_bound = True


def install() -> None:
    global _RUNTIME, _INSTALLED
    if _INSTALLED:
        return
    try:
        from core import assistant_components as components
        original = components.CommandProcessor.ask_ai
    except Exception:
        return

    _bind_active_window(components)

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

    cfg = components._cfg()
    try:
        permission_mode = max(1, min(3, int(cfg.get("agent_permission_mode", 3))))
    except (TypeError, ValueError):
        permission_mode = 3
    try:
        max_steps = max(1, min(500, int(cfg.get("agent_max_steps", 80))))
    except (TypeError, ValueError):
        max_steps = 80
    config = AgentConfig(
        permission_mode=permission_mode,
        max_steps=max_steps,
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
            assistant = getattr(self, "_neo_assistant", None) or getattr(components, "_neo_assistant", None)
            components._neo_assistant = assistant
            task = _RUNTIME.submit(goal, context={"source": "hud", "language": "fr-FR"}, background=True)
            _show_agent_event(assistant, "running", task.to_dict())
            return f"Mission autonome lancée. ID : {task.id}"
        except Exception:
            return original(self, text)

    def image_search(self, query: str):
        query = str(query).strip()
        if not query:
            return "Sujet de recherche d'images manquant."
        assistant = getattr(self, "_neo_assistant", None) or getattr(components, "_neo_assistant", None)
        if assistant is not None:
            _show_image_results(assistant, query)
            return f"Recherche d'images lancée pour « {query} »."
        return original_image_search(self, query) if original_image_search else "Recherche d'images indisponible."

    ask_ai._neo_agent_bridge = True
    components.CommandProcessor.ask_ai = ask_ai
    if original_image_search is not None:
        components.CommandProcessor.image_search = image_search
    _INSTALLED = True


try:
    install()
except Exception:
    pass
