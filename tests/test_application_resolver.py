from pathlib import Path

from core.application_resolver import ApplicationResolver


def test_resolver_prefers_config_alias():
    resolver = ApplicationResolver({"mon editeur": "python"})

    match = resolver.resolve("mon editeur")

    assert match is not None
    assert match.source == "config"
    assert str(match.target) == "python" or Path(str(match.target)).name.startswith("python")


def test_resolver_discovers_path_executable(tmp_path, monkeypatch):
    executable = tmp_path / "jarvis-test"
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    resolver = ApplicationResolver()
    match = resolver.resolve("jarvis-test")

    assert match is not None
    assert match.source == "path"
    assert Path(match.target) == executable


def test_resolver_returns_none_for_unknown_application(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    resolver = ApplicationResolver()

    assert resolver.resolve("definitely-not-installed") is None
