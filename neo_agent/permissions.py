from __future__ import annotations

from enum import IntEnum


class PermissionMode(IntEnum):
    """User-selectable autonomy levels.

    1 = cautious confirmations
    2 = autonomous for normal operations
    3 = no routine confirmation prompts
    """

    PRUDENT = 1
    AUTONOMOUS = 2
    UNRESTRICTED = 3


class PermissionPolicy:
    """Central policy gate between an agent decision and a real action."""

    # These actions are never silently treated as harmless. Mode 3 may bypass
    # routine confirmation, but the policy remains the single place where a
    # future hard-block/allow-list can be enforced.
    SENSITIVE = {
        "filesystem.delete",
        "system.run_command",
        "system.install_dependency",
        "system.change_setting",
        "network.write",
    }

    def __init__(self, mode: int = PermissionMode.PRUDENT):
        self.mode = PermissionMode(max(1, min(3, int(mode))))

    def set_mode(self, mode: int) -> None:
        self.mode = PermissionMode(max(1, min(3, int(mode))))

    def requires_approval(self, permission: str) -> bool:
        if self.mode == PermissionMode.UNRESTRICTED:
            return False
        if self.mode == PermissionMode.AUTONOMOUS:
            return permission in self.SENSITIVE
        return True

    def allowed(self, permission: str) -> bool:
        """Hard deny hook for future policy rules.

        Currently all registered permissions are allowed; confirmation is a
        separate decision. This keeps the architecture extensible.
        """

        return bool(permission)
