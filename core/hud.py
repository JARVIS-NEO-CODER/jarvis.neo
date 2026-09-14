"""Expanded J.A.R.V.I.S. NEO HUD.

The HUD is data-driven, but every enabled control must route to a real
runtime capability. Commands are sent through the same queue used by the
main assistant instead of trying to reach globals that live in assistant.py.
"""
from __future__ import annotations

import sys
import webbrowser
from functools import partial

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget, QInputDialog


CATEGORIES = [
    ("🧠 IA", [
        ("CHAT", "__focus__", True), ("MODE IA", "mode moyen", True), ("MODÈLE", "modèle actuel", True),
        ("AIDE", "aide", True), ("EFFACER CHAT", "vider le chat", True), ("STOP PAROLE", "__stop__", True),
    ]),
    ("🖥️ PC", [
        ("MÉTÉO", "météo", True), ("HEURE", "heure", True), ("DATE", "date", True),
        ("BATTERIE", "batterie", True), ("UPTIME", "uptime", True), ("PROCESSUS", "processus", True),
        ("PERFORMANCES", "performance", True), ("EXPLORATEUR", "ouvre explorateur", True),
        ("CALCULATRICE", "ouvre calculatrice", True), ("NOTEPAD", "ouvre bloc-notes", True),
        ("CAPTURE", "capture", True), ("SYSTÈME", "système", True),
    ]),
    ("🌐 WEB", [
        ("RECHERCHE", "__search__", True), ("IMAGES", "__images__", True),
        ("NAVIGATEUR", "__browser__", True), ("WEB LOCAL", "__web__", True),
    ]),
    ("🎙️ VOIX", [
        ("MICRO", "__mic__", True), ("ÉCOUTE PASSIVE", "écoute passive on", True),
        ("STOP PAROLE", "__stop__", True), ("WAKE WORD", None, False), ("VAD", None, False), ("WHISPER", None, False),
    ]),
    ("👁️ VISION", [
        ("ANALYSER ÉCRAN", "analyse l'écran", True), ("CAPTURE", "capture", True), ("CAMÉRA", "__cam__", True),
        ("RÉTROVISION", "__retro__", True), ("MÉMOIRE VISUELLE", None, False), ("SOURIS", None, False), ("CLAVIER", None, False),
    ]),
    ("🛡️ SÉCURITÉ", [
        ("SÉCURITÉ ON", "sécurité on", True), ("SÉCURITÉ OFF", "sécurité off", True),
        ("SENTINELLE", None, False), ("ACTIVITÉ", None, False),
        ("PERMISSIONS", None, False), ("SESSIONS", None, False), ("APPAREILS", None, False),
    ]),
    ("⏰ AUTOMATION", [
        ("TÂCHES", "mes tâches", True), ("MÉMOS", "mes mémos", True), ("AGENDA", None, False),
        ("RAPPELS", None, False), ("WORKFLOWS", None, False), ("MACROS", "__macros__", True), ("HISTORIQUE", None, False),
    ]),
    ("🧩 PLUGINS", [
        ("LISTE", "liste les plugins", True), ("CHARGER", "__load_plugin__", True), ("DÉCHARGER", "__unload_plugin__", True),
        ("PERMISSIONS", None, False), ("DÉPENDANCES", None, False), ("MISES À JOUR", None, False),
    ]),
    ("📱 MOBILE", [
        ("APPAREILS", None, False), ("NOTIFICATIONS", None, False), ("ÉCRAN DISTANT", None, False),
        ("SOURIS", None, False), ("CLAVIER", None, False), ("PRESSE-PAPIERS", None, False),
    ]),
    ("🎮 MODES", [
        ("GRAND", "mode grand", True), ("MOYEN", "mode moyen", True), ("PETIT", "mode petit", True), ("MINI", "mode mini", True),
    ]),
]


class NeoHudPanel(QFrame):
    """Dense command center whose enabled controls are backed by real runtime paths."""
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("neoHudPanel")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        title = QLabel("NEO CONTROL CENTER")
        title.setObjectName("hudTitle")
        root.addWidget(title)
        subtitle = QLabel("Centre de contrôle JARVIS NEO · commandes réellement raccordées au runtime.")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        for name, actions in CATEGORIES:
            self.tabs.addTab(self._make_category(actions), name)

    def _make_category(self, actions):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setSpacing(7)
        for index, (label, command, available) in enumerate(actions):
            button = QPushButton(label)
            button.setMinimumHeight(40)
            button.setEnabled(available)
            if available:
                button.clicked.connect(partial(self._dispatch, command))
            else:
                button.setToolTip("Moteur non exposé par le runtime actuel.")
            grid.addWidget(button, index // 2, index % 2)
        grid.setRowStretch((len(actions) + 1) // 2, 1)
        scroll.setWidget(body)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return page

    def _runtime(self):
        return sys.modules.get("assistant")

    def _prompt_command(self, title, prompt):
        text, ok = QInputDialog.getText(self.window, title, prompt)
        if ok and text.strip():
            self.window._run_command(text.strip())

    def _dispatch(self, command):
        if command == "__mic__":
            self.window.toggle_mic(); return
        if command == "__cam__":
            self.window.toggle_camera(); return
        if command == "__stop__":
            self.window._stop_tts(); return
        if command == "__retro__":
            self.window._toggle_retro(); return
        if command == "__macros__":
            self.window._show_module("MacrosWidget", "MACROS"); return
        if command == "__focus__":
            self.window.cmd_input.setFocus(); return
        if command == "__browser__":
            webbrowser.open("https://www.google.com"); return
        if command == "__web__":
            self.window._run_command("cherche web"); return
        if command == "__search__":
            self._prompt_command("Recherche Web", "Que veux-tu rechercher ?"); return
        if command == "__images__":
            self._prompt_command("Recherche d'images", "Quelles images rechercher ?"); return
        if command == "__load_plugin__":
            self._prompt_command("Charger un plugin", "Nom du plugin à charger :"); return
        if command == "__unload_plugin__":
            self._prompt_command("Décharger un plugin", "Nom du plugin à décharger :"); return
        self.window._run_command(command)


def install():
    """Wrap the existing JarvisWindow with the expanded HUD."""
    import importlib
    ac = importlib.import_module("core.assistant_components")
    if getattr(ac, "_neo_hud_installed", False):
        return
    BaseWindow = ac.JarvisWindow

    class ExpandedJarvisWindow(BaseWindow):
        def __init__(self):
            super().__init__()
            self.setMinimumSize(1250, 780)
            self._install_hud()

        def _install_hud(self):
            if hasattr(self, "neo_hud"):
                return
            central_layout = self.centralWidget().layout()
            if central_layout is None or central_layout.count() < 2:
                raise RuntimeError("Structure de fenêtre principale inattendue")
            right_layout = central_layout.itemAt(1).layout()
            if right_layout is None:
                raise RuntimeError("Layout principal droit introuvable")
            self.neo_hud = NeoHudPanel(self, self.centralWidget())
            right_layout.insertWidget(1, self.neo_hud)

        def _runtime(self):
            return sys.modules.get("assistant")

        def _run_command(self, command):
            runtime = self._runtime()
            command_queue = getattr(runtime, "command_queue", None) if runtime else None
            if command_queue is None:
                self.add_chat_msg("Système", "Le runtime JARVIS n'est pas encore prêt.")
                return
            command_queue.put(str(command))

        def _stop_tts(self):
            runtime = self._runtime()
            speech = getattr(runtime, "speech", None) if runtime else None
            if speech is not None and hasattr(speech, "stop"):
                speech.stop()
            self.add_chat_msg("JARVIS", "Synthèse vocale interrompue.")

        def _toggle_retro(self):
            runtime = self._runtime()
            state = getattr(runtime, "state", None) if runtime else None
            if state is None:
                self.add_chat_msg("JARVIS", "État runtime indisponible.")
                return
            state.retro_vision_active = not bool(getattr(state, "retro_vision_active", False))
            self.add_chat_msg("JARVIS", "Rétrovision " + ("activée." if state.retro_vision_active else "désactivée."))

        def _show_module(self, widget_name, title):
            widget_cls = getattr(ac, widget_name, None)
            if widget_cls is None:
                self.add_chat_msg("JARVIS", f"Module {title} indisponible.")
                return
            try:
                module = ac.ModuleWindow(title, widget_cls())
                module.show()
                self._neo_modules = getattr(self, "_neo_modules", [])
                self._neo_modules.append(module)
            except Exception as exc:
                self.add_chat_msg("JARVIS", f"Impossible d'ouvrir {title} : {exc}")

    ac.JarvisWindow = ExpandedJarvisWindow
    ac._neo_hud_installed = True


__all__ = ["NeoHudPanel", "install"]
