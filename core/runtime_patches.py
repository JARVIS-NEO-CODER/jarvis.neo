"""Runtime integration patches for the legacy assistant entry point."""
from __future__ import annotations

import os
import subprocess
import types
from pathlib import Path
from typing import Any

from .conversation_ai import ConversationAI
from .data_registry import get_data

CURRENT_GROQ_MODEL = "openai/gpt-oss-20b"
DEPRECATED_GROQ_MODELS = {"llama-3.1-8b-instant", "llama-3.3-70b-versatile"}


def _build_ai_messages(assistant: Any, text: str) -> list[dict[str, str]]:
    memory = assistant.memory
    history = memory.get_history(12)
    relevant = memory.search_memory(text, 5)
    messages: list[dict[str, str]] = [{
        "role": "system",
        "content": (
            "Tu es J.A.R.V.I.S. NEO, l'assistant personnel informatique de ton utilisateur.\n"
            "Réponds en français sauf demande contraire. Sois naturel et bref quand la demande est simple. "
            "Ne prétends jamais avoir effectué une action sans preuve du programme."
        ),
    }]
    if relevant:
        messages.append({
            "role": "system",
            "content": "Mémoire pertinente (peut être incomplète) :\n" + "\n".join(item["content"] for item in relevant),
        })
    messages.extend(history)
    messages.append({"role": "user", "content": text})
    return messages


def _ask_ai(self: Any, text: str) -> str:
    assistant = self._neo_assistant
    engine: ConversationAI = self._neo_conversation_ai
    assistant.state.is_processing = True
    assistant.signals.status_change.emit("RÉFLEXION")
    try:
        result = engine.chat(_build_ai_messages(assistant, text), temperature=0.2, max_tokens=2048)
        assistant.signals.status_change.emit("OPÉRATIONNEL")
        return result
    except Exception as exc:
        assistant.signals.status_change.emit("ERREUR")
        return f"Erreur noyau IA : {exc}"
    finally:
        assistant.state.is_processing = False


def _safe_lock_pc(self: Any) -> str:
    if os.name == "nt":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False, shell=False)
    elif os.name == "posix":
        subprocess.run(["xdg-screensaver", "lock"], check=False, shell=False)
    else:
        return "Verrouillage non pris en charge sur ce système."
    return "Session verrouillée."


def _dynamic_open_folder(self: Any, folder_name: str) -> str:
    aliases = get_data("folder_aliases", {})
    key = str(folder_name).lower().strip()
    target_name = aliases.get(key, folder_name)
    target = Path.home() / str(target_name)
    if target.exists():
        if os.name == "nt":
            os.startfile(str(target))
        elif os.name == "posix":
            subprocess.Popen(["xdg-open", str(target)], shell=False)
        return f"Accès au répertoire {folder_name} accordé."
    return f"Répertoire '{folder_name}' introuvable."


def _normalize_provider_config(assistant: Any) -> None:
    config = assistant.CONFIG
    config.setdefault("ai_provider", "groq")
    config.setdefault("groq_fallback_to_ollama", True)
    config.setdefault("groq_quota_fallback", "ollama")
    config.setdefault("groq_timeout", 60)
    config.setdefault("ollama_enabled", True)
    config.setdefault("ollama_base_url", "http://127.0.0.1:11434")
    model = str(config.get("groq_model", "")).strip()
    if not model or model in DEPRECATED_GROQ_MODELS:
        config["groq_model"] = CURRENT_GROQ_MODEL

    tiers = get_data("model_tiers", {})
    if isinstance(tiers, dict) and tiers:
        assistant.MODEL_TIERS.clear()
        assistant.MODEL_TIERS.update(tiers)
        tier = str(config.get("model_tier", "moyen"))
        if tier not in assistant.MODEL_TIERS and tier != "custom":
            config["model_tier"] = next(iter(assistant.MODEL_TIERS))
    try:
        assistant.save_config(config)
    except Exception:
        pass


def install(assistant: Any) -> ConversationAI:
    """Connect the modern provider router to the legacy desktop processor."""
    _normalize_provider_config(assistant)
    engine = ConversationAI(assistant.CONFIG, getattr(assistant, "ollama", None))
    processor = assistant.processor
    processor._neo_assistant = assistant
    processor._neo_conversation_ai = engine
    processor.ask_ai = types.MethodType(_ask_ai, processor)
    processor.lock_pc = types.MethodType(_safe_lock_pc, processor)
    processor.open_folder = types.MethodType(_dynamic_open_folder, processor)
    assistant._neo_conversation_ai = engine
    return engine


__all__ = ["CURRENT_GROQ_MODEL", "install"]
