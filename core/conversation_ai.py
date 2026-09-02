"""Conversation AI facade for J.A.R.V.I.S. NEO."""
from __future__ import annotations
from typing import Any
from .ai_provider_router import AIProviderRouter
from .groq_provider import GroqProvider

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

class OllamaChatProvider:
    def __init__(self, ollama_module: Any, model: str, base_url: str | None = None):
        self.ollama = ollama_module; self.model = model; self.base_url = base_url
    @property
    def available(self) -> bool: return self.ollama is not None
    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        if self.ollama is None: raise RuntimeError("Ollama n'est pas installé.")
        client = self.ollama.Client(**({"host": self.base_url} if self.base_url else {}))
        response = client.chat(model=self.model, messages=messages,
                               options={"temperature": temperature, "num_predict": max_tokens})
        try: return response["message"]["content"]
        except (KeyError, TypeError) as exc: raise RuntimeError("Réponse Ollama invalide.") from exc

class ConversationAI:
    def __init__(self, config: dict[str, Any], ollama_module: Any = None):
        self.config = config
        if ollama_module is None:
            try: import ollama as ollama_module
            except ImportError: ollama_module = None
        self.ollama_module = ollama_module
        self.config.setdefault("groq_model", DEFAULT_GROQ_MODEL)
        self.config.setdefault("ollama_enabled", True)
        self.config.setdefault("ai_provider", "groq")
        self.config.setdefault("groq_fallback_to_ollama", True)
        self.router = self._build_router()

    def _build_router(self):
        groq = GroqProvider(api_key=self.config.get("groq_api_key", ""),
                            model=self.config.get("groq_model", DEFAULT_GROQ_MODEL),
                            timeout=float(self.config.get("groq_timeout", 60)))
        ollama = None
        if self.config.get("ollama_enabled", True):
            ollama = OllamaChatProvider(self.ollama_module, self.config.get("model", "llama3.2:3b"),
                                        self.config.get("ollama_base_url", "http://127.0.0.1:11434"))
        return AIProviderRouter(groq=groq, ollama=ollama,
                                prefer_groq=self.config.get("ai_provider", "groq") != "ollama",
                                fallback_to_ollama=bool(self.config.get("groq_fallback_to_ollama", True)))

    def refresh(self) -> dict[str, Any]:
        """Rebuild the provider router from the current config in-place."""
        self.router = self._build_router()
        return self.router.status

    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        return self.router.chat(messages, temperature=temperature, max_tokens=max_tokens)
    @property
    def status(self): return self.router.status

__all__ = ["ConversationAI", "OllamaChatProvider"]
