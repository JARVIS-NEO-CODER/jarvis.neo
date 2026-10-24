"""J.A.R.V.I.S. NEO — terminal/chat display widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QWidget


class NeoTerminal(QPlainTextEdit):
    """Compact terminal-style conversation view for the left HUD panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setObjectName("neoTerminal")
        self.setStyleSheet("""
            QPlainTextEdit#neoTerminal {
                background: transparent;
                border: none;
                color: #e8eaf0;
                selection-background-color: #6b3527;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
            }
        """)

    def append_entry(self, speaker: str, message: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        prefix = "USER  > " if speaker.lower() in {"user", "you", "toi"} else "NEO   > "
        cursor.insertText(f"{prefix}{message}\n")
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
