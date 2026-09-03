"""Live command deck injected into the real J.A.R.V.I.S. NEO window."""
from __future__ import annotations

import datetime
import socket

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

try:
    import psutil
except Exception:
    psutil = None


class _Metric(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: rgba(0,243,255,0.055); border: 1px solid rgba(0,243,255,0.24); border-radius: 8px; }"
            "QLabel { border: none; background: transparent; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(2)
        self.title = QLabel(title)
        self.title.setStyleSheet("color:#5f91a2;font-size:8px;font-weight:700;letter-spacing:1.2px;")
        self.value = QLabel("--")
        self.value.setStyleSheet("color:#dffcff;font-size:15px;font-weight:800;")
        self.detail = QLabel("")
        self.detail.setStyleSheet("color:#4de8c1;font-size:8px;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class NeoCommandDeck(QFrame):
    """Obvious, live cockpit layer inside the existing HUD, not a separate window."""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.setObjectName("neoCommandDeck")
        self.setStyleSheet(
            "QFrame#neoCommandDeck { background: rgba(2,10,17,0.92); border: 1px solid rgba(0,243,255,0.34); border-radius: 12px; }"
            "QLabel { border: none; background: transparent; }"
            "QPushButton { background: rgba(0,243,255,0.055); color:#bfefff; border:1px solid rgba(0,243,255,0.25); border-radius:6px; padding:6px 8px; font-size:8px; font-weight:800; }"
            "QPushButton:hover { background: rgba(0,243,255,0.14); border-color:#00f3ff; }"
        )
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        try:
            assistant.signals.status_change.connect(lambda value: self.set_activity(str(value)))
            assistant.signals.listening_change.connect(lambda active: self.set_activity("LISTENING" if active else "READY"))
            assistant.signals.speaking_change.connect(lambda active: self.set_activity("SPEAKING" if active else "READY"))
            assistant.signals.stats_update.connect(self._stats)
            assistant.signals.log_msg.connect(lambda sender, message: self.set_activity(f"{sender}: {message}"))
        except Exception:
            pass
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 9, 10, 9)
        root.setSpacing(7)

        head = QHBoxLayout()
        title = QLabel("◈ NEO COMMAND DECK")
        title.setStyleSheet("color:#00f3ff;font-size:11px;font-weight:900;letter-spacing:1.8px;")
        self.state = QLabel("● ONLINE")
        self.state.setStyleSheet("color:#00ffaa;font-size:8px;font-weight:800;letter-spacing:1px;")
        self.clock = QLabel("--:--:--")
        self.clock.setStyleSheet("color:#77a8b7;font-size:9px;font-family:Consolas;")
        head.addWidget(title)
        head.addSpacing(8)
        head.addWidget(self.state)
        head.addStretch()
        head.addWidget(self.clock)
        root.addLayout(head)

        self.activity = QLabel("SYSTEM READY · awaiting activity")
        self.activity.setStyleSheet("color:#86cfe0;font-size:8px;font-family:Consolas;")
        self.activity.setMaximumHeight(24)
        root.addWidget(self.activity)

        metrics = QGridLayout()
        metrics.setSpacing(6)
        self.metrics = {}
        for i, (key, title) in enumerate((("cpu", "CPU"), ("ram", "RAM"), ("temp", "TEMP"), ("ai", "AI CORE"), ("mic", "MIC"), ("net", "NET"))):
            metric = _Metric(title)
            self.metrics[key] = metric
            metrics.addWidget(metric, i // 3, i % 3)
        root.addLayout(metrics)

        actions = QGridLayout()
        actions.setSpacing(5)
        for i, (label, command) in enumerate((
            ("WEB", "recherche web"), ("FILES", "ouvre explorateur de fichiers"),
            ("SYSTEM", "processus"), ("WEATHER", "météo"), ("AGENT", "mode agent"),
            ("SETTINGS", "paramètres"),
        )):
            button = QPushButton(label)
            button.clicked.connect(lambda _, cmd=command: self._command(cmd))
            actions.addWidget(button, i // 3, i % 3)
        root.addLayout(actions)

    def _command(self, command: str):
        try:
            queue = getattr(self.assistant, "command_queue", None)
            if queue is not None:
                queue.put(command)
                self.set_activity(f"> {command}")
        except Exception as exc:
            self.set_activity(f"ERROR: {exc}")

    def set_activity(self, text: str):
        clean = " ".join(str(text).split())
        self.activity.setText(clean[:130] if clean else "SYSTEM READY")

    def _stats(self, data):
        try:
            self.metrics["cpu"].value.setText(f"{float(data.get('cpu', 0)):.0f}%")
            self.metrics["ram"].value.setText(f"{float(data.get('ram', 0)):.0f}%")
        except Exception:
            pass

    def refresh(self):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.clock.setText(now)
        if psutil:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                self.metrics["cpu"].value.setText(f"{cpu:.0f}%")
                self.metrics["ram"].value.setText(f"{ram:.0f}%")
                self.metrics["cpu"].detail.setText("PROCESS LOAD")
                self.metrics["ram"].detail.setText("MEMORY")
                temps = getattr(psutil, "sensors_temperatures", lambda: {})()
                values = [x.current for group in temps.values() for x in group if x.current is not None]
                if values:
                    self.metrics["temp"].value.setText(f"{max(values):.0f}°C")
                    self.metrics["temp"].detail.setText("SENSOR")
                else:
                    self.metrics["temp"].value.setText("N/A")
            except Exception:
                pass
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=0.15).close()
            self.metrics["net"].value.setText("ONLINE")
        except Exception:
            self.metrics["net"].value.setText("OFFLINE")
        state = getattr(self.assistant, "state", None)
        config = getattr(self.assistant, "CONFIG", {}) or {}
        listening = bool(getattr(state, "is_listening", False))
        speaking = bool(getattr(state, "is_speaking", False))
        self.metrics["mic"].value.setText("LISTEN" if listening else "VOICE" if speaking else "READY")
        self.metrics["mic"].detail.setText("MIC ON" if bool(getattr(state, "mic_enabled", config.get("microphone_enabled", True))) else "MIC OFF")
        processor = getattr(self.assistant, "processor", None)
        conversation = getattr(processor, "conversation_ai", None) if processor else None
        status = getattr(conversation, "status", {}) if conversation else {}
        provider = str(status.get("active_provider") or config.get("ai_provider", "local")).upper()
        model = str(config.get("groq_model" if provider == "GROQ" else "model", "--"))
        self.metrics["ai"].value.setText(provider[:10])
        self.metrics["ai"].detail.setText(model[:22])
        if listening:
            self.state.setText("● LISTENING")
        elif speaking:
            self.state.setText("● SPEAKING")
        elif bool(getattr(state, "is_processing", False)):
            self.state.setText("● THINKING")
        else:
            self.state.setText("● ONLINE")
