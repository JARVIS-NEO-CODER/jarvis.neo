"""Provider, model and startup settings dialog used by J.A.R.V.I.S. NEO."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout
from core.ai_model_catalog import apply_provider_settings, model_catalog


class ProviderSettingsDialog(QDialog):
    """Single, visible provider/model selector used by the HUD."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S. NEO • Paramètres IA")
        self.setMinimumWidth(560)
        self.setStyleSheet(
            "QDialog{background:#07101c;color:#e8f7ff} QLabel{color:#c8e8f5} "
            "QLineEdit,QComboBox{background:#0b1827;color:#fff;border:1px solid #23617a;padding:8px;border-radius:6px;min-height:20px} "
            "QComboBox::drop-down{width:30px;border-left:1px solid #23617a} "
            "QPushButton{background:#10283a;color:#63d9ff;border:1px solid #23617a;padding:9px;border-radius:6px} "
            "QCheckBox{color:#c8e8f5}"
        )
        self.path = Path.home() / ".jarvis_neo" / "jarvis_config.json"
        self.config = self._load()
        root = QVBoxLayout(self)
        title = QLabel("⚡ CERVEAU IA • FOURNISSEUR & MODÈLE")
        title.setStyleSheet("font-weight:bold;color:#63d9ff;font-size:15px")
        root.addWidget(title)
        root.addWidget(QLabel("Le menu ci-dessous est la liste réelle des modèles que J.A.R.V.I.S. peut sélectionner."))

        form = QFormLayout()
        self.provider = QComboBox()
        self.provider.addItem("Groq • Cloud", "groq")
        self.provider.addItem("Ollama • Local", "ollama")
        self.provider.setCurrentIndex(0 if str(self.config.get("ai_provider", "groq")).lower() == "groq" else 1)
        self.provider.currentIndexChanged.connect(self._refresh_models)
        form.addRow("Fournisseur IA", self.provider)

        self.model = QComboBox()
        self.model.setMinimumHeight(40)
        self.model.setMinimumContentsLength(34)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        form.addRow("Modèle IA", self.model)

        self.key = QLineEdit(str(self.config.get("groq_api_key", "") or ""))
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("gsk_... (Groq uniquement)")
        form.addRow("Clé API Groq", self.key)

        self.fallback = QComboBox()
        self.fallback.addItem("Ollama", "ollama")
        self.fallback.addItem("Mode Simple", "simple")
        self.fallback.setCurrentIndex(1 if self.config.get("groq_quota_fallback", "ollama") == "simple" else 0)
        form.addRow("Fallback quota", self.fallback)
        root.addLayout(form)

        self.model_hint = QLabel()
        self.model_hint.setWordWrap(True)
        self.model_hint.setStyleSheet("color:#7f9aaa;font-size:11px")
        root.addWidget(self.model_hint)
        self._refresh_models()

        self.autostart = QCheckBox("Démarrer NEO automatiquement avec Windows")
        self.autostart.setChecked(bool(self.config.get("autostart", True)))
        root.addWidget(self.autostart)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("ANNULER")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("✓ ENREGISTRER ET APPLIQUER")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except Exception:
            return {}

    def _refresh_models(self, *_):
        provider = str(self.provider.currentData() or "groq")
        current = str(self.config.get("groq_model", "llama-3.1-8b-instant")) if provider == "groq" else str(self.config.get("model", "llama3.2:3b"))
        models = model_catalog(provider)
        self.model.blockSignals(True)
        self.model.clear()
        for label, model_id in models:
            self.model.addItem(label, model_id)
        index = self.model.findData(current)
        if index < 0 and current:
            self.model.addItem(f"Personnalisé • {current}", current)
            index = self.model.count() - 1
        if index >= 0:
            self.model.setCurrentIndex(index)
        self.model.blockSignals(False)
        self.model_hint.setText(f"{self.model.count()} modèles disponibles pour {provider.upper()}. Le modèle choisi est enregistré et appliqué au moteur actif.")
        self.key.setEnabled(provider == "groq")

    def _save(self):
        provider = str(self.provider.currentData() or "groq")
        selected_model = str(self.model.currentData() or self.model.currentText().strip())
        self.config = apply_provider_settings(
            self.config,
            provider=provider,
            api_key=self.key.text(),
            model=selected_model,
            fallback=str(self.fallback.currentData() or "ollama"),
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

        # The running app uses the modular engine installed by
        # runtime_conversation_bridge. Refresh that engine in place so the
        # next message really uses the newly selected provider/model.
        runtime_ok = False
        try:
            import assistant
            engine = getattr(getattr(assistant, "processor", None), "_neo_conversation_ai", None)
            if engine is not None:
                engine.config.clear()
                engine.config.update(self.config)
                engine.refresh()
                runtime_ok = True
            else:
                from core.conversation_ai import ConversationAI
                processor = getattr(assistant, "processor", None)
                if processor is not None:
                    processor.conversation_ai = ConversationAI(self.config, getattr(assistant, "ollama", None))
                    runtime_ok = True
        except Exception:
            pass

        try:
            import assistant
            signals = getattr(assistant, "signals", None)
            if signals is not None and hasattr(signals, "log_msg"):
                selected = self.config.get("groq_model") if provider == "groq" else self.config.get("model")
                status = "appliqués immédiatement" if runtime_ok else "enregistrés pour le prochain démarrage"
                signals.log_msg.emit("IA", f"Paramètres IA {status} : {provider} / {selected}")
        except Exception:
            pass
        self.accept()


__all__ = ["ProviderSettingsDialog", "model_catalog", "apply_provider_settings"]
