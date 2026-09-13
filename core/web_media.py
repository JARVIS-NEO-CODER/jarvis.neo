from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

# Ce module est importé très tôt par le launcher source.
# Le hook applique le thème après l'initialisation de l'interface afin que
# les styles globaux de l'ancien HUD ne puissent pas l'écraser.
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from core.neo_theme import apply_theme


_THEME_HOOK_INSTALLED = getattr(QApplication, "_jarvis_neo_theme_hook", False)
if not _THEME_HOOK_INSTALLED:
    _original_qapplication_init = QApplication.__init__

    def _jarvis_neo_qapplication_init(self, *args, **kwargs):
        _original_qapplication_init(self, *args, **kwargs)
        QTimer.singleShot(0, lambda: _safe_apply_theme(self))

    def _safe_apply_theme(app):
        try:
            apply_theme(app)
        except Exception:
            # Le thème est purement visuel et ne doit jamais bloquer JARVIS.
            pass

    QApplication.__init__ = _jarvis_neo_qapplication_init
    QApplication._jarvis_neo_theme_hook = True


@dataclass(frozen=True)
class MediaResult:
    title: str
    url: str
    thumbnail: str = ''
    source_url: str = ''

    def as_dict(self) -> dict[str, str]:
        return {
            'title': self.title,
            'url': self.url,
            'thumbnail': self.thumbnail,
            'source_url': self.source_url,
        }


class WebMediaProvider:
    """Recherche web de médias avec parsing tolérant aux changements HTML."""

    def __init__(self, timeout: float = 8.0, user_agent: str = 'JARVIS-NEO/3.6') -> None:
        self.timeout = max(3.0, min(float(timeout), 15.0))
        self.user_agent = user_agent

    def _fetch(self, url: str) -> str:
        req = Request(
            url,
            headers={
                'User-Agent': self.user_agent,
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml',
            },
        )
        with urlopen(req, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return response.read(4_000_000).decode(charset, errors='replace')

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

    @staticmethod
    def _decode_m(value: str) -> dict:
        try:
            decoded = html.unescape(value)
            return json.loads(decoded)
        except Exception:
            return {}

    def _image_items_from_html(self, text: str, query: str):
        results = []
        for tag in re.findall(r'<a\b[^>]*>', text, re.I | re.S):
            if not re.search(r'class\s*=\s*["\'][^"\']*\biusc\b', tag, re.I):
                continue
            match = re.search(r'\bm\s*=\s*["\'](.*?)["\']', tag, re.I | re.S)
            if not match:
                continue
            data = self._decode_m(match.group(1))
            url = str(data.get('murl') or '').strip()
            if not url.startswith(('http://', 'https://')):
                continue
            results.append(
                MediaResult(
                    str(data.get('t') or data.get('title') or '').strip() or query,
                    url,
                    str(data.get('turl') or '').strip(),
                    str(data.get('purl') or '').strip(),
                )
            )

        if not results:
            for match in re.finditer(r'\bmurl\s*[:=]\s*["\'](https?://[^"\']+)', text, re.I):
                url = html.unescape(match.group(1)).strip()
                if url.startswith(('http://', 'https://')):
                    results.append(MediaResult(query, url))
        return results

    def search_images(self, query: str, *, limit: int = 8):
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche d'images ne peut pas être vide.")
        text = self._fetch(
            'https://www.bing.com/images/search?q=' + quote(query) + '&form=HDRSC2&setlang=fr-FR'
        )
        return self._limit(self._image_items_from_html(text, query), max(1, min(int(limit), 12)))

    def search_videos(self, query: str, *, limit: int = 6):
        query = str(query).strip()
        if not query:
            raise ValueError("La recherche vidéo ne peut pas être vide.")
        text = self._fetch(
            'https://www.bing.com/videos/search?q=' + quote(query) + '&form=HDRSC4&setlang=fr-FR'
        )
        results = []
        for match in re.finditer(r'<a\b[^>]*>', text, re.I | re.S):
            tag = match.group(0)
            if not re.search(r'class\s*=\s*["\'][^"\']*(?:mc_vtvc|iusc)[^"\']*["\']', tag, re.I):
                continue
            m_match = re.search(r'\bm\s*=\s*["\'](.*?)["\']', tag, re.I | re.S)
            if not m_match:
                continue
            data = self._decode_m(m_match.group(1))
            url = str(data.get('murl') or data.get('purl') or '').strip()
            source = str(data.get('purl') or url).strip()
            if source.startswith(('http://', 'https://')):
                results.append(
                    MediaResult(
                        str(data.get('t') or data.get('title') or '').strip() or query,
                        url or source,
                        str(data.get('turl') or '').strip(),
                        source,
                    )
                )

        if not results:
            for match in re.finditer(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
                url, raw = match.groups()
                title = re.sub(r'<[^>]+>', ' ', html.unescape(raw))
                title = re.sub(r'\s+', ' ', title).strip()
                if title and any(host in url.lower() for host in ('youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com')):
                    results.append(MediaResult(title[:180], url, '', url))
        return self._limit(results, max(1, min(int(limit), 8)))


__all__ = ['MediaResult', 'WebMediaProvider']
