"""Provider, model and startup settings dialog used by J.A.R.V.I.S. NEO."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from core.ai_model_catalog import (
    GROQ_MODELS,
    OLLAMA_MODELS,
    apply_provider_settings,
    model_catalog,
)


class ProviderSettingsDialog(QDialog):
    """Single source of truth for provider/model settings.

    Settings are persisted locally and applied immediately to the running
    conversation engine when the dialog is accepted.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S. NEO • Paramètres IA")
        self.setMinimumWidth(500)
        self.setStyleSheet(
            "QDialog{background:#07101c;color:#e8f7ff} "
            "QLabel{color:#c8e8f5} "
            "QLineEdit,QComboBox{background:#0b1827;color:#fff;"
            "border:1px solid #23617a;padding:7px;border-radius:6px} "
            "QPushButton{background:#10283a;color:#63d9ff;border:1px solid #23617a;"
            "padding:8px;border-radius:6px} QCheckBox{color:#c8e8f5}"
        )
        self.path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
        self.config = self._load()
        root = QVBoxLayout(self)

        title = QLabel("⚡ CONFIGURATION DE J.A.R.V.I.S. NEO")
        title.setStyleSheet("font-weight:bold;color:#63d9ff;font-size:14px")
        root.addWidget(title)

        form = QFormLayout()
        self.provider = QComboBox()
        self.provider.addItems(["Groq", "Ollama"])
        self.provider.setCurrentText(
            "Groq" if self.config.get("ai_provider", "groq").lower() == "groq" else "Ollama"
        )
        self.provider.currentTextChanged.connect(self._refresh_models)

        self.key = QLineEdit(str(self.config.get("groq_api_key", "") or ""))
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("gsk_... (Groq uniquement)")

        self.model = QComboBox()
        self.model.setMinimumContentsLength(28)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.fallback = QComboBox()
        self.fallback.addItems(["Ollama", "Mode Simple"])
        self.fallback.setCurrentText(
            "Mode Simple"
            if self.config.get("groq_quota_fallback", "ollama") == "simple"
            else "Ollama"
        )

        form.addRow("Fournisseur principal", self.provider)
        form.addRow("Clé API Groq", self.key)
        form.addRow("Modèle IA", self.model)
        form.addRow("Fallback quota Groq", self.fallback)
        root.addLayout(form)

        self.model_hint = QLabel()
        self.model_hint.setWordWrap(True)
        self.model_hint.setStyleSheet("color:#7f9aaa;font-size:11px")
        root.addWidget(self.model_hint)
        self._refresh_models(self.provider.currentText())

        self.autostart = QCheckBox("Démarrer NEO automatiquement avec Windows")
        self.autostart.setChecked(bool(self.config.get("autostart", True)))
        root.addWidget(self.autostart)

        note = QLabel(
            "Le fournisseur et le modèle sélectionnés sont enregistrés localement "
            "et appliqués immédiatement au prochain message."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#7f9aaa;font-size:11px")
        root.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        save = QPushButton("ENREGISTRER")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        cancel = QPushButton("ANNULER")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except Exception:
            return {}

    def _refresh_models(self, provider: str):
        provider_key = str(provider).lower()
        if provider_key == "groq":
            current = str(self.config.get("groq_model", GROQ_MODELS[0][1]))
        else:
            current = str(self.config.get("model", OLLAMA_MODELS[1][1]))

        models = model_catalog(provider_key)
        self.model.blockSignals(True)
        self.model.clear()
        for label, model_id in models:
            self.model.addItem(label, model_id)

        index = self.model.findData(current)
        if index >= 0:
            self.model.setCurrentIndex(index)
        elif current:
            self.model.addItem(f"Personnalisé • {current}", current)
            self.model.setCurrentIndex(self.model.count() - 1)
        self.model.blockSignals(False)

        if provider_key == "groq":
            self.model_hint.setText("Groq : choisissez un modèle cloud dans la liste.")
        else:
            self.model_hint.setText(
                "Ollama : choisissez un modèle local. Un modèle personnalisé déjà configuré reste disponible."
            )

    def _apply_runtime_config(self):
        """Refresh the live conversation router without requiring a restart."""
        try:
            import assistant
            processor = getattr(assistant, "processor", None)
            if processor is None:
                return False
            from core.conversation_ai import ConversationAI
            processor.conversation_ai = ConversationAI(self.config, getattr(assistant, "ollama", None))
            return True
        except Exception:
            return False

    def _save(self):
        selected_model = self.model.currentData() or self.model.currentText().strip()
        self.config = apply_provider_settings(
            self.config,
            provider=self.provider.currentText(),
            api_key=self.key.text(),
            model=selected_model,
            fallback=self.fallback.currentText(),
            autostart=self.autostart.isChecked(),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.config, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        try:
            from core.windows_autostart import set_enabled
            set_enabled(self.config["autostart"])
        except Exception:
            pass

        runtime_ok = self._apply_runtime_config()
        self.accept()

        # Keep the caller informed through the existing activity signal when
        # JARVIS is already running. A restart is only needed if no live engine
        # exists yet, never for a normal settings change.
        try:
            import assistant
            signals = getattr(assistant, "signals", None)
            if signals is not None and hasattr(signals, "log_msg"):
                status = "appliqués immédiatement" if runtime_ok else "enregistrés, appliqués au prochain démarrage"
                signals.log_msg.emit("IA", f"Paramètres IA {status} : {self.config['ai_provider']} / {self.config.get('groq_model') if self.config['ai_provider'] == 'groq' else self.config.get('model')}")
        except Exception:
            pass


__all__ = ["ProviderSettingsDialog", "GROQ_MODELS", "OLLAMA_MODELS", "model_catalog", "apply_provider_settings"]
