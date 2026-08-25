"""J.A.R.V.I.S. NEO — visual HUD redesign.

Standalone PyQt6 visual layer. It deliberately does not touch the core assistant,
AI, memory, voice, plugins, camera, or network logic. Import the components from
assistant.py when ready to integrate them into the main window.
"""
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

CYAN = QColor("#62F6FF")
WHITE = QColor("#EAFBFF")
GREEN = QColor("#58FFC4")
DIM = QColor(98, 246, 255, 55)
BG = QColor("#050A13")


def panel_style(accent="#62F6FF"):
    return f"""
    QFrame {{
        background: rgba(5, 12, 24, 225);
        border: 1px solid rgba(98,246,255,45);
        border-radius: 12px;
    }}
    QLabel {{
        color: #EAFBFF;
        background: transparent;
        border: none;
        font-family: 'Segoe UI';
    }}
    QPushButton {{
        color: #62F6FF;
        background: rgba(98,246,255,10);
        border: 1px solid rgba(98,246,255,65);
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background: rgba(98,246,255,24);
        border-color: #62F6FF;
    }}
    QPushButton:pressed {{ background: rgba(98,246,255,40); }}
    """


class NeoFrame(QFrame):
    """Minimal cockpit frame: thin corners, subtle scan and no heavy neon border."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(45)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def _tick(self):
        self.phase = (self.phase + 1) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QBrush(BG))

        # Very soft center illumination.
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0, QColor(8, 25, 42, 210))
        g.setColorAt(.52, QColor(4, 12, 24, 235))
        g.setColorAt(1, QColor(2, 7, 15, 245))
        p.fillRect(self.rect(), QBrush(g))

        # Corner brackets instead of a glowing box around everything.
        pen = QPen(QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 150), 1.4)
        p.setPen(pen)
        c = 34
        m = 8
        for x1, y1, x2, y2 in [
            (m,m,c,m),(m,m,m,c),(w-m-c,m,w-m,m),(w-m,m,w-m,c),
            (m,h-m,m,h-m-c),(m,h-m,c,h-m),(w-m-c,h-m,w-m,h-m),(w-m,h-m,w-m,h-m-c)
        ]:
            p.drawLine(x1,y1,x2,y2)

        # Scan line, intentionally very dim.
        y = int((self.phase / 360) * max(1, h))
        p.fillRect(10, y, max(0, w-20), 1, QColor(98,246,255,18))
        super().paintEvent(event)


class NeoButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(panel_style())


class MetricCard(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setStyleSheet(panel_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        row = QHBoxLayout()
        self.name = QLabel(name.upper())
        self.name.setStyleSheet("color:#7895A5;font-size:9px;font-weight:700;letter-spacing:1.5px;")
        self.value = QLabel("0%")
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.value.setStyleSheet("color:#EAFBFF;font-size:14px;font-weight:700;")
        row.addWidget(self.name); row.addWidget(self.value)
        layout.addLayout(row)
        self.bar = QProgressBar()
        self.bar.setRange(0,100); self.bar.setValue(0); self.bar.setTextVisible(False); self.bar.setFixedHeight(4)
        self.bar.setStyleSheet("QProgressBar{background:rgba(255,255,255,12);border:0;border-radius:2px;} QProgressBar::chunk{background:#62F6FF;border-radius:2px;}")
        layout.addWidget(self.bar)

    def set_value(self, value):
        value = max(0, min(100, int(value)))
        self.bar.setValue(value); self.value.setText(f"{value}%")


class ReactorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(190,190)
        self.angle = 0
        self.pulse = 0
        self.status = "ONLINE"
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(24)

    def _tick(self):
        self.angle = (self.angle + 2) % 360
        self.pulse = (self.pulse + 1) % 100
        self.update()

    def set_status(self, status):
        self.status = status.upper(); self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width()/2, self.height()/2)
        r = min(self.width(), self.height())/2 - 12
        color = CYAN if self.status == "ONLINE" else GREEN if self.status in ("VOICE","LISTENING") else QColor("#FFB454")
        # outer technical ticks
        p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),70),1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(24):
            p.save(); p.translate(c); p.rotate(i*15); p.drawLine(0,-r,0,-r+7); p.restore()
        for rr, alpha in ((r-8,30),(r-25,55),(r-43,90)):
            p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),alpha),1.5)); p.drawEllipse(c,rr,rr)
        p.save(); p.translate(c); p.rotate(self.angle)
        p.setPen(QPen(color,2)); p.drawRoundedRect(-28,-28,56,56,12,12)
        p.drawLine(-44,0,-32,0); p.drawLine(32,0,44,0); p.restore()
        p.setPen(QPen(color,1.5)); p.setBrush(QColor(color.red(),color.green(),color.blue(),28)); p.drawEllipse(c,25,25)
        p.setPen(WHITE); p.setFont(QFont("Segoe UI",9,QFont.Weight.Bold)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,self.status)


class StatusStrip(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setStyleSheet(panel_style())
        layout=QHBoxLayout(self); layout.setContentsMargins(12,7,12,7)
        self.dot=QLabel("●"); self.dot.setStyleSheet("color:#58FFC4;font-size:11px;border:none;")
        self.text=QLabel("NEO CORE  /  ONLINE")
        self.text.setStyleSheet("color:#A9C8D4;font-size:10px;font-weight:700;letter-spacing:1.2px;border:none;")
        self.detail=QLabel("READY")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.detail.setStyleSheet("color:#62F6FF;font-size:9px;font-weight:700;border:none;")
        layout.addWidget(self.dot); layout.addWidget(self.text); layout.addStretch(); layout.addWidget(self.detail)

    def set_state(self, label, detail="READY", danger=False):
        self.text.setText(f"NEO CORE  /  {label.upper()}"); self.detail.setText(detail.upper())
        self.dot.setStyleSheet(f"color:{'#FF5E6C' if danger else '#58FFC4'};font-size:11px;border:none;")


class ActivityPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setStyleSheet(panel_style())
        layout=QVBoxLayout(self); layout.setContentsMargins(12,10,12,10)
        title=QLabel("LIVE ACTIVITY")
        title.setStyleSheet("color:#7895A5;font-size:9px;font-weight:700;letter-spacing:1.5px;border:none;")
        layout.addWidget(title)
        self.lines=[]
        for text in ("Core initialized","Memory channel ready","Waiting for directive"):
            lbl=QLabel("›  "+text); lbl.setStyleSheet("color:#9BB4BF;font-family:Consolas;font-size:9px;border:none;"); layout.addWidget(lbl); self.lines.append(lbl)

    def push(self, text):
        self.lines = self.lines[1:] + self.lines[:1]
        self.lines[-1].setText("›  "+text)


class HudSidebar(QWidget):
    """Ready-to-use redesigned visual column."""
    def __init__(self, parent=None):
        super().__init__(parent)
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(8)
        self.reactor=ReactorWidget(); root.addWidget(self.reactor,0,Qt.AlignmentFlag.AlignCenter)
        self.status=StatusStrip(); root.addWidget(self.status)
        metrics=QGridLayout(); metrics.setSpacing(8)
        self.cpu=MetricCard("CPU"); self.ram=MetricCard("RAM"); self.disk=MetricCard("DISK")
        metrics.addWidget(self.cpu,0,0); metrics.addWidget(self.ram,0,1); metrics.addWidget(self.disk,1,0,1,2)
        root.addLayout(metrics)
        self.activity=ActivityPanel(); root.addWidget(self.activity)
        actions=QHBoxLayout();
        for label in ("MIC","VISION","SENTINEL"):
            actions.addWidget(NeoButton(label))
        root.addLayout(actions)
        root.addStretch()
