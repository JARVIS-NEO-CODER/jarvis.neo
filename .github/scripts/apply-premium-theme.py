from pathlib import Path
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

# Import the visual layer once.
if 'from core.neo_theme import apply_theme' not in s:
    anchor = 'from core.web_media import WebMediaProvider\n'
    if anchor not in s:
        raise SystemExit('import anchor not found')
    s = s.replace(anchor, anchor + 'from core.neo_theme import apply_theme\n', 1)

# Apply after QApplication creation, before the window is shown.
if 'apply_theme(app)' not in s:
    patterns = [
        r'(app\s*=\s*QApplication\([^\n]*\)\s*\n)',
        r'(application\s*=\s*QApplication\([^\n]*\)\s*\n)',
    ]
    inserted = False
    for pattern in patterns:
        m = re.search(pattern, s)
        if m:
            s = s[:m.end()] + 'apply_theme(app if \'app\' in globals() else application)\n' + s[m.end():]
            inserted = True
            break
    if not inserted:
        # Safer fallback: insert immediately before the first main-window show call.
        m = re.search(r'(?m)^([ \t]*)(?:window|main_window)\.show\(\)', s)
        if not m:
            raise SystemExit('QApplication/show anchor not found')
        indent = m.group(1)
        s = s[:m.start()] + indent + 'apply_theme(app)\n' + s[m.start():]

p.write_text(s, encoding='utf-8')
compile(s, 'assistant.py', 'exec')
print('Premium theme applied and assistant.py compiles.')
