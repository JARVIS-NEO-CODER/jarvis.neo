"""Small provider settings dialog used by the discrete HUD."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class ProviderSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S. NEO • Fournisseur IA")
        self.setMinimumWidth(430)
        self.setStyleSheet("QDialog{background:#07101c;color:#e8f7ff} QLabel{color:#c8e8f5} QLineEdit,QComboBox{background:#0b1827;color:#fff;border:1px solid #23617a;padding:7px;border-radius:6px} QPushButton{background:#10283a;color:#63d9ff;border:1px solid #23617a;padding:8px;border-radius:6px}")
        self.path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
        self.config = self._load()
        root = QVBoxLayout(self)
        title = QLabel("⚡ CONFIGURATION DU NOYAU IA")
        title.setStyleSheet("font-weight:bold;color:#63d9ff;font-size:14px")
        root.addWidget(title)
        form = QFormLayout()
        self.provider = QComboBox(); self.provider.addItems(["Groq", "Ollama"])
        self.provider.setCurrentText("Groq" if self.config.get("ai_provider", "groq").lower() == "groq" else "Ollama")
        self.key = QLineEdit(str(self.config.get("groq_api_key", "") or "")); self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.model = QLineEdit(str(self.config.get("groq_model", "llama-3.1-8b-instant")))
        self.fallback = QComboBox(); self.fallback.addItems(["Ollama", "Mode Simple"])
        self.fallback.setCurrentText("Mode Simple" if self.config.get("groq_quota_fallback", "ollama") == "simple" else "Ollama")
        form.addRow("Fournisseur principal", self.provider)
        form.addRow("Clé API Groq", self.key)
        form.addRow("Modèle Groq", self.model)
        form.addRow("Fallback quota", self.fallback)
        root.addLayout(form)
        note = QLabel("La clé reste dans la configuration locale de NEO et n'est pas écrite dans le code source.")
        note.setWordWrap(True); note.setStyleSheet("color:#7f9aaa;font-size:11px")
        root.addWidget(note)
        buttons = QHBoxLayout(); buttons.addStretch()
        save = QPushButton("ENREGISTRER"); save.clicked.connect(self._save); buttons.addWidget(save)
        cancel = QPushButton("ANNULER"); cancel.clicked.connect(self.reject); buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except Exception:
            return {}

    def _save(self):
        self.config["ai_provider"] = self.provider.currentText().lower()
        self.config["groq_api_key"] = self.key.text().strip()
        self.config["groq_model"] = self.model.text().strip() or "llama-3.1-8b-instant"
        self.config["groq_quota_fallback"] = "simple" if self.fallback.currentText() == "Mode Simple" else "ollama"
        self.config["groq_fallback_to_ollama"] = self.config["groq_quota_fallback"] == "ollama"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.config, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        self.accept()


__all__ = ["ProviderSettingsDialog"]
