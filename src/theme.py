"""Verdant design tokens – single source of truth for all colours and metrics."""

# ── Colour palette ────────────────────────────────────────────────────────
BG          = "#0d1a13"   # oklch(0.11 0.035 155)  main background
SURFACE     = "#112018"   # oklch(0.15 0.04  155)  sidebar / panels
SURFACE2    = "#162618"   # oklch(0.18 0.04  155)  secondary surfaces
SURFACE3    = "#1c2e1e"   # oklch(0.22 0.045 155)  hover / active elements
BORDER      = "#22361f"   # oklch(0.26 0.05  155)  dividers
ACCENT      = "#3dba6a"   # oklch(0.62 0.18  155)  primary green
ACCENT2     = "#5edd82"   # oklch(0.72 0.20  150)  lighter green
ACCENT_DIM  = "#1a3d26"   # accent at ~15% opacity on BG
TEXT        = "#e4efe6"   # oklch(0.93 0.02  155)  primary text
TEXT_BODY   = "#c8dccb"   # oklch(0.82 0.02  155)  body text
MUTED       = "#7a9680"   # oklch(0.60 0.04  155)  secondary / labels
DANGER      = "#b94040"
WARN        = "#c49a28"

# Highlight annotation colours (RGBA tuples for QColor)
HL_GREEN  = (61,  186, 106, 110)
HL_YELLOW = (196, 154,  40, 110)
HL_RED    = (185,  64,  64, 110)

# ── Layout metrics ────────────────────────────────────────────────────────
SIDENAV_W    = 52
LEFT_W       = 240
LEFT_SM_W    = 220
RIGHT_W      = 220
TOOLBAR_H    = 46
STATUSBAR_H  = 26
PAGE_RADIUS  = 6
PAGE_MARGIN  = 32   # viewer padding

# ── Font families ─────────────────────────────────────────────────────────
FONT_UI   = "'DM Sans', 'Segoe UI', Arial, sans-serif"
FONT_MONO = "'DM Mono', 'Consolas', 'Courier New', monospace"


def _scrollbar(w: int = 5) -> str:
    return (
        f"QScrollBar:vertical{{background:{BG};width:{w}px;margin:0;}}"
        f"QScrollBar::handle:vertical{{background:{BORDER};border-radius:{w//2}px;min-height:20px;}}"
        f"QScrollBar::handle:vertical:hover{{background:{MUTED};}}"
        f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
        f"QScrollBar:horizontal{{background:{BG};height:{w}px;margin:0;}}"
        f"QScrollBar::handle:horizontal{{background:{BORDER};border-radius:{w//2}px;min-width:20px;}}"
        f"QScrollBar::handle:horizontal:hover{{background:{MUTED};}}"
        f"QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{{width:0;}}"
    )


APP_STYLE = f"""
* {{
    font-family: 'DM Sans', 'Segoe UI', Arial, sans-serif;
    font-size: 11px;
    color: {TEXT};
}}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget {{ background: {BG}; color: {TEXT}; }}
QToolTip {{
    background: {SURFACE2}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 4px; padding: 4px 8px; font-size: 10px;
}}
QMenu {{
    background: {SURFACE}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 6px; padding: 4px;
}}
QMenu::item {{ padding: 6px 14px; border-radius: 4px; }}
QMenu::item:selected {{ background: {SURFACE3}; }}
QMenu::separator {{ background: {BORDER}; margin: 4px 8px; height: 1px; }}
QMenuBar {{ background: {SURFACE}; color: {TEXT}; border-bottom: 1px solid {BORDER}; padding: 1px; }}
QMenuBar::item {{ padding: 4px 8px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: {SURFACE3}; }}
QSplitter::handle {{ background: {BORDER}; width: 1px; height: 1px; }}
QMessageBox {{ background: {SURFACE}; }}
QMessageBox QPushButton {{
    background: {ACCENT}; color: {BG}; border: none; border-radius: 6px; padding: 6px 16px;
    font-weight: 600;
}}
QMessageBox QPushButton:hover {{ background: {ACCENT2}; }}
QFileDialog {{ background: {SURFACE}; }}
""" + _scrollbar()
