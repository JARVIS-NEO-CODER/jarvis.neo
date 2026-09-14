# Modularization engine for assistant.py. Deterministic and idempotent.
from __future__ import annotations
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"assistant.py"
MEMORY_TARGET=ROOT/"core"/"legacy_memory.py"
COMPONENT_TARGET=ROOT/"core"/"assistant_components.py"
IMPORT_LINE="from core.legacy_memory import MemoryManager"
COMPONENT_IMPORT="from core.assistant_components import (\n    CameraManager, PluginManager, ToolManager, SpeechEngine, CommandProcessor,\n    ModuleWindow, SecurityModuleWidget, SystemMonitorWidget, RetroVisionWidget,\n    MacrosWidget, NtfySettingsWidget, HolographicFrame, GlowButton,\n    TechProgressBar, AudioLevelBar, ArcReactor, PrivacyActivityPanel, JarvisWindow,\n    configure_components,\n)"
COMPONENT_CLASSES=["CameraManager","PluginManager","ToolManager","SpeechEngine","CommandProcessor","ModuleWindow","SecurityModuleWidget","SystemMonitorWidget","RetroVisionWidget","MacrosWidget","NtfySettingsWidget","HolographicFrame","GlowButton","TechProgressBar","AudioLevelBar","ArcReactor","PrivacyActivityPanel","JarvisWindow"]


def extract_memory(source):
    if IMPORT_LINE in source: return source,False
    tree=ast.parse(source); node=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="MemoryManager"),None)
    if not node: raise SystemExit("MemoryManager class not found")
    lines=source.splitlines(keepends=True); start,end=node.lineno-1,node.end_lineno; body="".join(lines[start:end]).rstrip()+"\n"
    MEMORY_TARGET.parent.mkdir(parents=True,exist_ok=True)
    MEMORY_TARGET.write_text('"""Legacy SQLite memory adapter."""\nfrom __future__ import annotations\nimport datetime, json, time\nfrom pathlib import Path\n\n'+body+'\n__all__=["MemoryManager"]\n',encoding="utf-8")
    return "".join(lines[:start])+IMPORT_LINE+"\n"+"".join(lines[end:]),True


def extract_components(source):
    if "from core.assistant_components import (" in source: return source,False
    tree=ast.parse(source); nodes={n.name:n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in COMPONENT_CLASSES}
    missing=[n for n in COMPONENT_CLASSES if n not in nodes]
    if missing: raise SystemExit("Component classes missing: "+", ".join(missing))
    lines=source.splitlines(keepends=True); spans=sorted((nodes[n].lineno-1,nodes[n].end_lineno,n) for n in COMPONENT_CLASSES)
    if not COMPONENT_TARGET.exists():
        raise SystemExit("core/assistant_components.py is missing; restore the generated component module before continuing")
    ranges=[(a,b) for a,b,_ in spans]+[(i,i+1) for i,l in enumerate(lines) if any(l.strip().startswith(f"{x} = ") for x in {"camera_manager","plugin_manager","tools","speech","processor"})]
    ranges.sort(); kept=[]; cursor=0
    for a,b in ranges:
        if a<cursor: continue
        kept.extend(lines[cursor:a]); cursor=b
    kept.extend(lines[cursor:]); source="".join(kept)
    if COMPONENT_IMPORT not in source:
        source=source.replace("from pathlib import Path\n","from pathlib import Path\n\n"+COMPONENT_IMPORT+"\n",1)
    marker="# --- INTENT ENGINE & AI ---\n"
    bootstrap="""# --- EXTRACTED COMPONENT RUNTIME ---\nconfigure_components(**globals())\ncamera_manager = CameraManager()\nplugin_manager = PluginManager(PLUGINS_DIR)\ntools = ToolManager()\nspeech = SpeechEngine()\nprocessor = CommandProcessor()\nconfigure_components(**globals())\n\n"""
    source=source.replace(marker,bootstrap+marker,1)
    return source,True


def ensure_runtime_sync(source):
    marker="processor = CommandProcessor()\n"
    sync="processor = CommandProcessor()\nconfigure_components(**globals())\n"
    if "processor = CommandProcessor()\nconfigure_components(**globals())" in source: return source,False
    if marker not in source: raise SystemExit("CommandProcessor bootstrap not found")
    return source.replace(marker,sync,1),True


def _replace_once(text: str, old: str, new: str) -> tuple[str, bool]:
    if old not in text: return text, False
    return text.replace(old, new, 1), True


def apply_component_fixes() -> bool:
    """Apply small, source-controlled fixes to the generated component module."""
    if not COMPONENT_TARGET.exists(): return False
    text = COMPONENT_TARGET.read_text(encoding="utf-8")
    original = text

    if "from urllib.parse import quote_plus" not in text:
        text = text.replace("from pathlib import Path\n", "from pathlib import Path\nfrom urllib.parse import quote_plus\n", 1)

    intent = 'r"(?:cherche|recherche|trouve|montre)\\s+(?:des?\\s+)?(?:images?|photos?)\\s+(?:de|sur|pour)?\\s*(.+)": self.image_search,'
    if intent not in text:
        marker = '            r"cherche\\s+(.+)": self.web_search, r"note\\s+(.+)": self.take_note,'
        replacement = '            r"(?:cherche|recherche|trouve|montre)\\s+(?:des?\\s+)?(?:images?|photos?)\\s+(?:de|sur|pour)?\\s*(.+)": self.image_search,\n            r"cherche\\s+(.+)": self.web_search, r"note\\s+(.+)": self.take_note,'
        text, _ = _replace_once(text, marker, replacement)

    if "    def image_search(self, query):" not in text:
        marker = "    def web_search(self, query):\n"
        method = '''    def image_search(self, query):\n        query = str(query).strip()\n        if not query:\n            return "Sujet de recherche d'images manquant."\n        try:\n            from .web_media import WebMediaProvider\n            WebMediaProvider().search_images(query, limit=8)\n        except Exception as exc:\n            _log.warning("Recherche images échouée: %s", exc)\n            url = "https://www.google.com/search?q=" + quote_plus(query) + "&tbm=isch&hl=fr&safe=active"\n            _signals.open_url.emit(url)\n        return f"Recherche d'images lancée pour « {query} »."\n\n'''
        text, _ = _replace_once(text, marker, method + marker)

    old_web_prefix = '    def web_search(self, query):\n        url = f"https://www.google.com/search?q='
    if old_web_prefix in text:
        start = text.index(old_web_prefix)
        end = text.index('    def take_note(', start)
        new_web = '''    def web_search(self, query):\n        query = str(query).strip()\n        url = "https://www.google.com/search?q=" + quote_plus(query)\n        _signals.open_url.emit(url)\n        return f"Recherche web exécutée pour : {query}"\n\n'''
        text = text[:start] + new_web + text[end:]

    text, _ = _replace_once(
        text,
        '    def save(self): signals.log_msg.emit("Macros","Routine enregistrée.")\n',
        '    def save(self):\n        _signals.log_msg.emit("Macros", "Routine enregistrée.")\n',
    )

    if text != original:
        COMPONENT_TARGET.write_text(text, encoding="utf-8")
        return True
    return False


def apply_web_security_fixes(source: str) -> tuple[str, bool]:
    """Harden the remote dashboard against HTML injection and HTTPS deployments."""
    original = source
    old = '''            function appendMsg(sender, text) {\n                const div = document.createElement('div');\n                div.className = 'msg ' + (sender.includes('Vous') ? 'user' : 'jarvis');\n                div.innerHTML = `<b>${sender}:</b> ${text}`;\n                chat.appendChild(div);\n                chat.scrollTop = chat.scrollHeight;\n            }'''
    new = '''            function appendMsg(sender, text) {\n                const div = document.createElement('div');\n                div.className = 'msg ' + (String(sender).includes('Vous') ? 'user' : 'jarvis');\n                const name = document.createElement('b');\n                name.textContent = String(sender) + ': ';\n                const body = document.createTextNode(String(text));\n                div.appendChild(name);\n                div.appendChild(body);\n                chat.appendChild(div);\n                chat.scrollTop = chat.scrollHeight;\n            }'''
    source, _ = _replace_once(source, old, new)
    old_ws = "            const ws = new WebSocket(`ws://${location.host}/ws?token=${encodeURIComponent(jarvisToken || '')}`);"
    new_ws = "            const wsScheme = location.protocol === 'https:' ? 'wss' : 'ws';\n            const ws = new WebSocket(`${wsScheme}://${location.host}/ws?token=${encodeURIComponent(jarvisToken || '')}`);"
    source, _ = _replace_once(source, old_ws, new_ws)
    return source, source != original


def main():
    source=SOURCE.read_text(encoding="utf-8")
    changed=False
    source,c=extract_memory(source); changed|=c
    source,c=extract_components(source); changed|=c
    source,c=ensure_runtime_sync(source); changed|=c
    source,c=apply_web_security_fixes(source); changed|=c
    ast.parse(source,filename=str(SOURCE))
    if changed: SOURCE.write_text(source,encoding="utf-8")
    component_changed=apply_component_fixes()
    ast.parse(COMPONENT_TARGET.read_text(encoding="utf-8"),filename=str(COMPONENT_TARGET))
    changed |= component_changed
    print("Assistant modularization/audit pass completed" if changed else "Assistant modularization/audit already applied")

if __name__=="__main__": main()
