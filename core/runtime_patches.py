"""Runtime integration patches for the legacy assistant entry point."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import types
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from .conversation_ai import ConversationAI
from .data_registry import get_data

CURRENT_GROQ_MODEL = "openai/gpt-oss-20b"
DEPRECATED_GROQ_MODELS = {"llama-3.1-8b-instant", "llama-3.3-70b-versatile"}
_MEDIA_PAYLOAD = re.compile(r"\{\s*[\"'](?:id|kind|query)[\"'][^{}]{0,2000}\}", re.S)
_IMAGE_COMMAND = re.compile(
    r"^(?:cherche|recherche|trouve|montre)\s+(?:moi\s+)?(?:des?\s+)?(?:images?|photos?)\s+(?:de|sur|pour)\s+(.+)$",
    re.I,
)


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


def _extract_media_payloads(text: str):
    """Récupère les commandes média avant qu'elles soient nettoyées pour le chat."""
    for raw in re.findall(r"\{[^{}]*\}", str(text or ""), re.S):
        try:
            data = json.loads(raw)
        except Exception:
            continue
        kind = str(data.get("kind") or "").lower().strip()
        query = str(data.get("query") or "").strip()
        if kind in {"image_search", "video_search"} and query:
            yield kind, query


def _dispatch_media_search(assistant: Any, text: str) -> None:
    """Exécute réellement une recherche média sans bloquer la boucle Qt."""
    payloads = list(_extract_media_payloads(text))
    if not payloads:
        return

    dynamic_space = getattr(assistant, "dynamic_space", None)
    if dynamic_space is None:
        return

    def worker() -> None:
        try:
            from .web_media import WebMediaProvider
            provider = WebMediaProvider()
            kind, query = payloads[0]
            if kind == "image_search":
                results = [item.as_dict() for item in provider.search_images(query, limit=8)]
            else:
                results = [item.as_dict() for item in provider.search_videos(query, limit=6)]
        except Exception:
            return

        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(
                0,
                lambda: dynamic_space.update_media_search(kind, results, query)
                if results and getattr(assistant, "dynamic_space", None) is dynamic_space
                else None,
            )
        except Exception:
            return

    threading.Thread(target=worker, daemon=True, name="jarvis-media-search").start()


def _handle_direct_image_search(processor: Any, text: str) -> str | None:
    """Intercept explicit image/photo commands before the generic `cherche` intent."""
    match = _IMAGE_COMMAND.match(str(text or "").strip())
    if not match:
        return None

    query = match.group(1).strip()
    if not query:
        return "Il me faut un sujet pour la recherche d'images."

    # This is intentionally handled before CommandProcessor's generic
    # `cherche (.+) -> web_search` rule. That rule was sending image requests
    # to ordinary Google Search and therefore bypassing the media pipeline.
    url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch&hl=fr&safe=active"
    try:
        processor._neo_assistant.signals.open_url.emit(url)
    except Exception:
        return "Impossible d'ouvrir Google Images."

    assistant = getattr(processor, "_neo_assistant", None)
    dynamic_space = getattr(assistant, "dynamic_space", None) if assistant else None
    if dynamic_space is not None:
        def worker() -> None:
            try:
                from .web_media import WebMediaProvider
                results = [item.as_dict() for item in WebMediaProvider().search_images(query, limit=8)]
            except Exception:
                return
            try:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(
                    0,
                    lambda: dynamic_space.update_media_search("image_search", results, query)
                    if results and getattr(assistant, "dynamic_space", None) is dynamic_space
                    else None,
                )
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True, name="jarvis-direct-image-search").start()

    return f"Recherche d'images lancée pour « {query} »."


def _patch_command_router(processor: Any) -> None:
    """Put media routing in front of CommandProcessor.process()."""
    if getattr(processor, "_neo_image_router_installed", False):
        return
    original_process = processor.process

    def routed_process(self: Any, text: str):
        direct_result = _handle_direct_image_search(self, text)
        if direct_result is not None:
            return direct_result
        return original_process(text)

    processor.process = types.MethodType(routed_process, processor)
    processor._neo_image_router_installed = True


def _clean_media_response(text: str) -> str:
    """Keep internal media JSON/control payloads out of the visible chat."""
    raw = str(text or "").strip()
    if not raw:
        return raw
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and str(data.get("kind", "")).lower() in {"image_search", "video_search"}:
            query = str(data.get("query") or "").strip()
            if query:
                return f"Recherche d'images lancée pour « {query} »."
    except Exception:
        pass

    match = _MEDIA_PAYLOAD.search(raw)
    if match:
        try:
            data = json.loads(match.group(0).replace("'", '"'))
            if isinstance(data, dict) and str(data.get("kind", "")).lower() in {"image_search", "video_search"}:
                query = str(data.get("query") or "").strip()
                cleaned = _MEDIA_PAYLOAD.sub("", raw).strip()
                if cleaned and query:
                    return cleaned
                if query:
                    return f"Recherche d'images lancée pour « {query} »."
        except Exception:
            pass
    return raw


def _ask_ai(self: Any, text: str) -> str:
    assistant = self._neo_assistant
    engine: ConversationAI = self._neo_conversation_ai
    assistant.state.is_processing = True
    assistant.signals.status_change.emit("RÉFLEXION")
    try:
        result = engine.chat(_build_ai_messages(assistant, text), temperature=0.2, max_tokens=2048)
        _dispatch_media_search(assistant, result)
        assistant.signals.status_change.emit("OPÉRATIONNEL")
        return _clean_media_response(result)
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
    _patch_command_router(processor)
    processor.ask_ai = types.MethodType(_ask_ai, processor)
    processor.lock_pc = types.MethodType(_safe_lock_pc, processor)
    processor.open_folder = types.MethodType(_dynamic_open_folder, processor)
    assistant._neo_conversation_ai = engine
    return engine


__all__ = ["CURRENT_GROQ_MODEL", "install"]