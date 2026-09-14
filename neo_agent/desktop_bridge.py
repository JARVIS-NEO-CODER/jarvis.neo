from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AgentConfig
from .runtime import JarvisAgentRuntime

_RUNTIME: JarvisAgentRuntime | None = None
_INSTALLED = False


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
        context = task.get("context") or {}
        try:
            if state == "completed":
                components._signals.log_msg.emit("Jarvis", str(context.get("result") or "Mission terminée."))
            elif state == "failed":
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

    def ask_ai(self, text: str):
        goal = str(text).strip()
        if not goal:
            return "Directive vide."
        try:
            task = _RUNTIME.submit(goal, context={"source": "hud", "language": "fr-FR"}, background=True)
            return f"Mission autonome lancée. ID : {task.id}"
        except Exception:
            return original(self, text)

    def image_search(self, query: str):
        """Return a media payload so Dynamic Space performs the real search.

        The legacy implementation launched Google and discarded its results.
        Dynamic Space already knows how to render the structured payload, so
        the command now becomes a real result-producing operation.
        """
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
