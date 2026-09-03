"""Small always-on-top desktop reactor for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import json, math, os
from pathlib import Path
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

class DiscreteHud(QWidget):
    """Lightweight top-right reactor with live provider state."""
    def __init__(self, window):
        super().__init__(None); self.window=window; self.phase=0.0; self.last_stats={"cpu":0.0,"ram":0.0}
        self.setFixedSize(92,92); self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating); self.setToolTip("J.A.R.V.I.S. NEO • clic gauche : cockpit • clic droit : menu")
        self._timer=QTimer(self); self._timer.timeout.connect(self._refresh); self._timer.start(1500)
    def show_discrete(self):
        screen=QApplication.primaryScreen()
        if screen:
            area=screen.availableGeometry(); self.move(area.right()-self.width()-18,area.top()+18)
        self.show(); self.raise_(); self._refresh()
    def _config(self):
        try:
            path=Path.home()/".jarvis_neo"/"jarvis_config.json"; return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception: return {}
    def _refresh(self):
        try:
            import psutil; self.last_stats={"cpu":psutil.cpu_percent(interval=None),"ram":psutil.virtual_memory().percent}
        except Exception: pass
        self.phase=(self.phase+0.22)%(math.pi*2); self.update()
    def _state(self):
        try:
            import assistant; state=getattr(assistant,"state",None)
        except Exception: state=None
        if state is None:return "online","ONLINE"
        if getattr(state,"alarm_triggered",False):return "error","ALERTE"
        if getattr(state,"is_speaking",False):return "speaking","VOIX"
        if getattr(state,"is_listening",False):return "listening","ÉCOUTE"
        if getattr(state,"is_processing",False):return "processing","TRAITEMENT"
        return "online","EN LIGNE"
    def _provider(self):
        try:
            import assistant
            processor=getattr(assistant,"processor",None); engine=getattr(processor,"_neo_conversation_ai",None)
            if engine is not None:
                status=engine.status; active=status.get("active_provider")
                if active:return active.upper()+(" • FALLBACK" if status.get("last_fallback_reason") else "")
            config=getattr(assistant,"CONFIG",{})
        except Exception: config=self._config()
        provider=str(config.get("ai_provider","groq")).lower()
        if provider=="ollama":return "OLLAMA"
        if provider=="groq":return "GROQ" if config.get("groq_api_key") or os.getenv("GROQ_API_KEY") else "GROQ • CLÉ MANQUANTE"
        return provider.upper()
    def paintEvent(self,event):
        del event; painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); state,label=self._state(); colors={"online":"#28b8ff","listening":"#ffd34d","processing":"#b66cff","speaking":"#42e89a","error":"#ff4b5c"}; color=QColor(colors.get(state,colors["online"])); cx,cy=self.width()/2,38; pulse=1.0+0.045*math.sin(self.phase)
        painter.setPen(QPen(QColor(color.red(),color.green(),color.blue(),35),5)); painter.drawEllipse(int(cx-28*pulse),int(cy-28*pulse),int(56*pulse),int(56*pulse)); painter.setPen(QPen(QColor(color.red(),color.green(),color.blue(),190),2)); painter.drawEllipse(int(cx-23),int(cy-23),46,46); painter.setPen(QPen(color,2.5)); painter.save(); painter.translate(cx,cy); painter.rotate(self.phase*35); painter.drawRect(-12,-12,24,24); painter.restore(); painter.setBrush(color); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(int(cx-5),int(cy-5),10,10); painter.setPen(QColor("#e9f7ff")); painter.drawText(0,69,self.width(),12,Qt.AlignmentFlag.AlignCenter,label); painter.setPen(QColor("#8aa0b2")); painter.drawText(0,83,self.width(),9,Qt.AlignmentFlag.AlignCenter,self._provider()); painter.end()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self._neo_reveal()
        elif event.button()==Qt.MouseButton.RightButton:
            menu=QMenu(self); settings=menu.addAction("⚙ Paramètres IA"); menu.addSeparator(); hide=menu.addAction("Masquer le HUD"); quit_action=menu.addAction("Quitter J.A.R.V.I.S. NEO"); chosen=menu.exec(self.mapToGlobal(event.position().toPoint()))
            if chosen is settings:
                try:
                    from ui.provider_settings import ProviderSettingsDialog; ProviderSettingsDialog(self).exec()
                    try:
                        import assistant; processor=getattr(assistant,"processor",None); engine=getattr(processor,"_neo_conversation_ai",None)
                        if engine is not None: engine.config.update(self._config()); engine.refresh()
                    except Exception: pass
                except Exception: pass
            elif chosen is hide:self.hide()
            elif chosen is quit_action:QApplication.quit()
        event.accept()
    def _neo_reveal(self):
        if self.window is None:return
        self.window._neo_reveal=True
        try:self.hide(); self.window.show(); self.window.raise_(); self.window.activateWindow()
        finally:self.window._neo_reveal=False
__all__=["DiscreteHud"]
