from __future__ import annotations

import html
import json
import re
import threading
import webbrowser
from dataclasses import dataclass
from urllib.parse import parse_qs, quote, unquote_plus, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

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
            pass

    QApplication.__init__ = _jarvis_neo_qapplication_init
    QApplication._jarvis_neo_theme_hook = True


# Compatibilité navigateur : les anciens appels Google contenant explicitement
# "image/photo" sont convertis en Google Images. Les recherches Web normales
# restent inchangées.
_ORIGINAL_WEBBROWSER_OPEN = webbrowser.open
_ORIGINAL_WEBBROWSER_OPEN_NEW_TAB = getattr(webbrowser, "open_new_tab", None)
_ORIGINAL_WEBBROWSER_OPEN_NEW = getattr(webbrowser, "open_new", None)
_MEDIA_TERMS = re.compile(r"(?:^|\b)(?:image|images|photo|photos)(?:\b|$)", re.I)


def _normalize_media_url(url):
    try:
        parsed = urlparse(str(url))
        if parsed.netloc.lower().endswith("google.com") and parsed.path.rstrip("/") == "/search":
            params = parse_qs(parsed.query, keep_blank_values=True)
            query = unquote_plus(params.get("q", [""])[0]).strip()
            if _MEDIA_TERMS.search(query):
                media_query = _MEDIA_TERMS.sub(" ", query)
                media_query = re.sub(r"\s+", " ", media_query).strip()
                params["q"] = [media_query]
                params["tbm"] = ["isch"]
                params.setdefault("hl", ["fr"])
                params.setdefault("safe", ["active"])
                return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
    except Exception:
        pass
    return url


def _jarvis_media_browser_open(url, new=0, autoraise=True):
    return _ORIGINAL_WEBBROWSER_OPEN(_normalize_media_url(url), new=new, autoraise=autoraise)


def _jarvis_media_browser_open_new_tab(url):
    target = _normalize_media_url(url)
    if _ORIGINAL_WEBBROWSER_OPEN_NEW_TAB is not None:
        return _ORIGINAL_WEBBROWSER_OPEN_NEW_TAB(target)
    return _ORIGINAL_WEBBROWSER_OPEN(target, new=2, autoraise=True)


def _jarvis_media_browser_open_new(url):
    target = _normalize_media_url(url)
    if _ORIGINAL_WEBBROWSER_OPEN_NEW is not None:
        return _ORIGINAL_WEBBROWSER_OPEN_NEW(target)
    return _ORIGINAL_WEBBROWSER_OPEN(target, new=1, autoraise=True)


if not getattr(webbrowser, "_jarvis_neo_media_patch", False):
    webbrowser.open = _jarvis_media_browser_open
    webbrowser.open_new_tab = _jarvis_media_browser_open_new_tab
    webbrowser.open_new = _jarvis_media_browser_open_new
    webbrowser._jarvis_neo_media_patch = True


def _open_google_images(query: str) -> bool:
    query = str(query).strip()
    if not query:
        return False
    url = "https://www.google.com/search?" + urlencode({
        "q": query,
        "tbm": "isch",
        "hl": "fr",
        "safe": "active",
    })
    try:
        if _ORIGINAL_WEBBROWSER_OPEN_NEW_TAB is not None:
            return bool(_ORIGINAL_WEBBROWSER_OPEN_NEW_TAB(url))
        return bool(_ORIGINAL_WEBBROWSER_OPEN(url, new=2, autoraise=True))
    except Exception:
        try:
            return bool(_ORIGINAL_WEBBROWSER_OPEN(url, new=2, autoraise=True))
        except Exception:
            return False


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
            return json.loads(html.unescape(value))
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
            results.append(MediaResult(
                str(data.get('t') or data.get('title') or '').strip() or query,
                url,
                str(data.get('turl') or '').strip(),
                str(data.get('purl') or '').strip(),
            ))

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
        # L'intention image connaît déjà le contexte média. On force donc
        # Google Images avec la requête réelle, même si elle vaut simplement
        # "cam" et ne contient pas le mot "image".
        _open_google_images(query)
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
                results.append(MediaResult(
                    str(data.get('t') or data.get('title') or '').strip() or query,
                    url or source,
                    str(data.get('turl') or '').strip(),
                    source,
                ))

        if not results:
            for match in re.finditer(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
                url, raw = match.groups()
                title = re.sub(r'<[^>]+>', ' ', html.unescape(raw))
                title = re.sub(r'\s+', ' ', title).strip()
                if title and any(host in url.lower() for host in ('youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com')):
                    results.append(MediaResult(title[:180], url, '', url))
        return self._limit(results, max(1, min(int(limit), 8)))


def _extract_media_payloads(message: str):
    """Extrait les objets JSON de média renvoyés par le cerveau JARVIS."""
    text = str(message or '').strip()
    candidates = re.findall(r'\{[^{}]*\}', text, re.S)
    for raw in candidates:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        kind = str(data.get('kind') or '').lower().strip()
        query = str(data.get('query') or '').strip()
        if kind in {'image_search', 'video_search'} and query:
            yield kind, query


def _install_dynamic_media_bridge():
    """Reconnecte les payloads image_search au Dynamic Space après la division du runtime."""
    try:
        from core.assistant_components import JarvisWindow
    except Exception:
        return

    original = getattr(JarvisWindow, 'add_chat_msg', None)
    if original is None or getattr(JarvisWindow, '_jarvis_media_bridge_installed', False):
        return

    # Une version antérieure possédait déjà ce pont dans assistant.py.
    # Ne pas l'exécuter deux fois.
    if '_handle_media_search_intent' in getattr(original, '__code__', None).co_names:
        JarvisWindow._jarvis_media_bridge_installed = True
        return

    def add_chat_msg_with_media(self, sender, msg):
        original(self, sender, msg)
        if sender not in ('Jarvis', 'J.A.R.V.I.S.'):
            return
        payloads = list(_extract_media_payloads(str(msg)))
        if not payloads or not hasattr(self, 'dynamic_space') or self.dynamic_space is None:
            return

        def worker():
            for kind, query in payloads[:1]:
                try:
                    provider = WebMediaProvider()
                    if kind == 'image_search':
                        results = [item.as_dict() for item in provider.search_images(query)]
                    else:
                        results = [item.as_dict() for item in provider.search_videos(query)]
                except Exception as exc:
                    logging_message = f'MEDIA SEARCH: {exc}'
                    try:
                        import logging
                        logging.warning(logging_message)
                    except Exception:
                        pass
                    continue

                def apply_results(results=results, kind=kind, query=query):
                    if getattr(self, 'dynamic_space', None) is not None and results:
                        self.dynamic_space.update_media_search(kind, results, query)

                QTimer.singleShot(0, apply_results)

        threading.Thread(target=worker, daemon=True, name='jarvis-media-search').start()

    JarvisWindow.add_chat_msg = add_chat_msg_with_media
    JarvisWindow._jarvis_media_bridge_installed = True


_install_dynamic_media_bridge()

__all__ = ['MediaResult', 'WebMediaProvider']