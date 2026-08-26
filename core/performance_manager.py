"""Resource-aware performance policy for J.A.R.V.I.S. NEO.

This module does not change OS process priorities or kill applications. It
only exposes a lightweight policy that other NEO components can consult so
expensive features can back off while a demanding game is running.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PerformanceProfile(str, Enum):
    NORMAL = "normal"
    GAMING = "gaming"
    POWER_SAVE = "power_save"
    SENTINEL = "sentinel"


@dataclass(frozen=True)
class PerformancePolicy:
    profile: PerformanceProfile
    context_poll_seconds: float
    allow_ollama: bool
    allow_vision: bool
    allow_heavy_background_tasks: bool
    hud_animation_level: int


POLICIES = {
    PerformanceProfile.NORMAL: PerformancePolicy(
        PerformanceProfile.NORMAL, 2.0, True, True, True, 3
    ),
    PerformanceProfile.GAMING: PerformancePolicy(
        PerformanceProfile.GAMING, 10.0, False, False, False, 1
    ),
    PerformanceProfile.POWER_SAVE: PerformancePolicy(
        PerformanceProfile.POWER_SAVE, 20.0, False, False, False, 0
    ),
    PerformanceProfile.SENTINEL: PerformancePolicy(
        PerformanceProfile.SENTINEL, 5.0, False, False, True, 1
    ),
}


class PerformanceManager:
    """Select a conservative resource policy without performing system tweaks."""

    def __init__(self, profile: PerformanceProfile = PerformanceProfile.NORMAL) -> None:
        self._profile = profile

    @property
    def profile(self) -> PerformanceProfile:
        return self._profile

    @property
    def policy(self) -> PerformancePolicy:
        return POLICIES[self._profile]

    def set_profile(self, profile: PerformanceProfile) -> PerformancePolicy:
        self._profile = profile
        return self.policy

    def apply_context(self, context_name: str) -> PerformancePolicy:
        """Switch to a conservative profile based on high-level context."""
        normalized = context_name.strip().lower()
        if normalized == "gaming":
            return self.set_profile(PerformanceProfile.GAMING)
        if normalized in {"idle", "away", "power_save"}:
            return self.set_profile(PerformanceProfile.POWER_SAVE)
        if normalized == "sentinel":
            return self.set_profile(PerformanceProfile.SENTINEL)
        return self.set_profile(PerformanceProfile.NORMAL)

    def should_poll(self, elapsed_seconds: float) -> bool:
        return elapsed_seconds >= self.policy.context_poll_seconds


__all__ = ["PerformanceManager", "PerformancePolicy", "PerformanceProfile"]
