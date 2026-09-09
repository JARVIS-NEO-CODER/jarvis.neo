"""Dynamic cockpit panels for J.A.R.V.I.S. NEO.

The engine manages safe, UI-level panels. It deliberately does not execute
arbitrary Python from configuration or AI output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


@dataclass
class CockpitPanel:
    panel_id: str
    title: str
    kind: str = "info"
    content: str = ""
    source: str = ""


class CockpitWidgetEngine:
    """Create, update and remove dynamic panels inside the cockpit."""

    ALLOWED_KINDS = {"info", "web", "image", "status", "notification"}

    def __init__(self, host: QWidget):
        self.host = host
        self.panels: dict[str, tuple[CockpitPanel, QWidget]] = {}
        self.layout = QVBoxLayout(host)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self.empty = QLabel("NO DYNAMIC DATA")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet("color:#456b78;font-size:8px;letter-spacing:1.5px;padding:14px;")
        self.layout.addWidget(self.empty)

    def show_panel(self, panel_id: str, title: str, content: str = "", kind: str = "info", source: str = "") -> bool:
        kind = str(kind or "info").lower()
        if kind not in self.ALLOWED_KINDS or not panel_id:
            return False
        panel = CockpitPanel(str(panel_id), str(title)[:80], kind, str(content)[:4000], str(source)[:500])
        if panel_id in self.panels:
            _, widget = self.panels[panel_id]
            self._render(widget, panel)
            self.panels[panel_id] = (panel, widget)
            return True
        widget = QFrame(self.host)
        widget.setStyleSheet(
            "QFrame { background:rgba(0,243,255,0.035); border:1px solid rgba(0,243,255,0.20); border-radius:8px; }"
            "QLabel { background:transparent; border:none; }"
        )
        self.layout.addWidget(widget)
        self._render(widget, panel)
        self.panels[panel_id] = (panel, widget)
        self.empty.setVisible(False)
        return True

    def remove_panel(self, panel_id: str) -> bool:
        item = self.panels.pop(panel_id, None)
        if not item:
            return False
        _, widget = item
        self.layout.removeWidget(widget)
        widget.deleteLater()
        self.empty.setVisible(not self.panels)
        return True

    def clear(self) -> None:
        for panel_id in list(self.panels):
            self.remove_panel(panel_id)

    def _render(self, widget: QWidget, panel: CockpitPanel) -> None:
        old = widget.layout()
        if old is not None:
            while old.count():
                item = old.takeAt(0)
                child = item.widget()
                if child:
                    child.deleteLater()
        layout = old or QVBoxLayout(widget)
        layout.setContentsMargins(9, 7, 9, 7)
        title = QLabel(f"◈ {panel.title.upper()}")
        title.setStyleSheet("color:#00f3ff;font-size:9px;font-weight:900;letter-spacing:1px;")
        body = QLabel(panel.content or "")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet("color:#bfefff;font-size:9px;")
        layout.addWidget(title)
        layout.addWidget(body)
        if panel.source:
            source = QLabel(panel.source)
            source.setStyleSheet("color:#4d8290;font-size:7px;")
            layout.addWidget(source)

    def snapshot(self) -> list[dict[str, Any]]:
        return [panel.__dict__.copy() for panel, _ in self.panels.values()]
