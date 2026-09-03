"""Groq cloud AI provider for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from core.ai_model_catalog import GROQ_MODELS

DEFAULT_MODEL = "llama-3.1-8b-instant"
USER_AGENT = "JARVIS-NEO/1.2"


class GroqProvider:
    """Dependency-free Groq client with access-aware model recovery."""

    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    models_endpoint = "https://api.groq.com/openai/v1/models"

    def __init__(self, api_key=None, model=DEFAULT_MODEL, timeout=60.0):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = str(model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.timeout = max(1.0, float(timeout))
        self.last_model = self.model
        self.last_error_code = None

    @property
    def configured(self):
        return bool(self.api_key.strip())

    def _request_json(self, url: str, *, method: str = "GET", payload=None):
        if not self.configured:
            raise RuntimeError("Groq API key absente.")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.last_error_code = None
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            self.last_error_code = exc.code
            try:
                parsed = json.loads(detail)
                error = parsed.get("error", {})
                message = error.get("message", detail)
                code = error.get("code")
            except (json.JSONDecodeError, AttributeError):
                message, code = detail, None
            suffix = f" [{code}]" if code else ""
            if exc.code == 401:
                raise RuntimeError("Groq HTTP 401 : clé API invalide ou expirée." + suffix) from exc
            if exc.code == 403:
                raise RuntimeError("Groq HTTP 403 : accès refusé par l'organisation ou le projet Groq." + suffix) from exc
            if exc.code == 404:
                raise RuntimeError(f"Groq HTTP 404 : {message}" + suffix) from exc
            if exc.code == 429:
                raise RuntimeError("Groq HTTP 429 : limite de débit ou quota atteint." + suffix) from exc
            raise RuntimeError(f"Groq HTTP {exc.code} : {message}" + suffix) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            self.last_error_code = None
            raise RuntimeError(f"Groq inaccessible : {exc}") from exc

    def list_models(self) -> list[dict]:
        body = self._request_json(self.models_endpoint)
        models = body.get("data", []) if isinstance(body, dict) else []
        return [item for item in models if isinstance(item, dict) and item.get("id")]

    def _listed_model_ids(self) -> set[str]:
        """Return only documented chat-capable candidates, never arbitrary media models."""
        listed = {str(item.get("id")) for item in self.list_models()}
        return listed & {model_id for _, model_id in GROQ_MODELS}

    def model_exists(self, model_id: str) -> bool:
        model_id = str(model_id or "").strip()
        if not model_id:
            return False
        try:
            encoded = urllib.parse.quote(model_id, safe="")
            body = self._request_json(f"{self.models_endpoint}/{encoded}")
            return isinstance(body, dict) and body.get("id") == model_id
        except RuntimeError as exc:
            text = str(exc)
            if "HTTP 403" in text or "HTTP 404" in text:
                return False
            raise

    def _find_working_model(self) -> str | None:
        """Prefer the configured model, then verify only chat models exposed by Groq."""
        try:
            listed = self._listed_model_ids()
        except RuntimeError:
            listed = set()
        candidates = [self.model, DEFAULT_MODEL]
        candidates.extend(model_id for _, model_id in GROQ_MODELS)
        for candidate in candidates:
            if candidate in listed and self.model_exists(candidate):
                return candidate
        return None

    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        if not self.configured:
            raise RuntimeError("Clé API Groq non configurée.")

        def send(model: str):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
            }
            body = self._request_json(self.endpoint, method="POST", payload=payload)
            try:
                return body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError("Réponse Groq invalide.") from exc

        try:
            result = send(self.model)
            self.last_model = self.model
            return result
        except RuntimeError as exc:
            text = str(exc)
            model_error = "HTTP 404" in text and ("model" in text.lower() or "not found" in text.lower())
            if not model_error:
                raise
            working = self._find_working_model()
            if not working or working == self.model:
                raise RuntimeError(
                    f"Modèle Groq indisponible : {self.model}. "
                    "Aucun modèle de conversation Groq accessible n'a été confirmé avec cette clé. "
                    "Vérifiez la clé API et les permissions du projet Groq."
                ) from exc
            self.model = working
            result = send(working)
            self.last_model = working
            return result


__all__ = ["GroqProvider", "DEFAULT_MODEL"]
