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
