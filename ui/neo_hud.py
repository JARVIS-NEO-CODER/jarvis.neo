"""J.A.R.V.I.S. NEO — main HUD composition layer.

This file only composes the reusable UI widgets. It intentionally does not
own assistant logic, Ollama, audio, plugins, or system-monitor collection.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from .arc_reactor import ArcReactor
from .hud import HudPanel
from .system_panel import SystemPanel
from .terminal import NeoTerminal


class NeoHud(QWidget):
    """Full-screen NEO cockpit layout ready to be embedded in JarvisWindow."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("neoHud")
        self.setStyleSheet("""
            QWidget#neoHud {
                background: #050907;
                color: #d9f5c4;
            }
            QLabel#neoHeader {
                color: #baff62;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#neoSubHeader {
                color: #657565;
                font-size: 9px;
                letter-spacing: 1px;
            }
            QPushButton.neoControl {
                background: #0b1710;
                color: #ccefb4;
                border: 1px solid #304833;
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton.neoControl:hover {
                background: #122419;
                border-color: #80ad54;
            }
            QPushButton.neoControl:pressed {
                background: #1a3020;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("J.A.R.V.I.S. NEO")
        title.setObjectName("neoHeader")
        subtitle = QLabel("LOCAL INTELLIGENCE COCKPIT  //  SYSTEM ONLINE")
        subtitle.setObjectName("neoSubHeader")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(subtitle)
        root.addLayout(header)

        # Main cockpit: terminal | reactor | telemetry
        main = QHBoxLayout()
        main.setSpacing(14)

        left = HudPanel("Terminal")
        self.terminal = NeoTerminal()
        left.add_widget(self.terminal)
        left.setMinimumWidth(270)
        left.setMaximumWidth(360)

        center = QFrame()
        center.setStyleSheet("QFrame { background: transparent; border: none; }")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reactor = ArcReactor()
        self.reactor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout.addWidget(self.reactor, 1, Qt.AlignmentFlag.AlignCenter)

        right = HudPanel("System")
        self.system_panel = SystemPanel()
        right.add_widget(self.system_panel)
        right.setMinimumWidth(210)
        right.setMaximumWidth(290)

        main.addWidget(left, 0)
        main.addWidget(center, 1)
        main.addWidget(right, 0)
        root.addLayout(main, 1)

        # Bottom controls
        controls = QHBoxLayout()
        controls.setSpacing(8)
        for label in ("MIC", "VOICE", "MODE", "PLUGINS", "SENTINEL", "SETTINGS"):
            button = QPushButton(label)
            button.setProperty("class", "neoControl")
            button.setObjectName("neoControl")
            button.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            controls.addWidget(button)
        root.addLayout(controls)

    def set_reactor_state(self, state: str) -> None:
        self.reactor.set_state(state)

    def append_terminal(self, speaker: str, message: str) -> None:
        self.terminal.append_entry(speaker, message)

    def set_system_value(self, name: str, value: str) -> None:
        self.system_panel.set_value(name, value)
