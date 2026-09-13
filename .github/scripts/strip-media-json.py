from pathlib import Path
import ast
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

# Add a small sanitizer next to the media-intent handler.
marker = '    def _handle_media_search_intent(self, message):\n'
if marker not in s:
    raise SystemExit('media handler marker not found')

helper = '''    def _sanitize_media_response(self, message):\n        """Hide internal media JSON from the user-facing chat while preserving its intent."""\n        text = str(message or "")\n        # Remove fenced JSON blocks and standalone JSON objects containing media kinds.\n        text = re.sub(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", lambda m: "", text, flags=re.S | re.I)\n\n        def remove_media_object(m):\n            raw = m.group(0)\n            return "" if re.search(r'\\\"kind\\\"\\s*:\\s*\\\"(?:image_search|video_search)\\\"', raw, re.I) else raw\n\n        # Non-greedy object scan is sufficient for the flat media payload JARVIS emits.\n        text = re.sub(r"\\{[^{}]{0,5000}\\}", remove_media_object, text, flags=re.S)\n        # Remove the common pseudo-markup prefix accidentally emitted before JSON.\n        text = re.sub(r"\\b(?:NEO_PANEL|LIVE FEED)\\s*", "", text, flags=re.I)\n        text = re.sub(r"\\n[ \\t]*\\n[ \\t]*", "\\n\\n", text)\n        return text.strip()\n\n'''
if '_sanitize_media_response(self, message)' not in s:
    s = s.replace(marker, helper + marker, 1)

# Make the existing handler robust to JSON embedded anywhere in prose.
old = '        objects = re.findall(r"\\{.*?\\}", str(message), flags=re.S)\n'
new = '        objects = re.findall(r"\\{[^{}]{0,5000}\\}", str(message), flags=re.S)\n'
if old in s:
    s = s.replace(old, new, 1)

# add_chat_msg: sanitize only the user-visible Jarvis message, never system messages.
needle = '        bubble = f"<div style=\'margin: 8px 0;\'><b style=\'color:{color};\'>{sender}</b><div style=\'background: rgba(0,20,40,0.72); padding: 10px 12px; border-radius: 10px; margin-top: 4px;\'>{msg}</div></div>"\n'
if needle not in s:
    raise SystemExit('chat bubble marker not found')
replacement = '''        display_msg = msg\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            display_msg = self._sanitize_media_response(msg) or ""\n        bubble = f"<div style='margin: 8px 0;'><b style='color:{color};'>{sender}</b><div style='background: rgba(0,20,40,0.72); padding: 10px 12px; border-radius: 10px; margin-top: 4px;'>{display_msg}</div></div>"\n'''
s = s.replace(needle, replacement, 1)

p.write_text(s, encoding='utf-8')
compile(s, 'assistant.py', 'exec')
print('patched')
