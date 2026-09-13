"""Premium visual theme for J.A.R.V.I.S. NEO.

This module only changes presentation. Existing widgets, buttons and command
handlers remain untouched.
"""

from PyQt6.QtGui import QFont


NEO_STYLE = r"""
/* ===== J.A.R.V.I.S. NEO // PREMIUM HUD ===== */
QMainWindow, QWidget {
    background: #070b12;
    color: #d9f7ff;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}

QMainWindow {
    border: 1px solid #183246;
}

QFrame#MainFrame, QFrame#LeftPanel, QFrame#RightPanel, QFrame#DynamicSpace {
    background: #0a1019;
    border: 1px solid #173044;
    border-radius: 16px;
}

QFrame#DynamicSpace {
    background: #080e17;
    border: 1px solid #1d5068;
}

QLabel {
    color: #b9d9e6;
    background: transparent;
}

QLabel#titleLabel, QLabel#headerLabel {
    color: #7eeeff;
    font-size: 14pt;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton {
    background: #0d1824;
    color: #c9eff8;
    border: 1px solid #1d4053;
    border-radius: 9px;
    padding: 8px 11px;
    min-height: 18px;
    font-weight: 600;
}
QPushButton:hover {
    background: #102738;
    border: 1px solid #35d9ff;
    color: #ffffff;
}
QPushButton:pressed {
    background: #12384a;
    border: 1px solid #76edff;
    padding-top: 9px;
    padding-left: 12px;
}
QPushButton:checked {
    background: #123446;
    border: 1px solid #00eaff;
    color: #8ff5ff;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background: #060b12;
    color: #dff8ff;
    border: 1px solid #1b3b4d;
    border-radius: 10px;
    padding: 9px;
    selection-background-color: #15566d;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #25dfff;
}

QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background: #0a121c;
    color: #dff8ff;
    border: 1px solid #245066;
    selection-background-color: #123d50;
}

QCheckBox {
    color: #bcdce7;
    spacing: 8px;
    padding: 3px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #28556a;
    background: #071019;
}
QCheckBox::indicator:checked {
    background: #0aa8c5;
    border: 1px solid #67efff;
}

QProgressBar {
    background: #050a10;
    border: 1px solid #173749;
    border-radius: 7px;
    text-align: center;
    color: #dffaff;
    min-height: 10px;
}
QProgressBar::chunk {
    background: #08bfdc;
    border-radius: 6px;
}

QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: #070d14;
    width: 9px;
    margin: 4px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #1c5267;
    min-height: 35px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #28cde9;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QTableWidget {
    background: #070d15;
    alternate-background-color: #0a121c;
    color: #ccebf4;
    border: 1px solid #19394b;
    border-radius: 10px;
    gridline-color: #102a39;
}
QHeaderView::section {
    background: #0c1b28;
    color: #72eaff;
    border: none;
    border-bottom: 1px solid #1a4255;
    padding: 7px;
    font-weight: 700;
}

QTextEdit {
    line-height: 1.55;
}

QToolTip {
    background: #08141e;
    color: #dffaff;
    border: 1px solid #28cde9;
    padding: 6px 8px;
    border-radius: 6px;
}
"""


def apply_theme(app):
    """Apply the visual layer once, without changing functionality."""
    if app.property("jarvis_neo_premium_theme"):
        return
    app.setStyleSheet(app.styleSheet() + "\n" + NEO_STYLE)
    app.setFont(QFont("Segoe UI", 10))
    app.setProperty("jarvis_neo_premium_theme", True)
