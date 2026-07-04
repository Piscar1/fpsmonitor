"""Global dark professional theme (Qt stylesheet) for the whole app."""

# ---------------------------------------------------------------- palette
BG_0      = "#0B0D12"   # window background
BG_1      = "#10131C"   # panels / toolbar / graph bg
BG_2      = "#151926"   # cards / inputs
BG_3      = "#1E2433"   # hover
BORDER    = "#232A3B"   # card borders
BORDER_HI = "#2F3850"   # hover borders
TEXT      = "#E9EBF1"
TEXT_DIM  = "#8B93A7"
ACCENT    = "#2BD576"   # primary emerald
ACCENT_2  = "#38BDF8"   # secondary sky blue
WARN      = "#F5A524"
CRIT      = "#FF4D5E"
OK        = ACCENT

# Default graph curve colors (harmonized with the palette)
GRAPH_FPS = ACCENT
GRAPH_CPU = "#FF8A3D"
GRAPH_GPU = ACCENT_2

MONO = "Consolas"

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

/* ---------- Section captions & small labels ---------- */
QLabel[class="caption"] {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel[class="statLabel"] {{
    color: {TEXT_DIM};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel[class="statValue"] {{
    font-family: "{MONO}";
    font-size: 16px;
    font-weight: 600;
    color: {TEXT};
}}

/* ---------- Hero / stats cards ---------- */
QFrame#heroCard, QFrame#statsCard {{
    background-color: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}

/* ---------- Metric cards ---------- */
QFrame#metricCard {{
    background-color: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#metricCard:hover {{
    border-color: {BORDER_HI};
}}
QFrame#metricCard[state="warn"] {{ border-color: rgba(245, 165, 36, 0.55); }}
QFrame#metricCard[state="crit"] {{ border-color: rgba(255, 77, 94, 0.6); }}
QLabel[class="cardTitle"] {{
    color: {TEXT_DIM};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel#fpsValue {{
    background: transparent;
}}
QLabel#statusText {{
    color: {TEXT_DIM};
    font-size: 12px;
}}

/* ---------- Toolbar ---------- */
QToolBar {{
    background: {BG_1};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 10px;
    spacing: 6px;
}}
QToolBar QToolButton {{
    background: transparent;
    color: {TEXT_DIM};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}}
QToolBar QToolButton:hover {{
    background: {BG_3};
    color: {TEXT};
}}
QToolBar QToolButton:pressed {{
    background: {BG_2};
}}
QToolBar QToolButton:checked {{
    background: rgba(43, 213, 118, 0.12);
    border-color: rgba(43, 213, 118, 0.35);
    color: {ACCENT};
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 6px 8px;
}}

/* ---------- GroupBox / metric cards ---------- */
QGroupBox {{
    background: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox:hover {{
    border-color: {BORDER_HI};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 6px;
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QGroupBox[state="warn"] {{ border: 1px solid rgba(245, 165, 36, 0.55); }}
QGroupBox[state="warn"]::title {{ color: {WARN}; }}
QGroupBox[state="crit"] {{ border: 1px solid rgba(255, 77, 94, 0.6); }}
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
    border-color: {BORDER_HI};
}}
QPushButton:pressed {{
    background: {BG_1};
}}
QPushButton:default {{
    background: {ACCENT};
    color: #06120B;
    border: 1px solid {ACCENT};
}}
QPushButton:default:hover {{
    background: #3BE68A;
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
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}

/* ---------- Inputs ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_1};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 9px;
    selection-background-color: {ACCENT};
    selection-color: #06120B;
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: {BORDER_HI};
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
    border-radius: 8px;
    selection-background-color: {BG_3};
    selection-color: {TEXT};
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {BG_3};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 4px solid {TEXT_DIM};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {TEXT_DIM};
}}

/* ---------- Checkboxes ---------- */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {BORDER_HI};
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
QScrollBar::handle:vertical:hover {{ background: {BORDER_HI}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BG_3}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {BORDER_HI}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------- Tooltips / menus ---------- */
QToolTip {{
    background: {BG_2};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    border-radius: 6px;
    padding: 5px 9px;
}}
QMenu {{
    background: {BG_2};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{ padding: 7px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {BG_3}; color: {TEXT}; }}
QMenu::separator {{
    height: 1px; background: {BORDER}; margin: 5px 8px;
}}
"""


def apply(app):
    app.setStyleSheet(QSS)
