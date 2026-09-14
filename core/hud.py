"""Expanded J.A.R.V.I.S. NEO HUD.

The HUD is deliberately data-driven: controls are grouped by capability and
route through the existing CommandProcessor where possible. Unsupported
future capabilities stay visible but disabled instead of pretending to work.
"""
from __future__ import annotations

from functools import partial

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget


CATEGORIES = [
    ("🧠 IA", [
        ("CHAT", None, True), ("MODE IA", "mode moyen", True), ("MODÈLE", "modèle actuel", True),
        ("AIDE", "aide", True), ("EFFACER CHAT", "vider le chat", True), ("STOP ACTION", "__stop__", True),
    ]),
    ("🖥️ PC", [
        ("MÉTÉO", "météo", True), ("HEURE", "heure", True), ("DATE", "date", True),
        ("BATTERIE", "batterie", True), ("UPTIME", "uptime", True), ("PROCESSUS", "processus", True),
        ("PERFORMANCES", "performance", True), ("EXPLORATEUR", "ouvre explorateur", True),
        ("CALCULATRICE", "ouvre calculatrice", True), ("NOTEPAD", "ouvre bloc-notes", True),
        ("CAPTURE", "capture", True), ("COPIER", "__focus__", True),
    ]),
    ("🌐 WEB", [
        ("RECHERCHE", None, True), ("IMAGES", None, True), ("NAVIGATEUR", "__browser__", True), ("WEB LOCAL", "__web__", True),
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
        ("SENTINELLE", "__sentinel__", True), ("ACTIVITÉ", "__activity__", True),
        ("PERMISSIONS", None, False), ("SESSIONS", None, False), ("APPAREILS", None, False),
    ]),
    ("⏰ AUTOMATION", [
        ("TÂCHES", "mes tâches", True), ("MÉMOS", "mes mémos", True), ("AGENDA", None, False),
        ("RAPPELS", None, False), ("WORKFLOWS", None, False), ("MACROS", "__macros__", True), ("HISTORIQUE", "__activity__", True),
    ]),
    ("🧩 PLUGINS", [
        ("LISTE", "liste les plugins", True), ("CHARGER", None, True), ("DÉCHARGER", None, True),
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
    """Dense but navigable command center for the desktop assistant."""
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("neoHudPanel")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        title = QLabel("NEO CONTROL CENTER")
        title.setObjectName("hudTitle")
        root.addWidget(title)
        subtitle = QLabel("Toutes les commandes utiles au même endroit. Les fonctions non câblées restent grisées.")
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
                button.setToolTip("Interface prête, moteur non exposé dans cette version.")
            grid.addWidget(button, index // 2, index % 2)
        grid.setRowStretch((len(actions) + 1) // 2, 1)
        scroll.setWidget(body)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return page

    def _dispatch(self, command):
        if command is None:
            self.window.cmd_input.setFocus()
            return
        if command == "__mic__": self.window.toggle_mic(); return
        if command == "__cam__": self.window.toggle_camera(); return
        if command == "__stop__": self.window._stop_tts(); return
        if command == "__retro__": self.window._toggle_retro(); return
        if command == "__sentinel__": self.window._run_command("sécurité on"); return
        if command == "__activity__": self.window._run_command("processus"); return
        if command == "__macros__": self.window._show_module("MacrosWidget", "MACROS"); return
        if command == "__focus__": self.window.cmd_input.setFocus(); return
        if command == "__browser__": self.window.load_url_in_browser("https://www.google.com"); return
        if command == "__web__": self.window._run_command("cherche web"); return
        self.window._run_command(command)


def install():
    """Replace the legacy small JarvisWindow with the expanded HUD wrapper."""
    import importlib
    ac = importlib.import_module("core.assistant_components")
    if getattr(ac, "_neo_hud_installed", False): return
    BaseWindow = ac.JarvisWindow

    class ExpandedJarvisWindow(BaseWindow):
        def __init__(self):
            super().__init__()
            self.setMinimumSize(1250, 780)
            self._install_hud()

        def _install_hud(self):
            if hasattr(self, "neo_hud"): return
            right_layout = self.centralWidget().layout().itemAt(1).layout()
            self.neo_hud = NeoHudPanel(self, self.centralWidget())
            right_layout.insertWidget(1, self.neo_hud)

        def _run_command(self, command):
            processor = getattr(ac, "processor", None)
            if processor is None:
                self.add_chat_msg("Système", "Le processeur de commandes n'est pas encore initialisé.")
                return
            try:
                result = processor.process(command)
                if result: self.add_chat_msg("JARVIS", result)
            except Exception as exc:
                self.add_chat_msg("JARVIS", f"Erreur commande : {exc}")

        def _stop_tts(self):
            speech = getattr(ac, "speech", None)
            if speech is not None and hasattr(speech, "stop"): speech.stop()
            self.add_chat_msg("JARVIS", "Synthèse vocale interrompue.")

        def _toggle_retro(self):
            state = getattr(ac, "_state", None)
            if state is not None:
                state.retro_vision_enabled = not getattr(state, "retro_vision_enabled", False)
                self.add_chat_msg("JARVIS", "Rétrovision " + ("activée." if state.retro_vision_enabled else "désactivée."))

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
