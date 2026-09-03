"""Provider, model and startup settings dialog used by J.A.R.V.I.S. NEO."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

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


def model_catalog(provider: str) -> list[tuple[str, str]]:
    """Return the selectable models for a provider."""
    return list(GROQ_MODELS if str(provider).lower() == "groq" else OLLAMA_MODELS)


def apply_provider_settings(
    config: dict[str, Any],
    *,
    provider: str,
    api_key: str,
    model: str,
    fallback: str,
    autostart: bool,
) -> dict[str, Any]:
    """Apply and normalize provider settings without depending on Qt."""
    provider = "groq" if str(provider).lower() == "groq" else "ollama"
    selected_model = str(model).strip()
    if provider == "groq":
        selected_model = selected_model or GROQ_MODELS[0][1]
    else:
        selected_model = selected_model or OLLAMA_MODELS[1][1]
    config["ai_provider"] = provider
    config["groq_api_key"] = str(api_key).strip()
    if provider == "groq":
        config["groq_model"] = selected_model
    else:
        config["model"] = selected_model
    config["groq_quota_fallback"] = "simple" if str(fallback).lower() in {"simple", "mode simple"} else "ollama"
    config["groq_fallback_to_ollama"] = config["groq_quota_fallback"] == "ollama"
    config["autostart"] = bool(autostart)
    return config


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
        self.provider.setCurrentText("Groq" if self.config.get("ai_provider", "groq").lower() == "groq" else "Ollama")
        self.provider.currentTextChanged.connect(self._refresh_models)
        self.key = QLineEdit(str(self.config.get("groq_api_key", "") or ""))
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.model = QComboBox()
        self.model.setMinimumContentsLength(28)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.fallback = QComboBox()
        self.fallback.addItems(["Ollama", "Mode Simple"])
        self.fallback.setCurrentText("Mode Simple" if self.config.get("groq_quota_fallback", "ollama") == "simple" else "Ollama")
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
        note = QLabel("Le modèle est choisi dans une liste et enregistré dans la configuration locale. Le prochain démarrage et le prochain message utiliseront ce choix.")
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
        current = str(self.config.get("groq_model", GROQ_MODELS[0][1])) if provider_key == "groq" else str(self.config.get("model", OLLAMA_MODELS[1][1]))
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
            self.model_hint.setText("Groq : sélectionnez directement un modèle compatible.")
        else:
            self.model_hint.setText("Ollama : sélectionnez le modèle local installé. Un modèle personnalisé déjà configuré reste disponible.")

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
        self.accept()


__all__ = ["ProviderSettingsDialog", "GROQ_MODELS", "OLLAMA_MODELS", "model_catalog", "apply_provider_settings"]
