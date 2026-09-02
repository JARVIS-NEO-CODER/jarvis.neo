"""Lightweight web search capability for J.A.R.V.I.S. NEO.

Uses a public HTML search endpoint and returns structured, bounded results. It is
intentionally independent from the browser UI so agents can consume the actual
search results instead of merely opening a Google URL.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen
import re


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class _DuckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._current_url = ""
        self._title = ""
        self._snippet = ""
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._current_url = attrs.get("href", "")
            self._title = ""
            self._in_title = True
        elif tag in {"a", "div", "span"} and classes & {"result__snippet", "result__body"}:
            if self._current_url:
                self._in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title:
            self._in_title = False
            self._append()
        if tag in {"a", "div", "span"} and self._in_snippet:
            self._in_snippet = False

    def handle_data(self, data):
        if self._in_title:
            self._title += data
        elif self._in_snippet:
            self._snippet += data

    def _append(self):
        title = re.sub(r"\s+", " ", self._title).strip()
        raw_url = self._current_url.strip()
        snippet = re.sub(r"\s+", " ", self._snippet).strip()
        if raw_url.startswith("//duckduckgo.com/l/?"):
            match = re.search(r"uddg=([^&]+)", raw_url)
            if match:
                raw_url = unquote(match.group(1))
        if title and raw_url.startswith(("http://", "https://")):
            self.results.append(SearchResult(title, raw_url, snippet[:500]))
        self._current_url = ""
        self._title = ""
        self._snippet = ""


class WebSearchProvider:
    """Perform bounded, read-only web searches without controlling the browser."""

    ENDPOINT = "https://html.duckduckgo.com/html/?q={query}"

    def __init__(self, timeout: float = 8.0, user_agent: str = "JARVIS-NEO/1.0") -> None:
        self.timeout = max(2.0, min(float(timeout), 20.0))
        self.user_agent = user_agent

    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche web ne peut pas être vide.")
        limit = max(1, min(int(limit), 10))
        request = Request(
            self.ENDPOINT.format(query=quote(query)),
            headers={"User-Agent": self.user_agent, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read(2_000_000).decode(charset, errors="replace")
        parser = _DuckParser()
        parser.feed(html)
        unique: list[SearchResult] = []
        seen: set[str] = set()
        for result in parser.results:
            if result.url in seen:
                continue
            seen.add(result.url)
            unique.append(result)
            if len(unique) >= limit:
                break
        if not unique:
            raise RuntimeError("Le moteur web n'a renvoyé aucun résultat exploitable.")
        return unique

    def search_text(self, query: str, *, limit: int = 5) -> str:
        results = self.search(query, limit=limit)
        lines = [f"{i}. {r.title}\n{r.url}\n{r.snippet}" for i, r in enumerate(results, 1)]
        return "Résultats web pour « " + query + " » :\n\n" + "\n\n".join(lines)


__all__ = ["SearchResult", "WebSearchProvider"]
