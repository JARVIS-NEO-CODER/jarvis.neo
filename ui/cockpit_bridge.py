"""Runtime bridge that attaches the NEO cockpit to the real JarvisWindow."""
from __future__ import annotations


def install(assistant) -> bool:
    window_cls = getattr(assistant, "JarvisWindow", None)
    if window_cls is None or getattr(window_cls, "_neo_cockpit_wired", False):
        return False
    try:
        from PyQt6.QtWidgets import QPushButton
        from ui.cockpit_hud import CockpitHud
    except Exception:
        return False

    original_init = window_cls.__init__

    def init_with_cockpit(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            button = QPushButton("◈ COCKPIT")
            button.setToolTip("Ouvrir le centre de commande J.A.R.V.I.S. NEO")
            button.setMinimumHeight(34)
            button.setStyleSheet(
                "QPushButton { background:rgba(0,243,255,0.07); color:#00f3ff; "
                "border:1px solid rgba(0,243,255,0.45); border-radius:7px; "
                "padding:7px 10px; font-weight:700; }"
                "QPushButton:hover { background:rgba(0,243,255,0.16); border-color:#00f3ff; }"
            )

            def open_cockpit():
                dialog = getattr(self, "_neo_cockpit", None)
                if dialog is None:
                    dialog = CockpitHud(assistant, self)
                    self._neo_cockpit = dialog
                dialog.refresh()
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()

            button.clicked.connect(open_cockpit)
            self._neo_cockpit_button = button
            if hasattr(self, "left_panel"):
                self.left_panel.insertWidget(0, button)
            else:
                button.setParent(self)
                button.show()
            self._neo_open_cockpit = open_cockpit
        except Exception as exc:
            try:
                assistant.log.warning(f"Cockpit HUD non chargé : {exc}")
            except Exception:
                pass

    window_cls.__init__ = init_with_cockpit
    window_cls._neo_cockpit_wired = True
    return True
