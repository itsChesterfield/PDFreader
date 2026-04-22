from enum import Enum, auto


class Tool(Enum):
    SELECT = auto()
    HIGHLIGHT = auto()
    TEXT = auto()
    NOTE = auto()


HIGHLIGHT_COLORS = {
    "Gelb":   (1.0, 1.0, 0.0),
    "Grün":   (0.0, 0.9, 0.2),
    "Blau":   (0.3, 0.7, 1.0),
    "Rosa":   (1.0, 0.4, 0.7),
    "Orange": (1.0, 0.6, 0.0),
}

HIGHLIGHT_QT_COLORS = {
    "Gelb":   (255, 255,   0, 140),
    "Grün":   (  0, 230,  50, 140),
    "Blau":   ( 77, 178, 255, 140),
    "Rosa":   (255, 102, 178, 140),
    "Orange": (255, 153,   0, 140),
}

DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.25
MAX_ZOOM = 4.0
ZOOM_STEP = 0.25

RENDER_DPI = 150          # Base DPI for rendering (72 * ~2.08)
PAGE_MARGIN = 12          # Vertical gap between pages in pixels
PAGE_BG_COLOR = "#525659" # Viewer background (dark grey like Adobe)
