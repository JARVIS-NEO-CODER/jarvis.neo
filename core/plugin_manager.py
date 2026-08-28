"""Plugin registry with permissions, dependencies and lifecycle checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginManifest:
    name: str
    version: str = "1.0.0"
    permissions: set[str] = field(default_factory=set)
    dependencies: set[str] = field(default_factory=set)


@dataclass
class PluginRecord:
    manifest: PluginManifest
    enabled: bool = False


class PluginManager:
    """Keeps plugin lifecycle explicit and blocks undeclared permissions."""

    def __init__(self, granted_permissions: set[str] | None = None) -> None:
        self.granted_permissions = set(granted_permissions or set())
        self.plugins: dict[str, PluginRecord] = {}

    def install(self, manifest: PluginManifest) -> None:
        missing = manifest.permissions - self.granted_permissions
        if missing:
            raise PermissionError(f"Plugin requires ungranted permissions: {sorted(missing)}")
        missing_deps = manifest.dependencies - set(self.plugins)
        if missing_deps:
            raise RuntimeError(f"Missing plugin dependencies: {sorted(missing_deps)}")
        self.plugins[manifest.name] = PluginRecord(manifest)

    def uninstall(self, name: str) -> None:
        if name not in self.plugins:
            raise KeyError(name)
        dependents = [n for n, p in self.plugins.items() if name in p.manifest.dependencies and n != name]
        if dependents:
            raise RuntimeError(f"Plugin is required by: {sorted(dependents)}")
        del self.plugins[name]

    def enable(self, name: str) -> None:
        self.plugins[name].enabled = True

    def disable(self, name: str) -> None:
        self.plugins[name].enabled = False

    def list_plugins(self) -> list[dict[str, Any]]:
        return [{"name": n, "version": p.manifest.version, "enabled": p.enabled,
                 "permissions": sorted(p.manifest.permissions),
                 "dependencies": sorted(p.manifest.dependencies)}
                for n, p in self.plugins.items()]


__all__ = ["PluginManager", "PluginManifest", "PluginRecord"]
