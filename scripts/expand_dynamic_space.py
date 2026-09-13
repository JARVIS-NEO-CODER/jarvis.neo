from pathlib import Path
import re

path = Path('assistant.py')
text = path.read_text(encoding='utf-8')

# Make Dynamic Space a real contextual display, not a short preview.
text = text.replace('self.setMaximumHeight(220)', 'self.setMinimumHeight(180)\n        self.setMaximumHeight(420)', 1)

pattern = re.compile(r'    def update_from_response\(self, message\):\n.*?(?=\nclass JarvisWindow\()', re.S)
replacement = '''    def update_from_response(self, message):
        """Display as much useful response content as possible automatically."""
        text = str(message or "").strip()
        if not text:
            return

        # Keep the complete response available. QTextEdit handles long content
        # with its own vertical scrollbar, so useful information is never thrown
        # away just to make a small preview.
        self.content.setPlainText(text)
        self.content.moveCursor(self.content.textCursor().MoveOperation.Start)

        # Lightweight metadata makes the space useful even for very long answers.
        lines = [line for line in text.splitlines() if line.strip()]
        urls = re.findall(r'https?://\\S+', text)
        code_blocks = text.count('```') // 2
        parts = []
        parts.append(f"{len(text):,} caractères".replace(',', ' '))
        parts.append(f"{len(lines)} lignes")
        if urls:
            parts.append(f"{len(urls)} lien{'s' if len(urls) > 1 else ''}")
        if code_blocks:
            parts.append(f"{code_blocks} bloc{'s' if code_blocks > 1 else ''} code")
        self.meta.setText(" · ".join(parts).upper())
        self.content.verticalScrollBar().setValue(0)
'''

new_text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit('Dynamic Space method not found')

path.write_text(new_text, encoding='utf-8')
print('Dynamic Space expanded')
