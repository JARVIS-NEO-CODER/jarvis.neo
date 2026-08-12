"""J.A.R.V.I.S. NEO platform layer.

This module is intentionally separate from assistant.py so the large existing core
can evolve without replacing it. jarvis.bat launches this layer first; it patches
the existing window and reuses the existing processor/memory/tools.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path

try:
    import psutil
except Exception:
    psutil = None

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_OK = True
except Exception:
    FASTAPI_OK = False

try:
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtWidgets import (
        QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTabWidget,
        QTextEdit, QVBoxLayout, QWidget, QCheckBox
    )
    QT_OK = True
except Exception:
    QT_OK = False

BASE_DIR = Path.home() / ".jarvis_neo"
PLATFORM_DIR = BASE_DIR / "platform"
PLATFORM_DIR.mkdir(parents=True, exist_ok=True)
DEV_PLUGINS = Path(__file__).resolve().parent / "plugins"
USER_PLUGINS = BASE_DIR / "plugins"
USER_PLUGINS.mkdir(parents=True, exist_ok=True)
DEVICES_FILE = PLATFORM_DIR / "authorized_devices.json"
SECURITY_FILE = PLATFORM_DIR / "security.json"


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


class PermissionErrorJARVIS(Exception):
    pass


class PluginContext:
    """Small capability API exposed to plugins.

    Plugin Python is still trusted code because Python modules cannot be securely
    sandboxed inside the JARVIS process. The context therefore gates the official
    JARVIS capabilities, while the store must additionally validate plugin code.
    """
    def __init__(self, assistant, plugin_name, permissions):
        self.assistant = assistant
        self.plugin_name = plugin_name
        self.permissions = set(permissions or [])

    def require(self, permission):
        if permission not in self.permissions:
            raise PermissionErrorJARVIS(f"Permission refusée: {permission}")

    def notify(self, message):
        self.assistant.signals.log_msg.emit(f"Plugin {self.plugin_name}", str(message))

    def open_app(self, name):
        return self.assistant.tools.open_application(name)

    def close_app(self, name):
        return self.assistant.tools.close_application(name)

    def web(self, url):
        self.require("network")
        self.assistant.signals.open_url.emit(url)
        return True

    def camera_enabled(self):
        self.require("camera")
        return bool(self.assistant.state.camera_enabled)

    def read_file(self, path):
        self.require("files")
        return Path(path).read_text(encoding="utf-8")


class PlatformPluginManager:
    """Discover, load, unload and reload plugins from both plugin directories."""
    ALLOWED = {"network", "spotify", "camera", "microphone", "files", "keyboard", "system"}

    def __init__(self, assistant):
        self.assistant = assistant
        self.plugins = {}
        self.errors = {}
        self.scan()

    def _dirs(self):
        return [p for p in (DEV_PLUGINS, USER_PLUGINS) if p.exists()]

    def scan(self):
        self.plugins.clear()
        for root in self._dirs():
            for folder in root.iterdir():
                if not folder.is_dir():
                    continue
                manifest_path = folder / "manifest.json"
                code_path = folder / "plugin.py"
                if not (manifest_path.exists() and code_path.exists()):
                    continue
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    name = str(manifest.get("id") or folder.name)
                    permissions = [p for p in manifest.get("permissions", []) if p in self.ALLOWED]
                    self.plugins[name] = {
                        "path": folder, "code": code_path, "manifest": manifest,
                        "permissions": permissions, "module": None, "active": False,
                        "error": None,
                    }
                except Exception as exc:
                    self.errors[folder.name] = str(exc)
        return self.plugins

    def info(self):
        return list(self.plugins.values())

    def load(self, plugin_id):
        info = self.plugins.get(plugin_id)
        if not info:
            return False, f"Plugin inconnu : {plugin_id}"
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"jarvis_neo_plugin_{plugin_id}", info["code"])
            module = importlib.util.module_from_spec(spec)
            module.jarvis = PluginContext(self.assistant, plugin_id, info["permissions"])
            assert spec.loader is not None
            spec.loader.exec_module(module)
            if hasattr(module, "on_load"):
                module.on_load(module.jarvis)
            info["module"] = module
            info["active"] = True
            info["error"] = None
            self.assistant.memory.log_activity("plugin", f"Plugin {plugin_id} chargé")
            return True, f"Plugin {plugin_id} chargé."
        except Exception as exc:
            info["active"] = False
            info["error"] = str(exc)
            self.assistant.memory.log_activity("plugin", f"Erreur chargement {plugin_id}: {exc}", "ERROR")
            return False, f"Échec chargement {plugin_id}: {exc}"

    def unload(self, plugin_id):
        info = self.plugins.get(plugin_id)
        if not info or not info["active"]:
            return False, f"Plugin {plugin_id} non chargé."
        try:
            if hasattr(info["module"], "on_unload"):
                info["module"].on_unload()
        except Exception as exc:
            info["error"] = str(exc)
        info["module"] = None
        info["active"] = False
        self.assistant.memory.log_activity("plugin", f"Plugin {plugin_id} déchargé")
        return True, f"Plugin {plugin_id} déchargé."

    def reload(self, plugin_id):
        self.unload(plugin_id)
        return self.load(plugin_id)

    def commands(self):
        result = {}
        for pid, info in self.plugins.items():
            module = info.get("module")
            commands = getattr(module, "COMMANDS", {}) if module else {}
            if isinstance(commands, dict):
                for command, fn in commands.items():
                    result[f"{pid}:{command}"] = fn
        return result


class MobileBridge:
    """Pairing/token/WebSocket bridge for the future Flutter app and the PWA."""
    def __init__(self, assistant):
        self.assistant = assistant
        self.app = FastAPI(title="J.A.R.V.I.S. NEO Mobile") if FASTAPI_OK else None
        self.host = "0.0.0.0"
        self.port = 8890
        self.enabled = False
        self.pair_code = None
        self.pair_expires = 0
        self.devices = _read_json(DEVICES_FILE, {})
        self.clients = set()
        self.thread = None
        if self.app:
            self._routes()

    def new_code(self):
        self.pair_code = f"{secrets.randbelow(1_000_000):06d}"
        self.pair_expires = time.time() + 300
        return self.pair_code

    def _routes(self):
        @self.app.get("/mobile/info")
        async def info():
            return {"name": "J.A.R.V.I.S. NEO", "version": self.assistant.VERSION, "pairing": bool(self.pair_code and time.time() < self.pair_expires)}

        @self.app.post("/mobile/pair")
        async def pair(payload: dict):
            code = str(payload.get("code", ""))
            name = str(payload.get("device_name") or "Téléphone")[:60]
            if not self.pair_code or time.time() >= self.pair_expires or not secrets.compare_digest(code, self.pair_code):
                raise HTTPException(status_code=403, detail="Code d'appairage invalide ou expiré")
            token = secrets.token_urlsafe(32)
            device_id = str(uuid.uuid4())
            self.devices[device_id] = {"name": name, "token": token, "created_at": time.time(), "revoked": False}
            _write_json(DEVICES_FILE, self.devices)
            self.pair_code = None
            return {"device_id": device_id, "token": token}

        @self.app.get("/mobile/devices")
        async def devices():
            return [{"id": k, "name": v["name"], "revoked": v.get("revoked", False)} for k, v in self.devices.items()]

        @self.app.post("/mobile/devices/{device_id}/revoke")
        async def revoke(device_id: str, payload: dict):
            if not self._auth(payload.get("token")):
                raise HTTPException(status_code=401, detail="Non autorisé")
            if device_id in self.devices:
                self.devices[device_id]["revoked"] = True
                _write_json(DEVICES_FILE, self.devices)
            return {"ok": True}

        @self.app.post("/mobile/command")
        async def command(payload: dict):
            if not self._auth(payload.get("token")):
                raise HTTPException(status_code=401, detail="Non autorisé")
            return self.command(payload.get("command", ""), bool(payload.get("confirmed")))

        @self.app.get("/mobile/status")
        async def status(token: str):
            if not self._auth(token):
                raise HTTPException(status_code=401, detail="Non autorisé")
            return self.status()

        @self.app.websocket("/mobile/ws")
        async def ws(socket: WebSocket):
            token = socket.query_params.get("token", "")
            if not self._auth(token):
                await socket.close(code=1008)
                return
            await socket.accept()
            self.clients.add(socket)
            try:
                await socket.send_json({"type": "status", "data": self.status()})
                while True:
                    await socket.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                self.clients.discard(socket)

    def _auth(self, token):
        return any(v.get("token") == token and not v.get("revoked") for v in self.devices.values())

    def status(self):
        if not psutil:
            return {"online": True}
        battery = psutil.sensors_battery()
        return {
            "online": True,
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage(Path.home().anchor or "/").percent,
            "battery": battery.percent if battery else None,
            "uptime": int(time.time() - psutil.boot_time()),
        }

    def command(self, text, confirmed=False):
        text = str(text).strip()
        low = text.lower()
        sensitive = any(x in low for x in ("ferme", "supprime", "supprimer", "arrête", "éteins", "veille", "clique"))
        if sensitive and not confirmed:
            return {"ok": False, "confirmation_required": True, "message": "Cette action nécessite une confirmation."}
        try:
            # Reuse the existing safe command engine instead of accepting arbitrary shell commands.
            result = self.assistant.processor.process(text)
            self.broadcast({"type": "notification", "message": result})
            return {"ok": True, "result": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def broadcast(self, payload):
        # WebSocket objects belong to the event loop; notifications are best-effort.
        async def _send():
            dead = []
            for client in list(self.clients):
                try:
                    await client.send_json(payload)
                except Exception:
                    dead.append(client)
            for client in dead:
                self.clients.discard(client)
        try:
            import asyncio
            asyncio.create_task(_send())
        except Exception:
            pass

    def start(self):
        if not FASTAPI_OK or self.enabled:
            return False, "FastAPI/uvicorn indisponible ou serveur déjà actif."
        self.new_code()
        self.enabled = True
        self.thread = threading.Thread(target=lambda: uvicorn.run(self.app, host=self.host, port=self.port, log_level="warning"), daemon=True)
        self.thread.start()
        return True, f"Serveur mobile actif sur le port {self.port}. Code: {self.pair_code}"


class NeoCenter(QWidget if QT_OK else object):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.plugins = PlatformPluginManager(assistant)
        self.mobile = MobileBridge(assistant)
        self.setWindowTitle("J.A.R.V.I.S. NEO — Centre de contrôle")
        self.resize(1050, 700)
        self.setStyleSheet("QWidget{background:#020617;color:#e2f8ff;} QLabel{color:#00f3ff;} QPushButton{background:#071b32;color:#dffcff;border:1px solid #00f3ff;border-radius:6px;padding:8px;} QPushButton:hover{background:#0b2b4a;} QListWidget,QTextEdit,QLineEdit{background:#050d1f;color:#dffcff;border:1px solid #16445b;border-radius:6px;padding:6px;}")
        root = QVBoxLayout(self)
        title = QLabel("◈ J.A.R.V.I.S. NEO — CENTRE DE CONTRÔLE")
        title.setStyleSheet("font-size:18px;font-weight:bold;letter-spacing:2px;")
        root.addWidget(title)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self._build_home(); self._build_plugins(); self._build_devices(); self._build_agent(); self._build_memory(); self._build_security(); self._build_settings()

    def _tab(self, name):
        page = QWidget(); self.tabs.addTab(page, name); return page, QVBoxLayout(page)

    def _build_home(self):
        page, lay = self._tab("⌂ Accueil")
        self.home_status = QLabel("J.A.R.V.I.S. NEO opérationnel")
        lay.addWidget(self.home_status)
        self.home_stats = QTextEdit(); self.home_stats.setReadOnly(True); lay.addWidget(self.home_stats)
        btn = QPushButton("Actualiser")
        btn.clicked.connect(self.refresh_home); lay.addWidget(btn); self.refresh_home()

    def refresh_home(self):
        self.home_stats.setPlainText(json.dumps(self.mobile.status(), indent=2, ensure_ascii=False))

    def _build_plugins(self):
        page, lay = self._tab("🧩 Plugins")
        row = QHBoxLayout(); lay.addLayout(row)
        self.plugin_list = QListWidget(); row.addWidget(self.plugin_list, 2)
        right = QVBoxLayout(); row.addLayout(right, 3)
        self.plugin_info = QTextEdit(); self.plugin_info.setReadOnly(True); right.addWidget(self.plugin_info)
        for label, fn in (("Charger", self.load_plugin), ("Décharger", self.unload_plugin), ("Recharger", self.reload_plugin), ("Actualiser", self.refresh_plugins)):
            b = QPushButton(label); b.clicked.connect(fn); right.addWidget(b)
        self.plugin_list.currentItemChanged.connect(self.show_plugin)
        self.refresh_plugins()

    def refresh_plugins(self):
        self.plugins.scan(); self.plugin_list.clear()
        for p in self.plugins.info():
            item = QListWidgetItem(("● " if p["active"] else "○ ") + str(p["manifest"].get("name", p["manifest"].get("id", "Plugin"))))
            item.setData(Qt.ItemDataRole.UserRole, p["manifest"].get("id") or p["path"].name); self.plugin_list.addItem(item)

    def selected_plugin(self):
        item = self.plugin_list.currentItem(); return item.data(Qt.ItemDataRole.UserRole) if item else None

    def show_plugin(self):
        pid = self.selected_plugin(); p = self.plugins.plugins.get(pid)
        if not p: return
        m = p["manifest"]; self.plugin_info.setPlainText(json.dumps({"nom": m.get("name"), "version": m.get("version"), "description": m.get("description"), "permissions": p["permissions"], "actif": p["active"], "erreur": p["error"]}, indent=2, ensure_ascii=False))

    def load_plugin(self):
        pid = self.selected_plugin();
        if pid: self.plugins.load(pid); self.refresh_plugins(); self.show_plugin()

    def unload_plugin(self):
        pid = self.selected_plugin();
        if pid: self.plugins.unload(pid); self.refresh_plugins(); self.show_plugin()

    def reload_plugin(self):
        pid = self.selected_plugin();
        if pid: self.plugins.reload(pid); self.refresh_plugins(); self.show_plugin()

    def _build_devices(self):
        page, lay = self._tab("📱 Appareils")
        self.device_status = QLabel("Serveur mobile arrêté")
        lay.addWidget(self.device_status)
        self.code_label = QLabel("Code: —")
        self.code_label.setStyleSheet("font-size:28px;font-weight:bold;")
        lay.addWidget(self.code_label)
        start = QPushButton("Démarrer le serveur mobile + générer un code")
        start.clicked.connect(self.start_mobile); lay.addWidget(start)
        self.device_list = QListWidget(); lay.addWidget(self.device_list)
        self.refresh_devices()

    def start_mobile(self):
        ok, msg = self.mobile.start(); self.device_status.setText(msg); self.code_label.setText(f"Code: {self.mobile.pair_code or '—'}"); self.refresh_devices()

    def refresh_devices(self):
        self.device_list.clear()
        for did, d in self.mobile.devices.items():
            self.device_list.addItem(f"{d['name']} — {'RÉVOQUÉ' if d.get('revoked') else 'AUTORISÉ'} ({did[:8]})")

    def _build_agent(self):
        page, lay = self._tab("🤖 Agent")
        lay.addWidget(QLabel("Actions réelles via les outils sécurisés de J.A.R.V.I.S. — aucune commande shell arbitraire."))
        self.agent_cmd = QLineEdit(); self.agent_cmd.setPlaceholderText("Ex: ouvre Discord puis ouvre le dossier Téléchargements"); lay.addWidget(self.agent_cmd)
        run = QPushButton("Exécuter")
        run.clicked.connect(self.run_agent); lay.addWidget(run)
        self.agent_log = QTextEdit(); self.agent_log.setReadOnly(True); lay.addWidget(self.agent_log)
        stop = QPushButton("🛑 Arrêter la tâche")
        stop.clicked.connect(lambda: setattr(self.assistant.state, "abort_requested", True)); lay.addWidget(stop)

    def run_agent(self):
        text = self.agent_cmd.text().strip()
        if not text: return
        try: result = self.assistant.processor.process(text)
        except Exception as exc: result = f"Erreur: {exc}"
        self.agent_log.append(f"> {text}\n{result}\n")

    def _build_memory(self):
        page, lay = self._tab("🧠 Mémoire")
        row = QHBoxLayout(); lay.addLayout(row)
        q = QLineEdit(); q.setPlaceholderText("Rechercher dans les souvenirs et conversations"); row.addWidget(q)
        out = QTextEdit(); out.setReadOnly(True); lay.addWidget(out)
        search = QPushButton("Rechercher"); row.addWidget(search)
        def do_search():
            rows = self.assistant.memory.search_memory(q.text(), 20)
            out.setPlainText("\n\n".join(f"[{x['kind']}] {x['timestamp']}\n{x['content']}" for x in rows))
        search.clicked.connect(do_search)
        delete = QPushButton("Supprimer un souvenir par texte exact")
        lay.addWidget(delete)
        def do_delete():
            text = q.text().strip()
            if not text: return
            with sqlite3.connect(self.assistant.memory.path) as db: db.execute("DELETE FROM memories WHERE content = ?", (text,)); db.commit()
            do_search()
        delete.clicked.connect(do_delete)

    def _build_security(self):
        page, lay = self._tab("🛡️ Sécurité")
        data = _read_json(SECURITY_FILE, {"pin_hash": None})
        self.pin = QLineEdit(); self.pin.setEchoMode(QLineEdit.EchoMode.Password); self.pin.setPlaceholderText("Nouveau PIN"); lay.addWidget(self.pin)
        save = QPushButton("Enregistrer le PIN"); lay.addWidget(save)
        status = QLabel("PIN configuré" if data.get("pin_hash") else "Aucun PIN configuré")
        lay.addWidget(status)
        def set_pin():
            value = self.pin.text().strip()
            if len(value) < 4 or not value.isdigit(): status.setText("PIN invalide: 4 chiffres minimum."); return
            _write_json(SECURITY_FILE, {"pin_hash": hashlib.sha256(value.encode()).hexdigest()}); status.setText("PIN enregistré."); self.pin.clear()
        save.clicked.connect(set_pin)
        lay.addWidget(QLabel("Le mode Sentinelle existant reste piloté par le noyau assistant.py."))

    def _build_settings(self):
        page, lay = self._tab("⚙️ Paramètres")
        lay.addWidget(QLabel(f"Plateforme: {Path(__file__).resolve().parent}"))
        lay.addWidget(QLabel("Serveur mobile: 0.0.0.0:8890 (démarré uniquement à la demande)"))
        lay.addWidget(QLabel("Plugins développeur: ./plugins  |  Plugins utilisateur: ~/.jarvis_neo/plugins"))
        note = QTextEdit(); note.setReadOnly(True); note.setPlainText("Sécurité: les plugins Python tournent dans le processus JARVIS. Les permissions sont donc des garde-fous de l'API officielle, pas une sandbox OS. Pour un Store public, une sandbox séparée sera nécessaire."); lay.addWidget(note)


_CENTER = None

def install(assistant):
    """Patch the existing assistant at runtime and launch its normal UI."""
    global _CENTER
    original_init = assistant.JarvisWindow.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.btn_neo_center = QPushButton("◈ CENTRE NEO")
        self.btn_neo_center.setStyleSheet("background:#071b32;color:#00f3ff;border:1px solid #00f3ff;border-radius:7px;padding:8px;font-weight:bold;")
        self.btn_neo_center.clicked.connect(self.open_neo_center)
        self.left_panel.addWidget(self.btn_neo_center)

    def open_neo_center(self):
        global _CENTER
        if _CENTER is None:
            _CENTER = NeoCenter(assistant, self)
        _CENTER.show(); _CENTER.raise_(); _CENTER.activateWindow()

    assistant.JarvisWindow.__init__ = patched_init
    assistant.JarvisWindow.open_neo_center = open_neo_center
    assistant.plugin_manager = assistant.plugin_manager
    return assistant


def main():
    import assistant
    install(assistant)
    assistant.main()


if __name__ == "__main__":
    main()
