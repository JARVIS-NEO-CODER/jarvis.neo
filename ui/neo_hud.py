"""J.A.R.V.I.S. NEO — main HUD composition layer.

The HUD owns presentation and small user-facing controls only. AI provider
configuration is persisted through the existing assistant configuration and
ConversationAI is rebuilt after changes, while vision remains untouched.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .arc_reactor import ArcReactor
from .hud import HudPanel
from .system_panel import SystemPanel
from .terminal import NeoTerminal


DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


class GroqSettingsDialog(QDialog):
    """Small HUD dialog for Groq/Ollama conversation settings."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S. NEO — Intelligence")
        self.setMinimumWidth(470)
        self.setStyleSheet(
            """
            QDialog { background:#050907; color:#d9f5c4; }
            QLabel { color:#b8d8b0; }
            QLineEdit, QComboBox {
                background:#07110b; color:#e7f7df;
                border:1px solid #304833; border-radius:7px; padding:8px;
            }
            QCheckBox { color:#ccefb4; }
            QPushButton {
                background:#0b1710; color:#ccefb4;
                border:1px solid #304833; border-radius:7px; padding:8px 12px;
            }
            QPushButton:hover { background:#122419; border-color:#80ad54; }
            """
        )

        self.core = None
        try:
            import assistant as core
            self.core = core
        except Exception:
            pass

        config = getattr(self.core, "CONFIG", {}) if self.core else self._load_config_file()

        root = QVBoxLayout(self)
        intro = QLabel(
            "Configure le fournisseur de conversation. La vision continue d'utiliser Ollama."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.api_key = QLineEdit(str(config.get("groq_api_key", "")))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("gsk_…")

        self.model = QLineEdit(str(config.get("groq_model", DEFAULT_GROQ_MODEL)))
        self.provider = QComboBox()
        self.provider.addItem("Groq prioritaire → Ollama fallback", "groq")
        self.provider.addItem("Ollama uniquement", "ollama")
        current_provider = config.get("ai_provider", "groq")
        index = self.provider.findData(current_provider)
        if index >= 0:
            self.provider.setCurrentIndex(index)

        self.ollama_enabled = QCheckBox("Autoriser Ollama comme fallback")
        self.ollama_enabled.setChecked(bool(config.get("ollama_enabled", True)))

        form.addRow("Clé API Groq", self.api_key)
        form.addRow("Modèle Groq", self.model)
        form.addRow("Fournisseur", self.provider)
        form.addRow("Fallback", self.ollama_enabled)
        root.addLayout(form)

        actions = QHBoxLayout()
        self.test_button = QPushButton("TESTER GROQ")
        self.test_button.clicked.connect(self.test_groq)
        actions.addWidget(self.test_button)
        actions.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        actions.addWidget(buttons)
        root.addLayout(actions)

        self.status = QLabel("Modèle recommandé : llama-3.1-8b-instant")
        self.status.setStyleSheet("color:#7895A5;font-size:10px;")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _load_config_file() -> dict:
        path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            return {}

    def _current_config(self) -> dict:
        if self.core is not None:
            return self.core.CONFIG
        return self._load_config_file()

    def test_groq(self) -> None:
        key = self.api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Groq", "Aucune clé API Groq n'est renseignée.")
            return

        try:
            from core.groq_provider import GroqProvider
            provider = GroqProvider(
                api_key=key,
                model=self.model.text().strip() or DEFAULT_GROQ_MODEL,
                timeout=15,
            )
            result = provider.chat(
                [{"role": "user", "content": "Réponds uniquement : OK"}],
                temperature=0,
                max_tokens=8,
            )
            self.status.setText("✓ Groq répond correctement : " + result.strip()[:80])
            self.status.setStyleSheet("color:#58FFC4;font-size:10px;")
        except Exception as exc:
            self.status.setText("✗ Test Groq échoué : " + str(exc))
            self.status.setStyleSheet("color:#FF7A86;font-size:10px;")

    def save(self) -> None:
        config = self._current_config()
        config["groq_api_key"] = self.api_key.text().strip()
        config["groq_model"] = self.model.text().strip() or DEFAULT_GROQ_MODEL
        config["ai_provider"] = self.provider.currentData() or "groq"
        config["ollama_enabled"] = self.ollama_enabled.isChecked()
        config.setdefault("groq_timeout", 60)

        try:
            if self.core is not None:
                self.core.save_config(config)
                processor = getattr(self.core, "processor", None)
                if processor is not None:
                    from core.conversation_ai import ConversationAI
                    processor.conversation_ai = ConversationAI(config, getattr(self.core, "ollama", None))
            else:
                path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Configuration", f"Impossible d'enregistrer : {exc}")
            return

        self.accept()


class NeoHud(QWidget):
    """Full-screen NEO cockpit layout ready to be embedded in JarvisWindow."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("neoHud")
        self.setStyleSheet("""
            QWidget#neoHud {
                background: #050907;
                color: #d9f5c4;
            }
            QLabel#neoHeader {
                color: #baff62;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#neoSubHeader {
                color: #657565;
                font-size: 9px;
                letter-spacing: 1px;
            }
            QPushButton.neoControl {
                background: #0b1710;
                color: #ccefb4;
                border: 1px solid #304833;
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton.neoControl:hover {
                background: #122419;
                border-color: #80ad54;
            }
            QPushButton.neoControl:pressed {
                background: #1a3020;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("J.A.R.V.I.S. NEO")
        title.setObjectName("neoHeader")
        subtitle = QLabel("LOCAL INTELLIGENCE COCKPIT  //  SYSTEM ONLINE")
        subtitle.setObjectName("neoSubHeader")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(subtitle)
        root.addLayout(header)

        main = QHBoxLayout()
        main.setSpacing(14)

        left = HudPanel("Terminal")
        self.terminal = NeoTerminal()
        left.add_widget(self.terminal)
        left.setMinimumWidth(270)
        left.setMaximumWidth(360)

        center = QFrame()
        center.setStyleSheet("QFrame { background: transparent; border: none; }")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reactor = ArcReactor()
        self.reactor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout.addWidget(self.reactor, 1, Qt.AlignmentFlag.AlignCenter)

        right = HudPanel("System")
        self.system_panel = SystemPanel()
        right.add_widget(self.system_panel)
        right.setMinimumWidth(210)
        right.setMaximumWidth(290)

        main.addWidget(left, 0)
        main.addWidget(center, 1)
        main.addWidget(right, 0)
        root.addLayout(main, 1)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.buttons = {}
        for label in ("MIC", "VOICE", "MODE", "PLUGINS", "SENTINEL", "SETTINGS"):
            button = QPushButton(label)
            button.setProperty("class", "neoControl")
            button.setObjectName("neoControl")
            button.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.buttons[label] = button
            controls.addWidget(button)

        self.buttons["MIC"].clicked.connect(self._toggle_microphone)
        self.buttons["VOICE"].clicked.connect(self._open_settings)
        self.buttons["MODE"].clicked.connect(self._cycle_mode)
        self.buttons["PLUGINS"].clicked.connect(self._open_plugins)
        self.buttons["SENTINEL"].clicked.connect(self._toggle_sentinel)
        self.buttons["SETTINGS"].clicked.connect(self._open_settings)
        root.addLayout(controls)

    def _core(self):
        try:
            import assistant as core
            return core
        except Exception:
            return None

    def _open_settings(self) -> None:
        dialog = GroqSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.append_terminal("SYSTEM", "Configuration IA enregistrée.")

    def _toggle_microphone(self) -> None:
        core = self._core()
        if core is None:
            return
        core.CONFIG["microphone_enabled"] = not bool(core.CONFIG.get("microphone_enabled", True))
        core.save_config(core.CONFIG)
        state = core.CONFIG["microphone_enabled"]
        self.buttons["MIC"].setText("MIC ON" if state else "MIC OFF")
        self.append_terminal("SYSTEM", "Microphone " + ("activé." if state else "désactivé."))

    def _cycle_mode(self) -> None:
        core = self._core()
        if core is None:
            return
        tiers = ["mini", "petit", "moyen", "grand"]
        current = core.CONFIG.get("model_tier", "moyen")
        next_tier = tiers[(tiers.index(current) + 1) % len(tiers)] if current in tiers else tiers[0]
        core.CONFIG["model_tier"] = next_tier
        core.save_config(core.CONFIG)
        self.append_terminal("SYSTEM", f"Mode IA local : {next_tier.upper()}")

    def _open_plugins(self) -> None:
        core = self._core()
        path = Path(getattr(core, "PLUGINS_DIR", Path.home() / ".jarvis_neo" / "plugins"))
        path.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self.append_terminal("SYSTEM", f"Dossier plugins ouvert : {path}")
        except Exception as exc:
            QMessageBox.warning(self, "Plugins", str(exc))

    def _toggle_sentinel(self) -> None:
        core = self._core()
        processor = getattr(core, "processor", None) if core else None
        if processor is None or not hasattr(processor, "toggle_security"):
            QMessageBox.information(self, "Sentinel", "Le module Sentinelle n'est pas disponible.")
            return
        try:
            active = bool(getattr(core.state, "security_mode", False))
            message = processor.toggle_security("off" if active else "on")
            self.append_terminal("SYSTEM", message)
        except Exception as exc:
            QMessageBox.warning(self, "Sentinel", str(exc))

    def set_reactor_state(self, state: str) -> None:
        self.reactor.set_state(state)

    def append_terminal(self, speaker: str, message: str) -> None:
        self.terminal.append_entry(speaker, message)

    def set_system_value(self, name: str, value: str) -> None:
        self.system_panel.set_value(name, value)
