"""Premium visual theme for J.A.R.V.I.S. NEO.

Presentation-only layer. Existing widgets, buttons and command handlers stay
intact. The style is applied to both QApplication and the real Jarvis window.
"""

from PyQt6.QtGui import QFont

NEO_STYLE = r"""
/* ===== J.A.R.V.I.S. NEO // PREMIUM HUD ===== */
QMainWindow, QWidget { background: #090a0e; color: #e8eaf0; font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; }
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #090a0e, stop:.48 #15151b, stop:1 #0d0e13); border: 1px solid #ff7043; }
QFrame#MainFrame, QFrame#LeftPanel, QFrame#RightPanel, QFrame#DynamicSpace, QFrame#CommandDeck { background: #111218; border: 1px solid #38333a; border-radius: 16px; }
QFrame#DynamicSpace { background: #111218; border: 1px solid #ff7043; }
QFrame#CommandDeck { border: 1px solid #38333a; border-radius: 14px; }
QLabel { color: #b9bdc7; background: transparent; }
QLabel#titleLabel, QLabel#headerLabel { color: #ff8a65; font-size: 14pt; font-weight: 800; letter-spacing: 1px; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #21171a, stop:1 #15161c); color: #f5c8bb; border: 1px solid #514047; border-radius: 10px; padding: 8px 12px; min-height: 18px; font-weight: 700; }
QPushButton:hover { background: #2a1b19; border: 1px solid #ff8a65; color: #ffffff; }
QPushButton:pressed { background: #6b3527; border: 1px solid #ffb199; }
QPushButton:checked { background: #33201d; border: 1px solid #ff7043; color: #ffe0d5; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox { background: #0d0e13; color: #e8eaf0; border: 1px solid #38333a; border-radius: 11px; padding: 9px; selection-background-color: #6b3527; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #ff7043; }
QComboBox::drop-down { border: 0; width: 28px; }
QComboBox QAbstractItemView { background: #111218; color: #e8eaf0; border: 1px solid #514047; selection-background-color: #33201d; }
QCheckBox { color: #b9bdc7; spacing: 8px; padding: 3px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #514047; background: #0d0e13; }
QCheckBox::indicator:checked { background: #ff7043; border: 1px solid #ffb199; }
QProgressBar { background: #0d0e13; border: 1px solid #38333a; border-radius: 7px; text-align: center; color: #e8eaf0; min-height: 10px; }
QProgressBar::chunk { background: #ff7043; border-radius: 6px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #0d0e13; width: 9px; margin: 4px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #6b3527; min-height: 35px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #ff8a65; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QTableWidget { background: #111218; alternate-background-color: #171820; color: #e8eaf0; border: 1px solid #38333a; border-radius: 10px; gridline-color: #25262d; }
QHeaderView::section { background: #171820; color: #ff8a65; border: none; border-bottom: 1px solid #38333a; padding: 7px; font-weight: 700; }
QToolTip { background: #111218; color: #e8eaf0; border: 1px solid #ff8a65; padding: 6px 8px; border-radius: 6px; }
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
