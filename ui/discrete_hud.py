"""Small always-on-top desktop reactor for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget


class DiscreteHud(QWidget):
    """Lightweight top-right reactor. No background worker and no heavy polling."""

    def __init__(self, window):
        super().__init__(None)
        self.window = window
        self.phase = 0.0
        self.last_stats = {"cpu": 0.0, "ram": 0.0}
        self.setFixedSize(92, 92)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setToolTip("J.A.R.V.I.S. NEO • cliquer pour ouvrir")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1500)

    def show_discrete(self):
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 18, area.top() + 18)
        self.show()
        self.raise_()
        self._refresh()

    def _config(self):
        try:
            path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            return {}

    def _refresh(self):
        try:
            import psutil
            self.last_stats = {
                "cpu": psutil.cpu_percent(interval=None),
                "ram": psutil.virtual_memory().percent,
            }
        except Exception:
            pass
        self.phase = (self.phase + 0.22) % (math.pi * 2)
        self.update()

    def _state(self):
        state = getattr(self.window, "_neo_state", None)
        if state is None:
            try:
                import assistant
                state = getattr(assistant, "state", None)
            except Exception:
                pass
        if state is None:
            return "online", "ONLINE"
        if getattr(state, "alarm_triggered", False):
            return "error", "ALERTE"
        if getattr(state, "is_speaking", False):
            return "speaking", "VOIX"
        if getattr(state, "is_listening", False):
            return "listening", "ÉCOUTE"
        if getattr(state, "is_processing", False):
            return "processing", "TRAITEMENT"
        return "online", "EN LIGNE"

    def _provider(self):
        try:
            import assistant
            config = getattr(assistant, "CONFIG", {})
        except Exception:
            config = self._config()
        provider = str(config.get("ai_provider", "groq")).lower()
        if provider == "ollama":
            return "OLLAMA"
        if provider == "groq":
            return "GROQ" if config.get("groq_api_key") or os.getenv("GROQ_API_KEY") else "GROQ • CLÉ MANQUANTE"
        return provider.upper()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        state, label = self._state()
        colors = {
            "online": QColor("#28b8ff"),
            "listening": QColor("#ffd34d"),
            "processing": QColor("#b66cff"),
            "speaking": QColor("#42e89a"),
            "error": QColor("#ff4b5c"),
        }
        color = colors.get(state, colors["online"])
        cx = self.width() / 2
        cy = 38
        pulse = 1.0 + 0.045 * math.sin(self.phase)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 35), 5))
        painter.drawEllipse(int(cx - 28 * pulse), int(cy - 28 * pulse), int(56 * pulse), int(56 * pulse))
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 180), 2))
        painter.drawEllipse(int(cx - 23), int(cy - 23), 46, 46)
        painter.setPen(QPen(color, 2.5))
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.phase * 35)
        painter.drawRect(-12, -12, 24, 24)
        painter.restore()
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - 5), int(cy - 5), 10, 10)
        painter.setPen(QColor("#e9f7ff"))
        painter.drawText(0, 69, self.width(), 12, Qt.AlignmentFlag.AlignCenter, label)
        painter.setPen(QColor("#8aa0b2"))
        painter.drawText(0, 83, self.width(), 9, Qt.AlignmentFlag.AlignCenter, self._provider())
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._neo_reveal()
        elif event.button() == Qt.MouseButton.RightButton:
            self.hide()
        event.accept()

    def _neo_reveal(self):
        if self.window is None:
            return
        self.window._neo_reveal = True
        try:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
        finally:
            self.window._neo_reveal = False


__all__ = ["DiscreteHud"]
