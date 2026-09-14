"""Runtime components extracted from assistant.py.

The classes in this module keep the historical assistant runtime API while
receiving their mutable runtime dependencies through configure_components().
"""
from __future__ import annotations

import asyncio
import datetime
import html
import importlib.util
import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote_plus

import psutil
import pyautogui
import pyperclip
import speech_recognition as sr

try:
    import numpy as np
except ImportError:
    np = None
try:
    import cv2
except ImportError:
    cv2 = None
try:
    import edge_tts
except ImportError:
    edge_tts = None
try:
    import ollama
except ImportError:
    ollama = None
try:
    import pygame
except ImportError:
    pygame = None
try:
    import sounddevice as sd
except ImportError:
    sd = None
try:
    import soundfile as sf
except ImportError:
    sf = None

from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QProgressBar, QPushButton, QScrollArea,
    QSystemTrayIcon, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    QHeaderView
)

_state = _signals = _memory = _config = None
_log = logging.getLogger("jarvis_neo")


def configure_components(**dependencies):
    """Inject assistant runtime objects without importing assistant.py."""
    globals().update(dependencies)
    globals()["_state"] = dependencies.get("state")
    globals()["_signals"] = dependencies.get("signals")
    globals()["_memory"] = dependencies.get("memory")
    globals()["_config"] = dependencies.get("CONFIG", dependencies.get("config"))
    globals()["_log"] = dependencies.get("log", _log)


def _cfg(): return _config or {}
def _state_obj(): return _state


def _activity(category, message, level="INFO"):
    try:
        _memory.log_activity(category, message, level)
    except Exception:
        pass
    try:
        _state.activity.put_nowait({"category": category, "message": message, "level": level, "at": time.time()})
    except Exception:
        pass
    try:
        getattr(_log, level.lower(), _log.info)("%s: %s", category, message)
    except Exception:
        pass


def _should_delegate_to_agent(text: str) -> bool:
    """Detect natural multi-step/action requests before legacy regex intents.

    The legacy intent table is intentionally kept for deterministic one-shot
    commands such as ``ouvre chrome``. Compound requests, browser navigation,
    coding tasks and explicit autonomous/recovery language must reach
    CommandProcessor.ask_ai(), which the desktop bridge replaces with the real
    autonomous runtime.
    """
    low = re.sub(r"\s+", " ", str(text).strip().lower())
    if not low:
        return False

    compound_markers = (
        " et ", " puis ", " ensuite ", " après ", " avant de ", ";",
        " puis ", " pour ensuite ",
    )
    action_markers = (
        "va sur ", "alle sur ", "navigue", "navigateur", "wikipedia",
        "site web", "page web", "clique", "écris", "tape", "fais défiler",
        "capture l'écran", "observe", "regarde", "analyse ce qui est affiché",
        "crée un programme", "code ", "programme ", "projet ", "teste ",
        "corrige", "répare", "retente", "réessaie", "jusqu'à ce que",
        "automatiquement", "mission", "tâche longue",
    )
    if any(marker in low for marker in compound_markers):
        return True
    if any(marker in low for marker in action_markers):
        return True
    return False


class CameraManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.cap = None

    def _init_cam(self):
        if cv2 is None:
            return
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)
        except Exception:
            self.cap = None

    def enable(self):
        if cv2 is None:
            return False
        with self.lock:
            if not self.cap or not self.cap.isOpened():
                self._init_cam()
            return bool(self.cap and self.cap.isOpened())

    def disable(self):
        with self.lock:
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.cap = None

    def get_frame(self):
        if cv2 is None or not _state.camera_enabled or not self.cap or not self.cap.isOpened():
            return None
        with self.lock:
            ret, frame = self.cap.read()
            return frame if ret else None

    def __del__(self):
        try: self.disable()
        except Exception: pass


class PluginManager:
    PERMISSION_FIELDS = {"network", "spotify", "camera", "microphone", "files", "keyboard"}

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.loaded = {}
        self.manifests = {}
        self.scan_plugins()

    def scan_plugins(self):
        self.manifests.clear()
        if not self.plugins_dir.exists():
            return
        for folder in self.plugins_dir.iterdir():
            if not folder.is_dir():
                continue
            manifest_path, code_path = folder / "manifest.json", folder / "plugin.py"
            if not manifest_path.exists() or not code_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["permissions"] = list(set(manifest.get("permissions", [])) & self.PERMISSION_FIELDS)
                self.manifests[folder.name] = {"path": folder, "manifest": manifest, "code": code_path}
            except Exception as exc:
                _log.error("Plugin manifest %s: %s", folder.name, exc)

    def load_plugin(self, name):
        info = self.manifests.get(name)
        if not info:
            return False, f"Plugin inconnu : {name}"
        try:
            spec = importlib.util.spec_from_file_location(f"jarvis_plugin_{name}", str(info["code"]))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.loaded[name] = {"module": module, "manifest": info["manifest"]}
            self.activity("plugin", f"Plugin {name} chargé.")
            return True, f"Plugin '{name}' chargé."
        except Exception as exc:
            return False, f"Échec chargement plugin '{name}' : {exc}"

    def unload_plugin(self, name):
        if name not in self.loaded:
            return False, f"Plugin non chargé : {name}"
        self.loaded.pop(name, None)
        self.activity("plugin", f"Plugin {name} déchargé.")
        return True, f"Plugin '{name}' déchargé."

    def activity(self, category, message, level="INFO"):
        _activity(category, message, level)


class ToolManager:
    APP_REGISTRY = {
        "calculatrice": ["calc.exe"], "calc": ["calc.exe"], "bloc-notes": ["notepad.exe"],
        "notepad": ["notepad.exe"], "explorateur": ["explorer.exe"], "explorer": ["explorer.exe"],
        "vscode": ["code"], "visual studio code": ["code"], "chrome": ["chrome"],
        "discord": ["Discord"], "spotify": ["Spotify"], "steam": ["steam"],
    }
    SAFE_APP_NAME = re.compile(r"^[\w .()'\-]+$", re.UNICODE)

    def activity(self, category, message, level="INFO"):
        _activity(category, message, level)

    def open_application(self, requested):
        name = str(requested).strip().lower()
        if name.startswith(("http://", "https://")):
            _signals.open_url.emit(name)
            return True, f"Navigation ouverte : {name}"
        if not self.SAFE_APP_NAME.fullmatch(name):
            return False, "Nom d'application refusé : caractères non autorisés."
        command = self.APP_REGISTRY.get(name)
        if not command:
            return False, f"Application non autorisée/inconnue : '{requested}'."
        try:
            subprocess.Popen(command, shell=False, close_fds=True)
            self.activity("outil", f"Lancement {requested}")
            return True, f"{requested} lancé."
        except (OSError, ValueError) as exc:
            return False, f"Impossible de lancer {requested} : {exc}"

    def close_application(self, requested):
        name = str(requested).strip().lower().removesuffix(".exe")
        if not self.SAFE_APP_NAME.fullmatch(name):
            return False, "Nom de processus invalide."
        matches = [p for p in psutil.process_iter(["pid", "name"]) if name in (p.info.get("name") or "").lower()]
        if not matches:
            return False, f"Aucun processus actif pour '{requested}'."
        for proc in matches:
            try: proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
        try: psutil.wait_procs(matches, timeout=3)
        except Exception: pass
        self.activity("outil", f"Fermeture contrôlée de {len(matches)} processus {requested}")
        return True, f"Fermeture de {len(matches)} processus liés à '{requested}'."

    def screen_click(self, x, y):
        if not _cfg().get("allow_screen_control", False):
            return False, "Contrôle écran désactivé par confidentialité."
        try:
            width, height = pyautogui.size(); x, y = int(x), int(y)
            if not (0 <= x < width and 0 <= y < height): return False, "Coordonnées hors écran."
            pyautogui.click(x, y); self.activity("vision", f"Clic prudent à {x}, {y}")
            return True, f"Clic exécuté à {x}, {y}."
        except Exception as exc: return False, f"Clic impossible : {exc}"

    def plan(self, text):
        pieces = [p.strip() for p in re.split(r"\s*(?:puis|et ensuite|;|,)\s*", str(text), flags=re.I) if p.strip()]
        return pieces or [str(text)]


class SpeechEngine:
    def __init__(self):
        self._lock = threading.Lock()
        if pygame:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception:
                pass
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        while True:
            text = tts_queue.get()
            if text is None: break
            try: loop.run_until_complete(self._say(text))
            except Exception as exc: _log.debug("TTS erreur: %s", exc)
            finally: tts_queue.task_done()

    async def _say(self, text):
        if not edge_tts or not _state.voice_enabled or not text: return
        path = Path(globals().get("BASE_DIR", Path.home())) / f"speech_{time.time_ns()}.mp3"
        _state.is_speaking = True; _signals.speaking_change.emit(True)
        try:
            communicate = edge_tts.Communicate(text, globals().get("VOICE", "fr-FR-HenriNeural"), rate=_cfg().get("tts_rate", "+5%"), volume=_cfg().get("tts_volume", "+0%"))
            await communicate.save(str(path))
            if pygame:
                try:
                    if not pygame.mixer.get_init(): pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                    pygame.mixer.music.load(str(path)); pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        if stop_event.is_set() or _state.abort_requested: pygame.mixer.music.stop(); break
                        await asyncio.sleep(0.05)
                except Exception: pass
        except Exception as exc:
            _log.warning("Échec TTS: %s", exc)
        finally:
            _state.is_speaking = False; _signals.speaking_change.emit(False)
            try: path.unlink(missing_ok=True)
            except Exception: pass

    def say(self, text, priority=False):
        clean = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", str(text))).strip()
        if not clean:
            return
        if priority:
            while True:
                try:
                    tts_queue.get_nowait()
                    tts_queue.task_done()
                except queue.Empty:
                    break
        tts_queue.put(clean)

    def stop(self):
        stop_event.set()
        try:
            if pygame: pygame.mixer.music.stop()
        except Exception: pass
        while not tts_queue.empty():
            try: tts_queue.get_nowait(); tts_queue.task_done()
            except Exception: break
        _state.is_speaking = False; _signals.speaking_change.emit(False); stop_event.clear()


class CommandProcessor:
    def __init__(self):
        self.faq = {
            r"comment vas-tu\s*\?*": "Tous mes systèmes fonctionnent à cent pour cent, monsieur.",
            r"qui es-tu\s*\?*": f"Je suis {globals().get('APP_NAME', 'J.A.R.V.I.S. NEO')}, votre intelligence artificielle de bureau.",
            r"tu es là\s*\?*": "Toujours à votre service, monsieur.",
            r"merci\s*": "Avec plaisir, monsieur.", r"bonjour\s*": "Bonjour monsieur. Tous les systèmes sont prêts.",
            r"bonne nuit\s*": "Bonne nuit, monsieur. Je veille sur les systèmes.",
        }
        self.intents = {
            r"ouvre\s+(.+)": self.open_app, r"ferme\s+(.+)|tue\s+(.+)": self.kill_app,
            r"(?:cherche|recherche|trouve|montre)\s+(?:des?\s+)?(?:images?|photos?)\s+(?:de|sur|pour)?\s*(.+)": self.image_search,
            r"cherche\s+(.+)": self.web_search, r"note\s+(.+)": self.take_note,
            r"météo": self.get_weather, r"heure|temps": self.get_time, r"date": self.get_date,
            r"système|stats|performance": self.get_system_stats, r"volume\s+(haut|bas|muet|plus|moins)": self.control_volume,
            r"batterie|charge": self.get_battery, r"uptime|depuis quand": self.get_uptime,
            r"processus|process": self.get_top_processes, r"copie\s+(.+)": self.copy_text,
            r"aide|help": self.get_help, r"analyse\s+l'écran": self.analyze_screen,
            r"capture|screenshot": self.take_screenshot, r"sécurité\s+(on|off|activer|désactiver)": self.toggle_security,
            r"écoute\s+passive\s+(on|off|activer|désactiver)": self.toggle_passive_listening,
            r"mode\s+(grand|moyen|petit|mini)": self.set_model_tier,
            r"modèle\s+actuel|quel\s+modèle": self.get_current_model_info,
            r"mes\s+tâches|liste\s+des\s+tâches": self.list_tasks,
            r"ajoute\s+(?:à\s+ma\s+liste\s+de\s+tâches|la\s+tâche)\s+(.+)": self.add_task,
            r"valide\s+la\s+tâche\s+(\d+)": self.complete_task,
            r"mes\s+mémos|liste\s+des\s+mémos": self.list_memos,
            r"vider\s+le\s+chat|efface\s+le\s+chat": self.clear_chat,
            r"charge\s+le\s+plugin\s+(.+)": self.load_plugin,
            r"décharge\s+le\s+plugin\s+(.+)": self.unload_plugin,
            r"liste\s+les\s+plugins": self.list_plugins,
        }

    def process(self, text):
        text = str(text).strip(); low = text.lower()
        if _state.alarm_triggered:
            return "⚠️ ALARME ACTIVE : code PIN requis."
        # Critical routing rule: natural multi-step requests must reach the
        # autonomous bridge before legacy regex intents can consume the first
        # clause (e.g. "ouvre le navigateur et va sur Wikipédia").
        if _should_delegate_to_agent(text):
            return self.ask_ai(text)
        pieces = tools.plan(text)
        if len(pieces) > 1: return " | ".join(self.process(p) for p in pieces)
        for pattern, response in self.faq.items():
            if re.search(pattern, low): return response
        for pattern, func in self.intents.items():
            match = re.search(pattern, low)
            if match:
                groups = [g for g in match.groups() if g is not None]
                return func(*groups) if groups else func()
        return self.ask_ai(text)

    def ask_ai(self, text):
        if not ollama: return "L'intelligence artificielle Ollama n'est pas installée."
        _state.is_processing = True; _signals.status_change.emit("RÉFLEXION")
        try:
            history = _memory.get_history(12); memories = _memory.search_memory(text, 5)
            model = globals().get('get_active_model', lambda **_: 'llama3.2:3b')(vision=False)
            messages = [{"role":"system","content":"Tu es J.A.R.V.I.S. NEO, un assistant personnel informatique. Réponds en français, brièvement et naturellement."}]
            messages.extend(history); messages.append({"role":"user","content":text})
            response = ollama.Client().chat(model=model, messages=messages)
            result = response["message"]["content"]
            _state.is_processing = False; _signals.status_change.emit("OPÉRATIONNEL")
            return result
        except Exception as exc:
            _state.is_processing = False; _signals.status_change.emit("ERREUR")
            return f"Erreur noyau IA : {exc}"

    def open_app(self, name): return tools.open_application(name)[1]
    def kill_app(self, name1, name2=None): return tools.close_application(name1 if name1 else name2)[1]
    def image_search(self, query):
        query = str(query).strip()
        if not query:
            return "Sujet de recherche d'images manquant."
        try:
            from .web_media import WebMediaProvider
            WebMediaProvider().search_images(query, limit=8)
        except Exception as exc:
            _log.warning("Recherche images échouée: %s", exc)
            url = "https://www.google.com/search?q=" + quote_plus(query) + "&tbm=isch&hl=fr&safe=active"
            _signals.open_url.emit(url)
        return f"Recherche d'images lancée pour « {query} »."

    def web_search(self, query):
        query = str(query).strip()
        url = "https://www.google.com/search?q=" + quote_plus(query)
        _signals.open_url.emit(url)
        return f"Recherche web exécutée pour : {query}"

    def take_note(self, content): _memory.add_note("Note", content); return "Note enregistrée dans la mémoire centrale."
    def get_weather(self):
        try:
            import urllib.request
            with urllib.request.urlopen("https://wttr.in/?format=%C+%t", timeout=5) as r: return f"Météo actuelle : {r.read().decode().strip()}"
        except Exception: return "Serveurs météo inaccessibles."
    def get_time(self): return f"Il est {datetime.datetime.now().strftime('%H:%M:%S')}."
    def get_date(self): return f"Nous sommes le {datetime.datetime.now().strftime('%d/%m/%Y')}."
    def get_system_stats(self):
        metrics = globals().get("collect_system_metrics", lambda: {"cpu_percent":0,"ram_percent":0,"disk_percent":0})()
        return f"CPU: {metrics['cpu_percent']}% | RAM: {metrics['ram_percent']}% | Disque: {metrics['disk_percent']}%"
    def control_volume(self, action):
        key = {"haut":"volumeup","plus":"volumeup","bas":"volumedown","moins":"volumedown","muet":"volumemute"}.get(action)
        if not key: return "Commande audio non reconnue."
        pyautogui.press(key, presses=5 if key != "volumemute" else 1); return "Commande audio exécutée."
    def sleep_pc(self):
        if sys.platform == "win32": subprocess.Popen(["rundll32.exe","powrprof.dll,SetSuspendState","0,1,0"], shell=False)
        return "Mise en veille du système en cours."
    def get_battery(self):
        b = psutil.sensors_battery(); return "Aucune batterie détectée." if b is None else f"Batterie : {b.percent:.0f}%"
    def get_uptime(self):
        elapsed=max(0,int(time.time()-_state.started_at)); h,r=divmod(elapsed,3600); m,s=divmod(r,60); return f"J.A.R.V.I.S. NEO est opérationnel depuis {h} h {m} min {s} s."
    def get_top_processes(self):
        procs=[]
        for p in psutil.process_iter(["name","cpu_percent"]):
            try: procs.append((p.info.get("cpu_percent") or 0,p.info.get("name") or "inconnu"))
            except Exception: pass
        procs.sort(reverse=True); return "Top processus CPU : " + " | ".join(f"{n} {c:.1f}%" for c,n in procs[:5])
