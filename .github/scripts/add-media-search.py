from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
web = ROOT / "core" / "web_search.py"
assistant = ROOT / "assistant.py"

media = r'''"""Real media search for J.A.R.V.I.S. NEO.

Uses public Bing HTML result pages and returns direct image URLs plus video
result pages. No API key is required. Results are bounded and deduplicated.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MediaResult:
    title: str
    url: str
    thumbnail: str = ""
    source_url: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url, "thumbnail": self.thumbnail, "source_url": self.source_url}


class WebMediaProvider:
    def __init__(self, timeout: float = 8.0, user_agent: str = "JARVIS-NEO/3.6") -> None:
        self.timeout = max(3.0, min(float(timeout), 15.0))
        self.user_agent = user_agent
        self.last_errors: list[str] = []

    def _fetch(self, url: str) -> str:
        req = Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urlopen(req, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(3_000_000).decode(charset, errors="replace")

    @staticmethod
    def _limit(items: list[MediaResult], limit: int) -> list[MediaResult]:
        out, seen = [], set()
        for item in items:
            if not item.url or item.url in seen:
                continue
            seen.add(item.url)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def search_images(self, query: str, *, limit: int = 8) -> list[MediaResult]:
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche d'images ne peut pas être vide.")
        html_text = self._fetch("https://www.bing.com/images/search?q=" + quote(query) + "&form=HDRSC2&setlang=fr-FR")
        results: list[MediaResult] = []
        for match in re.finditer(r'<a[^>]+class="[^"]*iusc[^"]*"[^>]+m="([^"]+)"', html_text, re.I):
            try:
                data = json.loads(html.unescape(match.group(1)))
            except Exception:
                continue
            url = str(data.get("murl", "")).strip()
            thumb = str(data.get("turl", "")).strip()
            title = str(data.get("t", "")).strip() or query
            source = str(data.get("purl", "")).strip()
            if url.startswith(("http://", "https://")):
                results.append(MediaResult(title[:180], url, thumb, source))
        return self._limit(results, max(1, min(int(limit), 12)))

    def search_videos(self, query: str, *, limit: int = 6) -> list[MediaResult]:
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche vidéo ne peut pas être vide.")
        html_text = self._fetch("https://www.bing.com/videos/search?q=" + quote(query) + "&form=HDRSC4&setlang=fr-FR")
        results: list[MediaResult] = []
        # Bing exposes video metadata in JSON-bearing attributes on result cards.
        for match in re.finditer(r'<a[^>]+class="[^"]*(?:mc_vtvc|iusc)[^"]*"[^>]+m="([^"]+)"', html_text, re.I):
            try:
                data = json.loads(html.unescape(match.group(1)))
            except Exception:
                continue
            url = str(data.get("murl") or data.get("purl") or "").strip()
            thumb = str(data.get("turl") or "").strip()
            title = str(data.get("t") or data.get("title") or "").strip() or query
            source = str(data.get("purl") or url).strip()
            if source.startswith(("http://", "https://")):
                results.append(MediaResult(title[:180], url or source, thumb, source))
        # Fallback to normal video result links if metadata is unavailable.
        if not results:
            for match in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html_text, re.I | re.S):
                url, raw_title = match.groups()
                title = re.sub(r"<[^>]+>", " ", html.unescape(raw_title))
                title = re.sub(r"\s+", " ", title).strip()
                if title and any(host in url.lower() for host in ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")):
                    results.append(MediaResult(title[:180], url, "", url))
        return self._limit(results, max(1, min(int(limit), 8)))


__all__ = ["MediaResult", "WebMediaProvider"]
'''
media_path = ROOT / "core" / "web_media.py"
media_path.write_text(media, encoding="utf-8")

text = assistant.read_text(encoding="utf-8")
if "from core.web_media import WebMediaProvider" not in text:
    text = text.replace("from core.conversation_ai import ConversationAI", "from core.conversation_ai import ConversationAI\nfrom core.web_media import WebMediaProvider")

marker = "    def update_from_response(self, text):"
if marker in text and "def update_media_search(self, kind, results, query=\"\")" not in text:
    methods = '''    def update_media_search(self, kind, results, query=""):\n        """Render actual image/video search results instead of raw JSON intents."""\n        self._clear_body()\n        kind = str(kind or "").lower()\n        items = results or []\n        label = "IMAGES" if kind == "image_search" else "VIDÉOS"\n        self.header.setText(f"◈ DYNAMIC SPACE · {label} · {len(items)} résultat(s)")\n        if query:\n            q = QLabel(f"Recherche : {query}")\n            q.setWordWrap(True)\n            q.setStyleSheet("color:#8fdcff; padding:6px;")\n            self.body_layout.insertWidget(0, q)\n        if kind == "image_search":\n            urls = [item.get("url", "") for item in items if item.get("url")]\n            self._add_images(urls)\n        else:\n            urls = [item.get("source_url") or item.get("url", "") for item in items if item.get("source_url") or item.get("url")]\n            self._add_videos(urls)\n        for item in items:\n            title = item.get("title") or query or "Résultat"\n            source = item.get("source_url") or item.get("url", "")\n            if source:\n                self._add_link_cards([source])\n        self.scroll.verticalScrollBar().setValue(0)\n\n'''
    text = text.replace(marker, methods + marker, 1)

# Hook the JSON media intent shown by the live feed into the real media backend.
if "_handle_media_search_intent" not in text:
    hook = '''    def _handle_media_search_intent(self, message):\n        try:\n            blocks = re.findall(r"\\{\\s*[^{}]*[\\\"']kind[\\\"']\\s*:\\s*[\\\"'](image_search|video_search)[\\\"'][^{}]*\\}", message, re.S)\n            for block in blocks:\n                try:\n                    data = json.loads(block.replace("'", '\"'))\n                except Exception:\n                    continue\n                kind = data.get("kind")\n                query = str(data.get("query") or "").strip()\n                if not query:\n                    continue\n                provider = WebMediaProvider()\n                if kind == "image_search":\n                    results = [r.as_dict() for r in provider.search_images(query)]\n                else:\n                    results = [r.as_dict() for r in provider.search_videos(query)]\n                if results and hasattr(self, "dynamic_space"):\n                    self.dynamic_space.update_media_search(kind, results, query)\n                    return True\n        except Exception as exc:\n            logging.warning("MEDIA SEARCH: %s", exc)\n        return False\n\n'''
    # Insert before the first add_chat_msg method, keeping class indentation.
    pos = text.find("    def add_chat_msg(")
    if pos >= 0:
        text = text[:pos] + hook + text[pos:]

# Make every Jarvis chat message attempt media-intent handling before normal text rendering.
needle = '    def add_chat_msg(self, sender, msg):'
pos = text.find(needle)
if pos >= 0:
    start = text.find("\n", pos) + 1
    inject = '        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            self._handle_media_search_intent(str(msg))\n'
    if inject.strip() not in text[pos:pos+1200]:
        text = text[:start] + inject + text[start:]

assistant.write_text(text, encoding="utf-8")
print("patched media backend")
'''
}