"""Dynamic cockpit panels for J.A.R.V.I.S. NEO.

The engine manages safe, UI-level panels. It deliberately does not execute
arbitrary Python from configuration or AI output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_OK = True
except Exception:
    QWebEngineView = None
    WEBENGINE_OK = False


@dataclass
class CockpitPanel:
    panel_id: str
    title: str
    kind: str = "info"
    content: str = ""
    source: str = ""


class CockpitWidgetEngine:
    """Create, update and remove bounded dynamic panels inside the cockpit."""

    ALLOWED_KINDS = {"info", "web", "image", "status", "notification"}
    MAX_PANELS = 8
    MAX_TEXT = 4000
    MAX_SOURCE = 1000

    def __init__(self, host: QWidget):
        self.host = host
        self.panels: dict[str, tuple[CockpitPanel, QWidget]] = {}
        self.layout = QVBoxLayout(host)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self.network = QNetworkAccessManager(host)
        self.empty = QLabel("NO DYNAMIC DATA")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet("color:#456b78;font-size:8px;letter-spacing:1.5px;padding:14px;")
        self.layout.addWidget(self.empty)

    @staticmethod
    def _valid_url(value: str) -> bool:
        try:
            parsed = urlparse(str(value).strip())
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:
            return False

    def show_panel(self, panel_id: str, title: str, content: str = "", kind: str = "info", source: str = "") -> bool:
        kind = str(kind or "info").lower().strip()
        panel_id = str(panel_id or "").strip()
        if kind not in self.ALLOWED_KINDS or not panel_id:
            return False
        source = str(source or "").strip()[: self.MAX_SOURCE]
        content = str(content or "").strip()[: self.MAX_TEXT]
        if kind in {"web", "image"}:
            target = source or content
            if not self._valid_url(target):
                return False
            source = target
        panel = CockpitPanel(panel_id, str(title)[:80], kind, content, source)
        if panel_id in self.panels:
            _, widget = self.panels[panel_id]
            self._render(widget, panel)
            self.panels[panel_id] = (panel, widget)
            return True
        if len(self.panels) >= self.MAX_PANELS:
            oldest = next(iter(self.panels))
            self.remove_panel(oldest)
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
        item = self.panels.pop(str(panel_id), None)
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
        layout.setSpacing(5)
        title = QLabel(f"◈ {panel.title.upper()}")
        title.setStyleSheet("color:#00f3ff;font-size:9px;font-weight:900;letter-spacing:1px;")
        layout.addWidget(title)

        if panel.kind == "web" and WEBENGINE_OK:
            view = QWebEngineView(widget)
            view.setMinimumHeight(210)
            view.setUrl(QUrl(panel.source))
            layout.addWidget(view)
        elif panel.kind == "image":
            image = QLabel("CHARGEMENT IMAGE…")
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image.setMinimumHeight(130)
            image.setStyleSheet("color:#7895a5;font-size:8px;border:none;")
            layout.addWidget(image)
            request = QNetworkRequest(QUrl(panel.source))
            reply = self.network.get(request)
            reply.finished.connect(lambda r=reply, label=image: self._finish_image(r, label))
        else:
            body = QLabel(panel.content or "")
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            body.setStyleSheet("color:#bfefff;font-size:9px;")
            layout.addWidget(body)

        if panel.source and panel.kind not in {"web", "image"}:
            source = QLabel(panel.source)
            source.setStyleSheet("color:#4d8290;font-size:7px;")
            source.setWordWrap(True)
            layout.addWidget(source)

    @staticmethod
    def _finish_image(reply, label: QLabel) -> None:
        try:
            if reply.error() or len(reply.readAll()) == 0:
                label.setText("IMAGE INDISPONIBLE")
                return
            reply.deleteLater()
        except Exception:
            try:
                label.setText("IMAGE INDISPONIBLE")
            except Exception:
                return
        try:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(bytes(data)):
                label.setPixmap(pixmap.scaled(420, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                label.setText("FORMAT IMAGE NON PRIS EN CHARGE")
        except Exception:
            label.setText("IMAGE INDISPONIBLE")

    def snapshot(self) -> list[dict[str, Any]]:
        return [panel.__dict__.copy() for panel, _ in self.panels.values()]


__all__ = ["CockpitPanel", "CockpitWidgetEngine", "WEBENGINE_OK"]
