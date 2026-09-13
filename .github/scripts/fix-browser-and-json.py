from pathlib import Path
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

# The previous patcher expected an older add_chat_msg layout. The current
# code already has the media parser, so patch the actual display path instead.

# 1) webbrowser is required by the non-WebEngine fallback.
if re.search(r'^import webbrowser\s*$', s, re.M) is None:
    imports = re.search(r'^(?:import|from) .*$', s, re.M)
    if imports:
        s = s[:imports.start()] + 'import webbrowser\n' + s[imports.start():]
    else:
        s = 'import webbrowser\n' + s

# 2) Never show the raw internal media JSON in the visible chat.
marker = '    def add_chat_msg(self, sender, msg):\n'
start = s.find(marker)
if start < 0:
    raise SystemExit('add_chat_msg not found')
end = s.find('\n    def ', start + len(marker))
if end < 0:
    raise SystemExit('add_chat_msg end not found')
body = s[start:end]

body = body.replace(
    '        media_handled = False\n'
    '        display_msg = str(msg)\n'
    '        if sender in ("Jarvis", "J.A.R.V.I.S."):\n'
    '            media_handled, display_msg = self._handle_media_search_intent(display_msg)\n',
    '        media_handled = False\n'
    '        display_msg = str(msg)\n'
    '        if sender in ("Jarvis", "J.A.R.V.I.S."):\n'
    '            media_handled, display_msg = self._handle_media_search_intent(display_msg)\n'
)

# Replace only the user-visible message variable in the bubble and escaping.
body = body.replace('{msg}</span></div>', '{display_msg}</span></div>')
body = body.replace('{msg}</span></div>', '{display_msg}</span></div>')
body = body.replace('html.escape(str(msg))', 'html.escape(str(display_msg))')
body = body.replace('bubble = bubble.replace(str(msg), safe_msg)', 'bubble = bubble.replace(str(display_msg), safe_msg)')
body = body.replace('self.dynamic_space.update_from_response(msg)', 'self.dynamic_space.update_from_response(display_msg)')

s = s[:start] + body + s[end:]

# 3) Make the browser gateway deterministic:
#    - embedded QWebEngine when available
#    - Windows/default browser fallback otherwise
marker = '    def load_url_in_browser(self, url_str):\n'
start = s.find(marker)
if start < 0:
    raise SystemExit('load_url_in_browser not found')
end = s.find('\n    def ', start + len(marker))
if end < 0:
    raise SystemExit('load_url_in_browser end not found')
new_browser = '''    def load_url_in_browser(self, url_str):
        """Open a URL in the embedded browser, with a real system-browser fallback."""
        url_str = str(url_str or "").strip()
        if not url_str:
            return
        if not url_str.startswith(("http://", "https://")):
            url_str = "https://" + url_str
        try:
            if WEBENGINE_OK and hasattr(self, "web_view"):
                self.chat_display.hide()
                self.web_view.setUrl(QUrl(url_str))
                self.web_view.show()
                if hasattr(self, "browser_toolbar_widget"):
                    self.browser_toolbar_widget.show()
                if hasattr(self, "url_bar"):
                    self.url_bar.setText(url_str)
                signals.log_msg.emit("J.A.R.V.I.S.", f"Navigateur intégré : {url_str}")
                return
        except Exception as exc:
            logging.warning("WEBENGINE: chargement échoué: %s", exc)

        # PyQtWebEngine is optional. Never let a missing/failed embedded engine
        # make web navigation silently do nothing.
        try:
            opened = webbrowser.open(url_str, new=2)
            logging.info("WEB: navigateur système demandé (%s): %s", opened, url_str)
            if not opened:
                webbrowser.open_new_tab(url_str)
        except Exception as exc:
            logging.error("WEB: navigateur système indisponible: %s", exc)
            signals.log_msg.emit("Web", f"Impossible d'ouvrir le navigateur : {exc}")
'''
s = s[:start] + new_browser + s[end:]

# 4) The top-right gateway button should actually open a web page instead of
#    sending the unrelated 'ip' command.
old = 'self.btn_ip.clicked.connect(lambda: command_queue.put("ip"))'
if old in s:
    s = s.replace(old, 'self.btn_ip.clicked.connect(lambda: self.load_url_in_browser("https://www.google.com"))', 1)

p.write_text(s, encoding='utf-8')
print('patched browser + media display')
