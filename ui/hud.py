"""J.A.R.V.I.S. NEO — reusable HUD shell components."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class HudPanel(QFrame):
    """Dark green NEO panel with a small title and content area."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("neoHudPanel")
        self.setStyleSheet("""
            QFrame#neoHudPanel {
                background: rgba(8, 18, 13, 235);
                border: 1px solid #354b3b;
                border-radius: 12px;
            }
            QLabel#neoHudTitle {
                color: #baff62;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(8)
        if title:
            label = QLabel(title.upper())
            label.setObjectName("neoHudTitle")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.layout.addWidget(label)

    def add_widget(self, widget: QWidget) -> None:
        self.layout.addWidget(widget)
