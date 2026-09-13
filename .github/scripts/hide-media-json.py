from pathlib import Path
import ast
import json
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

# Add a cleaner that extracts only recognized media-intent JSON and returns
# the natural-language part for the chat bubble.
marker = '    def _handle_media_search_intent(self, message):\n'
start = s.find(marker)
if start < 0:
    raise SystemExit('media handler not found')

# Locate method end by next class-level method.
next_method = s.find('\n    def ', start + len(marker))
if next_method < 0:
    raise SystemExit('media handler end not found')

old = s[start:next_method]
new = '''    def _handle_media_search_intent(self, message):
        """Extract media-intent JSON from JARVIS output without exposing it in chat."""
        text = str(message or "")
        intents = []
        spans = []

        # Parse JSON objects embedded in prose, fenced blocks, NEO_PANEL output,
        # etc. Only recognized media kinds are consumed, so normal JSON/code stays visible.
        for match in re.finditer(r"\\{", text):
            decoder = json.JSONDecoder()
            try:
                obj, end = decoder.raw_decode(text[match.start():])
            except (ValueError, TypeError):
                continue
            if not isinstance(obj, dict):
                continue
            kind = str(obj.get("kind", "")).lower().strip()
            if kind not in {"image_search", "video_search"}:
                continue
            query = str(obj.get("query", "")).strip()
            if not query:
                continue
            intents.append((kind, obj))
            spans.append((match.start(), match.start() + end))

        # Deduplicate overlapping/duplicate intent objects.
        unique = []
        seen = set()
        for kind, obj in intents:
            key = (kind, str(obj.get("query", "")).strip().lower())
            if key not in seen:
                seen.add(key)
                unique.append((kind, obj))

        for kind, obj in unique:
            try:
                provider = WebMediaProvider()
                query = str(obj.get("query", "")).strip()
                if kind == "image_search":
                    results = provider.search_images(query, limit=8)
                else:
                    results = provider.search_videos(query, limit=8)
                payload = []
                for item in results or []:
                    if hasattr(item, "__dict__"):
                        payload.append(dict(item.__dict__))
                    elif isinstance(item, dict):
                        payload.append(item)
                self.dynamic_space.update_media_search(kind, payload, query)
            except Exception as exc:
                logging.warning("MEDIA: recherche %s échouée: %s", kind, exc)

        if not unique:
            return False, text

        # Remove the exact JSON objects first.
        cleaned = text
        for a, b in sorted(spans, reverse=True):
            cleaned = cleaned[:a] + cleaned[b:]

        # Remove formatting wrappers left around an extracted internal panel.
        cleaned = re.sub(r"(?im)^\\s*(?:NEO_PANEL|\\*\\*\\*\\s*json|\\*\\*\\s*json|s\\*json)\\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^\\s*\\*\\*\\s*(?:Images?|Vidéos?)\\s*\\*\\*\\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^\\s*(?:\\{\\s*)?\\s*$", "", cleaned)
        cleaned = re.sub(r"[ \\t]+\\n", "\\n", cleaned)
        cleaned = re.sub(r"\\n{3,}", "\\n\\n", cleaned).strip()

        if not cleaned:
            cleaned = "Contenu multimédia chargé dans le Dynamic Space."
        return True, cleaned
'''
s = s[:start] + new + s[next_method:]

# Change add_chat_msg to use the cleaned text for the visible bubble.
needle = '''        media_handled = False\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            media_handled = self._handle_media_search_intent(str(msg))\n'''
replacement = '''        media_handled = False\n        display_msg = str(msg)\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            media_handled, display_msg = self._handle_media_search_intent(display_msg)\n'''
if needle not in s:
    raise SystemExit('add_chat_msg media block not found')
s = s.replace(needle, replacement, 1)

# The bubble must use display_msg, while media detection already consumed the raw message.
s = s.replace('        safe_msg = html.escape(str(msg))\n', '        safe_msg = html.escape(display_msg)\n', 1)

p.write_text(s, encoding='utf-8')
print('patched assistant.py')
