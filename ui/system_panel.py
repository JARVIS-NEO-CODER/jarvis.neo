"""J.A.R.V.I.S. NEO — compact system telemetry panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget


class SystemPanel(QWidget):
    """Small reusable panel for CPU/RAM/GPU/status values."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._values: dict[str, QLabel] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        for row, name in enumerate(("CPU", "RAM", "GPU", "TEMP", "NET", "AI")):
            key = QLabel(name)
            key.setStyleSheet("color:#778b7b;font-weight:700;font-size:10px;")
            value = QLabel("--")
            value.setStyleSheet("color:#d9f5c4;font-size:11px;")
            layout.addWidget(key, row, 0)
            layout.addWidget(value, row, 1)
            self._values[name] = value

    def set_value(self, name: str, value: str) -> None:
        key = str(name).upper()
        if key in self._values:
            self._values[key].setText(str(value))
