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

COMPONENT_PRELUDE = '''"""Runtime components extracted from the historical assistant monolith.

The module deliberately receives its runtime dependencies through configure_components()
so the extraction does not create a circular import back into assistant.py.
"""
from __future__ import annotations

import asyncio
import datetime
import importlib.util
import json
import logging
import os
import pathlib
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import pyautogui
import pyperclip
import speech_recognition as sr

try:
    import numpy as np
except ImportError:
    np = None
try:
    import ollama
except ImportError:
    ollama = None
try:
    import edge_tts
except ImportError:
    edge_tts = None
try:
    import pygame
except ImportError:
    pygame = None
try:
    import cv2
except ImportError:
    cv2 = None
try:
    import sounddevice as sd
except ImportError:
    sd = None
try:
    import soundfile as sf
except ImportError:
    sf = None
try:
    import whisper
except ImportError:
    whisper = None

from PyQt6.QtCore import (
    QObject, QPoint, QPointF, QRect, QTimer, Qt, pyqtSignal, QCoreApplication, QUrl, QEvent
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QImage, QIcon, QPixmap, QPolygonF,
    QLinearGradient
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QComboBox,
    QWidget, QSystemTrayIcon, QMenu, QCheckBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView
)

state = signals = memory = config = None
log = logging.getLogger("jarvis_neo")


def configure_components(**dependencies):
    """Inject assistant runtime objects without importing assistant.py."""
    globals().update(dependencies)

'''


def extract_memory(source: str) -> tuple[str, bool]:
    if IMPORT_LINE in source:
        return source, False
    tree = ast.parse(source, filename=str(SOURCE))
    node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MemoryManager"), None)
    if node is None:
        raise SystemExit("MemoryManager class not found")
    if node.end_lineno is None:
        raise SystemExit("MemoryManager has no end line")
    lines = source.splitlines(keepends=True)
    start, end = node.lineno - 1, node.end_lineno
    class_source = "".join(lines[start:end]).rstrip() + "\n"
    MEMORY_TARGET.parent.mkdir(parents=True, exist_ok=True)
    module = (
        '"""Legacy SQLite memory adapter kept compatible with the historical assistant runtime."""\n'
        "from __future__ import annotations\n\n"
        "import datetime\nimport json\nimport time\nfrom pathlib import Path\n\n"
        + class_source + "\n\n__all__ = [\"MemoryManager\"]\n"
    )
    MEMORY_TARGET.write_text(module, encoding="utf-8")
    source = "".join(lines[:start]) + IMPORT_LINE + "\n" + "".join(lines[end:])
    return source, True


def extract_components(source: str) -> tuple[str, bool]:
    if "from core.assistant_components import (" in source:
        return source, False

    tree = ast.parse(source, filename=str(SOURCE))
    nodes = {
        n.name: n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name in COMPONENT_CLASSES
    }
    missing = [name for name in COMPONENT_CLASSES if name not in nodes]
    if missing:
        raise SystemExit(f"Component classes missing: {', '.join(missing)}")

    lines = source.splitlines(keepends=True)
    spans = sorted((nodes[name].lineno - 1, nodes[name].end_lineno, name) for name in COMPONENT_CLASSES)
    extracted = ["# --- extracted components ---\n"]
    for start, end, name in spans:
        extracted.append("\n" + "".join(lines[start:end]).rstrip() + "\n")

    COMPONENT_TARGET.parent.mkdir(parents=True, exist_ok=True)
    COMPONENT_TARGET.write_text(
        COMPONENT_PRELUDE + "\n".join(extracted) + "\n\n__all__ = [" + ", ".join(repr(n) for n in COMPONENT_CLASSES) + ", 'configure_components']\n",
        encoding="utf-8",
    )

    # Remove the class blocks, plus their historical eager instantiation lines.
    remove_ranges = [(start, end) for start, end, _ in spans]
    extra_names = {"camera_manager", "plugin_manager", "tools", "speech", "processor"}
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(f"{name} = ") for name in extra_names):
            remove_ranges.append((idx, idx + 1))

    remove_ranges.sort()
    kept = []
    cursor = 0
    for start, end in remove_ranges:
        if start < cursor:
            continue
        kept.extend(lines[cursor:start])
        cursor = end
    kept.extend(lines[cursor:])
    source = "".join(kept)

    # Import the extracted classes immediately after the standard imports.
    if COMPONENT_IMPORT not in source:
        marker = "from pathlib import Path\n"
        source = source.replace(marker, marker + "\n" + COMPONENT_IMPORT + "\n", 1)

    # Recreate runtime instances after helper functions used by the components exist.
    marker = "# --- INTENT ENGINE & AI ---\n"
    bootstrap = '''# --- EXTRACTED COMPONENT RUNTIME ---
configure_components(**globals())
camera_manager = CameraManager()
plugin_manager = PluginManager(PLUGINS_DIR)
tools = ToolManager()
speech = SpeechEngine()
processor = CommandProcessor()

'''
    if bootstrap not in source:
        source = source.replace(marker, bootstrap + marker, 1)
    return source, True


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    changed = False

    source, did_memory = extract_memory(source)
    changed |= did_memory

    source, did_components = extract_components(source)
    changed |= did_components

    if changed:
        SOURCE.write_text(source, encoding="utf-8")
        ast.parse(source, filename=str(SOURCE))
        print("Assistant modularization pass completed")
    else:
        print("Assistant modularization already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
