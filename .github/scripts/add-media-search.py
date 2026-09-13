from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
assistant = ROOT / 'assistant.py'

media = r"""from __future__ import annotations

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
    thumbnail: str = ''
    source_url: str = ''

    def as_dict(self) -> dict[str, str]:
        return {'title': self.title, 'url': self.url, 'thumbnail': self.thumbnail, 'source_url': self.source_url}

class WebMediaProvider:
    def __init__(self, timeout: float = 8.0, user_agent: str = 'JARVIS-NEO/3.6') -> None:
        self.timeout = max(3.0, min(float(timeout), 15.0))
        self.user_agent = user_agent

    def _fetch(self, url: str) -> str:
        req = Request(url, headers={'User-Agent': self.user_agent, 'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.7', 'Accept': 'text/html,application/xhtml+xml'})
        with urlopen(req, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return response.read(3_000_000).decode(charset, errors='replace')

    @staticmethod
    def _limit(items, limit):
        out, seen = [], set()
        for item in items:
            if not item.url or item.url in seen:
                continue
            seen.add(item.url)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def search_images(self, query: str, *, limit: int = 8):
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche d'images ne peut pas être vide.")
        text = self._fetch('https://www.bing.com/images/search?q=' + quote(query) + '&form=HDRSC2&setlang=fr-FR')
        results = []
        for match in re.finditer(r'<a[^>]+class="[^"]*iusc[^"]*"[^>]+m="([^"]+)"', text, re.I):
            try:
                data = json.loads(html.unescape(match.group(1)))
            except Exception:
                continue
            url = str(data.get('murl', '')).strip()
            if url.startswith(('http://', 'https://')):
                results.append(MediaResult(str(data.get('t', '')).strip() or query, url, str(data.get('turl', '')).strip(), str(data.get('purl', '')).strip()))
        return self._limit(results, max(1, min(int(limit), 12)))

    def search_videos(self, query: str, *, limit: int = 6):
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche vidéo ne peut pas être vide.")
        text = self._fetch('https://www.bing.com/videos/search?q=' + quote(query) + '&form=HDRSC4&setlang=fr-FR')
        results = []
        for match in re.finditer(r'<a[^>]+class="[^"]*(?:mc_vtvc|iusc)[^"]*"[^>]+m="([^"]+)"', text, re.I):
            try:
                data = json.loads(html.unescape(match.group(1)))
            except Exception:
                continue
            url = str(data.get('murl') or data.get('purl') or '').strip()
            source = str(data.get('purl') or url).strip()
            if source.startswith(('http://', 'https://')):
                results.append(MediaResult(str(data.get('t') or data.get('title') or '').strip() or query, url or source, str(data.get('turl') or '').strip(), source))
        if not results:
            for match in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', text, re.I | re.S):
                url, raw = match.groups()
                title = re.sub(r'<[^>]+>', ' ', html.unescape(raw))
                title = re.sub(r'\s+', ' ', title).strip()
                if title and any(host in url.lower() for host in ('youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com')):
                    results.append(MediaResult(title[:180], url, '', url))
        return self._limit(results, max(1, min(int(limit), 8)))

__all__ = ['MediaResult', 'WebMediaProvider']
"""
(ROOT / 'core' / 'web_media.py').write_text(media, encoding='utf-8')

text = assistant.read_text(encoding='utf-8')
if 'from core.web_media import WebMediaProvider' not in text:
    text = text.replace('from core.conversation_ai import ConversationAI', 'from core.conversation_ai import ConversationAI\nfrom core.web_media import WebMediaProvider', 1)

if 'def update_media_search(self, kind, results, query="")' not in text:
    marker = '    def update_from_response(self, message):'
    methods = '''    def update_media_search(self, kind, results, query=""):\n        self._clear_body()\n        kind = str(kind or "").lower()\n        items = results or []\n        label = "IMAGES" if kind == "image_search" else "VIDÉOS"\n        self.header.setText(f"◈ DYNAMIC SPACE · {label} · {len(items)} résultat(s)")\n        if query:\n            q = QLabel(f"Recherche : {query}")\n            q.setWordWrap(True)\n            q.setStyleSheet("color:#8fdcff; padding:6px;")\n            self.body_layout.insertWidget(0, q)\n        if kind == "image_search":\n            self._add_images([x.get("url", "") for x in items if x.get("url")])\n        else:\n            self._add_videos([x.get("source_url") or x.get("url", "") for x in items if x.get("source_url") or x.get("url")])\n        self.scroll.verticalScrollBar().setValue(0)\n\n'''
    if marker not in text:
        raise SystemExit('DynamicSpace marker not found')
    text = text.replace(marker, methods + marker, 1)

if 'def _handle_media_search_intent(self, message):' not in text:
    hook = '''    def _handle_media_search_intent(self, message):\n        try:\n            candidates = re.findall(r'\\{[^{}]*\\}', str(message), re.S)\n            for raw in candidates:\n                try:\n                    data = json.loads(raw)\n                except Exception:\n                    continue\n                kind = str(data.get("kind") or "").lower()\n                query = str(data.get("query") or "").strip()\n                if kind not in ("image_search", "video_search") or not query:\n                    continue\n                provider = WebMediaProvider()\n                if kind == "image_search":\n                    results = [r.as_dict() for r in provider.search_images(query)]\n                else:\n                    results = [r.as_dict() for r in provider.search_videos(query)]\n                if results and hasattr(self, "dynamic_space"):\n                    self.dynamic_space.update_media_search(kind, results, query)\n                    return True\n        except Exception as exc:\n            logging.warning("MEDIA SEARCH: %s", exc)\n        return False\n\n'''
    pos = text.find('    def add_chat_msg(')
    if pos < 0:
        raise SystemExit('add_chat_msg not found')
    text = text[:pos] + hook + text[pos:]

needle = '    def add_chat_msg(self, sender, msg):'
pos = text.find(needle)
if pos >= 0:
    line_end = text.find('\n', pos) + 1
    inject = '        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            self._handle_media_search_intent(str(msg))\n'
    if inject.strip() not in text[pos:pos+1000]:
        text = text[:line_end] + inject + text[line_end:]

assistant.write_text(text, encoding='utf-8')
print('patched media backend')
