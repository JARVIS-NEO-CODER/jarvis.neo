from core.goal_verifier import GoalVerifier
from core.system_observer import SystemSnapshot

def snap(process="MinecraftLauncher.exe", window="Minecraft Launcher"):
    return SystemSnapshot(0, 10, 30, window, process)

def test_close_objective_requires_target_to_disappear():
    result = GoalVerifier().verify("ferme le Minecraft Launcher", before=snap(), after=snap(), action_success=True, action_verified=True)
    assert result.achieved is False

def test_close_objective_succeeds_when_target_is_gone():
    result = GoalVerifier().verify("ferme le Minecraft Launcher", before=snap(), after=snap("explorer.exe", "Bureau"), action_success=True, action_verified=True)
    assert result.achieved is True

def test_failed_action_never_verifies():
    result = GoalVerifier().verify("ferme le Minecraft Launcher", before=snap(), after=snap("explorer.exe", "Bureau"), action_success=False, action_verified=False)
    assert result.achieved is False



def test_generic_objective_is_not_verified_by_a_successful_action_alone():
    before = snap("explorer.exe", "Desktop")
    after = snap("editor.exe", "Editor")
    result = GoalVerifier().verify(
        "Make my workspace better",
        before=before,
        after=after,
        action_success=True,
        action_verified=True,
    )

    assert result.achieved is False
    assert result.confidence == 0.0
    assert "spécifique" in result.reason.lower()
    assert result.evidence["foreground_changed"] is True


def test_generic_objective_without_system_observation_is_not_verified():
    result = GoalVerifier().verify(
        "Do something useful",
        before=None,
        after=None,
        action_success=True,
        action_verified=True,
    )

    assert result.achieved is False
    assert result.confidence == 0.0


def test_create_directory_goal_requires_directory_to_exist(tmp_path):
    target = tmp_path / "created-folder"
    target.mkdir()
    result = GoalVerifier().verify(
        "Crée le dossier created-folder",
        before=snap("explorer.exe", "Desktop"),
        after=snap("explorer.exe", "Desktop"),
        action_success=True,
        action_verified=True,
        action_name="action.create_directory",
        action_kwargs={"path": str(target)},
    )

    assert result.achieved is True
    assert result.evidence["is_directory"] is True


def test_create_directory_goal_fails_when_directory_is_missing(tmp_path):
    target = tmp_path / "missing-folder"
    result = GoalVerifier().verify(
        "Crée le dossier missing-folder",
        before=snap("explorer.exe", "Desktop"),
        after=snap("explorer.exe", "missing-folder"),
        action_success=True,
        action_verified=True,
        action_name="action.create_directory",
        action_kwargs={"path": str(target)},
    )

    assert result.achieved is False
    assert result.evidence["is_directory"] is False


def test_write_file_goal_requires_exact_content(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("contenu attendu", encoding="utf-8")
    result = GoalVerifier().verify(
        "Écris le fichier note.txt",
        before=snap(),
        after=snap("editor.exe", "note.txt"),
        action_success=True,
        action_verified=True,
        action_name="action.write_text_file",
        action_kwargs={"path": str(target), "content": "contenu attendu", "encoding": "utf-8"},
    )

    assert result.achieved is True
    assert result.evidence["content_matches"] is True


def test_write_file_goal_fails_when_content_differs(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("mauvais contenu", encoding="utf-8")
    result = GoalVerifier().verify(
        "Écris le fichier note.txt",
        before=snap(),
        after=snap("editor.exe", "note.txt"),
        action_success=True,
        action_verified=True,
        action_name="action.write_text_file",
        action_kwargs={"path": str(target), "content": "contenu attendu", "encoding": "utf-8"},
    )

    assert result.achieved is False
    assert result.evidence["content_matches"] is False


def test_close_app_goal_checks_background_processes(monkeypatch):
    class FakeProcess:
        info = {"pid": 42, "name": "chrome.exe"}

    monkeypatch.setattr("core.goal_verifier.psutil.process_iter", lambda fields: [FakeProcess()])
    result = GoalVerifier().verify(
        "Ferme Chrome",
        before=snap("chrome.exe", "Chrome"),
        after=snap("explorer.exe", "Desktop"),
        action_success=True,
        action_verified=True,
        action_name="action.close_app",
        action_kwargs={"name": "chrome"},
    )

    assert result.achieved is False
    assert result.reason == "Le processus existe encore : fermeture non confirmée."


def test_unrelated_builtin_action_cannot_use_foreground_change_as_proof():
    result = GoalVerifier().verify(
        "Ferme Chrome",
        before=snap("chrome.exe", "Chrome"),
        after=snap("explorer.exe", "Desktop"),
        action_success=True,
        action_verified=True,
        action_name="action.show_hud",
        action_kwargs={"target": "context"},
    )

    assert result.achieved is False
    assert "vérificateur adapté" in result.reason


def test_directory_verification_rejects_a_different_target(tmp_path):
    target = tmp_path / "folder-a"
    target.mkdir()
    result = GoalVerifier().verify(
        "Crée le dossier folder-b",
        before=snap(),
        after=snap("explorer.exe", "folder-a"),
        action_success=True,
        action_verified=True,
        action_name="action.create_directory",
        action_kwargs={"path": str(target)},
    )

    assert result.achieved is False
    assert result.evidence["target_matches_objective"] is False


def test_file_verification_rejects_a_different_target(tmp_path):
    target = tmp_path / "file-a.txt"
    target.write_text("contenu attendu", encoding="utf-8")
    result = GoalVerifier().verify(
        "Écris le fichier file-b.txt",
        before=snap(),
        after=snap("editor.exe", "file-a.txt"),
        action_success=True,
        action_verified=True,
        action_name="action.write_text_file",
        action_kwargs={"path": str(target), "content": "contenu attendu", "encoding": "utf-8"},
    )

    assert result.achieved is False
    assert result.evidence["target_matches_objective"] is False


def test_launch_goal_requires_process_evidence(monkeypatch):
    monkeypatch.setattr("core.goal_verifier.psutil.process_iter", lambda fields: [])
    result = GoalVerifier().verify(
        "Lance Chrome",
        before=snap("explorer.exe", "Desktop"),
        after=snap("explorer.exe", "Desktop"),
        action_success=True,
        action_verified=True,
        action_name="action.launch_app",
        action_kwargs={"command": "chrome.exe"},
    )

    assert result.achieved is False
    assert result.evidence["running_processes"] == []


def test_close_verification_ignores_similarly_named_process(monkeypatch):
    class FakeProcess:
        info = {"pid": 43, "name": "chromedriver.exe"}

    monkeypatch.setattr("core.goal_verifier.psutil.process_iter", lambda fields: [FakeProcess()])
    result = GoalVerifier().verify(
        "Ferme Chrome",
        before=snap("chrome.exe", "Chrome"),
        after=snap("explorer.exe", "Desktop"),
        action_success=True,
        action_verified=True,
        action_name="action.close_app",
        action_kwargs={"name": "chrome"},
    )

    assert result.achieved is True
    assert result.evidence["remaining_processes"] == []
