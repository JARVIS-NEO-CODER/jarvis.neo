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


GROQ_MODELS = [
    ("Llama 3.1 8B Instant", "llama-3.1-8b-instant"),
    ("Llama 3.3 70B Versatile", "llama-3.3-70b-versatile"),
    ("GPT-OSS 20B", "openai/gpt-oss-20b"),
    ("GPT-OSS 120B", "openai/gpt-oss-120b"),
    ("Qwen 3.8 27B", "qwen/qwen3.8-27b"),
    ("Groq Compound", "groq/compound"),
    ("Groq Compound Mini", "groq/compound-mini"),
]

OLLAMA_MODELS = [
    ("Grand • Llama 3.1 8B", "llama3.1:8b"),
    ("Moyen • Llama 3.2 3B", "llama3.2:3b"),
    ("Petit • Phi-3 Mini", "phi3:mini"),
    ("Mini • Gemma 2 2B", "gemma2:2b"),
]


class ProviderSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S. NEO • Paramètres")
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
        form.addRow("Fallback quota", self.fallback)
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
            "Le modèle est maintenant choisi dans une liste. Le choix est enregistré "
            "dans la configuration locale et sera utilisé par le fournisseur sélectionné."
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
        current = (
            str(self.config.get("groq_model", "llama-3.1-8b-instant"))
            if provider == "Groq"
            else str(self.config.get("model", "llama3.2:3b"))
        )
        models = GROQ_MODELS if provider == "Groq" else OLLAMA_MODELS

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

        if provider == "Groq":
            self.model_hint.setText(
                "Groq : sélectionnez directement un modèle compatible. "
                "Les modèles proposés correspondent au catalogue Groq actuel."
            )
        else:
            self.model_hint.setText(
                "Ollama : sélectionnez le modèle local que vous avez installé. "
                "Si un modèle personnalisé était déjà configuré, il reste sélectionnable."
            )

    def _save(self):
        selected_model = self.model.currentData() or self.model.currentText().strip()
        self.config["ai_provider"] = self.provider.currentText().lower()
        self.config["groq_api_key"] = self.key.text().strip()
        self.config["groq_model"] = (
            str(selected_model) if self.provider.currentText() == "Groq" else self.config.get("groq_model", "llama-3.1-8b-instant")
        )
        self.config["model"] = (
            str(selected_model) if self.provider.currentText() == "Ollama" else self.config.get("model", "llama3.2:3b")
        )
        self.config["groq_quota_fallback"] = (
            "simple" if self.fallback.currentText() == "Mode Simple" else "ollama"
        )
        self.config["groq_fallback_to_ollama"] = self.config["groq_quota_fallback"] == "ollama"
        self.config["autostart"] = self.autostart.isChecked()

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
        self.accept()


__all__ = ["ProviderSettingsDialog"]
