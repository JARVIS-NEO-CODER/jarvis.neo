"""Enhanced JARVIS NEO cockpit HUD panel."""
from __future__ import annotations
from typing import Callable
try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
except Exception:
    QWidget = object

from .hud_upgrade import HudTelemetry

class HudCockpit(QWidget):
    """Compact live cockpit that can be embedded or floated by the existing HUD."""
    def __init__(self, state_provider: Callable[[], dict] | None = None, parent=None):
        super().__init__(parent)
        self.state_provider = state_provider or (lambda: {})
        self.telemetry = HudTelemetry()
        self.setWindowTitle("JARVIS NEO • COCKPIT")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        self.title = QLabel("◉ J.A.R.V.I.S NEO  /  COCKPIT")
        self.status = QLabel("SYSTEM  •  READY")
        self.ai = QLabel("AI  •  LOCAL")
        self.voice = QLabel("VOICE  •  STANDBY")
        self.telemetry_label = QLabel("CPU 0%   RAM 0%   NET ONLINE")
        self.activity = QLabel("ACTIVITY  •  IDLE")
        for w in (self.title, self.status, self.ai, self.voice, self.telemetry_label, self.activity):
            w.setStyleSheet("font-family: Consolas; font-size: 12px; padding: 3px;")
            root.addWidget(w)
        row = QHBoxLayout()
        for text, mode in (("NORMAL", "NORMAL"), ("AGENT", "AGENT"), ("SENTINEL", "SENTINEL")):
            b = QPushButton(text)
            b.clicked.connect(lambda _, m=mode: self._set_mode(m))
            row.addWidget(b)
        root.addLayout(row)
        actions = QHBoxLayout()
        for text, action in (("APP", "open_app"), ("WEB", "web"), ("FILES", "files"), ("SETTINGS", "settings")):
            b = QPushButton(text)
            b.clicked.connect(lambda _, a=action: self._action(a))
            actions.addWidget(b)
        root.addLayout(actions)
        self.setStyleSheet("QWidget{background:rgba(8,12,20,235);border:1px solid rgba(120,200,255,120);border-radius:12px;} QPushButton{padding:7px;border:1px solid rgba(120,200,255,90);border-radius:6px;background:rgba(20,30,45,220);} QPushButton:hover{background:rgba(50,70,95,230);}")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _set_mode(self, mode: str):
        state = self.state_provider()
        setter = state.get("set_mode")
        if callable(setter): setter(mode)
        self.refresh()

    def _action(self, action: str):
        state = self.state_provider()
        handler = state.get("action")
        if callable(handler): handler(action)

    def refresh(self):
        state = self.state_provider()
        snap = self.telemetry.snapshot(**state)
        self.status.setText(f"SYSTEM  •  {snap.mode}  •  {snap.activity}")
        self.ai.setText(f"AI  •  {snap.provider.upper()}  •  {snap.model or 'DEFAULT'}")
        self.voice.setText(f"VOICE  •  {'LISTENING' if snap.listening else 'SPEAKING' if snap.speaking else 'STANDBY'}")
        temp = f"  TEMP {snap.temperature:.0f}°C" if snap.temperature is not None else ""
        self.telemetry_label.setText(f"CPU {snap.cpu:.0f}%   RAM {snap.ram:.0f}%   NET {snap.network}{temp}")
        self.activity.setText(f"ACTIVITY  •  {snap.activity}")
