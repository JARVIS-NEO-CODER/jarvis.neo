"""AI provider router: Groq first, Ollama as local fallback."""
from __future__ import annotations
from typing import Any

class AIProviderRouter:
    def __init__(self, groq: Any, ollama: Any, *, prefer_groq=True):
        self.groq=groq; self.ollama=ollama; self.prefer_groq=prefer_groq; self.last_provider=None; self.last_error=None
    def chat(self, messages, **kwargs):
        providers=[("groq",self.groq),("ollama",self.ollama)] if self.prefer_groq else [("ollama",self.ollama),("groq",self.groq)]
        errors=[]
        for name,provider in providers:
            if provider is None: continue
            if name=="groq" and hasattr(provider,"configured") and not provider.configured: continue
            try:
                result=provider.chat(messages,**kwargs)
                self.last_provider=name; self.last_error=None
                return result
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                self.last_error=str(exc)
        raise RuntimeError("Aucun fournisseur IA disponible. " + " | ".join(errors))
    @property
    def status(self):
        return {"active_provider":self.last_provider,"groq_configured":bool(getattr(self.groq,"configured",False)),"ollama_available":self.ollama is not None,"last_error":self.last_error}

__all__=["AIProviderRouter"]
