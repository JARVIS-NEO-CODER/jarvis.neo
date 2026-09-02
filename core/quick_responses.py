"""Fast local responses loaded from the runtime data source."""
from __future__ import annotations

import re
from typing import Callable

from .data_registry import get_data


class QuickResponseEngine:
    """Matches simple phrases locally so the AI model is only used when needed."""

    def __init__(self, responses: dict[str, str | Callable[[], str]] | None = None) -> None:
        configured = responses if responses is not None else get_data("quick_responses", {})
        self._responses: dict[str, str | Callable[[], str]] = {
            self._normalize(phrase): response
            for phrase, response in configured.items()
            if isinstance(phrase, str) and (isinstance(response, str) or callable(response))
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
