# J.A.R.V.I.S. NEO - Advanced Desktop Intelligence & Control Center
# Version: 3.6.0 "Sonic HUD & Neural Command"
#
# Pour la prochaine grosse version de J.A.R.V.I.S. NEO, voilà le résumé complet de ce qu’on s’est fixé :
#
# 🚀 J.A.R.V.I.S. NEO — prochaine version
#
# 🧠 1. Nouveau cerveau
# - Intent Engine pour comprendre les demandes naturelles.
# - Tool Manager : l'IA peut choisir les outils dont elle a besoin.
# - Planification de plusieurs actions.
# - Vérification du résultat après chaque action.
# - Gestion propre des erreurs et possibilité d'annuler une opération.
#
# 🧠 2. Mémoire améliorée
# - Mémoire longue durée.
# - Souvenirs importants.
# - Recherche dans les anciennes conversations.
# - Mémoire des projets/préférences.
# - Mémoire épisodique.
# - Historique d'événements.
#
# 🖥️ 3. Contrôle du PC
# - Ouverture/fermeture d'applications plus fiable.
# - Registre automatique des programmes.
# - Contrôle plus propre des processus.
# - Actions système via des outils sécurisés.
# - Éviter shell=True et les exécutions dangereuses.
#
# 👁️ 4. Vision améliorée
# - Meilleure compréhension de l'écran.
# - Détection des éléments d'interface.
# - Coordonnées des boutons/éléments.
# - Préparation au contrôle souris/clavier.
# - Vérification visuelle après une action.
# - Mémoire visuelle configurable.
#
# 📷 5. Caméra / Sentinelle
# - États réellement synchronisés avec l'interface.
# - Détection de personnes plutôt que simple différence d'image.
# - Zones surveillées.
# - Niveau de confiance.
# - Alertes et historique.
# - Contrôles ON/OFF clairs.
# - Respect de la confidentialité.
#
# 📊 6. Monitoring intelligent
# - CPU
# - RAM
# - GPU
# - VRAM
# - disque
# - réseau
# - batterie
# - températures quand disponibles
# - processus
# - erreurs système
# Et surtout : ne plus confondre utilisation CPU et température.
#
# ⏰ 7. Tâches / rappels / agenda
# - Rappels persistants après redémarrage.
# - Priorités.
# - Échéances.
# - Répétitions.
# - Notifications.
# - Meilleure compréhension de « demain », « vendredi », etc.
#
# 🧩 8. Nouveau moteur d'automatisation
# Des workflows avec :
# - actions
# - délais
# - conditions
# - variables
# - répétitions
# - gestion des erreurs
# Exemple :
#   « Quand je lance ETS2 → active le mode jeu. »
#
# 🎙️ 9. Voix améliorée
# - Wake word plus propre.
# - VAD.
# - Whisper local quand disponible.
# - Moins de dépendance au cloud.
# - Réponses vocales prioritaires.
# - Possibilité d'interrompre JARVIS.
#
# 🌐 10. Web / navigateur
# - Recherche Web améliorée.
# - Analyse de pages.
# - Résumés.
# - Comparaison de résultats.
# - Navigateur intégré mieux exploité.
#
# 📱 11. Base J.A.R.V.I.S. Mobile
# Préparer directement le PC pour l'application Flutter :
# - connexion par code ;
# - appareils autorisés ;
# - plusieurs PC ;
# - dashboard ;
# - chat ;
# - Sentinelle ;
# - notifications ;
# - écran distant ;
# - contrôle souris/clavier ;
# - fichiers ;
# - presse-papiers ;
# - commandes vocales ;
# - monitoring ;
# - automatisations ;
# - historique ;
# - actions d'urgence.
#
# 🔐 12. Sécurité mobile
# - Authentification.
# - Tokens.
# - Permissions.
# - Appareils autorisés/révoqués.
# - Contrôle des actions sensibles.
# - API/WebSocket sécurisés.
# - Pas d'accès distant ouvert sans protection.
#
# 🔔 13. Centre d'événements
# Une timeline centralisée :
#   14:32 📥 Téléchargement terminé
#   14:47 ✅ Installation terminée
#   15:02 ⚠️ Programme en erreur
#   15:18 🛡️ Événement Sentinelle
# Et ces événements pourront ensuite alimenter les notifications mobiles.
#
# 🧩 14. SYSTÈME DE PLUGINS — le nouveau gros morceau
# JARVIS pourra être étendu par des développeurs externes.
# Exemple :
#   🧩 ETS2 Assistant
#   🧩 Spotify Controller
#   🧩 Gaming Mode
#   🧩 Discord Controller
# Chaque plugin aura notamment :
#   plugin/
#   ├── manifest
#   ├── code
#   ├── icône
#   ├── description
#   ├── permissions
#   └── version
# Avec :
# - installation
# - désinstallation
# - mises à jour
# - dépendances
# - désactivation
# - retour à une version précédente
# - permissions.
#
# 🔐 Permissions des plugins
# Un plugin devra déclarer :
#   ☑️ Réseau
#   ☑️ Spotify
#   ❌ Caméra
#   ❌ Micro
#   ❌ Fichiers
#   ❌ Clavier
# JARVIS empêchera le plugin de dépasser ce qui lui est autorisé.
#
# 🌐 15. Préparation du J.A.R.V.I.S. Store
# Le Store sera un site séparé, pas directement intégré au programme.
# Il permettra :
# - rechercher des plugins
# - catégories
# - notes
# - profils développeurs
# - installations
# - changelogs
# - images
# - signalements
# - versions.
# Et surtout :
#   🌐 STORE
#      ↓
#   🛡️ MODÉRATION
#      ↓
#   📦 PLUGIN VALIDÉ
#      ↓
#   💻 JARVIS
# Avec analyse automatique + modération humaine, parce qu'on ne peut pas considérer une analyse automatique comme une garantie de sécurité.
#
# 👨‍💻 Developer Portal
# Les créateurs pourront :
# - créer leur compte ;
# - envoyer leurs plugins ;
# - déclarer leurs permissions ;
# - publier des versions ;
# - consulter installations/notes ;
# - gérer leurs mises à jour.
#
# 🏗️ Et le gros changement architectural
# On ne veut plus :
#   Commande → regex → fonction
# mais :
#   👤 Utilisateur
#          ↓
#   🧠 Compréhension
#          ↓
#   📋 Planification
#          ↓
#   🧩 Outils / Plugins
#          ↓
#   ⚙️ Exécution
#          ↓
#   ✅ Vérification
#          ↓
#   🧠 Mémoire
#          ↓
#   📱 Événement / notification
# Donc la prochaine version n'est pas juste “JARVIS avec plus de commandes”.
# C'est JARVIS NEO qui devient une plateforme extensible, capable d'accueillir plus tard le mobile + le Store + les plugins de la communauté. 🔥

import asyncio
import base64
import datetime
import hashlib
import hmac
import html
import importlib.util
import json
import logging
import os
import queue
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

from core.assistant_components import (
    CameraManager, PluginManager, ToolManager, SpeechEngine, CommandProcessor,
    ModuleWindow, SecurityModuleWidget, SystemMonitorWidget, RetroVisionWidget,
    MacrosWidget, NtfySettingsWidget, HolographicFrame, GlowButton,
    TechProgressBar, AudioLevelBar, ArcReactor, PrivacyActivityPanel, JarvisWindow,
    configure_components,
)

# Qt 6 peut afficher un avertissement DPI sous Windows lorsque le contexte
# DPI a déjà été défini par le système ou une autre bibliothèque. Cela ne
# bloque pas J.A.R.V.I.S.; on masque uniquement cet avertissement parasite.
if sys.platform == "win32":
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window.warning=false")

import psutil
import pyautogui
import speech_recognition as sr
import pyperclip
import requests
from core.conversation_ai import ConversationAI
from core.web_media import WebMediaProvider

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

# Optional dependencies with graceful degradation
try:
    import ollama
except ImportError:
    ollama = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import pygame
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

try:
    import cv2
    OPENCV_OK = True
except ImportError:
    OPENCV_OK = False

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    SOUND_OK = True
except ImportError:
    SOUND_OK = False

try:
    import whisper
    WHISPER_OK = True
except ImportError:
    WHISPER_OK = False

from PyQt6.QtCore import (
    QObject, QPoint, QPointF, QRect, QTimer, Qt, pyqtSignal, QCoreApplication, QUrl, QEvent
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QImage, QIcon, QPixmap, QPolygonF,
    QLinearGradient
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QComboBox, 
    QWidget, QSystemTrayIcon, QMenu, QCheckBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView
)

# Tentative d'import du moteur web natif PyQtWebEngine
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_OK = True
except ImportError:
    WEBENGINE_OK = False

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, StreamingResponse
    import uvicorn
    FASTAPI_OK = True
except ImportError:
    FASTAPI_OK = False

# --- CONFIGURATION ---
APP_NAME = "J.A.R.V.I.S. NEO"
VERSION = "3.6.0"
BASE_DIR = Path.home() / ".jarvis_neo"
BASE_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "memory.db"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(exist_ok=True)
RETRO_DIR = BASE_DIR / "retrospective"
RETRO_DIR.mkdir(exist_ok=True)
MEMOS_DIR = BASE_DIR / "memos"
MEMOS_DIR.mkdir(exist_ok=True)
PLUGINS_DIR = BASE_DIR / "plugins"
PLUGINS_DIR.mkdir(exist_ok=True)
CONFIG_FILE = BASE_DIR / "jarvis_config.json"

DEFAULT_CONFIG = {
    "voice": os.getenv("JARVIS_VOICE", "fr-FR-HenriNeural"),
    "tts_rate": "+5%",
    "tts_volume": "+0%",
    "model": os.getenv("JARVIS_MODEL", "llava"),
    "model_tier": "moyen",
    "language": "fr-FR",
    "hotword": "jarvis",
    "use_whisper": False,
    "theme_accent": "#00f3ff",
    "theme_secondary": "#00ffaa",
    # Privacy first: capture devices and remote control are opt-in.
    "camera_enabled": False,
    "microphone_enabled": True,
    "retro_vision_enabled": False,
    "retro_vision_interval": 300,
    "retro_vision_retention_days": 7,
    "allow_screen_control": False,
    "web_enabled": False,
    "web_host": "127.0.0.1",
    "web_port": 8888,
}

# Profils IA : chat (texte) + vision (écran/caméra)
MODEL_TIERS = {
    "grand": {
        "label": "Grand",
        "description": "Puissance maximale — précision et raisonnement avancé",
        "chat": "llama3.1:8b",
        "vision": "llava:13b",
    },
    "moyen": {
        "label": "Moyen",
        "description": "Équilibre performance / vitesse (recommandé)",
        "chat": "llama3.2:3b",
        "vision": "llava",
    },
    "petit": {
        "label": "Petit",
        "description": "Rapide et léger — faible consommation RAM",
        "chat": "phi3:mini",
        "vision": "llava-phi3",
    },
    "mini": {
        "label": "Mini",
        "description": "Ultra-léger — réponses quasi instantanées",
        "chat": "gemma2:2b",
        "vision": "moondream",
    },
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erreur sauvegarde config : {e}")

CONFIG = load_config()
if "model_tier" not in CONFIG or (
    CONFIG["model_tier"] not in MODEL_TIERS and CONFIG["model_tier"] != "custom"
):
    CONFIG["model_tier"] = "moyen"

def get_active_model(vision=False):
    """Retourne le modèle Ollama actif selon le tier (chat ou vision)."""
    tier = CONFIG.get("model_tier", "moyen")
    if tier in MODEL_TIERS:
        key = "vision" if vision else "chat"
        custom = CONFIG.get("model_tiers_custom", {}).get(tier, {})
        if isinstance(custom, dict) and custom.get(key):
            return custom[key]
        return MODEL_TIERS[tier][key]
    return CONFIG.get("model", MODEL_TIERS["moyen"]["chat" if not vision else "vision"])

MODEL = get_active_model()
VOICE = CONFIG["voice"]
LANGUAGE = CONFIG["language"]
HOTWORD = CONFIG["hotword"]
WEB_PORT = int(CONFIG.get("web_port", 8888))

def _secret_path(name: str) -> Path:
    """Store local secrets outside the source code with restrictive permissions."""
    path = BASE_DIR / name
    try:
        if path.exists():
            os.chmod(path, 0o600)
    except OSError:
        pass
    return path

def _load_or_create_web_token() -> str:
    path = _secret_path("web.token")
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = os.getenv("JARVIS_WEB_TOKEN", secrets.token_urlsafe(32))
    path.write_text(token, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token

WEB_TOKEN = _load_or_create_web_token()
PIN_HASH = os.getenv("JARVIS_PIN_HASH", CONFIG.get("security_pin_hash", ""))

def generate_security_pin_hash(pin: str) -> str:
    """Generate a config-ready PBKDF2 value; call once from a trusted console."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 200_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_security_pin(candidate: str) -> bool:
    """Verify a PBKDF2 pin hash; no default or source-code PIN exists."""
    if not PIN_HASH or not candidate:
        return False
    try:
        salt_b64, digest_b64 = PIN_HASH.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", candidate.encode(), base64.urlsafe_b64decode(salt_b64), 200_000)
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(digest_b64))
    except (ValueError, TypeError):
        return False

def get_disk_path():
    if sys.platform == "win32":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"

# --- CONFIGURATION NTFY.SH ---
def get_or_create_ntfy_topic():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                if "ntfy_topic" in config:
                    return config["ntfy_topic"]
        except Exception:
            pass
    
    new_topic = f"jarvis-neo-{uuid.uuid4().hex[:16]}"
    config_data = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config_data = json.load(f)
        except Exception:
            pass
    config_data["ntfy_topic"] = new_topic
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)
    return new_topic

NTFY_TOPIC = get_or_create_ntfy_topic()
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def send_security_notification(message, title="Alerte Securite - J.A.R.V.I.S. NEO", priority="high", tags="warning,shield"):
    try:
        requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": tags
            },
            timeout=5
        )
    except Exception as e:
        logging.error(f"Erreur envoi notification ntfy.sh : {e}")

# --- GLOBAL STATE ---
class GlobalState:
    def __init__(self):
        self.is_active = True
        self.is_standby = False
        self.is_processing = False
        self.is_speaking = False
        self.is_listening = False
        self.mic_enabled = bool(CONFIG.get("microphone_enabled", True))
        self.voice_enabled = True
        self.security_mode = False
        self.alarm_triggered = False
        self.abort_requested = False
        self.passive_listening = True
        self.camera_enabled = bool(CONFIG.get("camera_enabled", False))
        self.retro_vision_active = bool(CONFIG.get("retro_vision_enabled", False))
        self.system_monitor_active = True
        self.web_enabled = bool(CONFIG.get("web_enabled", False))
        self.activity = queue.Queue(maxsize=500)
        self.current_model_tier = CONFIG.get("model_tier", "moyen")
        self.current_model = get_active_model()
        self.audio_level = 0.0
        self.theme_color = QColor(CONFIG.get("theme_accent", "#00f3ff"))
        self.secondary_color = QColor(CONFIG.get("theme_secondary", "#00ffaa"))
        self.started_at = time.time()

state = GlobalState()
command_queue = queue.Queue()
tts_queue = queue.Queue()
stop_event = threading.Event()
active_reminders = []
reminders_lock = threading.Lock()

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("jarvis_neo")

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

# --- CAMERA MANAGER ---


# --- DATABASE / MEMORY ---
from core.legacy_memory import MemoryManager

memory = MemoryManager(DB_PATH)

# --- SIGNALS ---
class JarvisSignals(QObject):
    log_msg = pyqtSignal(str, str)
    status_change = pyqtSignal(str)
    stats_update = pyqtSignal(dict)
    open_url = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    speaking_change = pyqtSignal(bool)
    listening_change = pyqtSignal(bool)
    model_tier_change = pyqtSignal(str)

signals = JarvisSignals()

# --- SAFE TOOLS / PLANNING ---






def collect_system_metrics():
    """Best-effort monitoring; optional hardware metrics never block startup."""
    counters = psutil.net_io_counters()
    data = {
        "cpu_percent": psutil.cpu_percent(), "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage(get_disk_path()).percent,
        "network_sent": counters.bytes_sent, "network_received": counters.bytes_recv,
    }
    battery = psutil.sensors_battery()
    if battery: data["battery_percent"] = battery.percent
    try:
        temps = psutil.sensors_temperatures()
        data["temperatures"] = {name: [entry.current for entry in entries] for name, entries in temps.items()}
    except (AttributeError, OSError):
        data["temperatures"] = {}
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2, shell=False)
        if result.returncode == 0 and result.stdout.strip():
            name, gpu, used, total, temperature = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
            data["gpu"] = {"name": name, "percent": float(gpu), "vram_used_mb": float(used), "vram_total_mb": float(total), "temperature_c": float(temperature)}
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return data

def apply_model_tier(tier: str):
    """Applique un tier IA et persiste la config. Retourne un message ou None si invalide."""
    tier = tier.lower().strip()
    if tier not in MODEL_TIERS:
        return None
    CONFIG["model_tier"] = tier
    CONFIG["model"] = get_active_model(vision=False)
    save_config(CONFIG)
    state.current_model_tier = tier
    state.current_model = CONFIG["model"]
    signals.model_tier_change.emit(tier)
    info = MODEL_TIERS[tier]
    chat = get_active_model(vision=False)
    vision = get_active_model(vision=True)
    return (
        f"Mode {info['label']} activé. "
        f"Chat : {chat} — Vision : {vision}. "
        f"{info['description']}"
    )

# --- WEB INTERFACE (FASTAPI - Mode secours distant optionnel) ---
if FASTAPI_OK:
    app = FastAPI(title=APP_NAME)

    @app.middleware("http")
    async def local_token_guard(request: Request, call_next):
        # The dashboard is local-only by default. When enabled remotely, callers
        # must supply the generated token in X-Jarvis-Token.
        supplied_token = request.headers.get("X-Jarvis-Token", "") or request.query_params.get("token", "")
        if request.url.path != "/" and not hmac.compare_digest(supplied_token, WEB_TOKEN):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
    
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>JARVIS NEO - Command Center</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {
                --bg-main: #020617;
                --bg-panel: #080e21;
                --accent: #00f3ff;
                --accent-glow: rgba(0, 243, 255, 0.35);
                --text-main: #e2f8ff;
                --border: rgba(0, 243, 255, 0.25);
            }
            body { background: var(--bg-main); color: var(--text-main); font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
            header { padding: 12px 20px; border-bottom: 1px solid var(--border); background: var(--bg-panel); display: flex; justify-content: space-between; align-items: center; box-shadow: 0 0 25px var(--accent-glow); }
            header h1 { margin: 0; font-size: 18px; letter-spacing: 3px; color: var(--accent); text-shadow: 0 0 12px var(--accent-glow); }
            .status-badge { font-size: 11px; padding: 4px 12px; border: 1px solid var(--accent); border-radius: 12px; background: rgba(0,243,255,0.1); }
            .container { display: flex; flex: 1; overflow: hidden; }
            .sidebar { width: 340px; border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 15px; background: #040817; gap: 15px; overflow-y: auto; }
            .main-content { flex: 1; display: flex; flex-direction: column; padding: 15px; background: radial-gradient(circle at center, #06112d 0%, #020617 100%); }
            .card { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 10px; padding: 12px; box-shadow: inset 0 0 15px rgba(0,243,255,0.03); }
            .card h3 { margin: 0 0 10px 0; font-size: 13px; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; }
            .alarm-banner { display: none; background: rgba(255, 50, 50, 0.2); border: 2px solid #ff3333; color: #ff6666; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; animation: pulse 1s infinite; margin-bottom: 15px; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
            .cam-container { position: relative; width: 100%; border-radius: 6px; overflow: hidden; background: black; border: 1px solid var(--border); aspect-ratio: 4/3; }
            .cam-container img { width: 100%; height: 100%; object-fit: cover; }
            .stat-bar { margin-bottom: 8px; font-size: 12px; }
            .progress-bg { background: rgba(255,255,255,0.05); height: 6px; border-radius: 3px; overflow: hidden; margin-top: 4px; border: 1px solid var(--border); }
            .progress-fill { background: linear-gradient(90deg, var(--accent), #00ffaa); height: 100%; width: 0%; transition: width 0.5s ease; }
            #chat { flex: 1; overflow-y: auto; background: rgba(2, 6, 23, 0.6); border: 1px solid var(--border); border-radius: 10px; padding: 15px; margin-bottom: 12px; display: flex; flex-direction: column; gap: 10px; min-height: 200px; }
            .msg { padding: 10px 14px; border-radius: 8px; max-width: 80%; font-size: 13px; line-height: 1.4; word-break: break-word; }
            .user { align-self: flex-end; background: rgba(0, 243, 255, 0.15); border: 1px solid var(--accent); color: white; border-bottom-right-radius: 2px; }
            .jarvis { align-self: flex-start; background: #0c1836; border: 1px solid var(--border); color: var(--accent); border-bottom-left-radius: 2px; }
            .input-area { display: flex; gap: 10px; }
            input { flex: 1; background: var(--bg-panel); border: 1px solid var(--border); color: white; padding: 12px 15px; border-radius: 8px; outline: none; font-size: 14px; }
            input:focus { border-color: var(--accent); box-shadow: 0 0 10px var(--accent-glow); }
            button { background: var(--accent); color: var(--bg-main); border: none; padding: 0 20px; border-radius: 8px; font-weight: bold; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; }
        </style>
    </head>
    <body>
        <header>
            <h1>⚡ J.A.R.V.I.S. NEO - COMMAND CENTER</h1>
            <div class="status-badge" id="statusBadge">ONLINE</div>
        </header>
        <div class="container">
            <div class="sidebar">
                <div id="alarmBanner" class="alarm-banner">
                    ⚠️ ALERTE INTRUSION ACTIVE<br><small style="font-size:10px; color:#ff9999;">Entrez le code secret pour désarmer</small>
                </div>
                <div class="card">
                    <h3>Flux Caméra Live</h3>
                    <div class="cam-container">
                        <img id="cameraFeed" alt="Caméra non disponible">
                    </div>
                </div>
                <div class="card">
                    <h3>Diagnostics Système</h3>
                    <div class="stat-bar"><span>CPU</span><span id="cpuText" style="float: right;">0%</span><div class="progress-bg"><div class="progress-fill" id="cpuBar"></div></div></div>
                    <div class="stat-bar"><span>RAM</span><span id="ramText" style="float: right;">0%</span><div class="progress-bg"><div class="progress-fill" id="ramBar" style="background: linear-gradient(90deg, #a200ff, #ff00ea);"></div></div></div>
                </div>
            </div>
            <div class="main-content">
                <div id="chat">
                    <div class="msg jarvis">Système web initialisé. En attente de directive, monsieur.</div>
                </div>
                <div class="input-area">
                    <input type="text" id="cmdInput" placeholder="Entrez une directive pour J.A.R.V.I.S. NEO..." autocomplete="off" onkeydown="if(event.key==='Enter') sendCmd()">
                    <button onclick="sendCmd()">Envoyer</button>
                </div>
            </div>
        </div>
        <script>
            const jarvisToken = sessionStorage.getItem('jarvisToken') || new URLSearchParams(location.search).get('token') || prompt('Jeton JARVIS requis pour le contrôle distant :');
            if (jarvisToken) sessionStorage.setItem('jarvisToken', jarvisToken);
            document.getElementById('cameraFeed').src = `/video_feed?token=${encodeURIComponent(jarvisToken || '')}`;
            const ws = new WebSocket(`ws://${location.host}/ws?token=${encodeURIComponent(jarvisToken || '')}`);
            const chat = document.getElementById('chat');
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if(data.type === 'alarm') {
                    document.getElementById('alarmBanner').style.display = data.status ? 'block' : 'none';
                } else {
                    appendMsg(data.sender, data.msg);
                }
            };
            function appendMsg(sender, text) {
                const div = document.createElement('div');
                div.className = 'msg ' + (sender.includes('Vous') ? 'user' : 'jarvis');
                div.innerHTML = `<b>${sender}:</b> ${text}`;
                chat.appendChild(div);
                chat.scrollTop = chat.scrollHeight;
            }
            function sendCmd() {
                const input = document.getElementById('cmdInput');
                if(input.value.trim()) {
                    appendMsg('Vous (Web)', input.value);
                    ws.send(input.value);
                    input.value = '';
                }
            }
            setInterval(async () => {
                try {
                    const res = await fetch('/stats', {headers: {'X-Jarvis-Token': jarvisToken || ''}});
                    const data = await res.json();
                    document.getElementById('cpuText').innerText = data.cpu + '%';
                    document.getElementById('cpuBar').style.width = data.cpu + '%';
                    document.getElementById('ramText').innerText = data.ram + '%';
                    document.getElementById('ramBar').style.width = data.ram + '%';
                } catch(e) {}
            }, 2000);
        </script>
    </body>
    </html>
    """

    @app.get("/")
    async def get():
        return HTMLResponse(HTML_TEMPLATE)

    @app.get("/stats")
    async def get_stats():
        return {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage(get_disk_path()).percent
        }

    @app.get("/video_feed")
    async def video_feed():
        def generate_frames():
            while True:
                frame = camera_manager.get_frame()
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(0.1)
        return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        if not hmac.compare_digest(websocket.query_params.get("token", ""), WEB_TOKEN):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                signals.log_msg.emit("Vous (Web)", data)
                command_queue.put(data)
        except WebSocketDisconnect:
            pass

def run_web_server():
    if FASTAPI_OK and state.web_enabled:
        state.web_server_started = True
        host = str(CONFIG.get("web_host", "127.0.0.1"))
        if host not in {"127.0.0.1", "::1"}:
            log.warning("Le serveur distant demande HTTPS via un proxy inverse et un jeton d'accès.")
        uvicorn.run(app, host=host, port=WEB_PORT, log_level="error")

# --- SPEECH ENGINE (TTS) ---
def sanitize_for_speech(text: str) -> str:
    """Nettoie le texte avant synthèse vocale."""
    text = re.sub(r'[*_#`~\[\]()]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\sàâäéèêëïîôùûüçÀÂÄÉÈÊËÏÎÔÙÛÜÇ.,!?;:\'-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def play_wake_chime():
    """Signal sonore discret à la détection du mot-clé."""
    if not PYGAME_OK:
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        duration = 0.12
        fs = 22050
        t = np.linspace(0, duration, int(fs * duration), False) if SOUND_OK else None
        if t is not None:
            wave = (np.sin(2 * np.pi * 880 * t) * 0.25 * 32767).astype(np.int16)
            snd = pygame.sndarray.make_sound(wave)
            snd.play()
    except Exception:
        pass



# --- STT ENGINE (Whisper local optionnel) ---
_whisper_model = None
_whisper_lock = threading.Lock()

def get_whisper_model():
    global _whisper_model
    if not WHISPER_OK or not CONFIG.get("use_whisper", False):
        return None
    with _whisper_lock:
        if _whisper_model is None:
            try:
                log.info("Chargement du modèle Whisper local...")
                _whisper_model = whisper.load_model("base")
                log.info("Whisper prêt.")
            except Exception as e:
                log.warning(f"Whisper indisponible : {e}")
                return None
        return _whisper_model

def transcribe_audio(audio_data, sample_rate=16000):
    """Transcription locale Whisper ou Google STT en fallback."""
    model = get_whisper_model()
    if model and SOUND_OK:
        try:
            path = BASE_DIR / f"stt_{time.time_ns()}.wav"
            sf.write(str(path), audio_data, sample_rate)
            result = model.transcribe(str(path), language="fr", fp16=False)
            path.unlink(missing_ok=True)
            text = result.get("text", "").strip()
            if text:
                return text
        except Exception as e:
            log.debug(f"Whisper STT échec : {e}")
    return None

# --- EXTRACTED COMPONENT RUNTIME ---
configure_components(**globals())
camera_manager = CameraManager()
plugin_manager = PluginManager(PLUGINS_DIR)
tools = ToolManager()
speech = SpeechEngine()
processor = CommandProcessor()
configure_components(**globals())

# --- INTENT ENGINE & AI ---

# --- MODULES ET FENÊTRES SECONDAIRES ---






class GroqSettingsWidget(QWidget):
    """Local Groq/Ollama conversation provider settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🧠 FOURNISSEUR IA — GROQ / OLLAMA"))
        layout.addWidget(QLabel("Clé API Groq"))
        self.api_key = QLineEdit(CONFIG.get("groq_api_key", ""))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("gsk_...")
        layout.addWidget(self.api_key)
        layout.addWidget(QLabel("Fournisseur IA"))
        self.provider = QComboBox()
        self.provider.addItem("Groq", "groq")
        self.provider.addItem("Ollama", "ollama")
        current_provider = CONFIG.get("ai_provider", "groq")
        provider_index = self.provider.findData(current_provider)
        self.provider.setCurrentIndex(provider_index if provider_index >= 0 else 0)
        layout.addWidget(self.provider)

        layout.addWidget(QLabel("Modèle IA"))
        self.model = QComboBox()
        self.model.setMinimumContentsLength(28)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Single source of truth: this is the model list used by the visible UI.
        from core.ai_model_catalog import GROQ_MODELS
        self._groq_models = list(GROQ_MODELS)
        self._ollama_models = [
            ("Grand • Llama 3.1 8B", "llama3.1:8b"),
            ("Moyen • Llama 3.2 3B", "llama3.2:3b"),
            ("Petit • Phi-3 Mini", "phi3:mini"),
            ("Mini • Gemma 2 2B", "gemma2:2b"),
        ]
        self.provider.currentIndexChanged.connect(self._refresh_model_choices)
        self._refresh_model_choices()
        layout.addWidget(self.model)
        self.enabled = QCheckBox("Activer Groq pour les conversations")
        self.enabled.setChecked(current_provider == "groq")
        self.enabled.toggled.connect(lambda checked: self.provider.setCurrentIndex(0 if checked else 1))
        layout.addWidget(self.enabled)
        self.fallback = QCheckBox("Fallback automatique vers Ollama")
        self.fallback.setChecked(CONFIG.get("ollama_enabled", True))
        layout.addWidget(self.fallback)
        buttons = QHBoxLayout()
        self.btn_save = GlowButton("💾 ENREGISTRER", state.theme_color)
        self.btn_save.clicked.connect(self.save_settings)
        buttons.addWidget(self.btn_save)
        self.btn_test = GlowButton("🧪 TESTER GROQ", state.secondary_color)
        self.btn_test.clicked.connect(self.test_groq)
        buttons.addWidget(self.btn_test)
        layout.addLayout(buttons)
        self.status = QLabel("Statut : configuration locale")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)


    def _refresh_model_choices(self):
        provider = self.provider.currentData() or "groq"
        current = (
            CONFIG.get("groq_model", "openai/gpt-oss-20b")
            if provider == "groq"
            else CONFIG.get("model", "llama3.2:3b")
        )
        models = self._groq_models if provider == "groq" else self._ollama_models
        self.model.blockSignals(True)
        self.model.clear()
        for label, model_id in models:
            self.model.addItem(label, model_id)
        index = self.model.findData(current)
        if index < 0 and current:
            self.model.addItem(f"Personnalisé • {current}", current)
            index = self.model.count() - 1
        if index >= 0:
            self.model.setCurrentIndex(index)
        self.model.blockSignals(False)

    def save_settings(self):
        CONFIG["groq_api_key"] = self.api_key.text().strip()
        selected_model = self.model.currentData() or self.model.currentText().strip()
        provider = self.provider.currentData() or "groq"
        if provider == "groq":
            CONFIG["groq_model"] = str(selected_model) or "openai/gpt-oss-20b"
        else:
            CONFIG["model"] = str(selected_model) or "llama3.2:3b"
        CONFIG["ai_provider"] = provider
        CONFIG["ollama_enabled"] = self.fallback.isChecked()
        save_config(CONFIG)
        try:
            processor.conversation_ai = ConversationAI(CONFIG, ollama)
        except Exception:
            pass
        self.status.setText("Statut : paramètres enregistrés. Le prochain message utilisera la nouvelle configuration.")
        signals.log_msg.emit("IA", f"Fournisseur configuré : {CONFIG['ai_provider']} — Groq : {'configuré' if CONFIG['groq_api_key'] else 'non configuré'}")

    def test_groq(self):
        key = self.api_key.text().strip()
        if not key:
            self.status.setText("Statut : clé API Groq manquante.")
            return
        try:
            from core.groq_provider import GroqProvider
            provider = GroqProvider(api_key=key, model=str(self.model.currentData() or self.model.currentText().strip() or "openai/gpt-oss-20b"), timeout=15)
            result = provider.chat([{"role": "user", "content": "Réponds uniquement par OK."}], temperature=0, max_tokens=8)
            self.status.setText(f"Statut : Groq opérationnel — réponse : {result.strip()}")
        except Exception as exc:
            self.status.setText(f"Statut : test Groq échoué. Fallback Ollama disponible si activé.\n{exc}")



# --- HUD SUPRÊME & COMPOSANTS VISUELS HOLOGRAPHIQUES ---







class DynamicSpaceWidget(QFrame):
    """Espace riche: texte, images, sites, vidéos et liens détectés automatiquement."""
    image_loaded = pyqtSignal(int, str, bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DynamicSpace")
        self.setMinimumHeight(190)
        self.setMaximumHeight(430)
        self.setStyleSheet("""
            QFrame#DynamicSpace { background: rgba(0, 243, 255, 0.045); border: 1px solid rgba(0,243,255,0.30); border-radius: 12px; }
            QLabel { background: transparent; border: none; }
            QScrollArea { background: transparent; border: none; }
            QTextEdit { background: rgba(2,8,22,0.70); color: #dffaff; border: 1px solid rgba(0,243,255,0.18); border-radius: 10px; padding: 8px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        self.header = QLabel("◈ DYNAMIC SPACE  ·  CONTENU CONTEXTUEL")
        self.header.setStyleSheet("color:#00f3ff; font-weight:bold; letter-spacing:1px;")
        root.addWidget(self.header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(2, 2, 2, 2)
        self.body_layout.setSpacing(8)
        self.body_layout.addStretch()
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)

        self.image_loaded.connect(self._apply_image)
        self._media_generation = 0
        self._image_targets = {}

    def _clear_body(self):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _card(self, title, widget):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: rgba(5,16,38,0.88); border: 1px solid rgba(0,243,255,0.16); border-radius: 10px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        if title:
            label = QLabel(title)
            label.setStyleSheet("color:#00ffaa; font-weight:bold;")
            layout.addWidget(label)
        layout.addWidget(widget)
        self.body_layout.insertWidget(max(0, self.body_layout.count() - 1), frame)
        return frame

    @staticmethod
    def _urls(text):
        return list(dict.fromkeys(re.findall(r"https?://[^\s<>\]\)]+", text)))

    @staticmethod
    def _image_urls(text):
        return [u for u in DynamicSpaceWidget._urls(text) if re.search(r"\.(?:png|jpe?g|gif|webp|bmp)(?:\?.*)?$", u, re.I)]

    @staticmethod
    def _video_urls(text):
        urls = DynamicSpaceWidget._urls(text)
        out = []
        for u in urls:
            if re.search(r"\.(?:mp4|webm|mov|m3u8)(?:\?.*)?$", u, re.I) or any(host in u.lower() for host in ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")):
                out.append(u)
        return out

    def _text_card(self, text):
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setMinimumHeight(min(210, max(90, 34 + text.count("\n") * 18)))
        safe = html.escape(text)
        safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
        safe = safe.replace("\n", "<br>")
        editor.setHtml(f"<div style='font-size:13px;line-height:1.45'>{safe}</div>")
        self._card("📝 TEXTE", editor)

    def _add_link_cards(self, urls, video_urls, image_urls):
        media = set(image_urls + video_urls)
        for url in urls:
            if url in media:
                continue
            if WEBENGINE_OK:
                view = QWebEngineView()
                view.setMinimumHeight(230)
                view.setMaximumHeight(300)
                view.setUrl(QUrl(url))
                self._card(f"🌐 SITE · {url}", view)
            else:
                label = QLabel(f"🌐 {url}")
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                label.setOpenExternalLinks(True)
                self._card("🌐 SITE", label)

    def _add_videos(self, urls):
        for url in urls[:3]:
            if WEBENGINE_OK:
                view = QWebEngineView()
                view.setMinimumHeight(220)
                view.setMaximumHeight(300)
                view.setUrl(QUrl(url))
                self._card("▶ VIDÉO", view)
            else:
                label = QLabel(f"▶ {url}")
                label.setWordWrap(True)
                label.setOpenExternalLinks(True)
                self._card("▶ VIDÉO", label)

    def _add_images(self, items, generation=None):
        generation = self._media_generation if generation is None else generation
        for index, item in enumerate(items[:6]):
            if isinstance(item, dict):
                url = str(item.get("url") or "")
                thumbnail = str(item.get("thumbnail") or "")
            else:
                url = str(item or "")
                thumbnail = ""
            if not url and not thumbnail:
                continue
            label = QLabel("⏳ Chargement de l'image…")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumHeight(100)
            label.setWordWrap(True)
            self._card("🖼 IMAGE", label)
            key = f"{generation}:{index}"
            self._image_targets[key] = label
            threading.Thread(target=self._download_image, args=(generation, key, url, thumbnail), daemon=True).start()

    def _download_image(self, generation, key, url, thumbnail=""):
        headers = {
            "User-Agent": "JARVIS-NEO/3.6",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        candidates = [x for x in (url, thumbnail) if x]
        for candidate in candidates:
            try:
                response = requests.get(candidate, timeout=8, headers=headers)
                if response.ok and response.content:
                    self.image_loaded.emit(generation, key, response.content)
                    return
            except Exception as exc:
                logging.debug("Dynamic Space image load failed: %s", exc)

    def _apply_image(self, generation, key, data):
        if generation != self._media_generation:
            return
        label = self._image_targets.get(key)
        if label is None or not label.isVisible():
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return
        label.setPixmap(pixmap.scaled(700, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        label.setText("")

    def update_media_search(self, kind, results, query=""):
        self._media_generation += 1
        generation = self._media_generation
        self._image_targets = {}
        self._clear_body()
        kind = str(kind or "").lower()
        items = results or []
        label = "IMAGES" if kind == "image_search" else "VIDÉOS"
        self.header.setText(f"◈ DYNAMIC SPACE · {label} · {len(items)} résultat(s)")
        if query:
            q = QLabel(f"Recherche : {query}")
            q.setWordWrap(True)
            q.setStyleSheet("color:#8fdcff; padding:6px;")
            self.body_layout.insertWidget(0, q)
        if kind == "image_search":
            self._add_images(items, generation)
        else:
            self._add_videos([x.get("source_url") or x.get("url", "") for x in items if x.get("source_url") or x.get("url")])
        self.scroll.verticalScrollBar().setValue(0)

    def update_from_response(self, message):
        text = str(message or "").strip()
        if not text:
            return
        self._media_generation += 1
        self._image_targets = {}
        self._clear_body()
        urls = self._urls(text)
        image_urls = self._image_urls(text)
        video_urls = self._video_urls(text)
        self.header.setText(f"◈ DYNAMIC SPACE  ·  {len(urls)} LIEN(S)  ·  {len(image_urls)} IMAGE(S)  ·  {len(video_urls)} VIDÉO(S)")
        self._text_card(text)
        self._add_images(image_urls)
        self._add_videos(video_urls)
        self._add_link_cards(urls, video_urls, image_urls)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())



# --- WORKERS ---

def command_worker():
    while True:
        cmd = command_queue.get()
        state.abort_requested = False
        try:
            memory.add_message("user", cmd)
            response = processor.process(cmd)
            if not state.abort_requested:
                memory.add_message("assistant", response)
                signals.log_msg.emit("Jarvis", response)
                speech.say(response)
            else:
                signals.log_msg.emit("Jarvis", "Opération interrompue.")
        except Exception as e:
            log.exception("Erreur dans le processeur de commandes")
            response = f"Erreur de commande : {e}"
            signals.log_msg.emit("J.A.R.V.I.S.", response)
            if state.voice_enabled:
                speech.say(response)
        finally:
            state.abort_requested = False
            command_queue.task_done()

def voice_worker():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3

    while True:
        if not state.mic_enabled or state.is_processing or state.is_speaking:
            time.sleep(0.3)
            continue
        try:
            with sr.Microphone() as source:
                state.is_listening = True
                signals.listening_change.emit(True)
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)

                # Niveau audio approximatif pour le visualiseur
                raw = np.frombuffer(audio.get_raw_data(), dtype=np.int16) if SOUND_OK else None
                if raw is not None and len(raw) > 0:
                    level = min(1.0, float(np.abs(raw).mean()) / 8000.0)
                    state.audio_level = level
                    signals.audio_level.emit(level)

                text = None
                if CONFIG.get("use_whisper") and SOUND_OK and raw is not None:
                    text = transcribe_audio(raw.astype(np.float32) / 32768.0, sample_rate=audio.sample_rate)

                if not text:
                    text = recognizer.recognize_google(audio, language=LANGUAGE)

                state.is_listening = False
                signals.listening_change.emit(False)

                if text:
                    text_lower = text.lower()
                    if state.passive_listening:
                        if HOTWORD in text_lower:
                            play_wake_chime()
                            clean_cmd = re.sub(rf"\b{HOTWORD}\b", "", text_lower).strip()
                            if clean_cmd:
                                signals.log_msg.emit("Vous (Voix)", text)
                                command_queue.put(clean_cmd)
                            else:
                                signals.log_msg.emit("Vous (Voix)", text)
                                speech.say("À vos ordres, monsieur.")
                    else:
                        signals.log_msg.emit("Vous (Voix)", text)
                        command_queue.put(text)
        except sr.WaitTimeoutError:
            state.is_listening = False
            signals.listening_change.emit(False)
        except sr.UnknownValueError:
            state.is_listening = False
            signals.listening_change.emit(False)
        except Exception as e:
            state.is_listening = False
            signals.listening_change.emit(False)
            log.debug(f"STT : {e}")
        time.sleep(0.2)

def reminder_worker():
    while True:
        now = time.time()
        # SQLite is the source of truth, therefore reminders survive a restart.
        for reminder_id, task, _due_at, repeat_seconds in memory.due_reminders(now):
            memory.mark_reminder_fired(reminder_id, repeat_seconds, now)
            msg = f"Rappel : {task}"
            tools.activity("rappel", msg)
            signals.log_msg.emit("Rappel", msg)
            speech.say(f"Monsieur, je vous rappelle que : {task}")
        time.sleep(1)

def retro_vision_worker():
    while True:
        if state.retro_vision_active and CONFIG.get("retro_vision_enabled", False) and ollama:
            try:
                path = RETRO_DIR / f"retro_{int(time.time())}.png"
                pyautogui.screenshot(str(path))
                
                client = ollama.Client()
                response = client.chat(
                    model=get_active_model(vision=True),
                    messages=[{"role": "user", "content": "Résume en une phrase ce qui est affiché sur cet écran.", "images": [str(path)]}],
                    options={"temperature": 0},
                )
                summary = response['message']['content'].strip()
                memory.add_retro_vision(path, summary)
            except:
                pass
        time.sleep(max(60, int(CONFIG.get("retro_vision_interval", 300))))

def security_worker():
    previous_gray = None
    last_alert_time = 0
    while True:
        if state.security_mode and OPENCV_OK and NUMPY_OK:
            frame = camera_manager.get_frame()
            if frame is not None:
                small_frame = cv2.resize(frame, (320, 240))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if previous_gray is not None:
                    frame_delta = cv2.absdiff(previous_gray, gray)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                    
                    changed_pixels = int(cv2.countNonZero(thresh))
                    if changed_pixels > 450:
                        current_time = time.time()
                        if current_time - last_alert_time > 20:
                            alert_path = SNAPSHOTS_DIR / f"security_alert_{int(current_time)}.png"
                            cv2.imwrite(str(alert_path), frame)
                            state.alarm_triggered = True
                            msg = f"Alerte mouvement : {changed_pixels} pixels modifiés détectés."
                            signals.log_msg.emit("Sécurité", msg)
                            tools.activity("sécurité", msg, "WARNING")
                            speech.say("Alerte de sécurité. Mouvement détecté. Entrez le code PIN.")
                            send_security_notification(f"ALERTE INTRUSION : mouvement détecté ({changed_pixels} pixels).", title="Alerte J.A.R.V.I.S.", priority="urgent", tags="rotating_light,shield")
                            last_alert_time = current_time
                
                previous_gray = gray
            
            time.sleep(0.5)
        else:
            previous_gray = None
            time.sleep(2.0)

def system_monitor_worker():
    last_cpu_alert = 0
    last_ram_alert = 0
    while True:
        if state.system_monitor_active:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                now = time.time()
                
                if cpu > 85.0 and (now - last_cpu_alert) > 300:
                    last_cpu_alert = now
                    msg = f"Attention monsieur, surchauffe CPU critique à {int(cpu)}%."
                    signals.log_msg.emit("Système", msg)
                    speech.say(msg)
                    send_security_notification(f"Surcharge CPU critique : {int(cpu)}%", title="Alerte Système J.A.R.V.I.S.", priority="urgent")
                elif ram > 90.0 and (now - last_ram_alert) > 300:
                    last_ram_alert = now
                    msg = f"Attention monsieur, saturation de la mémoire vive à {int(ram)}%."
                    signals.log_msg.emit("Système", msg)
                    speech.say(msg)
            except: pass
        time.sleep(10)

# --- MAIN ---

def main():
    app = QApplication(sys.argv)
    
    send_security_notification(
        message="Le système J.A.R.V.I.S. NEO a démarré avec succès en mode omnipotent.",
        title="J.A.R.V.I.S. En Ligne",
        priority="default",
        tags="rocket"
    )

    threading.Thread(target=command_worker, daemon=True).start()
    threading.Thread(target=voice_worker, daemon=True).start()
    threading.Thread(target=reminder_worker, daemon=True).start()
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=security_worker, daemon=True).start()
    threading.Thread(target=system_monitor_worker, daemon=True).start()
    threading.Thread(target=retro_vision_worker, daemon=True).start()
    
    window = JarvisWindow()
    window.show()

    # HUD discret réellement attaché à la fenêtre principale.
    # Il est créé sur le thread Qt principal, donc aucun monkey-patch asynchrone
    # n'est nécessaire et le bouton de paramètres reste toujours accessible.
    try:
        from ui.discrete_hud import DiscreteHud
        window._jarvis_discrete_hud = DiscreteHud(window)
        window._jarvis_discrete_hud.show_discrete()
    except Exception as exc:
        logging.exception("Impossible d'initialiser le HUD discret : %s", exc)
    
    speech.say("Systèmes quantiques en ligne. Prêt à exécuter vos ordres.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
