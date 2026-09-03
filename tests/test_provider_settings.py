import json


def test_provider_settings_model_selector_saves_choice(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    from ui import provider_settings

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(provider_settings.Path, "home", staticmethod(lambda: tmp_path))

    dialog = provider_settings.ProviderSettingsDialog()
    assert dialog.provider.currentText() == "Groq"
    assert dialog.model.count() == len(provider_settings.GROQ_MODELS)
    assert dialog.model.itemData(0) == provider_settings.GROQ_MODELS[0][1]

    target_index = dialog.model.findData("openai/gpt-oss-120b")
    assert target_index >= 0
    dialog.model.setCurrentIndex(target_index)
    dialog._save()

    saved = json.loads((tmp_path / ".jarvis_neo" / "jarvis_config.json").read_text(encoding="utf-8"))
    assert saved["ai_provider"] == "groq"
    assert saved["groq_model"] == "openai/gpt-oss-120b"


def test_provider_settings_switches_to_ollama_models(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    from ui import provider_settings

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(provider_settings.Path, "home", staticmethod(lambda: tmp_path))

    dialog = provider_settings.ProviderSettingsDialog()
    dialog.provider.setCurrentText("Ollama")

    assert dialog.model.count() == len(provider_settings.OLLAMA_MODELS)
    assert dialog.model.itemData(1) == "llama3.2:3b"
