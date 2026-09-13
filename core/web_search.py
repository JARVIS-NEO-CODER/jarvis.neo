"""Lightweight resilient web search capability for J.A.R.V.I.S. NEO.

Uses public HTML search endpoints with provider fallback. The provider is
read-only and returns bounded structured results for the assistant and UI.
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
            if self._current_url:
                self._append()
            self._current_url = attrs.get("href", "")
            self._title = ""
            self._snippet = ""
            self._in_title = True
        elif tag in {"a", "div", "span"} and classes & {"result__snippet", "result__body"}:
            if self._current_url:
                self._in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title:
            self._in_title = False
        if tag in {"a", "div", "span"} and self._in_snippet:
            self._in_snippet = False
            self._append()

    def handle_data(self, data):
        if self._in_title:
            self._title += data
        elif self._in_snippet:
            self._snippet += data

    def close(self):
        super().close()
        if self._current_url:
            self._append()

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
        self._in_title = False
        self._in_snippet = False


class _BingParser(HTMLParser):
    """Small parser for Bing's public result page."""
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._url = ""
        self._title = ""
        self._snippet = ""
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "li" and "b_algo" in classes:
            self._url = self._title = self._snippet = ""
        elif tag == "a" and self._url == "" and attrs.get("href", "").startswith("http"):
            self._url = attrs["href"]
            self._in_title = True
        elif tag in {"p", "div"} and classes & {"b_caption", "b_algoSlug"}:
            if self._url:
                self._in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title:
            self._in_title = False
        if tag in {"p", "div"} and self._in_snippet:
            self._in_snippet = False
            self._append()

    def handle_data(self, data):
        if self._in_title:
            self._title += data
        elif self._in_snippet:
            self._snippet += data

    def close(self):
        super().close()
        if self._url:
            self._append()

    def _append(self):
        title = re.sub(r"\s+", " ", self._title).strip()
        snippet = re.sub(r"\s+", " ", self._snippet).strip()
        if title and self._url.startswith(("http://", "https://")):
            self.results.append(SearchResult(title, self._url, snippet[:500]))
        self._url = self._title = self._snippet = ""
        self._in_title = self._in_snippet = False


class WebSearchProvider:
    """Perform bounded read-only web searches with automatic provider fallback."""

    PROVIDERS = (
        ("duckduckgo", "https://html.duckduckgo.com/html/?q={query}", _DuckParser),
        ("bing", "https://www.bing.com/search?q={query}&setlang=fr-FR", _BingParser),
    )

    def __init__(self, timeout: float = 8.0, user_agent: str = "JARVIS-NEO/3.6") -> None:
        self.timeout = max(2.0, min(float(timeout), 20.0))
        self.user_agent = user_agent
        self.last_provider = None
        self.last_errors: list[str] = []

    def _search_provider(self, endpoint: str, parser_cls, query: str, limit: int) -> list[SearchResult]:
        request = Request(
            endpoint.format(query=quote(query)),
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read(2_000_000).decode(charset, errors="replace")
        parser = parser_cls()
        parser.feed(html)
        parser.close()
        unique: list[SearchResult] = []
        seen: set[str] = set()
        for result in parser.results:
            if result.url in seen:
                continue
            seen.add(result.url)
            unique.append(result)
            if len(unique) >= limit:
                break
        return unique

    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche web ne peut pas être vide.")
        limit = max(1, min(int(limit), 10))
        self.last_errors = []
        for name, endpoint, parser_cls in self.PROVIDERS:
            try:
                results = self._search_provider(endpoint, parser_cls, query, limit)
                if results:
                    self.last_provider = name
                    return results
                self.last_errors.append(f"{name}: aucun résultat exploitable")
            except Exception as exc:
                self.last_errors.append(f"{name}: {exc}")
        raise RuntimeError("Recherche web indisponible : " + " | ".join(self.last_errors))

    def search_text(self, query: str, *, limit: int = 5) -> str:
        results = self.search(query, limit=limit)
        lines = [f"{i}. {r.title}\n{r.url}\n{r.snippet}" for i, r in enumerate(results, 1)]
        provider = f" via {self.last_provider}" if self.last_provider else ""
        return "Résultats web" + provider + " pour « " + query + " » :\n\n" + "\n\n".join(lines)


__all__ = ["SearchResult", "WebSearchProvider"]
