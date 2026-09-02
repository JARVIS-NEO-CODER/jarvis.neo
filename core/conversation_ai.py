"""Conversation AI facade for J.A.R.V.I.S. NEO."""
from __future__ import annotations
from typing import Any
from .ai_provider_router import AIProviderRouter
from .groq_provider import GroqProvider

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

CONVERSATION_STYLE = """STYLE CONVERSATIONNEL NEO :
- Parle comme un assistant personnel présent, naturel et attentif, pas comme un formulaire.
- Réponds en français sauf demande contraire.
- Tutoye l'utilisateur si le ton de la conversation le permet. N'utilise pas « monsieur » par défaut.
- Ne répète pas la demande de l'utilisateur et n'annonce pas inutilement ce que tu vas faire.
- Pour une petite demande, une ou deux phrases suffisent.
- Pour une conversation, privilégie la continuité et les références au contexte récent.
- Si l'utilisateur dit « il », « elle », « le », « ça », etc., résous la référence avec le contexte récent avant de demander une précision.
- Ne pose une question que si une information réellement nécessaire manque.
- Si une action a déjà été exécutée par un outil, ne prétends pas l'exécuter à nouveau. Décris simplement le résultat fourni par le programme.
- Ne dis jamais qu'une action est terminée sans preuve fournie par le programme ou par une vérification explicite.
- Évite les formules génériques comme « Bien sûr ! », « Avec plaisir ! » ou « Comment puis-je vous aider ? » lorsqu'elles n'apportent rien.
- Varie naturellement la longueur et le ton. Une confirmation peut être très courte.
- En vocal, écris des phrases faciles à prononcer, sans listes lourdes ni symboles inutiles.
"""

class OllamaChatProvider:
    def __init__(self, ollama_module: Any, model: str, base_url: str | None = None):
        self.ollama = ollama_module
        self.model = model
        self.base_url = base_url
    @property
    def available(self) -> bool: return self.ollama is not None
    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        if self.ollama is None: raise RuntimeError("Ollama n'est pas installé.")
        client = self.ollama.Client(**({"host": self.base_url} if self.base_url else {}))
        response = client.chat(model=self.model, messages=messages, options={"temperature": temperature, "num_predict": max_tokens})
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
        self.config.setdefault("groq_quota_fallback", "ollama")
        self.router = self._build_router()

    def _build_router(self):
        groq = GroqProvider(api_key=self.config.get("groq_api_key", ""), model=self.config.get("groq_model", DEFAULT_GROQ_MODEL), timeout=float(self.config.get("groq_timeout", 60)))
        ollama = None
        if self.config.get("ollama_enabled", True):
            ollama = OllamaChatProvider(self.ollama_module, self.config.get("model", "llama3.2:3b"), self.config.get("ollama_base_url", "http://127.0.0.1:11434"))
        return AIProviderRouter(groq=groq, ollama=ollama, prefer_groq=self.config.get("ai_provider", "groq") != "ollama", fallback_to_ollama=bool(self.config.get("groq_fallback_to_ollama", True)), quota_fallback_mode=self.config.get("groq_quota_fallback", "ollama"))

    def refresh(self) -> dict[str, Any]:
        self.router = self._build_router()
        return self.router.status

    @staticmethod
    def _with_style(messages):
        """Add a focused conversational policy without destroying the caller's context."""
        items = list(messages or [])
        style = {"role": "system", "content": CONVERSATION_STYLE}
        if items and items[0].get("role") == "system":
            first = dict(items[0])
            first["content"] = first.get("content", "") + "\n\n" + CONVERSATION_STYLE
            items[0] = first
            return items
        return [style, *items]

    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        return self.router.chat(self._with_style(messages), temperature=temperature, max_tokens=max_tokens)

    @property
    def status(self): return self.router.status

__all__ = ["ConversationAI", "OllamaChatProvider", "CONVERSATION_STYLE"]
