from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import (
    QPoint,
    QRect,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    DEFAULT_ZOOM,
    HIGHLIGHT_QT_COLORS,
    MAX_ZOOM,
    MIN_ZOOM,
    Tool,
)
from .theme import BG as PAGE_BG_COLOR, PAGE_MARGIN, ACCENT

if TYPE_CHECKING:
    from .pdf_document import PDFDocument


# ---------------------------------------------------------------------------
# Single-page widget
# ---------------------------------------------------------------------------

class PDFPageWidget(QWidget):
    """Renders one PDF page and handles annotation mouse interactions."""

    annotation_added = pyqtSignal(int)

    def __init__(self, doc: "PDFDocument", page_num: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self._page_num = page_num
        self._zoom: float = DEFAULT_ZOOM
        self._pixmap: Optional[QPixmap] = None
        self._rendered = False

        self._tool: Tool = Tool.SELECT
        self._highlight_color_name: str = "Gelb"

        self._sel_active = False
        self._sel_start: Optional[QPoint] = None
        self._sel_end: Optional[QPoint] = None

        self._search_rects: list[tuple[float, float, float, float]] = []

        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: white;")

        # Adobe-style page drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 110))
        shadow.setOffset(2, 3)
        self.setGraphicsEffect(shadow)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        self._rendered = False
        self._pixmap = None
        w, h = self._doc.page_size_px(self._page_num, zoom)
        self.setFixedSize(w, h)
        self.update()

    def ensure_rendered(self) -> None:
        if self._rendered:
            return
        data = self._doc.render_page(self._page_num, self._zoom)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            self._pixmap = px
            self.setFixedSize(px.size())
        self._rendered = True
        self.update()

    def set_tool(self, tool: Tool) -> None:
        self._tool = tool
        cursors = {
            Tool.SELECT:    Qt.CursorShape.ArrowCursor,
            Tool.HIGHLIGHT: Qt.CursorShape.CrossCursor,
            Tool.TEXT:      Qt.CursorShape.IBeamCursor,
            Tool.NOTE:      Qt.CursorShape.PointingHandCursor,
        }
        self.setCursor(QCursor(cursors.get(tool, Qt.CursorShape.ArrowCursor)))

    def set_highlight_color(self, name: str) -> None:
        self._highlight_color_name = name

    def set_search_rects(self, rects: list) -> None:
        scale = self._doc._scale(self._zoom)
        self._search_rects = [
            (r.x0 * scale, r.y0 * scale, r.x1 * scale, r.y1 * scale)
            for r in rects
        ]
        self.update()

    def invalidate(self) -> None:
        self._rendered = False
        self._pixmap = None
        self.ensure_rendered()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)

        if self._pixmap:
            painter.drawPixmap(0, 0, self._pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#ffffff"))
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Laedt...")

        if self._sel_active and self._sel_start and self._sel_end:
            r = self._sel_qrect()
            painter.setPen(QPen(QColor(20, 115, 230), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(20, 115, 230, 40))
            painter.drawRect(r)

        for (x0, y0, x1, y1) in self._search_rects:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 160, 0, 130))
            painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0).toRect())

        painter.end()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if self._tool == Tool.HIGHLIGHT:
            self._sel_active = True
            self._sel_start = pos
            self._sel_end = pos
            self.update()
        elif self._tool == Tool.TEXT:
            self._request_freetext(pos)
        elif self._tool == Tool.NOTE:
            self._request_note(pos)

    def mouseMoveEvent(self, event) -> None:
        if self._sel_active:
            self._sel_end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._sel_active:
            self._sel_active = False
            r = self._sel_qrect()
            if r.width() > 4 and r.height() > 4:
                self._apply_highlight(r)
            self._sel_start = None
            self._sel_end = None
            self.update()

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def _apply_highlight(self, rect: QRect) -> None:
        color = HIGHLIGHT_QT_COLORS.get(self._highlight_color_name, (255, 255, 0, 140))
        fitz_color = (color[0] / 255, color[1] / 255, color[2] / 255)
        widget_rect = (
            float(rect.x()), float(rect.y()),
            float(rect.x() + rect.width()), float(rect.y() + rect.height()),
        )
        if self._doc.add_highlight(self._page_num, widget_rect, self._zoom, fitz_color):
            self.invalidate()
            self.annotation_added.emit(self._page_num)

    def _request_freetext(self, pos: QPoint) -> None:
        from .dialogs import TextAnnotDialog
        dlg = TextAnnotDialog(self)
        if dlg.exec() and dlg.result_text.strip():
            if self._doc.add_freetext(
                self._page_num, (float(pos.x()), float(pos.y())),
                self._zoom, dlg.result_text, dlg.result_size
            ):
                self.invalidate()
                self.annotation_added.emit(self._page_num)

    def _request_note(self, pos: QPoint) -> None:
        from .dialogs import NoteDialog
        dlg = NoteDialog(self)
        if dlg.exec() and dlg.result_text.strip():
            if self._doc.add_note(
                self._page_num, (float(pos.x()), float(pos.y())),
                self._zoom, dlg.result_text
            ):
                self.invalidate()
                self.annotation_added.emit(self._page_num)

    def _sel_qrect(self) -> QRect:
        if not self._sel_start or not self._sel_end:
            return QRect()
        x0 = min(self._sel_start.x(), self._sel_end.x())
        y0 = min(self._sel_start.y(), self._sel_end.y())
        x1 = max(self._sel_start.x(), self._sel_end.x())
        y1 = max(self._sel_start.y(), self._sel_end.y())
        return QRect(x0, y0, x1 - x0, y1 - y0)


# ---------------------------------------------------------------------------
# Background container with ambient glow
# ---------------------------------------------------------------------------

class _GlowContainer(QWidget):
    """Dark green background with a subtle central ambient glow."""

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(PAGE_BG_COLOR))

        # Ambient glow: large radial gradient in the centre
        from PyQt6.QtGui import QRadialGradient
        cx, cy = self.width() // 2, min(self.height() // 3, 400)
        grad = QRadialGradient(cx, cy, 300)
        grad.setColorAt(0, QColor(61, 186, 106, 10))   # accent at 4 %
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - 300, cy - 300, 600, 600)
        p.end()


# ---------------------------------------------------------------------------
# Multi-page scroll viewer
# ---------------------------------------------------------------------------

class PDFViewer(QScrollArea):
    """Displays all PDF pages stacked vertically with lazy rendering."""

    page_changed = pyqtSignal(int)
    annotation_added = pyqtSignal(int)
    zoom_changed = pyqtSignal(float)

    def __init__(self, doc: "PDFDocument", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self._zoom: float = DEFAULT_ZOOM
        self._tool: Tool = Tool.SELECT
        self._highlight_color: str = "Gelb"
        self._pages: list[PDFPageWidget] = []
        self._current_page: int = 0

        self._container = _GlowContainer()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(48, PAGE_MARGIN + 10, 48, PAGE_MARGIN + 10)
        self._layout.setSpacing(PAGE_MARGIN + 8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setStyleSheet(
            f"QScrollArea {{ background: {PAGE_BG_COLOR}; border: none; }}"
            f"QScrollBar:vertical {{ background: {PAGE_BG_COLOR}; width: 5px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: #22361f; border-radius: 2px; min-height: 20px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: #7a9680; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
            f"QScrollBar:horizontal {{ background: {PAGE_BG_COLOR}; height: 5px; margin: 0; }}"
            f"QScrollBar::handle:horizontal {{ background: #22361f; border-radius: 2px; min-width: 20px; }}"
            f"QScrollBar::handle:horizontal:hover {{ background: #7a9680; }}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}"
        )

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(80)
        self._render_timer.timeout.connect(self._render_visible)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_document(self) -> None:
        self._clear()
        for i in range(self._doc.page_count):
            pw = PDFPageWidget(self._doc, i)
            pw.set_zoom(self._zoom)
            pw.set_tool(self._tool)
            pw.set_highlight_color(self._highlight_color)
            pw.annotation_added.connect(self.annotation_added)
            self._layout.addWidget(pw, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._pages.append(pw)
        QTimer.singleShot(0, lambda: self._render_range(0, min(2, len(self._pages))))

    def set_zoom(self, zoom: float) -> None:
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        if abs(zoom - self._zoom) < 0.001:
            return
        vbar = self.verticalScrollBar()
        ratio = vbar.value() / (vbar.maximum() or 1)
        self._zoom = zoom
        for pw in self._pages:
            pw.set_zoom(zoom)
        self._container.adjustSize()
        QTimer.singleShot(10, lambda: self._restore_scroll(ratio))
        self._render_timer.start()
        self.zoom_changed.emit(zoom)

    def set_tool(self, tool: Tool) -> None:
        self._tool = tool
        for pw in self._pages:
            pw.set_tool(tool)

    def set_highlight_color(self, name: str) -> None:
        self._highlight_color = name
        for pw in self._pages:
            pw.set_highlight_color(name)

    def go_to_page(self, page_num: int) -> None:
        if self._pages and 0 <= page_num < len(self._pages):
            self.ensureWidgetVisible(self._pages[page_num], 0, 20)

    def fit_width(self) -> None:
        if not self._doc.is_open or not self._pages:
            return
        w, _ = self._doc.page_size_px(0, zoom=1.0)
        if w <= 0:
            return
        vp_w = self.viewport().width() - 48   # margins + scrollbar
        self.set_zoom(max(MIN_ZOOM, min(MAX_ZOOM, vp_w / w)))

    def fit_page(self) -> None:
        if not self._doc.is_open or not self._pages:
            return
        w, h = self._doc.page_size_px(self._current_page, zoom=1.0)
        if w <= 0 or h <= 0:
            return
        vp_w = self.viewport().width() - 48
        vp_h = self.viewport().height() - 28
        self.set_zoom(max(MIN_ZOOM, min(MAX_ZOOM, min(vp_w / w, vp_h / h))))

    def zoom_in(self) -> None:
        from .constants import ZOOM_STEP
        self.set_zoom(self._zoom + ZOOM_STEP)

    def zoom_out(self) -> None:
        from .constants import ZOOM_STEP
        self.set_zoom(self._zoom - ZOOM_STEP)

    def current_zoom(self) -> float:
        return self._zoom

    def current_page(self) -> int:
        return self._current_page

    def show_search_results(self, results: dict[int, list]) -> None:
        for i, pw in enumerate(self._pages):
            pw.set_search_rects(results.get(i, []))

    def clear_search(self) -> None:
        for pw in self._pages:
            pw.set_search_rects([])

    # ------------------------------------------------------------------
    # Ctrl+Scroll zoom
    # ------------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            from .constants import ZOOM_STEP
            if event.angleDelta().y() > 0:
                self.set_zoom(self._zoom + ZOOM_STEP)
            else:
                self.set_zoom(self._zoom - ZOOM_STEP)
            event.accept()
        else:
            super().wheelEvent(event)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear(self) -> None:
        for pw in self._pages:
            self._layout.removeWidget(pw)
            pw.deleteLater()
        self._pages.clear()
        self._current_page = 0

    def _on_scroll(self, _value: int) -> None:
        self._update_current_page()
        self._render_timer.start()

    def _update_current_page(self) -> None:
        vp_top = self.verticalScrollBar().value()
        vp_bottom = vp_top + self.viewport().height()
        best = self._current_page
        best_overlap = 0
        for i, pw in enumerate(self._pages):
            top = pw.mapTo(self._container, QPoint(0, 0)).y()
            overlap = max(0, min(top + pw.height(), vp_bottom) - max(top, vp_top))
            if overlap > best_overlap:
                best_overlap = overlap
                best = i
        if best != self._current_page:
            self._current_page = best
            self.page_changed.emit(best)

    def _render_visible(self) -> None:
        vp_top = self.verticalScrollBar().value()
        vp_bottom = vp_top + self.viewport().height()
        for pw in self._pages:
            top = pw.mapTo(self._container, QPoint(0, 0)).y()
            if top + pw.height() >= vp_top - pw.height() and top <= vp_bottom + pw.height():
                pw.ensure_rendered()

    def _render_range(self, start: int, end: int) -> None:
        for i in range(start, min(end, len(self._pages))):
            self._pages[i].ensure_rendered()

    def _restore_scroll(self, ratio: float) -> None:
        vbar = self.verticalScrollBar()
        vbar.setValue(int(ratio * vbar.maximum()))
