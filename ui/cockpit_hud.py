"""J.A.R.V.I.S. NEO futuristic command cockpit."""
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

CYAN, WHITE, GREEN, RED, BG = "#62F6FF", "#EAFBFF", "#58FFC4", "#FF6B7A", "#02060D"


def panel_style() -> str:
    return f"""QFrame.cockpitPanel {{ background:rgba(6,16,27,238); border:1px solid rgba(98,246,255,52); border-radius:14px; }}
QLabel {{ color:{WHITE}; background:transparent; border:none; }}
QPushButton {{ color:{CYAN}; background:rgba(98,246,255,7); border:1px solid rgba(98,246,255,48); border-radius:7px; padding:7px 8px; font-size:8px; font-weight:800; }}
QPushButton:hover {{ background:rgba(98,246,255,18); border-color:{CYAN}; }}
QPushButton:pressed {{ background:rgba(98,246,255,30); }}
QPushButton:checked {{ background:rgba(98,246,255,24); border-color:{CYAN}; }}
QScrollArea {{ background:transparent; border:none; }}"""


class Reactor(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle, self.status = 0.0, "ONLINE"
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(35)
        self.setMinimumSize(230, 230); self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _tick(self): self.angle = (self.angle + 1.8) % 360; self.update()
    def set_status(self, status): self.status = str(status or "ONLINE").upper(); self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        del event; p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = QPointF(self.width()/2, self.height()/2); r = min(self.width(), self.height())/2-16
        active = self.status in {"LISTENING", "SPEAKING", "THINKING", "PROCESSING"}
        color = QColor(GREEN if self.status in {"LISTENING", "SPEAKING"} else RED if self.status == "ERROR" else CYAN)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(3,14,24,245)); p.drawEllipse(c,r,r)
        for i in range(48):
            p.save(); p.translate(c); p.rotate(i*7.5+self.angle*.12); alpha = 150 if i%4==0 else 42
            p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),alpha),1.5)); length=13 if i%4==0 else 6
            p.drawLine(QPointF(0,-r),QPointF(0,-r+length)); p.restore()
        for rr,alpha,w in ((r-8,42,1),(r-26,80,1),(r-48,125,2)):
            p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),alpha),w)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(c,rr,rr)
        p.save(); p.translate(c); p.rotate(self.angle); p.setPen(QPen(color,2));
        p.drawArc(int(-r+26),int(-r+26),int((r-26)*2),int((r-26)*2),12*16,72*16); p.drawArc(int(-r+26),int(-r+26),int((r-26)*2),int((r-26)*2),192*16,72*16)
        p.setPen(QPen(QColor(color.red(),color.green(),color.blue(),150),2)); p.drawLine(QPointF(-r*.62,0),QPointF(-r*.40,0)); p.drawLine(QPointF(r*.40,0),QPointF(r*.62,0)); p.restore()
        p.setPen(QPen(color,2.5 if active else 1.5)); p.setBrush(QColor(color.red(),color.green(),color.blue(),38)); p.drawEllipse(c,31,31)
        p.setBrush(QColor(color.red(),color.green(),color.blue(),125)); p.drawEllipse(c,19,19); p.setBrush(QColor(color.red(),color.green(),color.blue(),225)); p.drawEllipse(c,7,7)
        p.setPen(QColor(WHITE)); p.setFont(QFont("Segoe UI",10,QFont.Weight.Bold)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,self.status)
        p.setPen(QColor("#6C8794")); p.setFont(QFont("Consolas",7,QFont.Weight.DemiBold)); p.drawText(0,int(self.height()*.67),self.width(),18,Qt.AlignmentFlag.AlignCenter,"NEO // CORE LINK"); p.end()


class Metric(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent); self.setObjectName("cockpitPanel"); self.setStyleSheet(panel_style())
        box=QVBoxLayout(self); box.setContentsMargins(10,8,10,8); box.setSpacing(5); row=QHBoxLayout()
        self.name=QLabel(str(name).upper()); self.name.setStyleSheet("color:#6C8794;font-size:7px;font-weight:800;letter-spacing:1.5px;")
        self.value=QLabel("0%"); self.value.setStyleSheet(f"color:{WHITE};font-size:13px;font-weight:900;"); self.value.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.name); row.addStretch(); row.addWidget(self.value); box.addLayout(row)
        self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setTextVisible(False); self.bar.setFixedHeight(3); self.bar.setStyleSheet(f"QProgressBar{{background:rgba(255,255,255,10);border:0;}} QProgressBar::chunk{{background:{CYAN};}} "); box.addWidget(self.bar)
    def set_value(self,value): value=max(0,min(100,int(value))); self.value.setText(f"{value}%"); self.bar.setValue(value)


class CockpitHud(QDialog):
    dynamic_request=pyqtSignal(str,str,str,str,str); dynamic_remove_request=pyqtSignal(str); dynamic_clear_request=pyqtSignal()

    def __init__(self, assistant: Any, parent=None):
        super().__init__(parent); self.assistant=assistant; self._mini_mode=False
        self.setWindowTitle("J.A.R.V.I.S. NEO // COMMAND CENTER"); self.setMinimumSize(860,540); self.resize(1280,760)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Window|Qt.WindowType.WindowStaysOnTopHint); self.setStyleSheet(f"QDialog{{background:{BG};color:{WHITE};}}"+panel_style())
        self._build(); self.dynamic_request.connect(self.show_dynamic_panel); self.dynamic_remove_request.connect(self.remove_dynamic_panel); self.dynamic_clear_request.connect(self.clear_dynamic_panels)
        signals=getattr(assistant,"signals",None)
        if signals is not None:
            try: signals.log_msg.connect(self._on_log)
            except Exception: pass
        self._timer=QTimer(self); self._timer.timeout.connect(self.refresh); self._timer.start(1500); self.refresh()

    def _panel(self,title):
        frame=QFrame(); frame.setObjectName("cockpitPanel"); frame.setStyleSheet(panel_style()); layout=QVBoxLayout(frame); layout.setContentsMargins(12,11,12,11); layout.setSpacing(8)
        label=QLabel(title); label.setStyleSheet("color:#6C8794;font-size:8px;font-weight:900;letter-spacing:1.8px;"); layout.addWidget(label); return frame,layout

    def _add_command_group(self, layout, title, actions):
        label=QLabel(title); label.setStyleSheet("color:#6C8794;font-size:7px;font-weight:900;letter-spacing:1.5px;margin-top:4px;"); layout.addWidget(label)
        grid=QGridLayout(); grid.setSpacing(5)
        for i,(text,command) in enumerate(actions):
            b=QPushButton(text); b.setToolTip(command); b.clicked.connect(lambda _,c=command:self._command(c)); grid.addWidget(b,i//2,i%2)
        layout.addLayout(grid)

    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(18,15,18,15); root.setSpacing(10)
        header=QHBoxLayout(); brand=QLabel("J.A.R.V.I.S. NEO"); brand.setStyleSheet(f"color:{CYAN};font-size:18px;font-weight:950;letter-spacing:3px;")
        subtitle=QLabel("NEURAL COMMAND INTERFACE  //  LOCAL CORE"); subtitle.setStyleSheet("color:#456774;font-size:7px;font-weight:800;letter-spacing:1.8px;")
        self.status=QLabel("● ONLINE"); self.status.setStyleSheet(f"color:{GREEN};font-size:9px;font-weight:900;"); self.mode=QLabel("NORMAL"); self.mode.setStyleSheet("color:#7A98A4;font-size:8px;font-weight:800;")
        close=QPushButton("×"); close.setFixedSize(32,28); close.clicked.connect(self._minimize_to_reactor)
        header.addWidget(brand); header.addSpacing(12); header.addWidget(subtitle); header.addStretch(); header.addWidget(self.status); header.addSpacing(10); header.addWidget(self.mode); header.addSpacing(8); header.addWidget(close); root.addLayout(header)
        line=QFrame(); line.setFixedHeight(1); line.setStyleSheet("background:rgba(98,246,255,70);border:none;"); root.addWidget(line); self._header_widgets=[brand,subtitle,self.status,self.mode,close]

        body=QHBoxLayout(); body.setSpacing(10); self._body_widgets=[]
        left,ll=self._panel("CORE TELEMETRY"); self.reactor=Reactor(); self.reactor.clicked.connect(self._restore_from_reactor); ll.addWidget(self.reactor,0,Qt.AlignmentFlag.AlignCenter)
        metrics=QGridLayout(); metrics.setSpacing(6); self.metrics={k:Metric(k) for k in ("CPU","RAM","DISK","NETWORK")}
        for i,k in enumerate(self.metrics): metrics.addWidget(self.metrics[k],i//2,i%2)
        ll.addLayout(metrics); self.ai_label=QLabel("AI CORE / INITIALIZING"); self.ai_label.setStyleSheet(f"color:{CYAN};font-size:8px;font-weight:800;"); ll.addWidget(self.ai_label); ll.addStretch(); body.addWidget(left,1); self._body_widgets.append(left)

        center,cl=self._panel("DYNAMIC INTELLIGENCE"); self.dynamic_host=QWidget(); self.dynamic_host.setStyleSheet("background:transparent;border:none;"); scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.dynamic_host); cl.addWidget(scroll,1); self.dynamic_engine=CockpitWidgetEngine(self.dynamic_host); body.addWidget(center,3); self._body_widgets.append(center)

        right,rl=self._panel("COMMAND DECK"); command_scroll=QScrollArea(); command_scroll.setWidgetResizable(True); command_host=QWidget(); command_layout=QVBoxLayout(command_host); command_layout.setContentsMargins(0,0,0,0); command_layout.setSpacing(5)
        self._add_command_group(command_layout,"JARVIS CORE",[("NEW TASK","nouvelle tâche"),("AGENT","lance une mission autonome"),("SENTINEL","active le mode Sentinel"),("MEMORY","ouvre ma mémoire"),("HISTORY","affiche l'historique"),("PLUGINS","liste les plugins"),("DIAGNOSTIC","diagnostic complet"),("SETTINGS","ouvre les paramètres")])
        self._add_command_group(command_layout,"SYSTEM",[("APPS","ouvre les applications"),("FILES","ouvre explorateur"),("DESKTOP","affiche le bureau"),("TASKS","gestionnaire des tâches"),("TERMINAL","ouvre le terminal"),("WINDOWS","ouvre les paramètres Windows"),("LOCK","verrouille le PC"),("RESTART","redémarre le PC")])
        self._add_command_group(command_layout,"WEB & MEDIA",[("WEB","recherche sur le web"),("IMAGES","recherche des images"),("YOUTUBE","ouvre YouTube"),("NEWS","cherche les actualités"),("WEATHER","météo"),("DOWNLOADS","ouvre les téléchargements"),("TRANSLATE","traduis"),("SEARCH","recherche")])
        self._add_command_group(command_layout,"DEVELOPMENT",[("VS CODE","ouvre VS Code"),("GITHUB","ouvre GitHub"),("PYTHON","ouvre Python"),("GIT","affiche le statut git"),("TESTS","lance les tests"),("BUILD","lance le build"),("PROJECTS","ouvre mes projets"),("LOGS","affiche les logs")])
        self._add_command_group(command_layout,"MONITORING",[("CPU","état du processeur"),("RAM","état de la mémoire"),("DISK","état du disque"),("NETWORK","état du réseau"),("PROCESSES","liste les processus"),("BATTERY","état de la batterie"),("REFRESH","actualise le système"),("HELP","aide")]); command_layout.addStretch(); command_scroll.setWidget(command_host); rl.addWidget(command_scroll,1)
        feed=QLabel("LIVE FEED"); feed.setStyleSheet("color:#6C8794;font-size:8px;font-weight:900;letter-spacing:1.8px;margin-top:6px;"); rl.addWidget(feed); self.activity_label=QLabel("› Core initialized\n› Cockpit ready\n› Waiting for directive"); self.activity_label.setStyleSheet("color:#89A9B5;font-family:Consolas;font-size:8px;"); self.activity_label.setWordWrap(True); rl.addWidget(self.activity_label); body.addWidget(right,2); self._body_widgets.append(right); root.addLayout(body,1)

        footer=QHBoxLayout(); self._footer_widgets=[]
        for text,slot in (("COMPACT",self._compact),("NORMAL",self._normal),("CLEAR",self.clear_dynamic_panels),("REFRESH",self.refresh)):
            b=QPushButton(text); b.clicked.connect(slot); footer.addWidget(b); self._footer_widgets.append(b)
        footer.addStretch(); self.pin=QPushButton("PIN"); self.pin.setCheckable(True); self.pin.setChecked(True); self.pin.clicked.connect(self._toggle_pin); footer.addWidget(self.pin); self._footer_widgets.append(self.pin); root.addLayout(footer)
        self.mini_reactor=Reactor(self); self.mini_reactor.setMinimumSize(0,0); self.mini_reactor.setFixedSize(190,190); self.mini_reactor.clicked.connect(self._restore_from_reactor); self.mini_reactor.hide()

    def _command(self,command):
        try:
            queue=getattr(self.assistant,"command_queue",None)
            if queue is None: raise RuntimeError("file de commandes indisponible")
            queue.put(str(command)); self._on_log("COMMAND",str(command))
        except Exception as exc: self._on_log("ERROR",str(exc))

    def _minimize_to_reactor(self):
        if self._mini_mode:return
        self._mini_mode=True
        for w in self._header_widgets+self._body_widgets+self._footer_widgets:w.hide()
        self.mini_reactor.set_status(self.reactor.status); self.mini_reactor.show(); self.setMinimumSize(0,0); self.setFixedSize(210,210); self.setStyleSheet("QDialog{background:transparent;border:none;}"); self.mini_reactor.move(10,10); self.setWindowOpacity(.88); self.raise_(); self.activateWindow()

    def _restore_from_reactor(self):
        if not self._mini_mode:return
        self._mini_mode=False; self.mini_reactor.hide(); self.setMinimumSize(860,540); self.setStyleSheet(f"QDialog{{background:{BG};color:{WHITE};}}"+panel_style())
        for w in self._header_widgets+self._body_widgets+self._footer_widgets:w.show()
        self._normal(); self.setWindowOpacity(1); self.show(); self.raise_(); self.activateWindow()

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
    def _available_size(self,w,h):
        screen=self.screen() or (self.windowHandle().screen() if self.windowHandle() else None)
        if screen is None:return w,h,None
        area=screen.availableGeometry(); return min(w,max(320,area.width()-28)),min(h,max(240,area.height()-28)),area
    def _center_on_available_screen(self,w,h):
        w,h,area=self._available_size(w,h); self.setFixedSize(w,h)
        if area is not None:self.move(area.center().x()-w//2,area.center().y()-h//2)
    def _compact(self): self._center_on_available_screen(900,560)
    def _normal(self): self._center_on_available_screen(1280,760)

    def refresh(self):
        cpu=ram=disk=0
        if psutil is not None:
            try:cpu,ram,disk=psutil.cpu_percent(),psutil.virtual_memory().percent,psutil.disk_usage("/").percent
            except Exception:pass
        for key,val in (("CPU",cpu),("RAM",ram),("DISK",disk)):self.metrics[key].set_value(val)
        try:socket.create_connection(("1.1.1.1",53),timeout=.12).close();net=100
        except Exception:net=0
        self.metrics["NETWORK"].set_value(net)
        state=getattr(self.assistant,"state",None); processor=getattr(self.assistant,"processor",None); config=getattr(self.assistant,"CONFIG",{}) or {}; conversation=getattr(processor,"conversation_ai",None) if processor else None; status=getattr(conversation,"status",{}) if conversation else {}
        if not isinstance(status,dict):status={}
        provider=str(status.get("active_provider") or config.get("ai_provider","ollama")).upper(); model=str(config.get("groq_model" if provider=="GROQ" else "model","--")); self.ai_label.setText(f"AI CORE / {provider} / {model}")
        listening=bool(getattr(state,"is_listening",False)) if state else False; speaking=bool(getattr(state,"is_speaking",False)) if state else False; voice="LISTENING" if listening else "SPEAKING" if speaking else "ONLINE"; self.reactor.set_status(voice); self.mini_reactor.set_status(voice); self.status.setText(f"● {voice}"); self.status.setStyleSheet(f"color:{GREEN if voice!='ONLINE' else CYAN};font-size:9px;font-weight:900;"); self.mode.setText("AGENT" if bool(getattr(processor,"_neo_agent_mode",False)) else "NORMAL")

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self._drag_pos=event.globalPosition().toPoint()-self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if getattr(self,"_drag_pos",None) is not None and event.buttons()&Qt.MouseButton.LeftButton:self.move(event.globalPosition().toPoint()-self._drag_pos)
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):self._drag_pos=None; super().mouseReleaseEvent(event)
