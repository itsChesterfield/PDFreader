from enum import Enum, auto


class Tool(Enum):
    SELECT    = auto()
    HIGHLIGHT = auto()
    TEXT      = auto()
    NOTE      = auto()


# Verdant highlight colours (fitz RGB 0-1 tuples)
HIGHLIGHT_COLORS = {
    "Gruen":  (0.24, 0.73, 0.42),   # accent green
    "Gelb":   (0.77, 0.60, 0.16),   # warn yellow
    "Rot":    (0.73, 0.25, 0.25),   # danger red
}

# Qt RGBA tuples for on-screen selection overlay
HIGHLIGHT_QT_COLORS = {
    "Gruen":  ( 61, 186, 106, 110),
    "Gelb":   (196, 154,  40, 110),
    "Rot":    (185,  64,  64, 110),
    # Legacy names kept for compatibility
    "Gelb_legacy":  (255, 255,   0, 110),
    "Gruen_legacy": (  0, 230,  50, 110),
}

DEFAULT_ZOOM = 1.0
MIN_ZOOM     = 0.25
MAX_ZOOM     = 4.0
ZOOM_STEP    = 0.10

RENDER_DPI   = 150
