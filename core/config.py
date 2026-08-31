from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
from pathlib import Path

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
    "camera_enabled": False,
    "microphone_enabled": True,
    "retro_vision_enabled": False,
    "retro_vision_interval": 300,
    "retro_vision_retention_days": 7,
    "allow_screen_control": False,
    "web_enabled": False,
    "web_host": "127.0.0.1",
    "web_port": 8888,
    "ai_provider": "groq",
    "groq_api_key": os.getenv("GROQ_API_KEY", ""),
    "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    "groq_fallback_to_ollama": True,
    "groq_timeout": 60,
    "ollama_enabled": True,
    "ollama_base_url": "http://127.0.0.1:11434",
}

MODEL_TIERS = {
    "grand": {"label": "Grand", "description": "Puissance maximale — précision et raisonnement avancé", "chat": "llama3.1:8b", "vision": "llava:13b"},
    "moyen": {"label": "Moyen", "description": "Équilibre performance / vitesse (recommandé)", "chat": "llama3.2:3b", "vision": "llava"},
    "petit": {"label": "Petit", "description": "Rapide et léger — faible consommation RAM", "chat": "phi3:mini", "vision": "llava-phi3"},
    "mini": {"label": "Mini", "description": "Ultra-léger — réponses quasi instantanées", "chat": "gemma2:2b", "vision": "moondream"},
}


def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass
    return config


def save_config(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
    except Exception as e:
        logging.error(f"Erreur sauvegarde config : {e}")


CONFIG = load_config()
if "model_tier" not in CONFIG or (CONFIG["model_tier"] not in MODEL_TIERS and CONFIG["model_tier"] != "custom"):
    CONFIG["model_tier"] = "moyen"


def get_active_model(vision: bool = False) -> str:
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
    path = BASE_DIR / name
    try:
        if path.exists(): os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_or_create_web_token() -> str:
    path = _secret_path("web.token")
    if path.exists(): return path.read_text(encoding="utf-8").strip()
    token = os.getenv("JARVIS_WEB_TOKEN", secrets.token_urlsafe(32))
    path.write_text(token, encoding="utf-8")
    try: os.chmod(path, 0o600)
    except OSError: pass
    return token


WEB_TOKEN = load_or_create_web_token()
PIN_HASH = os.getenv("JARVIS_PIN_HASH", CONFIG.get("security_pin_hash", ""))


def generate_security_pin_hash(pin: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 200_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_security_pin(candidate: str) -> bool:
    if not PIN_HASH or not candidate: return False
    try:
        salt_b64, digest_b64 = PIN_HASH.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", candidate.encode(), base64.urlsafe_b64decode(salt_b64), 200_000)
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(digest_b64))
    except (ValueError, TypeError): return False


def get_disk_path() -> str:
    if sys.platform == "win32": return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


__all__ = [
    "APP_NAME", "VERSION", "BASE_DIR", "DB_PATH", "SNAPSHOTS_DIR", "RETRO_DIR", "MEMOS_DIR", "PLUGINS_DIR", "CONFIG_FILE",
    "DEFAULT_CONFIG", "MODEL_TIERS", "CONFIG", "MODEL", "VOICE", "LANGUAGE", "HOTWORD", "WEB_PORT", "WEB_TOKEN", "PIN_HASH",
    "load_config", "save_config", "get_active_model", "generate_security_pin_hash", "verify_security_pin", "get_disk_path",
]
