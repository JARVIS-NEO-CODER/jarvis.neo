# Modularization engine for assistant.py. Keep this file intentionally deterministic and idempotent.

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assistant.py"
MEMORY_TARGET = ROOT / "core" / "legacy_memory.py"
COMPONENT_TARGET = ROOT / "core" / "assistant_components.py"
IMPORT_LINE = "from core.legacy_memory import MemoryManager"
COMPONENT_IMPORT = "from core.assistant_components import (\n    CameraManager, PluginManager, ToolManager, SpeechEngine, CommandProcessor,\n    ModuleWindow, SecurityModuleWidget, SystemMonitorWidget, RetroVisionWidget,\n    MacrosWidget, NtfySettingsWidget, HolographicFrame, GlowButton,\n    TechProgressBar, AudioLevelBar, ArcReactor, PrivacyActivityPanel, JarvisWindow,\n    configure_components,\n)"
COMPONENT_CLASSES = [
    "CameraManager", "PluginManager", "ToolManager", "SpeechEngine", "CommandProcessor",
    "ModuleWindow", "SecurityModuleWidget", "SystemMonitorWidget", "RetroVisionWidget",
    "MacrosWidget", "NtfySettingsWidget", "HolographicFrame", "GlowButton",
    "TechProgressBar", "AudioLevelBar", "ArcReactor", "PrivacyActivityPanel", "JarvisWindow",
]
COMPONENT_PRELUDE = '''"""Runtime components extracted from the historical assistant monolith."""
from __future__ import annotations
import asyncio, datetime, importlib.util, json, logging, os, pathlib, queue, re, subprocess, sys, threading, time
from pathlib import Path
import psutil, pyautogui, pyperclip, speech_recognition as sr
try: import numpy as np
except ImportError: np = None
try: import ollama
except ImportError: ollama = None
try: import edge_tts
except ImportError: edge_tts = None
try: import pygame
except ImportError: pygame = None
try: import cv2
except ImportError: cv2 = None
try: import sounddevice as sd
except ImportError: sd = None
try: import soundfile as sf
except ImportError: sf = None
try: import whisper
except ImportError: whisper = None
from PyQt6.QtCore import QObject, QPoint, QPointF, QRect, QTimer, Qt, pyqtSignal, QCoreApplication, QUrl, QEvent
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QImage, QIcon, QPixmap, QPolygonF, QLinearGradient
from PyQt6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QComboBox, QWidget, QSystemTrayIcon, QMenu, QCheckBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
state = signals = memory = config = None
log = logging.getLogger("jarvis_neo")
def configure_components(**dependencies):
    globals().update(dependencies)
'''

def extract_memory(source):
    if IMPORT_LINE in source:
        return source, False
    tree = ast.parse(source, filename=str(SOURCE))
    node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MemoryManager"), None)
    if not node or node.end_lineno is None:
        raise SystemExit("MemoryManager class not found")
    lines = source.splitlines(keepends=True)
    start, end = node.lineno - 1, node.end_lineno
    class_source = "".join(lines[start:end]).rstrip() + "\n"
    MEMORY_TARGET.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_TARGET.write_text('"""Legacy SQLite memory adapter kept compatible with the historical assistant runtime."""\nfrom __future__ import annotations\nimport datetime\nimport json\nimport time\nfrom pathlib import Path\n\n' + class_source + '\n__all__ = ["MemoryManager"]\n', encoding="utf-8")
    return "".join(lines[:start]) + IMPORT_LINE + "\n" + "".join(lines[end:]), True

def extract_components(source):
    if "from core.assistant_components import (" in source:
        return source, False
    tree = ast.parse(source, filename=str(SOURCE))
    nodes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in COMPONENT_CLASSES}
    missing = [n for n in COMPONENT_CLASSES if n not in nodes]
    if missing:
        raise SystemExit("Component classes missing: " + ", ".join(missing))
    lines = source.splitlines(keepends=True)
    spans = sorted((nodes[n].lineno - 1, nodes[n].end_lineno, n) for n in COMPONENT_CLASSES)
    extracted = ["# --- extracted components ---\n"]
    for start, end, name in spans:
        extracted.append("\n" + "".join(lines[start:end]).rstrip() + "\n")
    COMPONENT_TARGET.parent.mkdir(parents=True, exist_ok=True)
    COMPONENT_TARGET.write_text(COMPONENT_PRELUDE + "\n".join(extracted) + "\n__all__ = [" + ", ".join(repr(n) for n in COMPONENT_CLASSES) + ", 'configure_components']\n", encoding="utf-8")
    remove_ranges = [(start, end) for start, end, _ in spans]
    for idx, line in enumerate(lines):
        if any(line.strip().startswith(f"{name} = ") for name in {"camera_manager", "plugin_manager", "tools", "speech", "processor"}):
            remove_ranges.append((idx, idx + 1))
    remove_ranges.sort()
    kept, cursor = [], 0
    for start, end in remove_ranges:
        if start < cursor: continue
        kept.extend(lines[cursor:start]); cursor = end
    kept.extend(lines[cursor:])
    source = "".join(kept)
    if COMPONENT_IMPORT not in source:
        source = source.replace("from pathlib import Path\n", "from pathlib import Path\n\n" + COMPONENT_IMPORT + "\n", 1)
    marker = "# --- INTENT ENGINE & AI ---\n"
    bootstrap = '''# --- EXTRACTED COMPONENT RUNTIME ---
configure_components(**globals())
camera_manager = CameraManager()
plugin_manager = PluginManager(PLUGINS_DIR)
tools = ToolManager()
speech = SpeechEngine()
processor = CommandProcessor()

'''
    source = source.replace(marker, bootstrap + marker, 1)
    return source, True

def main():
    source = SOURCE.read_text(encoding="utf-8")
    source, memory_changed = extract_memory(source)
    source, components_changed = extract_components(source)
    if memory_changed or components_changed:
        SOURCE.write_text(source, encoding="utf-8")
        ast.parse(source, filename=str(SOURCE))
        print("Assistant modularization pass completed")
    else:
        print("Assistant modularization already applied")

if __name__ == "__main__":
    main()

# Trigger marker: component extraction pipeline v2
