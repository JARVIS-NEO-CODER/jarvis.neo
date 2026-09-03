from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSystemTrayIcon, QVBoxLayout,
    QWidget, QMenu,
)


CONFIG_DIR = Path.home() / ".jarvis_neo"
CONFIG_FILE = CONFIG_DIR / "jarvis_config.json"


class NeoMainHud(QMainWindow):
    """Primary JARVIS NEO desktop HUD.

    This is deliberately a normal main window rather than a floating overlay,
    so it cannot cover the application's own navigation controls.
    """

    command_requested = pyqtSignal(str)

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self._hidden = False
        self._last_activity = "Initialisation du centre de commande"
        self.setWindowTitle("J.A.R.V.I.S. NEO - Command Center")
        self.setMinimumSize(1080, 700)
        self.resize(1280, 820)
        self.setObjectName("NeoMainHud")
        self._build()
        self._setup_tray()
        self._setup_shortcut()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

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

        # IMPORTANT: add the QWidget, not its QVBoxLayout.
        outer.addWidget(sidebar)

        main = QWidget()
        mv = QVBoxLayout(main)
        mv.setContentsMargins(20, 15, 20, 15)
        mv.setSpacing(12)

        top = QFrame()
        top.setObjectName("TopBar")
        top.setFixedHeight(46)
        tv = QHBoxLayout(top)
        self.status = QLabel("●  NEO ONLINE")
        self.status.setObjectName("Status")
        self.clock = QLabel("--:--:--")
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tv.addWidget(self.status)
        tv.addStretch(1)
        tv.addWidget(self.clock)
        mv.addWidget(top)

        hero = QFrame()
        hero.setObjectName("Hero")
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(20, 18, 20, 18)
        title = QLabel("NEO COMMAND CENTER")
        title.setObjectName("HeroTitle")
        self.hero_state = QLabel("SYSTÈME OPÉRATIONNEL")
        self.hero_state.setObjectName("HeroState")
        hv.addWidget(title)
        hv.addWidget(self.hero_state)
        mv.addWidget(hero)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.cards = {}
        for idx, (key, label) in enumerate([
            ("cpu", "CPU"), ("ram", "RAM"), ("temp", "TEMPÉRATURE"),
            ("ai", "IA"), ("mic", "MICRO"), ("voice", "VOIX"),
        ]):
            card = QFrame()
            card.setObjectName("Card")
            cv = QVBoxLayout(card)
            cv.setContentsMargins(14, 12, 14, 12)
            l = QLabel(label)
            l.setObjectName("CardLabel")
            value = QLabel("--")
            value.setObjectName("CardValue")
            cv.addWidget(l)
            cv.addWidget(value)
            self.cards[key] = value
            grid.addWidget(card, idx // 3, idx % 3)
        mv.addLayout(grid)

        lower = QHBoxLayout()
        lower.setSpacing(10)

        ai_panel = QFrame()
        ai_panel.setObjectName("Panel")
        av = QVBoxLayout(ai_panel)
        av.addWidget(QLabel("INTELLIGENCE ACTIVE"))
        self.ai_detail = QLabel("Provider: --\nModèle: --")
        self.ai_detail.setObjectName("Detail")
        av.addWidget(self.ai_detail)
        ai_btn = QPushButton("⚙  CONFIGURER L'IA")
        ai_btn.clicked.connect(self._open_settings)
        av.addWidget(ai_btn)
        lower.addWidget(ai_panel, 1)

        quick = QFrame()
        quick.setObjectName("Panel")
        qv = QVBoxLayout(quick)
        qv.addWidget(QLabel("ACTIONS RAPIDES"))
        for text, command in [
            ("▸  TESTER JARVIS", "bonjour"),
            ("◌  ACTIVER MICRO", "écoute"),
            ("◇  MODE AGENT", "mode agent"),
        ]:
            b = QPushButton(text)
            b.clicked.connect(lambda checked, c=command: self._send_command(c))
            qv.addWidget(b)
        lower.addWidget(quick, 1)

        activity = QFrame()
        activity.setObjectName("Panel")
        acv = QVBoxLayout(activity)
        acv.addWidget(QLabel("ACTIVITÉ SYSTÈME"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("Activity")
        content_layout = QVBoxLayout(content)
        self.activity_label = QLabel(self._last_activity)
        self.activity_label.setWordWrap(True)
        content_layout.addWidget(self.activity_label)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        acv.addWidget(scroll)
        lower.addWidget(activity, 1)
        mv.addLayout(lower, 1)

        outer.addWidget(main, 1)
        self._apply_style()
        self.nav["overview"].setChecked(True)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
        #NeoMainHud, #Root { background:#070b10; color:#d9f7ff; }
        #Sidebar { background:#0a1118; border-right:1px solid #16313b; }
        #Brand { color:#d9f7ff; font-size:24px; font-weight:700; }
        #SubBrand, #CardLabel { color:#5f8c98; font-size:10px; font-weight:700; letter-spacing:1px; }
        QPushButton { background:#0c1820; color:#b8dbe2; border:1px solid #183843; border-radius:6px; padding:10px; text-align:left; }
        QPushButton:hover { background:#10232c; border-color:#2b6877; }
        QPushButton:checked { background:#12313a; border-color:#4aa8bb; color:#e8fcff; }
        #TopBar, #Card, #Panel, #Hero { background:#0b141b; border:1px solid #16343f; border-radius:8px; }
        #Status { color:#66d9b4; font-weight:700; }
        #HeroTitle { color:#86d9e8; font-size:26px; font-weight:700; }
        #HeroState { color:#70aab5; font-size:12px; }
        #CardValue { color:#e3fbff; font-size:20px; font-weight:700; }
        #Detail { color:#9bc6cf; padding:6px; }
        #Activity { background:#05090d; color:#83aeb8; border:1px solid #132e38; border-radius:7px; padding:9px; font-family:'Consolas'; font-size:10px; }
        QScrollArea { border:0; }
        """)

    def _setup_shortcut(self) -> None:
        self._shortcut = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        self._shortcut.activated.connect(self.toggle_hud)

    def _setup_tray(self) -> None:
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        menu = QMenu()
        show_action = QAction("Afficher le HUD", self)
        show_action.triggered.connect(self.show_hud)
        hide_action = QAction("Masquer le HUD", self)
        hide_action.triggered.connect(self.hide_hud)
        quit_action = QAction("Quitter JARVIS NEO", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("J.A.R.V.I.S. NEO")
        self.tray.show()

    def _config(self) -> dict:
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
        except Exception:
            return {}

    def _save_config(self, data: dict) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def hide_hud(self) -> None:
        cfg = self._config()
        cfg["main_hud_enabled"] = False
        self._save_config(cfg)
        self._hidden = True
        self.hide()

    def show_hud(self) -> None:
        cfg = self._config()
        cfg["main_hud_enabled"] = True
        self._save_config(cfg)
        self._hidden = False
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_hud(self) -> None:
        if self.isVisible():
            self.hide_hud()
        else:
            self.show_hud()

    def _navigate(self, key: str) -> None:
        for k, button in self.nav.items():
            button.setChecked(k == key)
        if key == "ai":
            self._open_settings()
        elif key == "voice":
            self._send_command("écoute")
        elif key == "agent":
            self._send_command("mode agent")
        elif key == "sentinel":
            self._send_command("mode sentinelle")
        self._last_activity = f"Navigation: {key}"
        self.activity_label.setText(self._last_activity)

    def _send_command(self, command: str) -> None:
        self._last_activity = f"> {command}"
        self.activity_label.setText(self._last_activity)
        try:
            self.command_requested.emit(command)
            if hasattr(self.assistant, "handle_command"):
                self.assistant.handle_command(command)
            elif hasattr(self.assistant, "process_command"):
                self.assistant.process_command(command)
        except Exception as exc:
            self.activity_label.setText(f"Erreur commande: {exc}")

    def _open_settings(self) -> None:
        for name in ("open_settings", "show_settings", "_open_settings"):
            fn = getattr(self.assistant, name, None)
            if callable(fn):
                try:
                    fn()
                    return
                except TypeError:
                    pass
        QMessageBox.information(self, "JARVIS NEO", "Les paramètres sont gérés par le moteur JARVIS.")

    def _get_attr(self, *names, default="--"):
        for name in names:
            obj = self.assistant
            try:
                for part in name.split("."):
                    obj = getattr(obj, part)
                if obj is not None:
                    return obj
            except Exception:
                continue
        return default

    def _refresh(self) -> None:
        self.clock.setText(time.strftime("%H:%M:%S"))
        cpu = self._get_attr("cpu_percent", "cpu_usage", default="--")
        ram = self._get_attr("ram_percent", "memory_percent", default="--")
        temp = self._get_attr("cpu_temp", "temperature", default="--")
        provider = self._get_attr("ai_provider", "provider", "ai.provider", default="--")
        model = self._get_attr("ai_model", "model", "ai.model", default="--")
        mic = self._get_attr("microphone_status", "mic_status", default="PRÊT")
        voice = self._get_attr("voice_status", "tts_status", default="PRÊT")
        self.cards["cpu"].setText(self._fmt(cpu, "%"))
        self.cards["ram"].setText(self._fmt(ram, "%"))
        self.cards["temp"].setText(self._fmt(temp, "°C"))
        self.cards["ai"].setText(str(provider))
        self.cards["mic"].setText(str(mic))
        self.cards["voice"].setText(str(voice))
        self.ai_detail.setText(f"Provider: {provider}\nModèle: {model}")
        self.hero_state.setText(f"SYSTÈME OPÉRATIONNEL  •  {platform.system()}  •  IA: {provider}")

    @staticmethod
    def _fmt(value, suffix: str) -> str:
        if value in (None, "", "--"):
            return "--"
        try:
            return f"{float(value):.0f}{suffix}"
        except Exception:
            return str(value)

    def closeEvent(self, event) -> None:
        # Closing the window hides the HUD instead of killing the assistant.
        event.ignore()
        self.hide_hud()
