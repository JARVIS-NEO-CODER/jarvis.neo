from pathlib import Path
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

marker = '    def update_from_response(self, text):\n'
if marker in s and 'def update_search_results(self, results, query="")' not in s:
    method = '''    def update_search_results(self, results, query=""):\n        """Render search results as clean cards instead of exposing raw URLs."""\n        self._clear_body()\n        self.header.setText("◈ WEB SEARCH" + (f" · {query}" if query else ""))\n        items = list(results or [])\n        if not items:\n            self._text_card("Aucun résultat exploitable.")\n            return\n        for index, result in enumerate(items, 1):\n            result_title = str(getattr(result, "title", "Sans titre") or "Sans titre")\n            url = str(getattr(result, "url", "") or "")\n            snippet = str(getattr(result, "snippet", "") or "")\n            frame = QFrame()\n            frame.setStyleSheet("QFrame { border: 1px solid rgba(0,243,255,70); border-radius: 10px; padding: 8px; } QLabel { border: none; }")\n            layout = QVBoxLayout(frame)\n            layout.setContentsMargins(10, 8, 10, 8)\n            label = QLabel(f"{index}. {html.escape(result_title)}")\n            label.setTextFormat(Qt.TextFormat.RichText)\n            label.setStyleSheet("font-weight: 700; color: #00f3ff; padding: 0;")\n            label.setWordWrap(True)\n            layout.addWidget(label)\n            if snippet:\n                desc = QLabel(html.escape(snippet))\n                desc.setTextFormat(Qt.TextFormat.RichText)\n                desc.setWordWrap(True)\n                desc.setStyleSheet("color: #d7e7ee; padding: 2px 0 4px 0;")\n                layout.addWidget(desc)\n            if url:\n                button = QPushButton("🔗 Ouvrir le résultat")\n                button.setCursor(Qt.CursorShape.PointingHandCursor)\n                button.clicked.connect(lambda checked=False, u=url: webbrowser.open(u))\n                layout.addWidget(button)\n            self.body_layout.insertWidget(max(0, self.body_layout.count() - 1), frame)\n        self.scroll.verticalScrollBar().setValue(0)\n\n'''
    s = s.replace(marker, method + marker, 1)

pattern = re.compile(r'    def web_search\(self, query\):\n.*?(?=\n    def |\nclass |\nif __name__ ==)', re.S)
match = pattern.search(s)
if not match:
    raise SystemExit('web_search method not found')
replacement = '''    def web_search(self, query):\n        """Search the web and feed structured results directly to Dynamic Space."""\n        try:\n            from core.web_search import WebSearchProvider\n            provider = WebSearchProvider(timeout=8.0)\n            results = provider.search(str(query), limit=6)\n            if hasattr(self, "dynamic_space"):\n                self.dynamic_space.update_search_results(results, str(query))\n            for result in results[:3]:\n                try:\n                    self.signals.open_url.emit(result.url)\n                except Exception:\n                    pass\n            lines = [f"{i}. {r.title}\\n{r.snippet}" for i, r in enumerate(results, 1)]\n            return "Résultats trouvés pour « " + str(query) + " » :\\n\\n" + "\\n\\n".join(lines)\n        except Exception as exc:\n            logging.warning("WEB SEARCH: %s", exc)\n            return "Recherche indisponible : " + str(exc)\n'''
s = s[:match.start()] + replacement + s[match.end():]
p.write_text(s, encoding='utf-8')
compile(s, 'assistant.py', 'exec')
print('patched')
