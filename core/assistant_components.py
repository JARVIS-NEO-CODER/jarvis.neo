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
                    if not pygame.mixer.get_init(): pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
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

    def say(self, text):
        clean = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", str(text))).strip()
        if clean: tts_queue.put(clean)

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
            model = globals().get("get_active_model", lambda **_: "llama3.2:3b")(vision=False)
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
    def web_search(self, query):
        url = f"https://www.google.com/search?q={str(query).strip().replace(' ', '+')}"; _signals.open_url.emit(url)
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
    def copy_text(self, text): pyperclip.copy(str(text)); return "Texte copié dans le presse-papiers."
    def take_screenshot(self):
        path=globals()["SNAPSHOTS_DIR"] / f"shot_{int(time.time())}.png"; pyautogui.screenshot(str(path)); return f"Capture enregistrée : {path.name}."
    def analyze_screen(self): return "Analyse écran disponible via le moteur de vision." if ollama else "Modules de vision non disponibles."
    def toggle_security(self, mode):
        _state.security_mode = mode in ("on","activer"); return "Protocoles de sécurité activés." if _state.security_mode else "Protocoles de sécurité désarmés."
    def toggle_passive_listening(self, mode): _state.passive_listening=mode in ("on","activer"); return "Écoute passive " + ("activée." if _state.passive_listening else "désactivée.")
    def set_model_tier(self, tier): return globals().get("apply_model_tier", lambda _: None)(tier) or "Mode IA inconnu."
    def get_current_model_info(self): return f"Mode {getattr(_state,'current_model_tier','moyen')} — modèle {getattr(_state,'current_model','inconnu')}."
    def add_task(self, content): _memory.add_task(content.strip()); return "Tâche enregistrée."
    def list_tasks(self): return str(_memory.get_tasks()) if _memory.get_tasks() else "Aucune tâche en attente."
    def complete_task(self, task_id): _memory.complete_task(int(task_id)); return "Tâche validée."
    def list_memos(self): return str(_memory.get_memos(5)) if _memory.get_memos(5) else "Aucun mémo."
    def clear_chat(self): _signals.log_msg.emit("Système","__CLEAR_CHAT__"); return "Interface nettoyée."
    def load_plugin(self,name): return plugin_manager.load_plugin(name)[1]
    def unload_plugin(self,name): return plugin_manager.unload_plugin(name)[1]
    def list_plugins(self): return ", ".join(plugin_manager.manifests) if plugin_manager.manifests else "Aucun plugin détecté."
    def get_help(self): return "Commandes : météo, heure, date, ouvre [app], cherche [texte], tâches, mémos, batterie, uptime, processus, sécurité on/off."


class ModuleWindow(QFrame):
    def __init__(self, title, content_widget, parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.resize(580,440)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        layout=QVBoxLayout(self); header=QHBoxLayout(); header.addWidget(QLabel(f"⚡ {title.upper()}")); header.addStretch()
        close=QPushButton("✕"); close.setFixedSize(28,28); close.clicked.connect(self.close); header.addWidget(close); layout.addLayout(header); layout.addWidget(content_widget)

class SecurityModuleWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); self.preview=QLabel("Caméra inactive"); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(self.preview)
        self.timer=QTimer(self); self.timer.timeout.connect(self.update_frame); self.timer.start(150)
    def update_frame(self):
        frame=camera_manager.get_frame()
        if frame is not None and cv2 is not None:
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB); h,w,ch=rgb.shape; self.preview.setPixmap(QPixmap.fromImage(QImage(rgb.data,w,h,ch*w,QImage.Format.Format_RGB888)).scaled(self.preview.size(),Qt.AspectRatioMode.KeepAspectRatio))
    def closeEvent(self,event): self.timer.stop(); event.accept()

class SystemMonitorWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); self.text=QTextEdit(); self.text.setReadOnly(True); layout.addWidget(self.text); self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(2000)
    def refresh(self):
        m=globals().get("collect_system_metrics",lambda:{"cpu_percent":0,"ram_percent":0,"disk_percent":0})(); self.text.append(f"CPU {m['cpu_percent']}% | RAM {m['ram_percent']}% | DISQUE {m['disk_percent']}%")
    def closeEvent(self,event): self.timer.stop(); event.accept()

class RetroVisionWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); self.table=QTableWidget(); self.table.setColumnCount(2); self.table.setHorizontalHeaderLabels(["Horodatage","Analyse"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); layout.addWidget(self.table); self.refresh_data()
    def refresh_data(self):
        rows=_memory.get_recent_retro_vision(20); self.table.setRowCount(len(rows));
        for i,(summary,timestamp) in enumerate(rows): self.table.setItem(i,0,QTableWidgetItem(str(timestamp))); self.table.setItem(i,1,QTableWidgetItem(str(summary)))

class MacrosWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); self.input=QTextEdit(); self.input.setPlaceholderText("Actions de routine"); layout.addWidget(self.input); btn=QPushButton("Enregistrer"); btn.clicked.connect(self.save); layout.addWidget(btn)
    def save(self): signals.log_msg.emit("Macros","Routine enregistrée.")

class NtfySettingsWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); layout.addWidget(QLabel(str(globals().get("NTFY_URL","ntfy.sh")))); btn=QPushButton("Copier"); btn.clicked.connect(lambda:pyperclip.copy(globals().get("NTFY_URL",""))); layout.addWidget(btn)

class HolographicFrame(QFrame):
    def __init__(self,parent=None): super().__init__(parent); self.setStyleSheet("QFrame { background: #020617; border: 1px solid #00f3ff; border-radius: 14px; }")

class GlowButton(QPushButton):
    def __init__(self,text,color=None,parent=None): super().__init__(text,parent); self._color=color or QColor(0,243,255); self._apply_style()
    def _apply_style(self): self.setStyleSheet(f"QPushButton {{ color:{self._color.name()}; background:#08132b; border:1px solid {self._color.name()}; border-radius:7px; padding:7px; font-weight:bold; }} QPushButton:hover {{ background:#10244a; }}")

class TechProgressBar(QProgressBar):
    def __init__(self,color=None,parent=None): super().__init__(parent); self.setTextVisible(False); self.setMaximum(100); self.setFixedHeight(7)

class AudioLevelBar(QProgressBar):
    def __init__(self,parent=None): super().__init__(parent); self.setRange(0,100); self.setTextVisible(False); self.setFixedHeight(7)
    def set_level(self,level): self.setValue(int(max(0,min(1,level))*100))

class ArcReactor(QFrame):
    def __init__(self,parent=None): super().__init__(parent); self.label=QLabel("◉ ONLINE",self); self.label.setAlignment(Qt.AlignmentFlag.AlignCenter); layout=QVBoxLayout(self); layout.addWidget(self.label); self.setFixedSize(150,70)

class PrivacyActivityPanel(QFrame):
    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); self.label=QLabel(); layout.addWidget(self.label); self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000); self.refresh()
    def refresh(self):
        self.label.setText(f"MIC {'ON' if _state.mic_enabled else 'OFF'} · CAM {'ON' if _state.camera_enabled else 'OFF'} · WEB {'ON' if _state.web_enabled else 'OFF'}")

class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(globals().get("APP_NAME","J.A.R.V.I.S. NEO")); self.resize(1150,750)
        central=HolographicFrame(); self.setCentralWidget(central); root=QHBoxLayout(central)
        left=QVBoxLayout(); root.addLayout(left,1); right=QVBoxLayout(); root.addLayout(right,2)
        self.status_label=QLabel("STATUT: NOMINAL"); left.addWidget(self.status_label); left.addWidget(PrivacyActivityPanel()); left.addWidget(ArcReactor())
        self.btn_camera=GlowButton("CAM OFF"); self.btn_camera.clicked.connect(self.toggle_camera); left.addWidget(self.btn_camera)
        self.btn_retro=GlowButton("VISION OFF"); left.addWidget(self.btn_retro); self.btn_web=GlowButton("WEB LOCAL OFF"); left.addWidget(self.btn_web)
        self.btn_mic=GlowButton("🎤 MICRO ON"); self.btn_mic.clicked.connect(self.toggle_mic); left.addWidget(self.btn_mic)
        left.addStretch(); exit_btn=GlowButton("DÉCONNECTER",QColor(255,50,50)); exit_btn.clicked.connect(QCoreApplication.quit); left.addWidget(exit_btn)
        self.chat_display=QTextEdit(); self.chat_display.setReadOnly(True); right.addWidget(self.chat_display)
        self.dynamic_space = globals().get("DynamicSpaceWidget", None)
        if self.dynamic_space: self.dynamic_space=self.dynamic_space(); right.addWidget(self.dynamic_space)
        row=QHBoxLayout(); self.cmd_input=QLineEdit(); self.cmd_input.setPlaceholderText("Entrez une directive..."); self.cmd_input.returnPressed.connect(self.handle_input); row.addWidget(self.cmd_input); send=GlowButton("⚡"); send.clicked.connect(self.handle_input); row.addWidget(send); right.addLayout(row)
        signals.log_msg.connect(self.add_chat_msg); signals.status_change.connect(self.update_status); signals.audio_level.connect(self._on_audio_level); self.audio_bar=AudioLevelBar(); left.addWidget(self.audio_bar)
    def handle_input(self):
        text=self.cmd_input.text().strip()
        if text: signals.log_msg.emit("Vous",text); command_queue.put(text); self.cmd_input.clear()
    def add_chat_msg(self,sender,msg):
        if msg=="__CLEAR_CHAT__": self.chat_display.clear(); return
        self.chat_display.append(f"<b>{html.escape(str(sender))}</b>: {html.escape(str(msg)).replace(chr(10),'<br>')}")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    def update_status(self,status): self.status_label.setText(f"STATUT: {status}")
    def _on_audio_level(self,level): self.audio_bar.set_level(level)
    def toggle_mic(self):
        _state.mic_enabled=not _state.mic_enabled; self.btn_mic.setText("🎤 MICRO ON" if _state.mic_enabled else "🎤 MICRO OFF")
    def toggle_camera(self):
        _state.camera_enabled=not _state.camera_enabled
        if _state.camera_enabled and not camera_manager.enable(): _state.camera_enabled=False
        if not _state.camera_enabled: camera_manager.disable()
        self.btn_camera.setText("CAM ON" if _state.camera_enabled else "CAM OFF")
    def apply_size_preset(self,preset):
        sizes={"compact":(820,580),"normal":(1150,750),"large":(1450,900),"wide":(1600,720)}; self.resize(*sizes.get(preset,sizes["normal"]))
    def toggle_minimize_window(self): self.showMinimized()
    def _abort_operations(self): _state.abort_requested=True
    def show_chat_view(self): pass
    def load_url_in_browser(self,url):
        import webbrowser; webbrowser.open(url)

# Runtime aliases are created by assistant.py after configure_components().
camera_manager = plugin_manager = tools = speech = processor = None
command_queue = queue.Queue(); tts_queue = queue.Queue(); stop_event = threading.Event()

__all__ = ["CameraManager","PluginManager","ToolManager","SpeechEngine","CommandProcessor","ModuleWindow","SecurityModuleWidget","SystemMonitorWidget","RetroVisionWidget","MacrosWidget","NtfySettingsWidget","HolographicFrame","GlowButton","TechProgressBar","AudioLevelBar","ArcReactor","PrivacyActivityPanel","JarvisWindow","configure_components"]
