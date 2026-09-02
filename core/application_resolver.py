"""Dynamic local application discovery and resolution."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApplicationMatch:
    name: str
    target: Path | str
    source: str


class ApplicationResolver:
    """Resolve applications from the machine instead of a hardcoded registry."""

    def __init__(self, aliases: dict[str, str] | None = None):
        self.aliases = {self._normalize(k): v for k, v in (aliases or {}).items()}

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().strip().split())

    @staticmethod
    def _start_menu_roots() -> tuple[Path, ...]:
        if os.name != "nt":
            return ()
        roots = []
        for raw in (
            os.environ.get("APPDATA", "") + r"\Microsoft\Windows\Start Menu\Programs",
            os.environ.get("PROGRAMDATA", "") + r"\Microsoft\Windows\Start Menu\Programs",
        ):
            if raw:
                path = Path(raw)
                if path.exists():
                    roots.append(path)
        return tuple(roots)

    def discover(self) -> list[ApplicationMatch]:
        """Build the application inventory from the current machine at runtime."""
        matches: dict[str, ApplicationMatch] = {}
        for root in self._start_menu_roots():
            for path in root.rglob("*.lnk"):
                key = self._normalize(path.stem)
                matches.setdefault(key, ApplicationMatch(path.stem, path, "start_menu"))
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            root = Path(directory)
            if not root.is_dir():
                continue
            try:
                for path in root.iterdir():
                    if path.is_file() and os.access(path, os.X_OK):
                        key = self._normalize(path.stem)
                        matches.setdefault(key, ApplicationMatch(path.stem, path, "path"))
            except OSError:
                continue
        for alias, target in self.aliases.items():
            resolved = shutil.which(target) or target
            matches[alias] = ApplicationMatch(alias, resolved, "config")
        return sorted(matches.values(), key=lambda item: item.name.casefold())

    def resolve(self, requested: str) -> ApplicationMatch | None:
        query = self._normalize(requested.removesuffix(".exe"))
        alias = self.aliases.get(query)
        if alias:
            target = shutil.which(alias) or alias
            return ApplicationMatch(requested.strip(), target, "config")

        direct = shutil.which(requested.strip()) or shutil.which(requested.strip() + ".exe")
        if direct:
            return ApplicationMatch(requested.strip(), Path(direct), "path")

        for match in self.discover():
            if self._normalize(match.name) == query:
                return match
        return None

    def launch(self, requested: str) -> ApplicationMatch:
        match = self.resolve(requested)
        if match is None:
            raise FileNotFoundError(f"Application introuvable : {requested}")
        target = str(match.target)
        if os.name == "nt" and target.lower().endswith(".lnk"):
            os.startfile(target)
        else:
            subprocess.Popen([target], shell=False, start_new_session=True)
        return match


__all__ = ["ApplicationMatch", "ApplicationResolver"]
