from __future__ import annotations

import json
import platform
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget, QMenu

CONFIG_FILE = Path.home() / ".jarvis_neo" / "jarvis_config.json"


class NeoMainHud(QMainWindow):
    command_requested = pyqtSignal(str)

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.setWindowTitle("J.A.R.V.I.S. NEO | Command Center")
        self.setMinimumSize(1050, 680)
        self.resize(1250, 780)
        self._build()
        self._setup_tray()
        self._shortcut = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        self._shortcut.activated.connect(self.toggle_hud)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    def _build(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("Header")
        hv = QHBoxLayout(header)
        title = QLabel("J.A.R.V.I.S. NEO")
        title.setObjectName("Title")
        subtitle = QLabel("COMMAND CENTER")
        subtitle.setObjectName("Subtitle")
        hv.addWidget(title)
        hv.addWidget(subtitle)
        hv.addStretch()
        self.status = QLabel("● ONLINE")
        self.status.setObjectName("Online")
        hv.addWidget(self.status)
        self.clock = QLabel("--:--:--")
        hv.addWidget(self.clock)
        layout.addWidget(header)

        hero = QFrame()
        hero.setObjectName("Hero")
        h = QVBoxLayout(hero)
        h.setContentsMargins(22, 18, 22, 18)
        self.hero = QLabel("SYSTÈME OPÉRATIONNEL")
        self.hero.setObjectName("HeroTitle")
        self.hero_detail = QLabel("Initialisation des systèmes...")
        self.hero_detail.setObjectName("HeroDetail")
        h.addWidget(self.hero)
        h.addWidget(self.hero_detail)
        layout.addWidget(hero)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.cards = {}
        for i, (key, label) in enumerate((("cpu", "CPU"), ("ram", "RAM"), ("temp", "TEMPÉRATURE"), ("ai", "IA"), ("mic", "MICRO"), ("voice", "VOIX"))):
            card = QFrame()
            card.setObjectName("Card")
            cv = QVBoxLayout(card)
            cv.setContentsMargins(14, 12, 14, 12)
            cap = QLabel(label)
            cap.setObjectName("Caption")
            val = QLabel("--")
            val.setObjectName("Value")
            cv.addWidget(cap)
            cv.addWidget(val)
            self.cards[key] = val
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)

        center = QHBoxLayout()
        center.setSpacing(10)

        ai = QFrame(); ai.setObjectName("Panel")
        av = QVBoxLayout(ai)
        av.addWidget(QLabel("INTELLIGENCE"))
        self.ai_detail = QLabel("Provider : --\nModèle : --")
        self.ai_detail.setObjectName("Detail")
        av.addWidget(self.ai_detail)
        b = QPushButton("⚙  PARAMÈTRES IA")
        b.clicked.connect(self._open_settings)
        av.addWidget(b)
        center.addWidget(ai, 1)

        actions = QFrame(); actions.setObjectName("Panel")
        qv = QVBoxLayout(actions)
        qv.addWidget(QLabel("COMMANDES"))
        row = QHBoxLayout()
        for text, command in (("TESTER", "bonjour"), ("MICRO", "écoute"), ("AGENT", "mode agent"), ("SENTINELLE", "mode sentinelle")):
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, c=command: self._send_command(c))
            row.addWidget(btn)
        qv.addLayout(row)
        center.addWidget(actions, 2)
        layout.addLayout(center)

        activity = QFrame(); activity.setObjectName("ActivityPanel")
        act = QVBoxLayout(activity)
        act.addWidget(QLabel("ACTIVITÉ EN DIRECT"))
        self.activity = QLabel("NEO prêt.")
        self.activity.setWordWrap(True)
        self.activity.setObjectName("Activity")
        act.addWidget(self.activity)
        layout.addWidget(activity, 1)

        command = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Écrire une commande à JARVIS...")
        self.input.returnPressed.connect(self._submit)
        send = QPushButton("⚡ EXÉCUTER")
        send.clicked.connect(self._submit)
        hide = QPushButton("◀ MASQUER")
        hide.clicked.connect(self.hide_hud)
        command.addWidget(self.input, 1)
        command.addWidget(send)
        command.addWidget(hide)
        layout.addLayout(command)
        self._style()

    def _style(self):
        self.setStyleSheet("""
        #Root { background:#070b10; color:#d9f7ff; }
        #Header, #Hero, #Card, #Panel, #ActivityPanel { background:#0b141b; border:1px solid #173845; border-radius:9px; }
        #Title { color:#e8fcff; font-size:24px; font-weight:700; }
        #Subtitle { color:#5f929f; font-size:10px; letter-spacing:2px; margin-left:10px; }
        #Online { color:#61e0b4; font-weight:700; }
        #HeroTitle { color:#78eaf5; font-size:27px; font-weight:700; }
        #HeroDetail, #Detail, #Activity { color:#86aeb8; }
        #Caption { color:#5f8b96; font-size:10px; font-weight:700; }
        #Value { color:#e3fbff; font-size:21px; font-weight:700; }
        QPushButton { background:#0c1b23; color:#bfe1e8; border:1px solid #1d4654; border-radius:6px; padding:9px 12px; }
        QPushButton:hover { background:#102a34; border-color:#4ba9bb; }
        QLineEdit { background:#050a0f; color:#dffaff; border:1px solid #1d4654; border-radius:6px; padding:10px; }
        """)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        menu = QMenu()
        show = QAction("Afficher le HUD", self); show.triggered.connect(self.show_hud)
        hide = QAction("Masquer le HUD", self); hide.triggered.connect(self.hide_hud)
        quit_action = QAction("Quitter JARVIS NEO", self); quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show); menu.addAction(hide); menu.addSeparator(); menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("J.A.R.V.I.S. NEO")
        self.tray.show()

    def _config(self):
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
        except Exception:
            return {}

    def _save_config(self, cfg):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    def hide_hud(self):
        cfg = self._config(); cfg["main_hud_enabled"] = False; self._save_config(cfg); self.hide()

    def show_hud(self):
        cfg = self._config(); cfg["main_hud_enabled"] = True; self._save_config(cfg); self.show(); self.raise_(); self.activateWindow()

    def toggle_hud(self):
        self.hide_hud() if self.isVisible() else self.show_hud()

    def _send_command(self, command):
        self.activity.setText(f"> {command}")
        try:
            self.assistant.command_queue.put(command)
        except Exception as exc:
            self.activity.setText(f"Erreur : {exc}")

    def _submit(self):
        text = self.input.text().strip()
        if text:
            self._send_command(text)
            self.input.clear()

    def _open_settings(self):
        try:
            from ui.provider_settings import ProviderSettingsDialog
            ProviderSettingsDialog(self).exec()
        except Exception as exc:
            QMessageBox.warning(self, "JARVIS NEO", f"Paramètres indisponibles : {exc}")

    def _get(self, *names, default="--"):
        for name in names:
            try:
                obj = self.assistant
                for part in name.split("."): obj = getattr(obj, part)
                return obj
            except Exception:
                pass
        return default

    def _refresh(self):
        self.clock.setText(time.strftime("%H:%M:%S"))
        self.cards["cpu"].setText(self._fmt(self._get("cpu_percent", default="--"), "%"))
        self.cards["ram"].setText(self._fmt(self._get("ram_percent", default="--"), "%"))
        self.cards["temp"].setText(self._fmt(self._get("cpu_temp", default="--"), "°C"))
        provider = self._get("CONFIG.ai_provider", "ai_provider", default="Ollama")
        model = self._get("CONFIG.groq_model", "ai_model", "MODEL", default="--")
        self.cards["ai"].setText(str(provider))
        self.cards["mic"].setText("ON" if bool(self._get("state.mic_enabled", default=True)) else "OFF")
        self.cards["voice"].setText("ON" if bool(self._get("state.voice_enabled", default=True)) else "OFF")
        self.ai_detail.setText(f"Provider : {provider}\nModèle : {model}")
        self.hero_detail.setText(f"{platform.system()}  •  IA {provider}  •  Micro {'actif' if self.cards['mic'].text() == 'ON' else 'désactivé'}")

    @staticmethod
    def _fmt(value, suffix):
        try: return f"{float(value):.0f}{suffix}"
        except Exception: return str(value)

    def closeEvent(self, event):
        event.ignore(); self.hide_hud()
