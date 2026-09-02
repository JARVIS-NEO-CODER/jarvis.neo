"""Route conversation requests across Groq and explicit local/simple fallbacks."""
from __future__ import annotations

from typing import Any


class SimpleFallbackProvider:
    """Deterministic fallback used when the cloud quota is exhausted."""

    configured = True

    def chat(self, messages, **kwargs):
        return (
            "Mode Simple actif : le quota Groq est atteint. "
            "Active le modèle local pour continuer avec une réponse IA complète."
        )


class AIProviderRouter:
    def __init__(
        self,
        groq: Any,
        ollama: Any,
        *,
        prefer_groq=True,
        fallback_to_ollama=True,
        quota_fallback_mode="ollama",
    ):
        self.groq = groq
        self.ollama = ollama
        self.prefer_groq = prefer_groq
        self.fallback_to_ollama = fallback_to_ollama
        self.quota_fallback_mode = quota_fallback_mode if quota_fallback_mode in {"ollama", "simple"} else "ollama"
        self.simple = SimpleFallbackProvider()
        self.last_provider = None
        self.last_error = None
        self.last_fallback_reason = None

    @staticmethod
    def is_fallback_error(exc: Exception) -> bool:
        """Return True for quota/rate-limit or temporary provider outages."""
        text = str(exc).lower()
        if "http 429" in text or "status code: 429" in text:
            return True
        if "quota" in text or "rate limit" in text or "too many requests" in text:
            return True
        if "http 5" in text or "groq inaccessible" in text:
            return True
        return False

    def _fallback_provider(self):
        if not self.fallback_to_ollama:
            return None, None
        if self.quota_fallback_mode == "simple":
            return "simple", self.simple
        return "ollama", self.ollama

    def chat(self, messages, **kwargs):
        if not self.prefer_groq:
            providers = [("ollama", self.ollama)]
        else:
            providers = [("groq", self.groq)]

        errors = []
        for name, provider in providers:
            if provider is None:
                continue
            if name == "groq" and hasattr(provider, "configured") and not provider.configured:
                continue
            try:
                result = provider.chat(messages, **kwargs)
                self.last_provider = name
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
                try:
                    result = fallback.chat(messages, **kwargs)
                    self.last_provider = fallback_name
                    self.last_error = None
                    self.last_fallback_reason = "quota_or_temporary_error"
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
        }


__all__ = ["AIProviderRouter", "SimpleFallbackProvider"]
