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
    clicked=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent); self.angle=0; self.status="ONLINE"; self.timer=QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(35); self.setMinimumSize(210,210); self.setCursor(Qt.CursorShape.PointingHandCursor)
    def _tick(self): self.angle=(self.angle+2)%360; self.update()
    def set_status(self,status): self.status=str(status).upper(); self.update()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton: self.clicked.emit()
        super().mousePressEvent(event)
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
        super().__init__(parent); self.assistant=assistant; self._drag_pos=None; self._mini_mode=False; self.setWindowTitle("J.A.R.V.I.S. NEO // COMMAND CENTER"); self.setMinimumSize(1040,680); self.resize(1240,780); self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Window|Qt.WindowType.WindowStaysOnTopHint); self.setStyleSheet("QDialog{background:#030810;color:#EAFBFF;}"+panel_style()); self._build(); self.dynamic_request.connect(self.show_dynamic_panel); self.dynamic_remove_request.connect(self.remove_dynamic_panel); self.dynamic_clear_request.connect(self.clear_dynamic_panels); signals=getattr(assistant,"signals",None)
        if signals is not None:
            try: signals.log_msg.connect(self._on_log)
            except Exception: pass
        self._timer=QTimer(self); self._timer.timeout.connect(self.refresh); self._timer.start(1000); self.refresh()
    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(20,16,20,16); root.setSpacing(12); self._root=root
        header=QHBoxLayout(); brand=QLabel("J.A.R.V.I.S. NEO"); brand.setStyleSheet("color:#62F6FF;font-size:19px;font-weight:900;letter-spacing:3px;"); subtitle=QLabel("NEURAL COMMAND CENTER  //  DYNAMIC COCKPIT"); subtitle.setStyleSheet("color:#587584;font-size:8px;font-weight:700;letter-spacing:1.6px;"); self.status=QLabel("● ONLINE"); self.status.setStyleSheet("color:#58FFC4;font-size:10px;font-weight:800;"); self.mode=QLabel("NORMAL"); self.mode.setStyleSheet("color:#7895A5;font-size:9px;font-weight:700;"); close=QPushButton("×"); close.setFixedSize(34,30); close.clicked.connect(self._minimize_to_reactor); header.addWidget(brand); header.addSpacing(14); header.addWidget(subtitle); header.addStretch(); header.addWidget(self.status); header.addSpacing(12); header.addWidget(self.mode); header.addWidget(close); root.addLayout(header)
        body=QHBoxLayout(); body.setSpacing(12); self._body_layout=body
        left=QFrame(); left.setStyleSheet(panel_style()); ll=QVBoxLayout(left); ll.setContentsMargins(12,12,12,12); self.reactor=Reactor(); ll.addWidget(self.reactor,0,Qt.AlignmentFlag.AlignCenter); self.reactor.clicked.connect(self._restore_from_reactor); metrics=QGridLayout(); metrics.setSpacing(7); self.metrics={k:Metric(k) for k in ("CPU","RAM","DISK","NETWORK")}; metrics.addWidget(self.metrics["CPU"],0,0); metrics.addWidget(self.metrics["RAM"],0,1); metrics.addWidget(self.metrics["DISK"],1,0); metrics.addWidget(self.metrics["NETWORK"],1,1); ll.addLayout(metrics); self.ai_label=QLabel("AI CORE / INITIALIZING"); self.ai_label.setStyleSheet("color:#62F6FF;font-size:9px;font-weight:700;letter-spacing:1px;"); ll.addWidget(self.ai_label); ll.addStretch(); body.addWidget(left,1); self._full_widgets=[left]
        center=QFrame(); center.setStyleSheet(panel_style()); cl=QVBoxLayout(center); cl.setContentsMargins(12,12,12,12); title=QLabel("DYNAMIC INTELLIGENCE"); title.setStyleSheet("color:#7895A5;font-size:9px;font-weight:800;letter-spacing:1.7px;"); cl.addWidget(title); self.dynamic_host=QWidget(); self.dynamic_host.setStyleSheet("background:transparent;border:none;"); dl=QVBoxLayout(self.dynamic_host); dl.setContentsMargins(0,0,0,0); dl.setSpacing(8); dl.addStretch(); scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.dynamic_host); cl.addWidget(scroll,1); body.addWidget(center,3); self.dynamic_engine=CockpitWidgetEngine(self.dynamic_host); self._full_widgets.append(center)
        right=QFrame(); right.setStyleSheet(panel_style()); rl=QVBoxLayout(right); rl.setContentsMargins(12,12,12,12); q=QLabel("COMMAND DECK"); q.setStyleSheet("color:#7895A5;font-size:9px;font-weight:800;letter-spacing:1.7px;"); rl.addWidget(q); self.action_layout=QGridLayout(); self.action_layout.setSpacing(6); rl.addLayout(self.action_layout); self._build_actions(); activity_title=QLabel("LIVE FEED"); activity_title.setStyleSheet("color:#7895A5;font-size:9px;font-weight:800;letter-spacing:1.7px;margin-top:10px;"); rl.addWidget(activity_title); self.activity_label=QLabel("› Core initialized\n› Dynamic cockpit ready\n› Waiting for directive"); self.activity_label.setStyleSheet("color:#9BB4BF;font-family:Consolas;font-size:9px;"); self.activity_label.setWordWrap(True); rl.addWidget(self.activity_label); rl.addStretch(); body.addWidget(right,1); self._full_widgets.append(right); root.addLayout(body,1)
        footer=QHBoxLayout(); self._footer_widgets=[]
        for text,slot in (("COMPACT",self._compact),("NORMAL",self._normal),("CLEAR PANELS",self.clear_dynamic_panels),("REFRESH",self.refresh)):
            b=QPushButton(text); b.clicked.connect(slot); footer.addWidget(b); self._footer_widgets.append(b)
        footer.addStretch(); self.pin=QPushButton("PIN"); self.pin.setCheckable(True); self.pin.setChecked(True); self.pin.clicked.connect(self._toggle_pin); footer.addWidget(self.pin); self._footer_widgets.append(self.pin); root.addLayout(footer)
        self._header_widgets=[brand,subtitle,self.status,self.mode,close]
        self.mini_reactor=Reactor(self); self.mini_reactor.setMinimumSize(0,0); self.mini_reactor.setFixedSize(190,190); self.mini_reactor.clicked.connect(self._restore_from_reactor); self.mini_reactor.hide()
    def _build_actions(self):
        configured=get_data("command_deck",None)
        if not isinstance(configured,list) or not configured: configured=get_data("ui_actions",[])
        for i,item in enumerate(configured):
            if not isinstance(item,dict): continue
            label,command=str(item.get("label","")).strip(),str(item.get("command","")).strip()
            if not label or not command: continue
            b=QPushButton(label); b.setToolTip(command); b.clicked.connect(lambda _,c=command:self._command(c)); self.action_layout.addWidget(b,i//2,i%2)
    def _command(self,command):
        try:
            queue=getattr(self.assistant,"command_queue",None)
            if queue is not None: queue.put(command); self._on_log("COMMAND",command)
        except Exception as exc: self._on_log("ERROR",str(exc))
    def _minimize_to_reactor(self):
        if self._mini_mode: return
        self._mini_mode=True
        for widget in self._header_widgets+self._full_widgets+self._footer_widgets: widget.hide()
        self.mini_reactor.set_status(getattr(self.reactor,"status","ONLINE")); self.mini_reactor.show(); self.setMinimumSize(0,0); self.setFixedSize(210,210); self.setStyleSheet("QDialog{background:transparent;border:none;}" ); self.mini_reactor.move(10,10); self.setWindowOpacity(0.82); self.raise_(); self.activateWindow()
    def _restore_from_reactor(self):
        if not self._mini_mode: return
        self._mini_mode=False; self.mini_reactor.hide(); self.setMinimumSize(1040,680); self.setFixedSize(1240,780); self.setStyleSheet("QDialog{background:#030810;color:#EAFBFF;}"+panel_style())
        for widget in self._header_widgets+self._full_widgets+self._footer_widgets: widget.show()
        self.setWindowOpacity(1.0); self.show(); self.raise_(); self.activateWindow()
    def show_dynamic_panel(self,panel_id,title,content="",kind="info",source=""): return self.dynamic_engine.show_panel(panel_id,title,content,kind,source)
    def enqueue_dynamic_panel(self,panel_id,title,content="",kind="info",source=""): self.dynamic_request.emit(str(panel_id),str(title),str(content),str(kind),str(source))
    def remove_dynamic_panel(self,panel_id): return self.dynamic_engine.remove_panel(panel_id)
    def enqueue_remove_dynamic_panel(self,panel_id): self.dynamic_remove_request.emit(str(panel_id))
    def clear_dynamic_panels(self): self.dynamic_engine.clear()
    def enqueue_clear_dynamic_panels(self): self.dynamic_clear_request.emit()
    def dynamic_panels(self): return self.dynamic_engine.snapshot()
    def _on_log(self,category,message): self.activity_label.setText(f"[{str(category).upper()}] {message}")
    def _toggle_pin(self):
        flags=self.windowFlags(); flags=flags|Qt.WindowType.WindowStaysOnTopHint if self.pin.isChecked() else flags&~Qt.WindowType.WindowStaysOnTopHint; self.setWindowFlags(flags); self.show()
    def _compact(self): self.resize(900,560)
    def _normal(self): self.resize(1240,780)
    def refresh(self):
        cpu=ram=disk=0
        if psutil:
            try: cpu,ram,disk=psutil.cpu_percent(),psutil.virtual_memory().percent,psutil.disk_usage('/').percent
            except Exception: pass
        self.metrics["CPU"].set_value(cpu); self.metrics["RAM"].set_value(ram); self.metrics["DISK"].set_value(disk)
        try: socket.create_connection(("1.1.1.1",53),timeout=.15).close(); net=100
        except Exception: net=0
        self.metrics["NETWORK"].set_value(net); state=getattr(self.assistant,"state",None); processor=getattr(self.assistant,"processor",None); config=getattr(self.assistant,"CONFIG",{}) or {}; conversation=getattr(processor,"conversation_ai",None) if processor else None; status=getattr(conversation,"status",{}) if conversation else {}; provider=str(status.get("active_provider") or config.get("ai_provider","ollama")).upper(); model=str(config.get("groq_model" if provider=="GROQ" else "model","--")); self.ai_label.setText(f"AI CORE  /  {provider}  /  {model}"); listening=bool(getattr(state,"is_listening",False)) if state else False; speaking=bool(getattr(state,"is_speaking",False)) if state else False; voice="LISTENING" if listening else "SPEAKING" if speaking else "ONLINE"; self.reactor.set_status(voice); self.mini_reactor.set_status(voice); self.status.setText(f"● {voice}"); self.mode.setText("AGENT" if bool(getattr(processor,"_neo_agent_mode",False)) else "NORMAL")
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton: self._drag_pos=event.globalPosition().toPoint()-self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self._drag_pos is not None and event.buttons()&Qt.MouseButton.LeftButton: self.move(event.globalPosition().toPoint()-self._drag_pos)
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event): self._drag_pos=None; super().mouseReleaseEvent(event)
