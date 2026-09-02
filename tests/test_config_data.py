import json


def test_model_profiles_are_loaded_from_runtime_data(tmp_path, monkeypatch):
    data_file = tmp_path / "data.json"
    data_file.write_text(
        json.dumps({"model_tiers": {"custom-tier": {"chat": "chat-x", "vision": "vision-x"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("JARVIS_NEO_DATA_FILE", str(data_file))

    import importlib
    import core.config as config
    importlib.reload(config)

    assert config.MODEL_TIERS == {"custom-tier": {"chat": "chat-x", "vision": "vision-x"}}
    assert config.get_active_model(False) == "llava" or config.get_active_model(False) == ""
