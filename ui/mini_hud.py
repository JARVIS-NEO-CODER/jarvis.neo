"""Compact always-on-top NEO status HUD."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class MiniHud(QWidget):
    """Small floating status display for the live NEO runtime."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("miniHud")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(285, 92)
        self.setStyleSheet("""
            QWidget#miniHud { background: transparent; }
            QFrame#panel { background: rgba(5,12,8,235); border: 1px solid #304833; border-radius: 12px; }
            QLabel#title { color:#baff62; font-size:11px; font-weight:700; }
            QLabel#state { color:#58ffc4; font-size:9px; font-weight:700; }
            QLabel#value { color:#d9f5c4; font-size:9px; }
            QLabel#muted { color:#71806f; font-size:8px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)
        top = QHBoxLayout()
        self.title = QLabel("J.A.R.V.I.S. NEO")
        self.title.setObjectName("title")
        self.state = QLabel("ONLINE")
        self.state.setObjectName("state")
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.state)
        layout.addLayout(top)
        values = QHBoxLayout()
        self.ai = QLabel("AI : --")
        self.ai.setObjectName("value")
        self.cpu = QLabel("CPU : --")
        self.cpu.setObjectName("value")
        self.ram = QLabel("RAM : --")
        self.ram.setObjectName("value")
        values.addWidget(self.ai)
        values.addStretch(1)
        values.addWidget(self.cpu)
        values.addWidget(self.ram)
        layout.addLayout(values)
        self.devices = QLabel("MIC ON   •   VOICE ON")
        self.devices.setObjectName("muted")
        layout.addWidget(self.devices)
        root.addWidget(panel)

    def set_state(self, state: str) -> None:
        self.state.setText(str(state).upper())

    def set_ai(self, value: str) -> None:
        self.ai.setText(f"AI : {value}")

    def set_stats(self, cpu: str, ram: str) -> None:
        self.cpu.setText(f"CPU : {cpu}")
        self.ram.setText(f"RAM : {ram}")

    def set_devices(self, mic: bool, voice: bool) -> None:
        self.devices.setText(f"MIC {'ON' if mic else 'OFF'}   •   VOICE {'ON' if voice else 'OFF'}")

    def place_top_right(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 18, area.top() + 18)
