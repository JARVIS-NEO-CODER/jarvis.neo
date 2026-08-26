"""Optional memory learning bridge for ContextEngine."""
from __future__ import annotations

from typing import Any


def learn_context(memory: Any, context: str, confidence: float) -> int | None:
    if not context or confidence < 0.5:
        return None
    context = str(context).strip().upper()
    return memory.remember_fact(
        "context", f"last_{context}", context,
        confidence=max(0.0, min(float(confidence), 1.0)),
        source="context_engine",
    )
