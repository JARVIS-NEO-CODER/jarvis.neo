"""Premium visual theme for J.A.R.V.I.S. NEO.

Presentation-only layer. Existing widgets, buttons and command handlers stay
intact. The style is applied to both QApplication and the real Jarvis window.
"""

from PyQt6.QtGui import QFont

NEO_STYLE = r"""
/* ===== J.A.R.V.I.S. NEO // PREMIUM HUD ===== */
QMainWindow, QWidget { background: #05080f; color: #d9f7ff; font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; }
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #04070d, stop:.48 #09121d, stop:1 #050b13); border: 1px solid #2ad9f5; }
QFrame#MainFrame, QFrame#LeftPanel, QFrame#RightPanel, QFrame#DynamicSpace, QFrame#CommandDeck { background: #07101b; border: 1px solid #173f54; border-radius: 16px; }
QFrame#DynamicSpace { background: #07111b; border: 1px solid #25bcd8; }
QFrame#CommandDeck { border: 1px solid #1e566c; border-radius: 14px; }
QLabel { color: #b9d9e6; background: transparent; }
QLabel#titleLabel, QLabel#headerLabel { color: #7eeeff; font-size: 14pt; font-weight: 800; letter-spacing: 1px; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #122331, stop:1 #0a141f); color: #d2f7ff; border: 1px solid #205169; border-radius: 10px; padding: 8px 12px; min-height: 18px; font-weight: 700; }
QPushButton:hover { background: #123347; border: 1px solid #42e5ff; color: #ffffff; }
QPushButton:pressed { background: #0b5368; border: 1px solid #8af3ff; }
QPushButton:checked { background: #10485a; border: 1px solid #00eaff; color: #9af7ff; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox { background: #050b12; color: #e4faff; border: 1px solid #1d4659; border-radius: 11px; padding: 9px; selection-background-color: #15566d; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #25dfff; }
QComboBox::drop-down { border: 0; width: 28px; }
QComboBox QAbstractItemView { background: #08121d; color: #dff8ff; border: 1px solid #245066; selection-background-color: #123d50; }
QCheckBox { color: #bcdce7; spacing: 8px; padding: 3px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #28556a; background: #071019; }
QCheckBox::indicator:checked { background: #0aa8c5; border: 1px solid #67efff; }
QProgressBar { background: #050a10; border: 1px solid #173749; border-radius: 7px; text-align: center; color: #dffaff; min-height: 10px; }
QProgressBar::chunk { background: #08bfdc; border-radius: 6px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #050b12; width: 9px; margin: 4px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #1c6278; min-height: 35px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #28cde9; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QTableWidget { background: #070d15; alternate-background-color: #0a121c; color: #ccebf4; border: 1px solid #19394b; border-radius: 10px; gridline-color: #102a39; }
QHeaderView::section { background: #0c1b28; color: #72eaff; border: none; border-bottom: 1px solid #1a4255; padding: 7px; font-weight: 700; }
QToolTip { background: #08141e; color: #dffaff; border: 1px solid #28cde9; padding: 6px 8px; border-radius: 6px; }
"""

def apply_theme(app, window=None):
    """Apply the premium visual layer to the actual running window."""
    if not app.property("jarvis_neo_premium_theme"):
        app.setStyleSheet(app.styleSheet() + "\n" + NEO_STYLE)
        app.setFont(QFont("Segoe UI", 10))
        app.setProperty("jarvis_neo_premium_theme", True)
    if window is not None:
        window.setStyleSheet(window.styleSheet() + "\n" + NEO_STYLE)
        window.update()
