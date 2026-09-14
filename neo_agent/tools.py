from __future__ import annotations

import html
import re
import shlex
import subprocess
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .models import ToolResult
from .permissions import PermissionPolicy


@dataclass
class ToolSpec:
    name: str
    description: str
    permission: str
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry and executor for JARVIS capabilities."""

    def __init__(self, policy: PermissionPolicy | None = None, cwd: str = "."):
        self.policy = policy or PermissionPolicy()
        self.cwd = Path(cwd).resolve()
        self._tools: dict[str, ToolSpec] = {}
        self._register_builtin_tools()

    def register(self, name: str, description: str, permission: str, handler: Callable[..., Any]) -> None:
        if not name or "." not in name:
            raise ValueError("Tool name must use a namespace, e.g. filesystem.read")
        self._tools[name] = ToolSpec(name, description, permission, handler)

    def describe(self) -> list[dict[str, str]]:
        return [{"name": t.name, "description": t.description, "permission": t.permission}
                for t in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any] | None = None, *, approved: bool = False) -> ToolResult:
        arguments = arguments or {}
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, name, error="unknown_tool")
        if not isinstance(arguments, dict):
            return ToolResult(False, name, error="invalid_arguments")
        if not self.policy.allowed(tool.permission):
            return ToolResult(False, name, error="permission_denied")
        if self.policy.requires_approval(tool.permission) and not approved:
            return ToolResult(False, name, message="Cette action nécessite une approbation.",
                              requires_approval=True, error="approval_required")
        try:
            value = tool.handler(**arguments)
            return ToolResult(True, name, message="ok", data=value)
        except TypeError as exc:
            return ToolResult(False, name, error=f"invalid_arguments: {exc}")
        except Exception as exc:
            return ToolResult(False, name, error=f"execution_error: {type(exc).__name__}: {exc}")

    def _safe_path(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.cwd / candidate
        return candidate.resolve()

    def _register_builtin_tools(self) -> None:
        self.register("filesystem.list", "Lister un dossier", "filesystem.read", self._list)
        self.register("filesystem.read", "Lire un fichier texte", "filesystem.read", self._read)
        self.register("filesystem.write", "Créer ou remplacer un fichier texte", "filesystem.write", self._write)
        self.register("filesystem.search", "Rechercher des fichiers par nom", "filesystem.read", self._search)
        self.register("filesystem.delete", "Supprimer un fichier", "filesystem.delete", self._delete)
        self.register("system.run_command", "Exécuter une commande sans shell", "system.run_command", self._run_command)
        self.register("system.processes", "Lister les processus actifs", "system.read", self._processes)
        self.register("browser.open", "Ouvrir une URL dans le navigateur", "network.open", self._browser_open)
        self.register("browser.back", "Revenir à la page précédente du navigateur actif", "desktop.control", self._browser_back)
        self.register("browser.forward", "Avancer dans l'historique du navigateur actif", "desktop.control", self._browser_forward)
        self.register("browser.reload", "Recharger la page du navigateur actif", "desktop.control", self._browser_reload)
        self.register("browser.scroll", "Faire défiler la page du navigateur actif", "desktop.control", self._browser_scroll)
        self.register("browser.click", "Cliquer à une position de l'écran", "desktop.control", self._browser_click)
        self.register("browser.type", "Saisir du texte dans le navigateur actif", "desktop.control", self._browser_type)
        self.register("browser.key", "Envoyer une touche ou un raccourci clavier", "desktop.control", self._browser_key)
        self.register("web.search", "Rechercher sur le Web et retourner des résultats", "network.read", self._web_search)
        self.register("web.fetch", "Lire le contenu textuel d'une page Web", "network.read", self._web_fetch)
        self.register("web.image_search", "Rechercher des images et retourner leurs URLs", "network.read", self._image_search)
        self.register("screen.screenshot", "Prendre une capture de l'écran", "screen.read", self._screenshot)

    def _list(self, path: str = ".") -> list[str]:
        return sorted(item.name + ("/" if item.is_dir() else "") for item in self._safe_path(path).iterdir())[:500]

    def _read(self, path: str, max_chars: int = 100_000) -> str:
        return self._safe_path(path).read_text(encoding="utf-8")[:max(1, min(int(max_chars), 500_000))]

    def _write(self, path: str, content: str) -> dict[str, Any]:
        p = self._safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes": p.stat().st_size}

    def _search(self, query: str, path: str = ".", max_results: int = 100) -> list[str]:
        root, needle, results = self._safe_path(path), query.lower(), []
        for item in root.rglob("*"):
            if len(results) >= max(1, min(int(max_results), 500)):
                break
            if needle in item.name.lower():
                results.append(str(item.relative_to(root)))
        return results

    def _delete(self, path: str) -> dict[str, str]:
        p = self._safe_path(path)
        if p.is_dir():
            raise IsADirectoryError("Refusing to delete directories with filesystem.delete")
        p.unlink()
        return {"deleted": str(p)}

    def _run_command(self, command: str | list[str], timeout: int = 60) -> dict[str, Any]:
        argv = shlex.split(command, posix=False) if isinstance(command, str) else [str(x) for x in command]
        if not argv:
            raise ValueError("Empty command")
        completed = subprocess.run(argv, cwd=str(self.cwd), shell=False, capture_output=True,
                                   text=True, timeout=max(1, min(int(timeout), 300)))
        return {"returncode": completed.returncode, "stdout": completed.stdout[-20_000:],
                "stderr": completed.stderr[-20_000:]}

    def _processes(self, limit: int = 30) -> list[dict[str, Any]]:
        import psutil
        rows = []
        for process in psutil.process_iter(["pid", "name", "status"]):
            try:
                rows.append(process.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return rows[:max(1, min(int(limit), 100))]

    @staticmethod
    def _browser_open(url: str, new_tab: bool = True) -> dict[str, str]:
        target = str(url).strip()
        if urllib.parse.urlparse(target).scheme not in {"http", "https"}:
            raise ValueError("URL must use http or https")
        opened = webbrowser.open_new_tab(target) if new_tab else webbrowser.open(target)
        return {"url": target, "opened": str(bool(opened))}

    @staticmethod
    def _pyautogui():
        import pyautogui
        pyautogui.PAUSE = 0.08
        return pyautogui

    def _browser_back(self) -> dict[str, str]:
        self._pyautogui().hotkey("alt", "left")
        return {"action": "back"}

    def _browser_forward(self) -> dict[str, str]:
        self._pyautogui().hotkey("alt", "right")
        return {"action": "forward"}

    def _browser_reload(self) -> dict[str, str]:
        self._pyautogui().hotkey("ctrl", "r")
        return {"action": "reload"}

    def _browser_scroll(self, amount: int = -5) -> dict[str, int]:
        value = max(-30, min(30, int(amount)))
        self._pyautogui().scroll(value)
        return {"amount": value}

    def _browser_click(self, x: int, y: int, button: str = "left") -> dict[str, int | str]:
        if button not in {"left", "right", "middle"}:
            raise ValueError("button must be left, right or middle")
        self._pyautogui().click(int(x), int(y), button=button)
        return {"x": int(x), "y": int(y), "button": button}

    def _browser_type(self, text: str, interval: float = 0.01) -> dict[str, int]:
        value = str(text)
        self._pyautogui().write(value, interval=max(0, min(float(interval), 0.2)))
        return {"characters": len(value)}

    def _browser_key(self, key: str) -> dict[str, str]:
        value = str(key).strip().lower()
        if not value:
            raise ValueError("key is empty")
        aliases = {
            "entrée": "enter", "retour": "enter", "echap": "esc", "échap": "esc",
            "espace": "space", "suppr": "delete", "arrière": "backspace",
            "haut": "up", "bas": "down", "gauche": "left", "droite": "right",
        }
        value = aliases.get(value, value)
        if "+" in value:
            parts = [part for part in value.split("+") if part]
            if len(parts) < 2:
                raise ValueError("Invalid shortcut")
            self._pyautogui().hotkey(*parts)
        else:
            self._pyautogui().press(value)
        return {"key": value}

    @staticmethod
    def _request(url: str, timeout: int = 15) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-NEO/4.0",
                                                     "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7"})
        with urllib.request.urlopen(req, timeout=max(3, min(int(timeout), 30))) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(5_000_000).decode(charset, errors="replace")

    def _web_search(self, query: str, max_results: int = 8) -> list[dict[str, str]]:
        query = str(query).strip()
        if not query:
            raise ValueError("Search query is empty")
        raw = self._request("https://www.google.com/search?q=" + urllib.parse.quote_plus(query) + "&hl=fr")
        results = []
        for href, title, snippet in re.findall(r'<a href="/url\?q=(https?[^&"]+)[^"]*"[^>]*>.*?<h3[^>]*>(.*?)</h3>(.*?)</a>', raw, re.I | re.S):
            clean = lambda value: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()
            results.append({"title": clean(title), "url": urllib.parse.unquote(href), "snippet": clean(snippet)[:500]})
            if len(results) >= max(1, min(int(max_results), 12)):
                break
        return results

    def _web_fetch(self, url: str, max_chars: int = 30_000) -> str:
        if urllib.parse.urlparse(str(url)).scheme not in {"http", "https"}:
            raise ValueError("URL must use http or https")
        raw = self._request(url)
        text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()[:max(1, min(int(max_chars), 100_000))]

    def _image_search(self, query: str, limit: int = 8) -> list[dict[str, str]]:
        from core.web_media import WebMediaProvider
        return [item.as_dict() for item in WebMediaProvider().search_images(query, limit=limit)]

    def _screenshot(self, path: str = ".jarvis/screen.png") -> dict[str, str]:
        import pyautogui
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pyautogui.screenshot(str(target))
        width, height = pyautogui.size()
        position = pyautogui.position()
        return {"path": str(target), "width": int(width), "height": int(height), "mouse_x": int(position.x), "mouse_y": int(position.y)}
