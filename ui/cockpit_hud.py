"""J.A.R.V.I.S. NEO futuristic command cockpit.

Presentation-only Qt layer. Dynamic agent output stays inside the cockpit
engine and never needs to be rendered as raw internal JSON in chat.
"""
from __future__ import annotations

import socket
from typing import Any

from PyQt6.QtCore import QPointF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget
from core.cockpit_widget_engine import CockpitWidgetEngine

try:
    import psutil
except Exception:
    psutil = None

CYAN = "#62F6FF"
WHITE = "#EAFBFF"
GREEN = "#58FFC4"
RED = "#FF6B7A"
BG = "#02060D"


def panel_style() -> str:
    return f"""
    QFrame.cockpitPanel {{ background: rgba(6,16,27,238); border: 1px solid rgba(98,246,255,52); border-radius: 14px; }}
    QLabel {{ color: {WHITE}; background: transparent; border: none; }}
    QPushButton {{ color: {CYAN}; background: rgba(98,246,255,7); border: 1px solid rgba(98,246,255,48); border-radius: 7px; padding: 8px 10px; font-size: 9px; font-weight: 800; }}
    QPushButton:hover {{ background: rgba(98,246,255,18); border-color: {CYAN}; }}
    QPushButton:pressed {{ background: rgba(98,246,255,30); }}
    QScrollArea {{ background: transparent; border: none; }}
    """


class Reactor(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.angle = 0.0
        self.status = "ONLINE"
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(35)
        self.setMinimumSize(230, 230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _tick(self) -> None:
        self.angle = (self.angle + 1.8) % 360
        self.update()

    def set_status(self, status: str) -> None:
        self.status = str(status or "ONLINE").upper()
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 16
        active = self.status in {"LISTENING", "SPEAKING", "THINKING", "PROCESSING"}
        color = QColor(GREEN if self.status in {"LISTENING", "SPEAKING"} else CYAN)
        if self.status == "ERROR":
            color = QColor(RED)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(3, 14, 24, 245))
        painter.drawEllipse(center, radius, radius)
        for i in range(48):
            painter.save()
            painter.translate(center)
            painter.rotate(i * 7.5 + self.angle * 0.12)
            alpha = 150 if i % 4 == 0 else 42
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), alpha), 1.5))
            length = 13 if i % 4 == 0 else 6
            painter.drawLine(QPointF(0, -radius), QPointF(0, -radius + length))
            painter.restore()
        for rr, alpha, width in ((radius - 8, 42, 1), (radius - 26, 80, 1), (radius - 48, 125, 2)):
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), alpha), width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, rr, rr)
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle)
        painter.setPen(QPen(color, 2))
        painter.drawArc(int(-radius + 26), int(-radius + 26), int((radius - 26) * 2), int((radius - 26) * 2), 12 * 16, 72 * 16)
        painter.drawArc(int(-radius + 26), int(-radius + 26), int((radius - 26) * 2), int((radius - 26) * 2), 192 * 16, 72 * 16)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 150), 2))
        painter.drawLine(QPointF(-radius * .62, 0), QPointF(-radius * .40, 0))
        painter.drawLine(QPointF(radius * .40, 0), QPointF(radius * .62, 0))
        painter.restore()
        painter.setPen(QPen(color, 2.5 if active else 1.5))
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 38))
        painter.drawEllipse(center, 31, 31)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 125))
        painter.drawEllipse(center, 19, 19)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 225))
        painter.drawEllipse(center, 7, 7)
        painter.setPen(QColor(WHITE))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.status)
        painter.setPen(QColor("#6C8794"))
        painter.setFont(QFont("Consolas", 7, QFont.Weight.DemiBold))
        painter.drawText(0, int(self.height() * .67), self.width(), 18, Qt.AlignmentFlag.AlignCenter, "NEO // CORE LINK")
        painter.end()


class Metric(QFrame):
    def __init__(self, name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("cockpitPanel")
        self.setStyleSheet(panel_style())
        box = QVBoxLayout(self)
        box.setContentsMargins(10, 8, 10, 8)
        box.setSpacing(5)
        row = QHBoxLayout()
        self.name = QLabel(str(name).upper())
        self.name.setStyleSheet("color:#6C8794;font-size:7px;font-weight:800;letter-spacing:1.5px;")
        self.value = QLabel("0%")
        self.value.setStyleSheet(f"color:{WHITE};font-size:13px;font-weight:900;")
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.name)
        row.addStretch()
        row.addWidget(self.value)
        box.addLayout(row)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(3)
        self.bar.setStyleSheet(f"QProgressBar{{background:rgba(255,255,255,10);border:0;border-radius:2px;}} QProgressBar::chunk{{background:{CYAN};border-radius:2px;}}")
        box.addWidget(self.bar)

    def set_value(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        self.value.setText(f"{value}%")
        self.bar.setValue(value)


class CockpitHud(QDialog):
    dynamic_request = pyqtSignal(str, str, str, str, str)
    dynamic_remove_request = pyqtSignal(str)
    dynamic_clear_request = pyqtSignal()

    def __init__(self, assistant: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        self._drag_pos = None
        self._mini_mode = False
        self.setWindowTitle("J.A.R.V.I.S. NEO // COMMAND CENTER")
        self.setMinimumSize(860, 540)
        self.resize(1180, 720)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(f"QDialog{{background:{BG};color:{WHITE};}}" + panel_style())
        self._build()
        self.dynamic_request.connect(self.show_dynamic_panel)
        self.dynamic_remove_request.connect(self.remove_dynamic_panel)
        self.dynamic_clear_request.connect(self.clear_dynamic_panels)
        signals = getattr(assistant, "signals", None)
        if signals is not None:
            try:
                signals.log_msg.connect(self._on_log)
            except Exception:
                pass
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(1500)
        self.refresh()

    def _panel(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("cockpitPanel")
        frame.setStyleSheet(panel_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)
        label = QLabel(title)
        label.setStyleSheet("color:#6C8794;font-size:8px;font-weight:900;letter-spacing:1.8px;")
        layout.addWidget(label)
        return frame, layout

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 15, 18, 15)
        root.setSpacing(10)
        header = QHBoxLayout()
        brand = QLabel("J.A.R.V.I.S. NEO")
        brand.setStyleSheet(f"color:{CYAN};font-size:18px;font-weight:950;letter-spacing:3px;")
        subtitle = QLabel("NEURAL COMMAND INTERFACE  //  LOCAL CORE")
        subtitle.setStyleSheet("color:#456774;font-size:7px;font-weight:800;letter-spacing:1.8px;")
        self.status = QLabel("● ONLINE")
        self.status.setStyleSheet(f"color:{GREEN};font-size:9px;font-weight:900;letter-spacing:1px;")
        self.mode = QLabel("NORMAL")
        self.mode.setStyleSheet("color:#7A98A4;font-size:8px;font-weight:800;")
        close = QPushButton("×")
        close.setFixedSize(32, 28)
        close.clicked.connect(self._minimize_to_reactor)
        header.addWidget(brand); header.addSpacing(12); header.addWidget(subtitle); header.addStretch(); header.addWidget(self.status); header.addSpacing(10); header.addWidget(self.mode); header.addSpacing(8); header.addWidget(close)
        root.addLayout(header)
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet("background:rgba(98,246,255,70);border:none;"); root.addWidget(line)
        self._header_widgets = [brand, subtitle, self.status, self.mode, close]

        body = QHBoxLayout(); body.setSpacing(10); self._body_widgets = []
        left, ll = self._panel("CORE TELEMETRY")
        self.reactor = Reactor(); self.reactor.clicked.connect(self._restore_from_reactor); ll.addWidget(self.reactor, 0, Qt.AlignmentFlag.AlignCenter)
        metrics = QGridLayout(); metrics.setSpacing(6)
        self.metrics = {k: Metric(k) for k in ("CPU", "RAM", "DISK", "NETWORK")}
        for i, key in enumerate(self.metrics): metrics.addWidget(self.metrics[key], i // 2, i % 2)
        ll.addLayout(metrics)
        self.ai_label = QLabel("AI CORE / INITIALIZING"); self.ai_label.setStyleSheet(f"color:{CYAN};font-size:8px;font-weight:800;letter-spacing:1px;"); ll.addWidget(self.ai_label)
        ll.addStretch(); body.addWidget(left, 1); self._body_widgets.append(left)

        center, cl = self._panel("DYNAMIC INTELLIGENCE")
        self.dynamic_host = QWidget(); self.dynamic_host.setStyleSheet("background:transparent;border:none;")
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.dynamic_host); cl.addWidget(scroll, 1)
        self.dynamic_engine = CockpitWidgetEngine(self.dynamic_host)
        body.addWidget(center, 3); self._body_widgets.append(center)

        right, rl = self._panel("COMMAND DECK")
        actions = QGridLayout(); actions.setSpacing(6)
        for i, (label, command) in enumerate((("WEB", "cherche actualités IA"), ("FILES", "ouvre explorateur"), ("SYSTEM", "processus"), ("WEATHER", "météo"), ("MODEL", "quel modèle"), ("HELP", "aide"))):
            button = QPushButton(label); button.setToolTip(command); button.clicked.connect(lambda _, c=command: self._command(c)); actions.addWidget(button, i // 2, i % 2)
        rl.addLayout(actions)
        activity_title = QLabel("LIVE FEED"); activity_title.setStyleSheet("color:#6C8794;font-size:8px;font-weight:900;letter-spacing:1.8px;margin-top:8px;"); rl.addWidget(activity_title)
        self.activity_label = QLabel("› Core initialized\n› Cockpit ready\n› Waiting for directive"); self.activity_label.setStyleSheet("color:#89A9B5;font-family:Consolas;font-size:8px;"); self.activity_label.setWordWrap(True); rl.addWidget(self.activity_label); rl.addStretch(); body.addWidget(right, 1); self._body_widgets.append(right)
        root.addLayout(body, 1)

        footer = QHBoxLayout(); self._footer_widgets = []
        for text, slot in (("COMPACT", self._compact), ("NORMAL", self._normal), ("CLEAR", self.clear_dynamic_panels), ("REFRESH", self.refresh)):
            button = QPushButton(text); button.clicked.connect(slot); footer.addWidget(button); self._footer_widgets.append(button)
        footer.addStretch(); self.pin = QPushButton("PIN"); self.pin.setCheckable(True); self.pin.setChecked(True); self.pin.clicked.connect(self._toggle_pin); footer.addWidget(self.pin); self._footer_widgets.append(self.pin); root.addLayout(footer)
        self.mini_reactor = Reactor(self); self.mini_reactor.setMinimumSize(0, 0); self.mini_reactor.setFixedSize(190, 190); self.mini_reactor.clicked.connect(self._restore_from_reactor); self.mini_reactor.hide()

    def _command(self, command: str) -> None:
        try:
            queue = getattr(self.assistant, "command_queue", None)
            if queue is None: raise RuntimeError("file de commandes indisponible")
            queue.put(str(command)); self._on_log("COMMAND", str(command))
        except Exception as exc: self._on_log("ERROR", str(exc))

    def _minimize_to_reactor(self) -> None:
        if self._mini_mode: return
        self._mini_mode = True
        for widget in self._header_widgets + self._body_widgets + self._footer_widgets: widget.hide()
        self.mini_reactor.set_status(self.reactor.status); self.mini_reactor.show(); self.setMinimumSize(0, 0); self.setFixedSize(210, 210); self.setStyleSheet("QDialog{background:transparent;border:none;}"); self.mini_reactor.move(10, 10); self.setWindowOpacity(0.88); self.raise_(); self.activateWindow()

    def _restore_from_reactor(self) -> None:
        if not self._mini_mode: return
        self._mini_mode = False; self.mini_reactor.hide(); self.setMinimumSize(860, 540); self.setStyleSheet(f"QDialog{{background:{BG};color:{WHITE};}}" + panel_style())
        for widget in self._header_widgets + self._body_widgets + self._footer_widgets: widget.show()
        self._normal(); self.setWindowOpacity(1.0); self.show(); self.raise_(); self.activateWindow()

    def show_dynamic_panel(self, panel_id: str, title: str, content: str = "", kind: str = "info", source: str = "") -> bool:
        return self.dynamic_engine.show_panel(panel_id, title, content, kind, source)

    def enqueue_dynamic_panel(self, panel_id: str, title: str, content: str = "", kind: str = "info", source: str = "") -> None:
        self.dynamic_request.emit(str(panel_id), str(title), str(content), str(kind), str(source))

    def remove_dynamic_panel(self, panel_id: str) -> bool: return self.dynamic_engine.remove_panel(panel_id)
    def enqueue_remove_dynamic_panel(self, panel_id: str) -> None: self.dynamic_remove_request.emit(str(panel_id))
    def clear_dynamic_panels(self) -> None: self.dynamic_engine.clear()
    def enqueue_clear_dynamic_panels(self) -> None: self.dynamic_clear_request.emit()
    def dynamic_panels(self): return self.dynamic_engine.snapshot()
    def _on_log(self, category: str, message: str) -> None: self.activity_label.setText(f"[{str(category).upper()}] {message}")

    def _toggle_pin(self) -> None:
        flags = self.windowFlags()
        flags = flags | Qt.WindowType.WindowStaysOnTopHint if self.pin.isChecked() else flags & ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags); self.show()

    def _available_size(self, preferred_w: int, preferred_h: int):
        screen = self.screen()
        if screen is None and self.windowHandle() is not None: screen = self.windowHandle().screen()
        if screen is None: return preferred_w, preferred_h, None
        area = screen.availableGeometry()
        return min(preferred_w, max(320, area.width() - 28)), min(preferred_h, max(240, area.height() - 28)), area

    def _center_on_available_screen(self, width: int, height: int) -> None:
        width, height, area = self._available_size(width, height)
        self.setFixedSize(width, height)
        if area is not None: self.move(area.center().x() - width // 2, area.center().y() - height // 2)

    def _compact(self) -> None: self._center_on_available_screen(900, 560)
    def _normal(self) -> None: self._center_on_available_screen(1180, 720)

    def refresh(self) -> None:
        cpu = ram = disk = 0
        if psutil is not None:
            try: cpu, ram, disk = psutil.cpu_percent(), psutil.virtual_memory().percent, psutil.disk_usage("/").percent
            except Exception: pass
        self.metrics["CPU"].set_value(cpu); self.metrics["RAM"].set_value(ram); self.metrics["DISK"].set_value(disk)
        try: socket.create_connection(("1.1.1.1", 53), timeout=0.12).close(); net = 100
        except Exception: net = 0
        self.metrics["NETWORK"].set_value(net)
        state = getattr(self.assistant, "state", None); processor = getattr(self.assistant, "processor", None); config = getattr(self.assistant, "CONFIG", {}) or {}
        conversation = getattr(processor, "conversation_ai", None) if processor else None; status = getattr(conversation, "status", {}) if conversation else {}
        if not isinstance(status, dict): status = {}
        provider = str(status.get("active_provider") or config.get("ai_provider", "ollama")).upper(); model = str(config.get("groq_model" if provider == "GROQ" else "model", "--")); self.ai_label.setText(f"AI CORE  /  {provider}  /  {model}")
        listening = bool(getattr(state, "is_listening", False)) if state else False; speaking = bool(getattr(state, "is_speaking", False)) if state else False; voice = "LISTENING" if listening else "SPEAKING" if speaking else "ONLINE"
        self.reactor.set_status(voice); self.mini_reactor.set_status(voice); self.status.setText(f"● {voice}"); self.status.setStyleSheet(f"color:{GREEN if voice != 'ONLINE' else CYAN};font-size:9px;font-weight:900;letter-spacing:1px;"); self.mode.setText("AGENT" if bool(getattr(processor, "_neo_agent_mode", False)) else "NORMAL")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton: self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton: self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_pos = None
        super().mouseReleaseEvent(event)
