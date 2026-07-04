"""Global dark 'gaming' theme (Qt stylesheet) for the whole app."""

# Palette
BG_0      = "#0e0e16"   # window background
BG_1      = "#16161f"   # panels / toolbar
BG_2      = "#1d1d2b"   # cards / inputs
BG_3      = "#26263a"   # hover / borders
BORDER    = "#2c2c40"
TEXT      = "#E6E6EF"
TEXT_DIM  = "#8A8AA0"
ACCENT    = "#00E676"   # primary green
ACCENT_2  = "#22C3FF"   # secondary cyan
WARN      = "#FFB020"
CRIT      = "#FF5252"

QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QDialog, QWidget#central {{
    background-color: {BG_0};
}}

QDialog {{
    background-color: {BG_0};
}}

/* ---------- Toolbar ---------- */
QToolBar {{
    background: {BG_1};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    spacing: 6px;
}}
QToolBar QToolButton {{
    background: {BG_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}}
QToolBar QToolButton:hover {{
    background: {BG_3};
    border-color: {ACCENT};
    color: {ACCENT};
}}
QToolBar QToolButton:checked {{
    background: rgba(0, 230, 118, 0.15);
    border-color: {ACCENT};
    color: {ACCENT};
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 4px 6px;
}}

/* ---------- GroupBox / metric cards ---------- */
QGroupBox {{
    background: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 16px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 6px;
    color: {ACCENT_2};
    font-size: 12px;
    font-weight: 700;
}}
QGroupBox[state="warn"] {{ border: 1px solid {WARN}; }}
QGroupBox[state="warn"]::title {{ color: {WARN}; }}
QGroupBox[state="crit"] {{ border: 1px solid {CRIT}; }}
QGroupBox[state="crit"]::title {{ color: {CRIT}; }}

QLabel {{ background: transparent; }}

/* ---------- Buttons ---------- */
QPushButton {{
    background: {BG_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {BG_3};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: rgba(0, 230, 118, 0.18);
}}
QPushButton:default {{
    background: {ACCENT};
    color: #06120b;
    border: none;
}}
QPushButton:default:hover {{
    background: #1BF086;
}}

/* ---------- Tabs ---------- */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    top: -1px;
    background: {BG_1};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 9px 18px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}

/* ---------- Inputs ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_1};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
    selection-color: #06120b;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_DIM};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 6px;
    selection-background-color: {ACCENT};
    selection-color: #06120b;
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {BG_2};
    border: none;
    width: 16px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {BG_3};
}}

/* ---------- Checkboxes ---------- */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {BORDER};
    border-radius: 5px;
    background: {BG_1};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ---------- Sliders ---------- */
QSlider::groove:horizontal {{
    height: 5px;
    background: {BG_3};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {TEXT};
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT}; }}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BG_3}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BG_3}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------- Tooltips / menus ---------- */
QToolTip {{
    background: {BG_2};
    color: {TEXT};
    border: 1px solid {ACCENT};
    border-radius: 6px;
    padding: 4px 8px;
}}
QMenu {{
    background: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{ padding: 6px 20px; border-radius: 6px; }}
QMenu::item:selected {{ background: {BG_3}; color: {ACCENT}; }}
"""


def apply(app):
    app.setStyleSheet(QSS)
