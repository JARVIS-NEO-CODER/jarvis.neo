from pathlib import Path
import re

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

if 'from core.neo_theme import apply_theme' not in s:
    anchor = 'from core.web_media import WebMediaProvider\n'
    if anchor not in s:
        raise SystemExit('import anchor not found')
    s = s.replace(anchor, anchor + 'from core.neo_theme import apply_theme\n', 1)

# QApplication may be stored in a local variable, so use the live instance.
if 'apply_theme(QApplication.instance())' not in s:
    s = s.replace('apply_theme(app if \'app\' in globals() else application)', 'apply_theme(QApplication.instance())')

if 'apply_theme(QApplication.instance())' not in s:
    patterns = [
        r'(app\s*=\s*QApplication\([^\n]*\)\s*\n)',
        r'(application\s*=\s*QApplication\([^\n]*\)\s*\n)',
    ]
    inserted = False
    for pattern in patterns:
        m = re.search(pattern, s)
        if m:
            s = s[:m.end()] + 'apply_theme(QApplication.instance())\n' + s[m.end():]
            inserted = True
            break
    if not inserted:
        m = re.search(r'(?m)^([ \t]*)(?:window|main_window)\.show\(\)', s)
        if not m:
            raise SystemExit('QApplication/show anchor not found')
        indent = m.group(1)
        s = s[:m.start()] + indent + 'apply_theme(QApplication.instance())\n' + s[m.start():]

p.write_text(s, encoding='utf-8')
compile(s, 'assistant.py', 'exec')
print('Premium theme applied and assistant.py compiles.')
