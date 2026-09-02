"""Presentation helpers for the active J.A.R.V.I.S. AI provider."""
from __future__ import annotations

from typing import Mapping, Any


def format_ai_status(status: Mapping[str, Any] | None) -> str:
    """Return a compact HUD label from ConversationAI.status."""
    status = status or {}
    active = str(status.get("active_provider") or "").lower()
    if active == "groq":
        return "GROQ"
    if active == "ollama":
        return "OLLAMA"
    if active == "simple":
        return "SIMPLE"
    if status.get("last_error"):
        return "ERROR"
    if status.get("groq_configured"):
        return "GROQ READY"
    if status.get("ollama_available"):
        return "OLLAMA READY"
    return "OFFLINE"


__all__ = ["format_ai_status"]