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
