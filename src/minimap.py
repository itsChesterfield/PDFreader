"""Floating minimap — bottom-right corner of the PDF viewer."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QWidget

from .theme import ACCENT, ACCENT_DIM, BG, BORDER, MUTED, SURFACE2

if TYPE_CHECKING:
    from .pdf_document import PDFDocument

_THUMB_W = 22
_THUMB_H = 30
_GAP = 4
_PADDING = 8
_ZOOM = 36 / 72   # low-res render zoom


class _Thumb(QLabel):
    clicked = pyqtSignal(int)   # page_num

    def __init__(self, page_num: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = page_num
        self.setFixedSize(_THUMB_W, _THUMB_H)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"background:{SURFACE2};border:1px solid {BORDER};border-radius:4px;"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool) -> None:
        border_color = ACCENT if active else BORDER
        bg = ACCENT_DIM if active else SURFACE2
        self.setStyleSheet(
            f"background:{bg};border:1px solid {border_color};border-radius:4px;"
        )

    def set_pixmap_data(self, data: bytes) -> None:
        px = QPixmap()
        px.loadFromData(data)
        self.setPixmap(px.scaled(
            _THUMB_W - 2, _THUMB_H - 2,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def mousePressEvent(self, _ev) -> None:
        self.clicked.emit(self._page)


class MiniMap(QWidget):
    """Shows up to 6 page thumbnails; clicking navigates there."""

    page_selected = pyqtSignal(int)

    _MAX_THUMBS = 6

    def __init__(self, doc: "PDFDocument", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self._thumbs: list[_Thumb] = []
        self._center: int = 0

        self.setStyleSheet(
            f"background:{SURFACE2};border:1px solid {BORDER};"
            f"border-radius:8px;padding:{_PADDING}px;"
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 130))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(_PADDING, _PADDING, _PADDING, _PADDING)
        self._layout.setSpacing(_GAP)

    # ------------------------------------------------------------------
    def load_document(self) -> None:
        for t in self._thumbs:
            self._layout.removeWidget(t)
            t.deleteLater()
        self._thumbs.clear()

        n = min(self._MAX_THUMBS, self._doc.page_count)
        for i in range(n):
            t = _Thumb(i)
            t.clicked.connect(self.page_selected)
            self._layout.addWidget(t)
            self._thumbs.append(t)
            # Render lazily
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(i * 30, lambda idx=i: self._render(idx))

        self.adjustSize()

    def set_current_page(self, page: int) -> None:
        self._center = page
        self._update_visible()

    def _update_visible(self) -> None:
        n = self._doc.page_count
        count = len(self._thumbs)
        half = count // 2
        start = max(0, min(self._center - half, n - count))

        for local_i, thumb in enumerate(self._thumbs):
            global_page = start + local_i
            thumb._page = global_page
            thumb.set_active(global_page == self._center)
            data = self._doc.render_page(global_page, zoom=_ZOOM)
            if data:
                thumb.set_pixmap_data(data)

    def _render(self, local_idx: int) -> None:
        if local_idx >= len(self._thumbs):
            return
        t = self._thumbs[local_idx]
        data = self._doc.render_page(t._page, zoom=_ZOOM)
        if data:
            t.set_pixmap_data(data)
