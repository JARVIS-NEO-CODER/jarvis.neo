"""Memory-assisted context learning helpers for J.A.R.V.I.S. NEO."""
from __future__ import annotations

from typing import Any


def learn_context(memory: Any, context: str, confidence: float, source: str = "context_engine") -> int | None:
    """Persist a context observation as a durable fact when confidence is useful."""
    if not context or confidence < 0.5:
        return None
    return memory.remember_fact(
        "context",
        f"last_{context.strip().upper()}",
        context.strip().upper(),
        confidence=max(0.0, min(float(confidence), 1.0)),
        source=source,
    )


def learned_contexts(memory: Any, min_confidence: float = 0.5) -> list[dict[str, Any]]:
    """Return learned context facts ordered by the memory layer."""
    return memory.get_facts(category="context", min_confidence=min_confidence)


def learn_signal(memory: Any, context: str, signal: str, confidence: float = 1.0) -> int | None:
    """Persist a neutral signal-to-context association."""
    context = str(context).strip().upper()
    signal = str(signal).strip().lower()
    if not context or not signal or confidence < 0.5:
        return None
    return memory.remember_fact(
        "context_signal",
        f"{context}:{signal}",
        {"context": context, "signal": signal},
        confidence=max(0.0, min(float(confidence), 1.0)),
        source="context_learning",
    )


def learned_signals(memory: Any, context: str | None = None, min_confidence: float = 0.5) -> list[dict[str, Any]]:
    """Return learned signal associations, optionally filtered by context."""
    facts = memory.get_facts(category="context_signal", min_confidence=min_confidence)
    if context is None:
        return facts
    wanted = str(context).strip().upper()
    return [f for f in facts if isinstance(f.get("value"), dict) and f["value"].get("context") == wanted]


__all__ = ["learn_context", "learned_contexts", "learn_signal", "learned_signals"]
