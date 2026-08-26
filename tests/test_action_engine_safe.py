from core.action_engine import ActionEngine


def test_safe_hud_action_is_registered_in_normal_mode():
    engine = ActionEngine()
    assert "action.show_hud" in engine._actions
    assert engine.mode.value == "normal"


def test_unknown_action_is_rejected():
    engine = ActionEngine()
    result = engine.execute("action.does_not_exist")
    assert result.success is False
