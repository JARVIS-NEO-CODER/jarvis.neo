"""Route conversation requests across Groq and explicit local/simple fallbacks."""
from __future__ import annotations
import time
from typing import Any


class SimpleFallbackProvider:
    configured = True

    def chat(self, messages, **kwargs):
        return "Mode Simple actif : le fournisseur IA distant est indisponible. Les fonctions locales restent disponibles."


class AIProviderRouter:
    def __init__(self, groq: Any, ollama: Any, *, prefer_groq=True, fallback_to_ollama=True, quota_fallback_mode="ollama"):
        self.groq = groq
        self.ollama = ollama
        self.prefer_groq = prefer_groq
        self.fallback_to_ollama = fallback_to_ollama
        self.quota_fallback_mode = quota_fallback_mode if quota_fallback_mode in {"ollama", "simple"} else "ollama"
        self.simple = SimpleFallbackProvider()
        self.last_provider = None
        self.last_error = None
        self.last_fallback_reason = None
        self.last_latency_ms = None

    @staticmethod
    def is_fallback_error(exc: Exception) -> bool:
        """Return True only for availability/quota failures, not bad credentials."""
        text = str(exc).lower()
        return any(x in text for x in (
            "http 429", "status code: 429", "quota", "rate limit", "too many requests",
            "model unavailable", "modèle groq indisponible", "no other",
            "http 500", "http 502", "http 503", "http 504", "service unavailable",
            "temporarily unavailable", "timeout", "timed out", "connection reset",
            "connection refused", "name or service not known", "groq inaccessible",
        ))

    @staticmethod
    def fallback_reason(exc: Exception) -> str:
        text = str(exc).lower()
        if any(x in text for x in ("http 429", "status code: 429", "quota", "rate limit", "too many requests")):
            return "quota_or_temporary_error"
        return "groq_unavailable"

    def _fallback_provider(self):
        if self.quota_fallback_mode == "simple":
            return "simple", self.simple
        if not self.fallback_to_ollama:
            return None, None
        return "ollama", self.ollama

    def chat(self, messages, **kwargs):
        providers = [("groq", self.groq)] if self.prefer_groq else [("ollama", self.ollama)]
        errors = []
        for name, provider in providers:
            if provider is None:
                continue
            if name == "groq" and hasattr(provider, "configured") and not provider.configured:
                continue
            started = time.perf_counter()
            try:
                result = provider.chat(messages, **kwargs)
                self.last_provider = name
                self.last_latency_ms = round((time.perf_counter() - started) * 1000, 1)
                self.last_error = None
                self.last_fallback_reason = None
                return result
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                self.last_error = str(exc)
                if name != "groq" or not self.is_fallback_error(exc):
                    break
                fallback_name, fallback = self._fallback_provider()
                if fallback is None:
                    break
                fallback_started = time.perf_counter()
                try:
                    result = fallback.chat(messages, **kwargs)
                    self.last_provider = fallback_name
                    self.last_latency_ms = round((time.perf_counter() - fallback_started) * 1000, 1)
                    self.last_error = None
                    self.last_fallback_reason = self.fallback_reason(exc)
                    return result
                except Exception as fallback_exc:
                    errors.append(f"{fallback_name}: {fallback_exc}")
                    self.last_error = str(fallback_exc)
                    break
        raise RuntimeError("Aucun fournisseur IA disponible. " + " | ".join(errors))

    @property
    def status(self):
        return {
            "active_provider": self.last_provider,
            "groq_configured": bool(getattr(self.groq, "configured", False)),
            "ollama_available": self.ollama is not None,
            "fallback_to_ollama": self.fallback_to_ollama,
            "quota_fallback_mode": self.quota_fallback_mode,
            "last_fallback_reason": self.last_fallback_reason,
            "last_error": self.last_error,
            "latency_ms": self.last_latency_ms,
        }


__all__ = ["AIProviderRouter", "SimpleFallbackProvider"]