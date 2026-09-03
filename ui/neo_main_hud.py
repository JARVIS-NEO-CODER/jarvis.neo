"""Modern visible J.A.R.V.I.S. NEO command center.

This is the primary desktop HUD. It is a single normal QMainWindow, not a
floating overlay, so it never covers navigation or application controls.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSystemTrayIcon, QVBoxLayout, QWidget,
    QMenu,
)

CONFIG_PATH = Path.home() / ".jarvis_neo" / "jarvis_config.json"


def _config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    except Exception:
        return {}


def _save_config(data: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "--", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 13, 16, 13)
        self.title = QLabel(title.upper())
        self.title.setObjectName("CardTitle")
        self.value = QLabel(value)
        self.value.setObjectName("MetricValue")
        box.addWidget(self.title)
        box.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(str(value))


class NeoMainHud(QMainWindow):
    """The actual primary desktop HUD, replacing the legacy cockpit layout."""

    closed = pyqtSignal()

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._hidden = False
        self.setWindowTitle("J.A.R.V.I.S. NEO | Command Center")
        self.setMinimumSize(1080, 680)
        self.resize(1320, 820)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet(self._style())
        self._build()
        self._connect_signals()
        self._setup_tray()
        self._setup_shortcut()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    def _style(self) -> str:
        return """
        QMainWindow, QWidget { background:#05080d; color:#d9f7ff; font-family:'Segoe UI'; }
        #Root { background:#05080d; }
        #Sidebar { background:#080d14; border-right:1px solid #173746; }
        #Brand { color:#70f4ff; font-size:21px; font-weight:700; letter-spacing:2px; }
        #SubBrand { color:#62808b; font-size:10px; letter-spacing:1px; }
        QPushButton { background:#09131b; color:#9bc7d0; border:1px solid #183846; border-radius:7px; padding:10px 12px; text-align:left; }
        QPushButton:hover { background:#0d202b; border-color:#2e91a8; color:#e8fdff; }
        QPushButton:checked { background:#0c2a35; border-color:#55e6f4; color:#75f4ff; }
        #TopBar { background:#070d13; border-bottom:1px solid #173746; }
        #Title { color:#e8fbff; font-size:17px; font-weight:600; }
        #Status { color:#5ff5c8; font-size:11px; font-weight:600; }
        #Section { color:#78eaf5; font-size:12px; font-weight:700; letter-spacing:1px; }
        #Hero { background:#071018; border:1px solid #164151; border-radius:12px; }
        #HeroTitle { color:#7ff6ff; font-size:27px; font-weight:600; }
        #HeroText { color:#7898a3; font-size:11px; }
        #MetricCard { background:#071019; border:1px solid #153846; border-radius:9px; }
        #CardTitle { color:#66818a; font-size:9px; font-weight:700; letter-spacing:1px; }
        #MetricValue { color:#dffcff; font-size:22px; font-weight:600; }
        #Panel { background:#071019; border:1px solid #153846; border-radius:10px; }
        #PanelTitle { color:#a7dce4; font-size:11px; font-weight:700; letter-spacing:1px; }
        #Activity { background:#04070b; color:#78a6b0; border:1px solid #132e38; border-radius:7px; padding:9px; font-family:'Consolas'; font-size:10px; }
        QScrollArea { border:0; }
        """

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 20, 16, 16)
        side.setSpacing(8)
        brand = QLabel("J.A.R.V.I.S.")
        brand.setObjectName("Brand")
        sub = QLabel("NEO COMMAND CENTER")
        sub.setObjectName("SubBrand")
        side.addWidget(brand)
        side.addWidget(sub)
        side.addSpacing(20)
        self.nav = {}
        for key, label in [
            ("overview", "◈  VUE GÉNÉRALE"),
            ("ai", "◉  INTELLIGENCE"),
            ("voice", "◌  VOIX & MICRO"),
            ("system", "▣  SYSTÈME"),
            ("agent", "◇  MODE AGENT"),
            ("sentinel", "⬡  SENTINELLE"),
            ("activity", "≡  ACTIVITÉ"),
        ]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, k=key: self._navigate(k))
            self.nav[key] = button
            side.addWidget(button)
        side.addStretch(1)
        hide = QPushButton("◀  MASQUER LE HUD")
        hide.clicked.connect(self.hide_hud)
        side.addWidget(hide)
        settings = QPushButton("⚙  PARAMÈTRES")
        settings.clicked.connect(self._open_settings)
        side.addWidget(settings)
        outer.addWidget(side)

        main = QWidget()
        mv = QVBoxLayout(main)
        mv.setContentsMargins(20, 15, 20, 15)
        mv.setSpacing(12)
        top = QFrame()
        top.setObjectName("TopBar")
        top.setFixedHeight(46)
        th = QHBoxLayout(top)
        th.setContentsMargins(12, 0, 12, 0)
        self.page_title = QLabel("COMMAND CENTER")
        self.page_title.setObjectName("Title")
        self.status = QLabel("● ONLINE")
        self.status.setObjectName("Status")
        self.clock = QLabel("--:--:--")
        self.clock.setStyleSheet("color:#67818a;font-size:11px;")
        th.addWidget(self.page_title)
        th.addStretch(1)
        th.addWidget(self.status)
        th.addSpacing(20)
        th.addWidget(self.clock)
        mv.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 4, 4, 8)
        cv.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("Hero")
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(20, 18, 20, 18)
        self.hero_title = QLabel("SYSTÈMES EN LIGNE")
        self.hero_title.setObjectName("HeroTitle")
        self.hero_text = QLabel("Le centre de commande NEO est actif. Tous les états sont surveillés en temps réel.")
        self.hero_text.setObjectName("HeroText")
        hv.addWidget(self.hero_title)
        hv.addWidget(self.hero_text)
        cv.addWidget(hero)

        sec = QLabel("TÉLÉMÉTRIE")
        sec.setObjectName("Section")
        cv.addWidget(sec)
        grid = QGridLayout()
        grid.setSpacing(10)
        self.cards = {k: MetricCard(t) for k, t in [
            ("cpu", "CPU"), ("ram", "RAM"), ("temp", "TEMPÉRATURE"),
            ("ai", "IA"), ("mic", "MICRO"), ("voice", "VOIX"),
        ]}
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 3, i % 3)
        cv.addLayout(grid)

        panels = QHBoxLayout()
        panels.setSpacing(10)
        ai_panel = QFrame(); ai_panel.setObjectName("Panel")
        av = QVBoxLayout(ai_panel)
        at = QLabel("INTELLIGENCE ACTIVE"); at.setObjectName("PanelTitle")
        self.ai_detail = QLabel("Fournisseur : --\nModèle : --\nFallback : --")
        self.ai_detail.setStyleSheet("color:#88aeb7;font-size:11px;")
        av.addWidget(at); av.addWidget(self.ai_detail); av.addStretch(1)
        panels.addWidget(ai_panel, 1)

        action_panel = QFrame(); action_panel.setObjectName("Panel")
        ac = QVBoxLayout(action_panel)
        act = QLabel("ACTIONS RAPIDES"); act.setObjectName("PanelTitle")
        ac.addWidget(act)
        for label, cmd in [
            ("WEB", "ouvre une recherche web"),
            ("FICHIERS", "ouvre mes fichiers"),
            ("AGENT", "active le mode agent"),
            ("SENTINELLE", "active le mode sentinelle"),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, c=cmd: self._command(c))
            ac.addWidget(button)
        panels.addWidget(action_panel, 1)
        cv.addLayout(panels)

        sec2 = QLabel("FLUX SYSTÈME")
        sec2.setObjectName("Section")
        cv.addWidget(sec2)
        self.activity = QLabel("Initialisation du flux…")
        self.activity.setObjectName("Activity")
        self.activity.setMinimumHeight(130)
        self.activity.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        cv.addWidget(self.activity)
        scroll.setWidget(content)
        mv.addWidget(scroll, 1)
        outer.addWidget(main, 1)
        self._navigate("overview")

    def _connect_signals(self) -> None:
        signals = getattr(self.core, "signals", None)
        if not signals:
            return
        for name, handler in [
            ("status_change", self._on_status),
            ("listening_change", self._on_listening),
            ("speaking_change", self._on_speaking),
            ("stats_update", self._on_stats),
            ("log_msg", self._on_log),
            ("model_tier_change", self._on_model_tier),
        ]:
            signal = getattr(signals, name, None)
            if signal:
                try:
                    signal.connect(handler)
                except Exception:
                    pass

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        menu = QMenu(self)
        show = QAction("Afficher / masquer le HUD", self)
        show.triggered.connect(self.toggle_hud)
        menu.addAction(show)
        quit_action = QAction("Quitter J.A.R.V.I.S. NEO", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("J.A.R.V.I.S. NEO")
        self.tray.show()

    def _setup_shortcut(self) -> None:
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        self.shortcut.activated.connect(self.toggle_hud)

    def _navigate(self, key: str) -> None:
        for k, button in self.nav.items():
            button.setChecked(k == key)
        titles = {
            "overview": "COMMAND CENTER", "ai": "INTELLIGENCE", "voice": "VOIX & MICRO",
            "system": "SYSTÈME", "agent": "MODE AGENT", "sentinel": "SENTINELLE", "activity": "ACTIVITÉ",
        }
        self.page_title.setText(titles.get(key, "COMMAND CENTER"))
        if key == "ai":
            self._open_settings()
        elif key == "agent":
            self._command("active le mode agent")
        elif key == "sentinel":
            self._command("active le mode sentinelle")

    def _command(self, text: str) -> None:
        try:
            self.core.command_queue.put(text)
            self._on_log("USER", f"> {text}")
        except Exception as exc:
            self._on_log("ERROR", str(exc))

    def _open_settings(self) -> None:
        try:
            from ui.provider_settings import ProviderSettingsDialog
            ProviderSettingsDialog(self).exec()
        except Exception as exc:
            QMessageBox.warning(self, "Paramètres IA", str(exc))

    def _on_status(self, status: str) -> None:
        value = str(status).upper()
        if "ERREUR" in value:
            self.status.setText("● ERREUR")
        elif "ÉCOUTE" in value or "ECOUTE" in value:
            self.status.setText("● ÉCOUTE")
        elif "RÉFLEXION" in value or "REFLEXION" in value:
            self.status.setText("● RÉFLEXION")
        elif "PARLE" in value:
            self.status.setText("● PAROLE")
        else:
            self.status.setText("● ONLINE")

    def _on_listening(self, active: bool) -> None:
        self.cards["mic"].set_value("ON" if active else "STANDBY")

    def _on_speaking(self, active: bool) -> None:
        self.cards["voice"].set_value("PARLE" if active else "PRÊT")

    def _on_stats(self, data: dict) -> None:
        self.cards["cpu"].set_value(f"{int(data.get('cpu', 0))}%")
        self.cards["ram"].set_value(f"{int(data.get('ram', 0))}%")
        temp = data.get("temp")
        self.cards["temp"].set_value(f"{int(temp)}°C" if isinstance(temp, (int, float)) else "--")

    def _on_model_tier(self, tier: str) -> None:
        self.cards["ai"].set_value(str(tier).upper())

    def _on_log(self, sender: str, message: str) -> None:
        if message == "__CLEAR_CHAT__":
            self.activity.setText("")
            return
        stamp = time.strftime("%H:%M:%S")
        old = self.activity.text().split("\n") if self.activity.text() else []
        lines = (old + [f"[{stamp}] {sender}: {str(message)}"])[-12:]
        self.activity.setText("\n".join(lines))

    def _refresh(self) -> None:
        self.clock.setText(time.strftime("%H:%M:%S"))
        cfg = getattr(self.core, "CONFIG", {})
        provider = str(cfg.get("ai_provider", "groq")).upper()
        model = str(cfg.get("groq_model" if provider == "GROQ" else "model", "--"))
        fallback = str(cfg.get("groq_quota_fallback", "ollama")).upper()
        self.ai_detail.setText(f"Fournisseur : {provider}\nModèle : {model}\nFallback : {fallback}")
        if self.cards["ai"].value.text() == "--":
            self.cards["ai"].set_value(provider)
        state = getattr(getattr(self.core, "state", None), "is_listening", False)
        self.cards["mic"].set_value("ON" if state else "STANDBY")

    def hide_hud(self) -> None:
        self._hidden = True
        cfg = getattr(self.core, "CONFIG", None)
        if not isinstance(cfg, dict):
            cfg = _config()
        cfg["main_hud_enabled"] = False
        _save_config(cfg)
        self.hide()

    def show_hud(self) -> None:
        self._hidden = False
        cfg = getattr(self.core, "CONFIG", None)
        if not isinstance(cfg, dict):
            cfg = _config()
        cfg["main_hud_enabled"] = True
        _save_config(cfg)
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_hud(self) -> None:
        self.show_hud() if self._hidden or not self.isVisible() else self.hide_hud()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide_hud()
        self.closed.emit()
