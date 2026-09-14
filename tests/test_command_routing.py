from core.assistant_components import _should_delegate_to_agent


def test_compound_browser_command_uses_autonomous_route():
    assert _should_delegate_to_agent("ouvre le navigateur et va sur Wikipédia") is True


def test_voice_repetition_still_uses_autonomous_route():
    assert _should_delegate_to_agent(
        "ouvre le ouvre le navigateur et va sur Wikipédia autant pour ce qui était déjà avant de continuer"
    ) is True


def test_simple_registered_app_keeps_legacy_route():
    assert _should_delegate_to_agent("ouvre chrome") is False


def test_simple_faq_does_not_use_autonomous_route():
    assert _should_delegate_to_agent("bonjour") is False
