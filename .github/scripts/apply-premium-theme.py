from pathlib import Path

p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

import_line = 'from core.neo_theme import apply_theme'
if import_line not in s:
    anchor = 'from core.web_media import WebMediaProvider\n'
    if anchor not in s:
        raise SystemExit('import anchor not found')
    s = s.replace(anchor, anchor + import_line + '\n', 1)

hook = '    apply_theme(QApplication.instance(), window)\n'
# Remove any previous variants of the hook so the final hook is deterministic.
s = s.replace('    apply_theme(QApplication.instance())\n', '')
s = s.replace('    apply_theme(app if \'app\' in globals() else application)\n', '')
s = s.replace('    apply_theme(QApplication.instance(), window)\n', '')

anchor = '    window = JarvisWindow()\n'
if anchor not in s:
    raise SystemExit('window construction anchor not found')
s = s.replace(anchor, anchor + hook, 1)

p.write_text(s, encoding='utf-8')
compile(s, 'assistant.py', 'exec')
print('Premium theme hook installed on the actual JarvisWindow.')
