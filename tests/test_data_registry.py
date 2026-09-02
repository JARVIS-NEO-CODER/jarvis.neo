import json

from core.data_registry import load_data


def test_load_data_reads_repository_source(tmp_path, monkeypatch):
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({"example_list": ["a", "b"]}), encoding="utf-8")
    monkeypatch.setenv("JARVIS_NEO_DATA_FILE", str(data_file))

    data = load_data()

    assert data["example_list"] == ["a", "b"]


def test_user_data_overrides_repository_data(tmp_path, monkeypatch):
    repo_file = tmp_path / "repo.json"
    repo_file.write_text(json.dumps({"example": {"a": 1, "b": 2}}), encoding="utf-8")
    monkeypatch.setenv("JARVIS_NEO_DATA_FILE", str(repo_file))

    user_file = tmp_path / "user.json"
    user_file.write_text(json.dumps({"example": {"b": 3, "c": 4}}), encoding="utf-8")

    import core.data_registry as registry
    monkeypatch.setattr(registry, "USER_DATA_FILE", user_file)

    assert load_data()["example"] == {"a": 1, "b": 3, "c": 4}
