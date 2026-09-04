from __future__ import annotations

import json
import platform
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PyQt6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget, QMenu

CONFIG_FILE = Path.home() / ".jarvis_neo" / "jarvis_config.json"


class NeoMainHud(QMainWindow):
    command_requested = pyqtSignal(str)

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self._compact = False
        self._main_root = None
        self._mini_root = None
        self.setWindowTitle("J.A.R.V.I.S. NEO | Command Center")
        self.setMinimumSize(1050, 680)
        self.resize(1250, 780)
        self._build()
        self._build_mini()
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
        self._main_root = root
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        header = QFrame(); header.setObjectName("Header")
        hv = QHBoxLayout(header)
        title = QLabel("J.A.R.V.I.S. NEO"); title.setObjectName("Title")
        subtitle = QLabel("COMMAND CENTER"); subtitle.setObjectName("Subtitle")
        hv.addWidget(title); hv.addWidget(subtitle); hv.addStretch()
        self.status = QLabel("● ONLINE"); self.status.setObjectName("Online"); hv.addWidget(self.status)
        self.clock = QLabel("--:--:--"); hv.addWidget(self.clock)
        mobile = QPushButton("📱 MOBILE"); mobile.setObjectName("MobileButton"); mobile.clicked.connect(self._show_mobile_pairing); hv.addWidget(mobile)
        layout.addWidget(header)

        hero = QFrame(); hero.setObjectName("Hero")
        h = QVBoxLayout(hero); h.setContentsMargins(22, 18, 22, 18)
        self.hero = QLabel("SYSTÈME OPÉRATIONNEL"); self.hero.setObjectName("HeroTitle")
        self.hero_detail = QLabel("Initialisation des systèmes..."); self.hero_detail.setObjectName("HeroDetail")
        h.addWidget(self.hero); h.addWidget(self.hero_detail); layout.addWidget(hero)

        grid = QGridLayout(); grid.setSpacing(10); self.cards = {}
        for i, (key, label) in enumerate((("cpu", "CPU"), ("ram", "RAM"), ("temp", "TEMPÉRATURE"), ("ai", "IA"), ("mic", "MICRO"), ("voice", "VOIX"))):
            card = QFrame(); card.setObjectName("Card")
            cv = QVBoxLayout(card); cv.setContentsMargins(14, 12, 14, 12)
            cap = QLabel(label); cap.setObjectName("Caption")
            val = QLabel("--"); val.setObjectName("Value")
            cv.addWidget(cap); cv.addWidget(val); self.cards[key] = val
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)

        center = QHBoxLayout(); center.setSpacing(10)
        ai = QFrame(); ai.setObjectName("Panel")
        av = QVBoxLayout(ai); av.addWidget(QLabel("INTELLIGENCE"))
        self.ai_detail = QLabel("Provider : --\nModèle : --"); self.ai_detail.setObjectName("Detail"); av.addWidget(self.ai_detail)
        b = QPushButton("⚙  PARAMÈTRES IA"); b.clicked.connect(self._open_settings); av.addWidget(b); center.addWidget(ai, 1)

        actions = QFrame(); actions.setObjectName("Panel")
        qv = QVBoxLayout(actions); qv.addWidget(QLabel("COMMANDES")); row = QHBoxLayout()
        for text, command in (("TESTER", "bonjour"), ("MICRO", "écoute"), ("AGENT", "mode agent"), ("SENTINELLE", "mode sentinelle")):
            btn = QPushButton(text); btn.clicked.connect(lambda checked, c=command: self._send_command(c)); row.addWidget(btn)
        qv.addLayout(row); center.addWidget(actions, 2); layout.addLayout(center)

        activity = QFrame(); activity.setObjectName("ActivityPanel")
        act = QVBoxLayout(activity); act.addWidget(QLabel("ACTIVITÉ EN DIRECT"))
        self.activity = QLabel("NEO prêt."); self.activity.setWordWrap(True); self.activity.setObjectName("Activity")
        act.addWidget(self.activity); layout.addWidget(activity, 1)

        command = QHBoxLayout(); self.input = QLineEdit(); self.input.setPlaceholderText("Écrire une commande à JARVIS...")
        self.input.returnPressed.connect(self._submit)
        send = QPushButton("⚡ EXÉCUTER"); send.clicked.connect(self._submit)
        compact = QPushButton("◀ RÉDUIRE"); compact.clicked.connect(self.minimize_hud)
        command.addWidget(self.input, 1); command.addWidget(send); command.addWidget(compact); layout.addLayout(command)
        self._style()

    def _show_mobile_pairing(self):
        try:
            from jarvis_mobile_bridge import bridge
            ip = self._get("get_local_ip", default="127.0.0.1")
            code = bridge.pairing_code
            QMessageBox.information(
                self,
                "J.A.R.V.I.S. NEO • Connexion mobile",
                f"Adresse du PC : {ip}\nPort : {bridge.port}\n\nCode d'appairage : {code}\n\nCe code est à usage unique. Entrez-le dans NEO Mobile."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Connexion mobile", f"La passerelle mobile n'est pas disponible : {exc}")

    def _build_mini(self):
        mini = QFrame(); mini.setObjectName("MiniRoot")
        layout = QHBoxLayout(mini)
        layout.setContentsMargins(13, 10, 10, 10)
        layout.setSpacing(10)

        orb = QLabel("●")
        orb.setObjectName("MiniOrb")
        orb.setFixedWidth(20)
        orb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        name = QLabel("J.A.R.V.I.S. NEO")
        name.setObjectName("MiniName")
        self.mini_status = QLabel("SYSTÈME EN LIGNE")
        self.mini_status.setObjectName("MiniStatus")
        identity.addWidget(name)
        identity.addWidget(self.mini_status)

        metrics = QVBoxLayout()
        metrics.setSpacing(1)
        self.mini_metrics = QLabel("CPU --  •  RAM --")
        self.mini_metrics.setObjectName("MiniMetrics")
        self.mini_context = QLabel("IA --  •  MICRO ON")
        self.mini_context.setObjectName("MiniContext")
        metrics.addWidget(self.mini_metrics)
        metrics.addWidget(self.mini_context)

        self.mini_clock = QLabel("--:--:--")
        self.mini_clock.setObjectName("MiniClock")
        self.mini_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mini_clock.setMinimumWidth(72)

        restore = QPushButton("⌃")
        restore.setObjectName("MiniButton")
        restore.setToolTip("Ouvrir le Command Center")
        restore.clicked.connect(self.restore_hud)
        restore.setFixedSize(34, 34)

        layout.addWidget(orb)
        layout.addLayout(identity)
        layout.addSpacing(8)
        layout.addLayout(metrics, 1)
        layout.addWidget(self.mini_clock)
        layout.addWidget(restore)

        self._mini_root = mini
        mini.hide()

    def _style(self):
        self.setStyleSheet("""
        #Root { background:#070b10; color:#d9f7ff; }
        #Header, #Hero, #Card, #Panel, #ActivityPanel { background:#0b141b; border:1px solid #173845; border-radius:9px; }
        #Title { color:#e8fcff; font-size:24px; font-weight:700; }
        #Subtitle { color:#5f929f; font-size:10px; letter-spacing:2px; margin-left:10px; }
        #Online, #MiniStatus { color:#61e0b4; font-weight:700; }
        #HeroTitle { color:#78eaf5; font-size:27px; font-weight:700; }
        #HeroDetail, #Detail, #Activity, #MiniMetrics, #MiniContext { color:#86aeb8; }
        #Caption { color:#5f8b96; font-size:10px; font-weight:700; }
        #Value { color:#e3fbff; font-size:21px; font-weight:700; }
        QPushButton { background:#0c1b23; color:#bfe1e8; border:1px solid #1d4654; border-radius:6px; padding:9px 12px; }
        QPushButton:hover { background:#102a34; border-color:#4ba9bb; }
        #MobileButton { color:#61e0b4; border-color:#2c6878; padding:7px 10px; }
        QLineEdit { background:#050a0f; color:#dffaff; border:1px solid #1d4654; border-radius:6px; padding:10px; }
        #MiniRoot { background:#081117; border:1px solid #245363; border-radius:14px; }
        #MiniOrb { color:#61e0b4; font-size:19px; }
        #MiniName { color:#e5fbff; font-size:12px; font-weight:700; }
        #MiniStatus { font-size:9px; letter-spacing:1px; }
        #MiniMetrics, #MiniContext { font-size:9px; }
        #MiniClock { color:#dffaff; font-size:12px; font-weight:700; }
        #MiniButton { background:#0d2029; color:#78eaf5; border:1px solid #285968; border-radius:8px; padding:0; font-size:16px; }
        #MiniButton:hover { background:#12303a; border-color:#61d9e7; }
        """)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self._make_tray_icon())
        menu = QMenu()
        show = QAction("Afficher le HUD", self); show.triggered.connect(self.restore_hud)
        compact = QAction("Réduire le HUD", self); compact.triggered.connect(self.minimize_hud)
        quit_action = QAction("Quitter JARVIS NEO", self); quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show); menu.addAction(compact); menu.addSeparator(); menu.addAction(quit_action)
        self.tray.setContextMenu(menu); self.tray.setToolTip("J.A.R.V.I.S. NEO")
        self.tray.activated.connect(lambda reason: self.restore_hud() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()

    @staticmethod
    def _make_tray_icon():
        pixmap = QPixmap(32, 32); pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor("#61e0b4"))); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(5, 5, 22, 22)
        painter.setBrush(QBrush(QColor("#071016"))); painter.drawEllipse(11, 11, 10, 10); painter.end()
        return QIcon(pixmap)

    def _config(self):
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
        except Exception:
            return {}

    def _save_config(self, cfg):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    def _place_mini(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        area = screen.availableGeometry()
        margin = 18
        self.move(area.right() - self.width() - margin, area.bottom() - self.height() - margin)

    def minimize_hud(self):
        cfg = self._config(); cfg["hud_mode"] = "mini"; cfg.pop("main_hud_enabled", None); self._save_config(cfg)
        self._compact = True
        self._main_root.hide()
        self.setCentralWidget(self._mini_root)
        self._mini_root.show()
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(470, 74)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.show(); self._place_mini(); self.raise_()

    def restore_hud(self):
        cfg = self._config(); cfg["hud_mode"] = "full"; cfg.pop("main_hud_enabled", None); self._save_config(cfg)
        self._compact = False
        self._mini_root.hide()
        self.setCentralWidget(self._main_root)
        self._main_root.show()
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumSize(1050, 680)
        self.resize(1250, 780)
        self.show(); self.raise_(); self.activateWindow()

    def toggle_hud(self):
        self.restore_hud() if self._compact else self.minimize_hud()

    def _send_command(self, command):
        self.activity.setText(f"> {command}")
        try: self.assistant.command_queue.put(command)
        except Exception as exc: self.activity.setText(f"Erreur : {exc}")

    def _submit(self):
        text = self.input.text().strip()
        if text: self._send_command(text); self.input.clear()

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
        now = time.strftime("%H:%M:%S")
        self.clock.setText(now)
        self.mini_clock.setText(now)
        cpu = self._fmt(self._get("cpu_percent", default="--"), "%")
        ram = self._fmt(self._get("ram_percent", default="--"), "%")
        temp = self._fmt(self._get("cpu_temp", default="--"), "°C")
        self.cards["cpu"].setText(cpu)
        self.cards["ram"].setText(ram)
        self.cards["temp"].setText(temp)
        provider = self._get("CONFIG.ai_provider", "ai_provider", default="Ollama")
        model = self._get("CONFIG.groq_model", "ai_model", "MODEL", default="--")
        mic_on = bool(self._get("state.mic_enabled", default=True))
        voice_on = bool(self._get("state.voice_enabled", default=True))
        self.cards["ai"].setText(str(provider))
        self.cards["mic"].setText("ON" if mic_on else "OFF")
        self.cards["voice"].setText("ON" if voice_on else "OFF")
        self.ai_detail.setText(f"Provider : {provider}\nModèle : {model}")
        self.hero_detail.setText(f"{platform.system()}  •  IA {provider}  •  Micro {'actif' if mic_on else 'désactivé'}")
        self.mini_status.setText("SYSTÈME EN LIGNE" if not bool(self._get("state.abort_requested", default=False)) else "ARRÊT DEMANDÉ")
        self.mini_metrics.setText(f"CPU {cpu}  •  RAM {ram}")
        self.mini_context.setText(f"IA {provider}  •  MICRO {'ON' if mic_on else 'OFF'}")

    @staticmethod
    def _fmt(value, suffix):
        try: return f"{float(value):.0f}{suffix}"
        except Exception: return str(value)

    def closeEvent(self, event):
        event.ignore()
        self.minimize_hud()
