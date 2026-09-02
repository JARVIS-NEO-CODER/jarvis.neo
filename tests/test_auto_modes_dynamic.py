from core.auto_modes import AutoModeEngine


def test_auto_modes_are_loaded_from_runtime_data(monkeypatch):
    monkeypatch.setattr(
        "core.auto_modes.get_data",
        lambda key, default=None: [{"name": "custom", "events": ["signal"]}] if key == "auto_modes" else default,
    )

    engine = AutoModeEngine()
    engine.configure_defaults()

    assert len(engine.rules) == 1
    assert engine.evaluate(["signal"])["mode"] == "custom"
