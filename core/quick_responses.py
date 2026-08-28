"""Fast local responses, checked before invoking the AI model."""
from __future__ import annotations

import re
from typing import Callable


class QuickResponseEngine:
    """Matches simple phrases locally so Ollama is only used when needed."""

    def __init__(self) -> None:
        self._responses: dict[str, str | Callable[[], str]] = {
            "jarvis ça va": "Je fonctionne parfaitement. Merci de demander !",
            "ça va jarvis": "Je fonctionne parfaitement. Merci de demander !",
            "qui es tu": "Je suis J.A.R.V.I.S. NEO, ton assistant local.",
            "qui es-tu": "Je suis J.A.R.V.I.S. NEO, ton assistant local.",
            "quel est ton nom": "Mon nom est J.A.R.V.I.S. NEO.",
        }

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()
        return re.sub(r"[^a-zà-ÿ0-9\s-]", "", text)

    def add(self, phrase: str, response: str | Callable[[], str]) -> None:
        self._responses[self._normalize(phrase)] = response

    def match(self, text: str) -> str | None:
        key = self._normalize(text)
        response = self._responses.get(key)
        if response is None:
            return None
        return response() if callable(response) else response


__all__ = ["QuickResponseEngine"]
