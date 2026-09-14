"""Route conversation requests across Groq and explicit local/simple fallbacks."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
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

    @staticmethod
    def _find_image_paths(messages) -> list[str]:
        """Extract real screenshot paths from an autonomous agent context."""
        found: list[str] = []

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "path" and isinstance(item, str):
                        path = Path(item).expanduser()
                        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                            resolved = str(path.resolve())
                            if resolved not in found:
                                found.append(resolved)
                    else:
                        walk(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    walk(item)

        for message in messages or []:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str):
                try:
                    walk(json.loads(content))
                except (TypeError, ValueError):
                    pass
            walk(message.get("context"))
        return found[-2:]

    def _vision_chat(self, messages, *, temperature=0.1, max_tokens=1400):
        """Send screenshot observations to a local vision model, bypassing text-only Groq."""
        if self.ollama is None or getattr(self.ollama, "ollama", None) is None:
            raise RuntimeError("Observation visuelle indisponible : Ollama local n'est pas disponible.")
        image_paths = self._find_image_paths(messages)
        if not image_paths:
            return None
        model = os.getenv("JARVIS_AGENT_VISION_MODEL", "qwen3-vl:2b")
        client_kwargs = {}
        base_url = getattr(self.ollama, "base_url", None)
        if base_url:
            client_kwargs["host"] = base_url
        client = self.ollama.ollama.Client(**client_kwargs)
        prepared = [dict(message) for message in messages]
        user = next((message for message in reversed(prepared) if message.get("role") == "user"), None)
        if user is None:
            raise RuntimeError("Observation visuelle impossible : message utilisateur absent.")
        user["images"] = image_paths
        response = client.chat(
            model=model,
            messages=prepared,
            format="json",
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        try:
            self.last_provider = f"ollama-vision:{model}"
            return response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Réponse du modèle de vision Ollama invalide.") from exc

    def _fallback_provider(self):
        if self.quota_fallback_mode == "simple":
            return "simple", self.simple
        if not self.fallback_to_ollama:
            return None, None
        return "ollama", self.ollama

    def chat(self, messages, **kwargs):
        image_paths = self._find_image_paths(messages)
        if image_paths:
            started = time.perf_counter()
            try:
                result = self._vision_chat(messages, temperature=kwargs.get("temperature", 0.1), max_tokens=kwargs.get("max_tokens", 1400))
                self.last_latency_ms = round((time.perf_counter() - started) * 1000, 1)
                self.last_error = None
                self.last_fallback_reason = None
                return result
            except Exception as exc:
                self.last_error = str(exc)
                raise

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
            "vision_model": os.getenv("JARVIS_AGENT_VISION_MODEL", "qwen3-vl:2b"),
            "fallback_to_ollama": self.fallback_to_ollama,
            "quota_fallback_mode": self.quota_fallback_mode,
            "last_fallback_reason": self.last_fallback_reason,
            "last_error": self.last_error,
            "latency_ms": self.last_latency_ms,
        }


__all__ = ["AIProviderRouter", "SimpleFallbackProvider"]
