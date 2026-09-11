"""J.A.R.V.I.S. NEO futuristic cockpit HUD with dynamic content panels."""
from __future__ import annotations
import socket
from PyQt6.QtCore import QPointF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QDialog,QFrame,QGridLayout,QHBoxLayout,QLabel,QPushButton,QProgressBar,QScrollArea,QVBoxLayout,QWidget
from core.cockpit_widget_engine import CockpitWidgetEngine
from core.data_registry import get_data
try: import psutil
except Exception: psutil=None
CYAN=QColor("#62F6FF"); WHITE=QColor("#EAFBFF"); GREEN=QColor("#58FFC4"); BG=QColor("#030810")
def panel_style():
    return """QFrame { background: rgba(5, 14, 27, 232); border: 1px solid rgba(98, 246, 255, 48); border-radius: 12px; } QLabel { color: #EAFBFF; background: transparent; border: none; } QPushButton { color: #62F6FF; background: rgba(98,246,255,8); border: 1px solid rgba(98,246,255,55); border-radius: 7px; padding: 8px 10px; font-size: 9px; font-weight: 700; } QPushButton:hover { background: rgba(98,246,255,20); border-color: #62F6FF; } QPushButton:pressed { background: rgba(98,246,255,32); } QScrollArea { background: transparent; border: none; }"""
class Reactor(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.angle=0; self.status="ONLINE"; self.timer=QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(35); self.setMinimumSize(210,210)
    def _tick(self): self.angle=(self.angle+2)%360; self.update()
    def set_status(self,status): self.status=str(status).upper(); self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); c=QPointF(self.width()/2,self.height()/2); r=min(self.width(),self.height())/2-14; color=GREEN if self.status in {"LISTENING","SPEAKING"} else CYAN
        p.setBrush(QBrush(QColor(4,18,31,210))); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(c,r-18,r-18)
        for i in range(24):
            p.save(); p.translate(c); p.rotate(i*15); p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),100),1.2)); p.drawLine(QPointF(0,-r),QPointF(0,-r+(10 if i%3==0 else 5))); p.restore()
        for rr,alpha in ((r-8,35),(r-27,65),(r-48,110)):
            p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),alpha),1.5)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(c,rr,rr)
        p.save(); p.translate(c); p.rotate(self.angle); p.setPen(QPen(color,2)); p.drawRoundedRect(-31,-31,62,62,14,14); p.drawLine(-49,0,-35,0); p.drawLine(35,0,49,0); p.restore()
        p.setPen(QPen(color,1.5)); p.setBrush(QColor(color.red(),color.green(),color.blue(),35)); p.drawEllipse(c,25,25); p.setPen(WHITE); p.setFont(QFont("Segoe UI",9,QFont.Weight.Bold)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,self.status)
class Metric(QFrame):
    def __init__(self,name,parent=None):
        super().__init__(parent); self.setStyleSheet(panel_style()); box=QVBoxLayout(self); box.setContentsMargins(11,9,11,9); box.setSpacing(5); row=QHBoxLayout(); self.name=QLabel(str(name).upper()); self.name.setStyleSheet("color:#7895A5;font-size:8px;font-weight:700;letter-spacing:1.4px;"); self.value=QLabel("0%"); self.value.setStyleSheet("color:#EAFBFF;font-size:14px;font-weight:800;"); self.value.setAlignment(Qt.AlignmentFlag.AlignRight); row.addWidget(self.name); row.addStretch(); row.addWidget(self.value); box.addLayout(row); self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setTextVisible(False); self.bar.setFixedHeight(3); self.bar.setStyleSheet("QProgressBar{background:rgba(255,255,255,12);border:0;border-radius:2px;} QProgressBar::chunk{background:#62F6FF;border-radius:2px;}"); box.addWidget(self.bar)
    def set_value(self,value): value=max(0,min(100,int(value))); self.value.setText(f"{value}%"); self.bar.setValue(value)
class CockpitHud(QDialog):
    dynamic_request=pyqtSignal(str,str,str,str,str); dynamic_remove_request=pyqtSignal(str); dynamic_clear_request=pyqtSignal()
    def __init__(self,assistant,parent=None):
        super().__init__(parent); self.assistant=assistant; self._drag_pos=None; self.setWindowTitle("J.A.R.V.I.S. NEO // COMMAND CENTER"); self.setMinimumSize(1040,680); self.resize(1240,780); self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Window|Qt.WindowType.WindowStaysOnTopHint); self.setStyleSheet("QDialog{background:#030810;color:#EAFBFF;}"+panel_style()); self._build(); self.dynamic_request.connect(self.show_dynamic_panel); self.dynamic_remove_request.connect(self.remove_dynamic_panel); self.dynamic_clear_request.connect(self.clear_dynamic_panels); signals=getattr(assistant,"signals",None)
        if signals is not None:
            try: signals.log_msg.connect(self._on_log)
            except Exception: pass
        self._timer=QTimer(self); self._timer.timeout.connect(self.refresh); self._timer.start(1000); self.refresh()
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(20,16,20,16); root.setSpacing(12); header=QHBoxLayout(); brand=QLabel("J.A.R.V.I.S. NEO"); brand.setStyleSheet("color:#62F6FF;font-size:19px;font-weight:900;letter-spacing:3px;"); subtitle=QLabel("NEURAL COMMAND CENTER  //  DYNAMIC COCKPIT"); subtitle.setStyleSheet("color:#587584;font-size:8px;font-weight:700;letter-spacing:1.6px;"); self.status=QLabel("● ONLINE"); self.status.setStyleSheet("color:#58FFC4;font-size:10px;font-weight:800;"); self.mode=QLabel("NORMAL"); self.mode.setStyleSheet("color:#7895A5;font-size:9px;font-weight:700;"); close=QPushButton("×"); close.setFixedSize(34,30); close.clicked.connect(self.close); header.addWidget(brand); header.addSpacing(14); header.addWidget(subtitle); header.addStretch(); header.addWidget(self.status); header.addSpacing(12); header.addWidget(self.mode); header.addWidget(close); root.addLayout(header)
        body=QHBoxLayout(); body.setSpacing(12); left=QFrame(); left.setStyleSheet(panel_style()); ll=QVBoxLayout(left); ll.setContentsMargins(12,12,12,12); self.reactor=Reactor(); ll.addWidget(self.reactor,0,Qt.AlignmentFlag.AlignCenter); metrics=QGridLayout(); metrics.setSpacing(7); self.metrics={k:Metric(k) for k in ("CPU","RAM","DISK","NETWORK")}; metrics.addWidget(self.metrics["CPU"],0,0); metrics.addWidget(self.metrics["RAM"],0,1); metrics.addWidget(self.metrics["DISK"],1,0); metrics.addWidget(self.metrics["NETWORK"],1,1); ll.addLayout(metrics); self.ai_label=QLabel("AI CORE / INITIALIZING"); self.ai_label.setStyleSheet("color:#62F6FF;font-size:9px;font-weight:700;letter-spacing:1px;"); ll.addWidget(self.ai_label); ll.addStretch(); body.addWidget(left,1)
        center=QFrame(); center.setStyleSheet(panel_style()); cl=QVBoxLayout(center); cl.setContentsMargins(12,12,12,12); title=QLabel("DYNAMIC INTELLIGENCE"); title.setStyleSheet("color:#7895A5;font-size:9px;font-weight:800;letter-spacing:1.7px;"); cl.addWidget(title); self.dynamic_host=QWidget(); self.dynamic_host.setStyleSheet("background:transparent;border:none;"); dl=QVBoxLayout(self.dynamic_host); dl.setContentsMargins(0,0,0,0); dl.setSpacing(8); dl.addStretch(); scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.dynamic_host); cl.addWidget(scroll,1); body.addWidget(center,3); self.dynamic_engine=CockpitWidgetEngine(self.dynamic_host)
        right=QFrame(); right.setStyleSheet(panel_style()); rl=QVBoxLayout(right); rl.setContentsMargins(12,12,12,12); q=QLabel("COMMAND DECK"); q.setStyleSheet("color:#7895A5;font-size:9px;font-weight:800;letter-spacing:1.7px;"); rl.addWidget(q); self.action_layout=QGridLayout(); self.action_layout.setSpacing(6); rl.addLayout(self.action_layout); self._build_actions(); activity_title=QLabel("LIVE FEED"); activity_title.setStyleSheet("color:#7895A5;font-size:9px;font-weight:800;letter-spacing:1.7px;margin-top:10px;"); rl.addWidget(activity_title); self.activity_label=QLabel("› Core initialized\n› Dynamic cockpit ready\n› Waiting for directive"); self.activity_label.setStyleSheet("color:#9BB4BF;font-family:Consolas;font-size:9px;"); self.activity_label.setWordWrap(True); rl.addWidget(self.activity_label); rl.addStretch(); body.addWidget(right,1); root.addLayout(body,1)
        footer=QHBoxLayout()