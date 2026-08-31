"""Groq cloud AI provider for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import json, os, urllib.error, urllib.request

class GroqProvider:
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    def __init__(self, api_key=None, model="llama-3.3-70b-versatile", timeout=60.0):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.timeout = max(1.0, float(timeout))
    @property
    def configured(self): return bool(self.api_key.strip())
    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        if not self.configured: raise RuntimeError("Clé API Groq non configurée.")
        payload={"model":self.model,"messages":messages,"temperature":temperature,"max_completion_tokens":max_tokens}
        req=urllib.request.Request(self.endpoint,data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as response: body=json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail=exc.read().decode(errors="replace")
            raise RuntimeError(f"Groq HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc: raise RuntimeError(f"Groq inaccessible: {exc}") from exc
        try: return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc: raise RuntimeError("Réponse Groq invalide.") from exc

__all__=["GroqProvider"]
