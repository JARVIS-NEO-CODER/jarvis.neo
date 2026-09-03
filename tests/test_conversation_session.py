from core.conversation_session import ConversationSession


def test_wake_word_starts_session():
    session = ConversationSession(timeout_seconds=12)
    assert session.should_wake("Jarvis ouvre Discord") is True
    assert session.active is True


def test_followup_does_not_require_wake_word():
    session = ConversationSession(timeout_seconds=12)
    session.start()
    assert session.should_wake("ouvre Discord") is True


def test_inactive_session_requires_wake_word():
    session = ConversationSession(timeout_seconds=12)
    session.active = False
    assert session.should_wake("ouvre Discord") is False
