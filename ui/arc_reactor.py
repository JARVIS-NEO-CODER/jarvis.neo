"""J.A.R.V.I.S. NEO — signature Arc Reactor widget.

Standalone PyQt6 widget designed to be embedded in the existing desktop UI.
The widget deliberately owns only its visual state; it does not know anything
about Ollama, audio, plugins, or the rest of JARVIS.
"""

from __future__ import annotations

from math import cos, sin, pi

from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class ArcReactor(QWidget):
    """Circular NEO reactor with a rotating inner square and state text."""

    STATES = {
        "online": ("ONLINE", 0.45),
        "listening": ("LISTENING", 1.25),
        "thinking": ("THINKING", 1.75),
        "speaking": ("SPEAKING", 1.10),
        "processing": ("PROCESSING", 1.45),
        "error": ("ERROR", 0.25),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._state = "online"
        self._angle = 0.0
        self._pulse = 0.0

        # Lightweight animation: deliberately modest so the HUD stays cheap.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

    def set_state(self, state: str) -> None:
        """Set the reactor state. Unknown values fall back to ONLINE."""
        normalized = str(state).strip().lower()
        self._state = normalized if normalized in self.STATES else "online"
        self.update()

    def setState(self, state: str) -> None:
        """Compatibility alias for common Qt/Python naming conventions."""
        self.set_state(state)

    def _tick(self) -> None:
        _, speed = self.STATES[self._state]
        self._angle = (self._angle + speed * 1.8) % 360.0
        self._pulse += 0.055
        self.update()

    def _draw_ring(self, painter: QPainter, radius: float, width: float,
                   color: QColor, start: float = 0.0, span: float = 360.0) -> None:
        painter.setPen(QPen(color, width))
        painter.drawArc(
            int(-radius), int(-radius), int(radius * 2), int(radius * 2),
            int(start * 16), int(span * 16)
        )

    def _draw_square(self, painter: QPainter, size: float) -> None:
        painter.save()
        painter.rotate(self._angle)
        half = size / 2
        points = [
            QPointF(-half, -half), QPointF(half, -half),
            QPointF(half, half), QPointF(-half, half),
        ]
        painter.setPen(QPen(QColor("#c8ff68"), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(points)

        # Four small cuts make the square more distinctive than a plain shape.
        painter.setPen(QPen(QColor("#8dcc3d"), 2))
        cut = size * 0.18
        for x, y, dx, dy in (
            (-half, -half, cut, 0), (half, -half, -cut, 0),
            (half, half, -cut, 0), (-half, half, cut, 0),
        ):
            painter.drawLine(QPointF(x, y), QPointF(x + dx, y + dy))
        painter.restore()

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt API
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(self.width() / 2, self.height() / 2)

        size = min(self.width(), self.height())
        outer = size * 0.42
        core = size * 0.115
        pulse = (sin(self._pulse) + 1.0) * 0.5
        state_text, _ = self.STATES[self._state]

        # Outer metallic reactor body.
        painter.setPen(QPen(QColor("#737a78"), max(8, int(size * 0.025)))
        painter.setBrush(QColor("#242927"))
        painter.drawEllipse(QPointF(0, 0), outer, outer)

        # Metallic inner ring and fine technical rings.
        self._draw_ring(painter, outer * 0.91, max(3, size * 0.008), QColor("#a9afab"))
        self._draw_ring(painter, outer * 0.78, max(2, size * 0.005), QColor("#555d59"))
        self._draw_ring(painter, outer * 0.67, max(2, size * 0.004), QColor("#8a928d"), 8, 78)
        self._draw_ring(painter, outer * 0.67, max(2, size * 0.004), QColor("#8a928d"), 188, 74)

        # Small outer markers, kept sparse instead of filling the HUD with clutter.
        painter.setPen(QPen(QColor("#66706b"), 2))
        marker_r = outer * 0.965
        for i in range(12):
            angle = i * 30 * pi / 180
            length = size * (0.018 if i % 3 else 0.030)
            p1 = QPointF(cos(angle) * marker_r, sin(angle) * marker_r)
            p2 = QPointF(cos(angle) * (marker_r - length), sin(angle) * (marker_r - length))
            painter.drawLine(p1, p2)

        # Green energy core.
        glow_radius = core * (1.35 + pulse * 0.14)
        painter.setPen(QPen(QColor(155, 245, 65, 55), max(4, int(size * 0.018))))
        painter.setBrush(QColor(70, 125, 30, 45))
        painter.drawEllipse(QPointF(0, 0), glow_radius, glow_radius)

        painter.setPen(QPen(QColor("#baff62"), max(3, int(size * 0.010))))
        painter.setBrush(QColor("#72a936"))
        painter.drawEllipse(QPointF(0, 0), core, core)

        # Signature rotating square.
        self._draw_square(painter, size * 0.155)

        # Minimal status text in the reactor center.
        painter.setPen(QColor("#e9ffd0"))
        font = QFont("Segoe UI", max(8, int(size * 0.027)), QFont.Weight.DemiBold)
        painter.setFont(font)
        text_rect_w = size * 0.34
        painter.drawText(
            int(-text_rect_w / 2), int(size * 0.18),
            int(text_rect_w), int(size * 0.045),
            Qt.AlignmentFlag.AlignCenter,
            state_text,
        )

        # Small NEO identifier below the status.
        painter.setPen(QColor("#84937f"))
        font_small = QFont("Segoe UI", max(6, int(size * 0.018)), QFont.Weight.Normal)
        painter.setFont(font_small)
        painter.drawText(
            int(-text_rect_w / 2), int(size * 0.225),
            int(text_rect_w), int(size * 0.035),
            Qt.AlignmentFlag.AlignCenter,
            "J.A.R.V.I.S.  NEO",
        )

        painter.end()
