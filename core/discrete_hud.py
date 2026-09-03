"""J.A.R.V.I.S. NEO — lightweight always-on-top desktop HUD.

The discrete HUD is intentionally cheap: one tiny translucent reactor, a compact
provider/status readout, and low-frequency telemetry. Clicking it restores the
full desktop cockpit.
"""
from __future__ import annotations

import os
import psutil
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.arc_reactor import ArcReactor
from core.ai_status import format_ai_status


class DiscreteHud(QWidget):
    """Tiny top-right JARVIS presence indicator."""

    def __init__(self, main_window=None):
        super().__init__(None)
        self.main_window = main_window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(128, 154)

        self.reactor = ArcReactor(self)
        self.reactor.setMinimumSize(0, 0)
        self.reactor.setFixedSize(118, 118)
        self.reactor.mousePressEvent = self._open_full_ui

        self.status = QLabel("NEO • ONLINE")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(
            "QLabel { color:#baff62; background:rgba(3,9,6,180); "
            "border:1px solid rgba(130,190,90,90); border-radius:6px; "
            "padding:2px 5px; font:700 8px 'Segoe UI'; }"
        )
        self.telemetry = QLabel("CPU --%  •  RAM --%")
        self.telemetry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.telemetry.setStyleSheet(
            "QLabel { color:#8da38d; background:rgba(3,9,6,150); "
            "border-radius:5px; padding:1px; font:7px 'Segoe UI'; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(2)
        layout.addWidget(self.reactor, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)
        layout.addWidget(self.telemetry)

        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def _open_full_ui(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.main_window is not None:
            self.main_window.showNormal()
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.hide()

    def move_to_top_right(self):
        screen = self.screen() or self.windowHandle().screen() if self.windowHandle() else None
        if screen is None:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 14, geo.top() + 14)

    def refresh(self):
        core = None
        try:
            import assistant as core
        except Exception:
            pass
        processor = getattr(core, "processor", None) if core else None
        ai = getattr(processor, "conversation_ai", None) if processor else None
        status_obj = getattr(ai, "status", None) if ai else None
        label = format_ai_status(status_obj)
        self.status.setText("NEO • " + label.upper()[:28])

        state = getattr(core, "state", None) if core else None
        if state is not None:
            if getattr(state, "is_listening", False):
                self.reactor.set_state("listening")
            elif getattr(state, "is_speaking", False):
                self.reactor.set_state("speaking")
            elif getattr(state, "is_processing", False):
                self.reactor.set_state("thinking")
            else:
                self.reactor.set_state("online")

        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            self.telemetry.setText(f"CPU {cpu:.0f}%  •  RAM {ram:.0f}%")
        except Exception:
            self.telemetry.setText("CPU --%  •  RAM --%")

    def show_discrete(self):
        self.move_to_top_right()
        self.show()
        self.raise_()


__all__ = ["DiscreteHud"]
