"""J.A.R.V.I.S. NEO runtime compatibility and agent bridge.

This hook keeps the legacy desktop runtime connected to the modular AI stack
without requiring a second launcher. Vision remains local to Ollama.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path


def _load_config() -> dict:
    path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _install_ollama_groq_bridge() -> None:
    try:
        import ollama
        from core.groq_provider import GroqProvider
    except Exception:
        return
    client_cls = getattr(ollama, "Client", None)
    if client_cls is None or getattr(client_cls, "_jarvis_groq_bridge", False):
        return
    original_chat = getattr(client_cls, "chat", None)
    if original_chat is None:
        return

    def chat(self, model=None, messages=None, **kwargs):
        config = _load_config()
        api_key = str(config.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")).strip()
        use_groq = str(config.get("ai_provider", "groq")).lower() == "groq" and bool(api_key)
        has_images = any(isinstance(m, dict) and m.get("images") for m in (messages or []))
        if not use_groq or has_images:
            return original_chat(self, model=model, messages=messages, **kwargs)
        options = kwargs.get("options") or {}
        temperature = options.get("temperature", kwargs.get("temperature", 0.2))
        max_tokens = options.get("num_predict", kwargs.get("max_tokens", 2048))
        try:
            content = GroqProvider(
                api_key=api_key,
                model=str(config.get("groq_model", "llama-3.1-8b-instant")),
                timeout=float(config.get("groq_timeout", 60)),
            ).chat(messages or [], temperature=temperature, max_tokens=max_tokens)
            return {"message": {"role": "assistant", "content": content}}
        except Exception:
            if bool(config.get("groq_fallback_to_ollama", True)):
                return original_chat(self, model=model, messages=messages, **kwargs)
            raise

    client_cls.chat = chat
    client_cls._jarvis_groq_bridge = True


def _install_agent_bridge() -> bool:
    """Attach the modular AgentEngine to the legacy CommandProcessor at runtime."""
    try:
        assistant = sys.modules.get("assistant")
        if assistant is None:
            return False
        processor = getattr(assistant, "processor", None)
        if processor is None or getattr(processor, "_neo_agent_bridge", False):
            return processor is not None
        from core.action_engine import ActionEngine, ControlMode
        from core.agent_engine import AgentEngine
        from core.conversation_session import ConversationSession
        from core.goal_planner import GoalPlanner
        from core.groq_planner import GroqPlanner
        from core.neo_capabilities import capability_summary
        from core.voice_session_bridge import install as install_voice_session_bridge
    except Exception:
        return False

    config = getattr(assistant, "CONFIG", {})
    api_key = str(config.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")).strip()
    planner = None
    if api_key:
        planner = GroqPlanner(
            api_key=api_key,
            model=str(config.get("groq_model", "llama-3.1-8b-instant")),
            timeout=float(config.get("groq_timeout", 60)),
        )
    else:
        try:
            from core.ollama_planner import OllamaPlanner
            planner = OllamaPlanner(model=str(config.get("model", "llama3.2:3b")), timeout=45)
        except Exception:
            pass

    action_engine = ActionEngine()
    agent = AgentEngine(
        action_engine,
        planner=GoalPlanner(action_engine, planner),
        max_retries=int(config.get("agent_max_retries", 2)),
        max_steps=int(config.get("agent_max_steps", 15)),
        max_ia_calls=int(config.get("agent_max_ia_calls", 30)),
    )
    session = ConversationSession(timeout_seconds=float(config.get("conversation_timeout_seconds", 12)))
    original_process = processor.process
    original_kill = getattr(processor, "kill_app", None)
    original_search = getattr(processor, "web_search", None)

    def _log(category: str, message: str) -> None:
        try:
            if hasattr(assistant, "signals"):
                assistant.signals.log_msg.emit(category, message)
        except Exception:
            pass

    def run_agent(objective: str):
        objective = objective.strip()
        if not objective:
            return "Donne-moi l'objectif à accomplir."
        action_engine.set_mode(ControlMode.AGENT)
        budget = agent.estimate_budget(objective)
        warning = (
            "⚠️ Mode Agent : cette tâche peut utiliser plusieurs appels IA et consommer "
            f"davantage de tokens/crédits. Estimation : {budget['estimated_ia_calls']} appels, "
            f"risque {budget['risk']}."
        )
        try:
            _log("Agent", warning)
            result = agent.run(objective, budget_confirm=lambda _b: True)
            if result.success:
                reason = result.verification.reason if result.verification else "Tâche terminée."
                return f"{reason} (vérifiée, {result.ia_calls} appels IA)."
            return f"Je n'ai pas validé la tâche : {result.error or 'échec non précisé'}."
        finally:
            action_engine.set_mode(ControlMode.NORMAL)

    def web_search(query):
        try:
            from core.web_search import WebSearchProvider
            results = WebSearchProvider().search(query, limit=5)
            _log("Web", f"Recherche réelle : {query} ({len(results)} résultats)")
            if hasattr(assistant, "signals"):
                assistant.signals.open_url.emit(results[0].url)
            return "Résultats web : " + " | ".join(
                f"{r.title} — {r.snippet or r.url}" for r in results
            )
        except Exception as exc:
            return original_search(query) if original_search else f"Recherche web indisponible : {exc}"

    def kill_app(name1, name2=None):
        name = name1 if name1 else name2
        if not name:
            return "Nom de programme invalide."
        try:
            action_engine.set_mode(ControlMode.AGENT)
            result = action_engine.execute("action.close_app", name=name)
            return result.message
        except Exception:
            return original_kill(name1, name2) if original_kill else "Impossible de fermer le programme."
        finally:
            action_engine.set_mode(ControlMode.NORMAL)

    def process(text):
        normalized = text.strip()
        low = normalized.lower()
        if not normalized:
            return ""
        if low in {"mode agent", "active le mode agent", "active mode agent"}:
            processor._neo_agent_mode = True
            session.start()
            return "Mode Agent activé. Je vérifierai les tâches avant de les déclarer terminées."
        if low in {"mode normal", "mode conversation", "désactive le mode agent", "désactive mode agent"}:
            processor._neo_agent_mode = False
            session.active = False
            return "Mode Agent désactivé."
        if low in {"capacités", "capacites", "que peux-tu faire", "qu'est-ce que tu peux faire", "quels sont tes outils"}:
            try:
                return capability_summary(action_engine.capabilities)
            except Exception:
                return "Je peux contrôler les fonctions actuellement enregistrées dans mon registre de capacités."
        if low.startswith("agent "):
            session.touch()
            return run_agent(normalized[6:].strip())
        if getattr(processor, "_neo_agent_mode", False):
            session.touch()
            return run_agent(normalized)
        if session.accepts_followup():
            session.touch()
        return original_process(text)

    processor._neo_agent_mode = False
    processor._neo_agent_session = session
    processor._neo_action_engine = action_engine
    processor._neo_agent = agent
    processor.run_agent = run_agent
    processor.process = process
    processor.web_search = web_search
    processor.kill_app = kill_app
    processor._neo_agent_bridge = True
    try:
        install_voice_session_bridge(assistant, session)
    except Exception as exc:
        _log("Voice", f"Session vocale non installée : {exc}")
    _log("NEO", "Pont Agent/Web/Session chargé.")
    return True


def _bootstrap_runtime() -> None:
    _install_ollama_groq_bridge()
    for _ in range(120):
        if _install_agent_bridge():
            return
        time.sleep(0.05)


_install_ollama_groq_bridge()
threading.Thread(target=_bootstrap_runtime, name="jarvis-runtime-bridge", daemon=True).start()
