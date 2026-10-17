from core.action_engine import ActionEngine


def test_safe_hud_action_is_registered_in_normal_mode():
    engine = ActionEngine()
    assert "action.show_hud" in engine._actions
    assert engine.mode.value == "normal"


def test_unknown_action_is_rejected():
    engine = ActionEngine()
    result = engine.execute("action.does_not_exist")
    assert result.success is False


def test_close_app_matches_exact_process_name(monkeypatch):
    class FakeProcess:
        def __init__(self, pid, name):
            self.info = {"pid": pid, "name": name}

    processes = [
        FakeProcess(1, "chrome.exe"),
        FakeProcess(2, "chromedriver.exe"),
        FakeProcess(3, "chrome_helper.exe"),
    ]
    monkeypatch.setattr("core.action_engine.psutil.process_iter", lambda fields: processes)

    matches = ActionEngine._process_matches("chrome")

    assert [process.info["name"] for process in matches] == ["chrome.exe"]
