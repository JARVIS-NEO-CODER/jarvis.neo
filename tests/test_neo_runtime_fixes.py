from core.cockpit_widget_engine import CockpitWidgetEngine
from neo_agent.permissions import PermissionMode, PermissionPolicy


def test_cockpit_accepts_agent_status_kinds():
    assert {"success", "warning", "error"}.issubset(CockpitWidgetEngine.ALLOWED_KINDS)


def test_unrestricted_agent_mode_skips_routine_approval():
    policy = PermissionPolicy(PermissionMode.UNRESTRICTED)
    assert policy.requires_approval("filesystem.write") is False
    assert policy.requires_approval("system.run_command") is False
