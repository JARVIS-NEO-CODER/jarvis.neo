"""Connect the modular ConversationAI/router to the legacy CommandProcessor."""
from __future__ import annotations


def install(assistant, processor) -> bool:
    if getattr(processor, "_neo_conversation_bridge", False):
        return True
    try:
        from core.conversation_ai import ConversationAI
    except Exception:
        return False

    config = getattr(assistant, "CONFIG", {})
    engine = ConversationAI(config, getattr(assistant, "ollama", None))
    original = processor.ask_ai

    def ask_ai(text: str) -> str:
        state = getattr(assistant, "state", None)
        signals = getattr(assistant, "signals", None)
        memory = getattr(assistant, "memory", None)
        if state is not None:
            state.is_processing = True
        if signals is not None:
            try: signals.status_change.emit("RÉFLEXION")
            except Exception: pass
        try:
            history = memory.get_history(12) if memory is not None else []
            relevant = memory.search_memory(text, 5) if memory is not None else []
            tier = getattr(state, "current_model_tier", "moyen") if state is not None else "moyen"
            messages = [{"role": "system", "content": (
                "Tu es J.A.R.V.I.S. NEO, assistant personnel informatique intégré au PC. "
                "Réponds en français sauf demande contraire. Sois naturel, concis pour les demandes simples, "
                "et conserve le contexte récent. Ne prétends jamais avoir effectué une action sans preuve. "
                f"Mode IA actuel : {tier}."
            )}]
            if relevant:
                messages.append({"role": "system", "content": "Mémoire pertinente :\n" + "\n".join(x["content"] for x in relevant)})
            messages.extend(history)
            messages.append({"role": "user", "content": text})
            result = engine.chat(messages)
            if state is not None: state.is_processing = False
            if signals is not None:
                try: signals.status_change.emit("OPÉRATIONNEL")
                except Exception: pass
            return result
        except Exception as exc:
            if state is not None: state.is_processing = False
            if signals is not None:
                try: signals.status_change.emit("ERREUR")
                except Exception: pass
            # Preserve the legacy diagnostic if the modular path itself is unavailable.
            fallback = original(text)
            if fallback and not fallback.startswith("Erreur noyau IA"):
                return fallback
            return f"Erreur noyau IA : {exc}"

    processor.ask_ai = ask_ai
    processor._neo_conversation_ai = engine
    processor._neo_conversation_bridge = True
    return True


__all__ = ["install"]
