from pathlib import Path
p = Path('assistant.py')
s = p.read_text(encoding='utf-8')
old = '''    def add_chat_msg(self, sender, msg):\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            self._handle_media_search_intent(str(msg))\n'''
new = '''    def add_chat_msg(self, sender, msg):\n        media_handled = False\n        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            media_handled = self._handle_media_search_intent(str(msg))\n'''
if old not in s:
    raise SystemExit('add_chat_msg media block not found')
s = s.replace(old, new, 1)
old2 = '''        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            self.dynamic_space.update_from_response(msg)\n'''
new2 = '''        if sender in ("Jarvis", "J.A.R.V.I.S.") and not media_handled:\n            self.dynamic_space.update_from_response(msg)\n'''
if old2 not in s:
    raise SystemExit('dynamic update block not found')
s = s.replace(old2, new2, 1)
p.write_text(s, encoding='utf-8')
print('media refresh fixed')
