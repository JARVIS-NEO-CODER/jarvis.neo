"""J.A.R.V.I.S. NEO cockpit dashboard.

A lightweight, detachable command center that sits on top of the real desktop
HUD. It is intentionally self-contained so the legacy assistant remains safe.
"""
from __future__ import annotations

import os
import socket
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

try:
    import psutil
except Exception:
    psutil = None


class _Card(QFrame if False else QWidget):
    """Small styled dashboard card without another custom dependency."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QWidget { background: rgba(5,15,25,235); border: 1px solid rgba(0,243,255,75); "
            "border-radius: 10px; } QLabel { border: none; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        self.title = QLabel(title.upper())
        self.title.setStyleSheet("color:#00f3ff;font-size:9px;font-weight:700;letter-spacing:1.3px;")
        self.value = QLabel("--")
        self.value.setStyleSheet("color:#e8fbff;font-size:17px;font-weight:700;")
        self.detail = QLabel("")
        self.detail.setStyleSheet("color:#7895a5;font-size:9px;")
        self.detail.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class CockpitHud(QDialog):
    """Full detachable NEO cockpit with live system, voice and AI telemetry."""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.setWindowTitle("J.A.R.V.I.S. NEO // COCKPIT")
        self.setMinimumSize(920, 640)
        self.resize(1100, 720)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(
            "QDialog { background:#02070c; color:#dffaff; }"
            "QLabel { color:#dffaff; }"
            "QPushButton { background:#07151f;color:#bdefff;border:1px solid #16465a;"
            "border-radius:7px;padding:8px 12px;font-weight:700;font-size:10px; }"
            "QPushButton:hover { background:#0b2532;border-color:#00f3ff; }"
            "QProgressBar { background:#071018;border:1px solid #173747;border-radius:4px;height:7px;text-align:center;color:transparent; }"
            "QProgressBar::chunk { background:#00f3ff;border-radius:3px; }"
            "QScrollArea { border:none;background:transparent; }"
        )
        self._drag_pos = None
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("J.A.R.V.I.S. NEO")
        title.setStyleSheet("color:#00f3ff;font-size:17px;font-weight:800;letter-spacing:2px;")
        self.status = QLabel("● SYSTEM ONLINE")
        self.status.setStyleSheet("color:#00ffaa;font-size:10px;font-weight:700;")
        self.mode = QLabel("MODE: NORMAL")
        self.mode.setStyleSheet("color:#7895a5;font-size:9px;font-weight:700;")
        close = QPushButton("×")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.close)
        header.addWidget(title)
        header.addSpacing(14)
        header.addWidget(self.status)
        header.addStretch()
        header.addWidget(self.mode)
        header.addWidget(close)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.cards = {}
        for idx, (key, label) in enumerate([
            ("cpu", "CPU"), ("ram", "RAM"), ("temp", "TEMP"), ("net", "NETWORK"),
            ("ai", "AI CORE"), ("voice", "VOICE"),
        ]):
            card = _Card(label)
            self.cards[key] = card
            grid.addWidget(card, idx // 3, idx % 3)
        root.addLayout(grid)

        middle = QHBoxLayout()
        middle.setSpacing(10)

        activity = _Card("Activity / neural feed")
        activity.setMinimumWidth(430)
        self.activity_label = QLabel("No recent activity")
        self.activity_label.setStyleSheet("color:#8be9ff;font-family:Consolas;font-size:10px;border:none;")
        self.activity_label.setWordWrap(True)
        activity.layout().addWidget(self.activity_label)
        middle.addWidget(activity, 2)

        actions = _Card("Quick actions")
        action_layout = QGridLayout()
        action_layout.setSpacing(6)
        for i, (label, command) in enumerate([
            ("🌐 WEB", "recherche web"), ("📁 FILES", "ouvre explorateur de fichiers"),
            ("🎵 MUSIC", "ouvre lecteur musique"), ("⚙ SETTINGS", "paramètres"),
            ("🧠 AGENT", "mode agent"), ("🛡 SENTINEL", "sécurité on"),
        ]):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, c=command: self._command(c))
            action_layout.addWidget(btn, i // 2, i % 2)
        actions.layout().addLayout(action_layout)
        middle.addWidget(actions, 1)
        root.addLayout(middle, 1)

        bottom = QHBoxLayout()
        for label, slot in [("COMPACT", self._compact), ("NORMAL", self._normal), ("REFRESH", self.refresh)]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            bottom.addWidget(btn)
        bottom.addStretch()
        self.pin = QPushButton("ALWAYS ON TOP")
        self.pin.setCheckable(True)
        self.pin.setChecked(True)
        self.pin.clicked.connect(self._toggle_pin)
        bottom.addWidget(self.pin)
        root.addLayout(bottom)

    def _command(self, command: str):
        try:
            queue = getattr(self.assistant, "command_queue", None)
            if queue is not None:
                queue.put(command)
                self.activity_label.setText(f"> {command}\nCommande envoyée au moteur NEO.")
        except Exception as exc:
            self.activity_label.setText(f"> ERREUR\n{exc}")

    def _toggle_pin(self):
        flags = self.windowFlags()
        if self.pin.isChecked():
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _compact(self):
        self.resize(760, 460)

    def _normal(self):
        self.resize(1100, 720)

    def refresh(self):
        state = getattr(self.assistant, "state", None)
        config = getattr(self.assistant, "CONFIG", {}) or {}
        cpu = ram = 0
        temp = None
        if psutil:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                temps = getattr(psutil, "sensors_temperatures", lambda: {})()
                vals = [v.current for group in temps.values() for v in group if v.current is not None]
                temp = max(vals) if vals else None
            except Exception:
                pass
        self.cards["cpu"].value.setText(f"{cpu:.0f}%")
        self.cards["cpu"].detail.setText("Charge processeur")
        self.cards["ram"].value.setText(f"{ram:.0f}%")
        self.cards["ram"].detail.setText("Mémoire vive")
        self.cards["temp"].value.setText(f"{temp:.0f} °C" if temp is not None else "N/A")
        self.cards["temp"].detail.setText("Température disponible selon le matériel")
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=0.15).close()
            net = "ONLINE"
        except Exception:
            net = "OFFLINE"
        self.cards["net"].value.setText(net)
        self.cards["net"].detail.setText("Connectivité réseau")

        processor = getattr(self.assistant, "processor", None)
        conversation = getattr(processor, "conversation_ai", None) if processor else None
        provider = str(config.get("ai_provider", "ollama")).upper()
        model = str(config.get("groq_model" if provider == "GROQ" else "model", "--"))
        self.cards["ai"].value.setText(provider)
        self.cards["ai"].detail.setText(model)

        listening = bool(getattr(state, "is_listening", False)) if state else False
        speaking = bool(getattr(state, "is_speaking", False)) if state else False
        voice = "LISTENING" if listening else "SPEAKING" if speaking else "READY"
        self.cards["voice"].value.setText(voice)
        self.cards["voice"].detail.setText(
            f"MIC {'ON' if bool(config.get('microphone_enabled', True)) else 'OFF'} · "
            f"VOICE {'ON' if bool(getattr(state, 'voice_enabled', True)) else 'OFF'}"
        )

        mode = str(getattr(processor, "_neo_agent_mode", False))
        self.mode.setText("MODE: AGENT" if mode.lower() == "true" else "MODE: NORMAL")
        if state:
            if listening:
                self.status.setText("● LISTENING")
            elif speaking:
                self.status.setText("● SPEAKING")
            elif bool(getattr(state, "is_processing", False)):
                self.status.setText("● THINKING")
            else:
                self.status.setText("● SYSTEM ONLINE")

        activity = getattr(state, "activity", None) if state else None
        if activity is not None:
            try:
                latest = None
                while not activity.empty():
                    latest = activity.get_nowait()
                if latest:
                    self.activity_label.setText(
                        f"[{str(latest.get('category', 'SYSTEM')).upper()}] "
                        f"{latest.get('message', '')}"
                    )
            except Exception:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
