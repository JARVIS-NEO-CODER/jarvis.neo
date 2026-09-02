from core.ai_status import format_ai_status


def test_format_ai_status_active_groq():
    assert format_ai_status({"active_provider": "groq"}) == "GROQ"


def test_format_ai_status_active_ollama():
    assert format_ai_status({"active_provider": "ollama"}) == "OLLAMA"


def test_format_ai_status_ready_without_first_request():
    assert format_ai_status({"groq_configured": True}) == "GROQ READY"
    assert format_ai_status({"ollama_available": True}) == "OLLAMA READY"


def test_format_ai_status_error_and_offline():
    assert format_ai_status({"last_error": "quota exceeded"}) == "ERROR"
    assert format_ai_status({}) == "OFFLINE"
