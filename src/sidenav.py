"""Vertical navigation bar (52 px wide) with pulsing logo and tab buttons."""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QVBoxLayout, QWidget

from .theme import ACCENT, ACCENT2, ACCENT_DIM, BORDER, MUTED, SIDENAV_W, SURFACE, SURFACE3

_BTN = f"""
QPushButton {{
    background: transparent;
    color: {MUTED};
    border: none;
    border-radius: 8px;
    font-size: 17px;
    padding: 0;
}}
QPushButton:hover               {{ background: {SURFACE3}; color: {ACCENT2}; }}
QPushButton[active="true"]      {{ background: {ACCENT_DIM}; color: {ACCENT}; }}
QPushButton[active="true"]:hover{{ background: {ACCENT_DIM}; color: {ACCENT2}; }}
"""


class _Logo(QWidget):
    """32 × 32 animated green "V" logo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(61, 186, 106, 150))
        shadow.setOffset(0, 0)
        shadow.setBlurRadius(8)
        self.setGraphicsEffect(shadow)
        self._shadow = shadow

        a1 = QPropertyAnimation(shadow, b"blurRadius", self)
        a1.setStartValue(8); a1.setEndValue(22)
        a1.setDuration(1500); a1.setEasingCurve(QEasingCurve.Type.InOutSine)

        a2 = QPropertyAnimation(shadow, b"blurRadius", self)
        a2.setStartValue(22); a2.setEndValue(8)
        a2.setDuration(1500); a2.setEasingCurve(QEasingCurve.Type.InOutSine)

        seq = QSequentialAnimationGroup(self)
        seq.addAnimation(a1); seq.addAnimation(a2)
        seq.setLoopCount(-1)
        seq.start()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(ACCENT))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 8, 8)
        p.setPen(QColor("#ffffff"))
        font = QFont("DM Sans", 13)
        font.setWeight(QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "V")
        p.end()


class SideNav(QWidget):
    """Emits tab_changed(str) — empty string means "close panel"."""

    tab_changed = pyqtSignal(str)

    _TABS = [
        ("files",     "⊞",  "Dateien"),
        ("bookmarks", "◈",  "Lesezeichen"),
        ("search",    "⌕",  "Suche"),
        ("settings",  "⚙",  "Einstellungen"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(SIDENAV_W)
        self.setStyleSheet(
            f"QWidget {{ background: {SURFACE}; }}"
            f"QWidget#nav_border {{ border-right: 1px solid {BORDER}; }}"
        )
        self.setObjectName("nav_border")

        self._active: str = ""
        self._btns: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(_Logo(), alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(14)

        for tab_id, icon, tip in self._TABS:
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setToolTip(tip)
            btn.setStyleSheet(_BTN)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda _, t=tab_id: self._toggle(t))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._btns[tab_id] = btn

        layout.addStretch()

    # ------------------------------------------------------------------
    def _toggle(self, tab_id: str) -> None:
        if self._active == tab_id:
            self._active = ""
        else:
            self._active = tab_id
        self._refresh()
        self.tab_changed.emit(self._active)

    def _refresh(self) -> None:
        for tid, btn in self._btns.items():
            btn.setProperty("active", "true" if tid == self._active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_active(self, tab_id: str) -> None:
        self._active = tab_id
        self._refresh()
