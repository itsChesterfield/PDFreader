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
    QLabel,
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
    PAGE_BG_COLOR,
    PAGE_MARGIN,
    Tool,
)

if TYPE_CHECKING:
    from .pdf_document import PDFDocument


# ---------------------------------------------------------------------------
# Single-page widget
# ---------------------------------------------------------------------------

class PDFPageWidget(QWidget):
    """Renders one PDF page and handles annotation mouse interactions."""

    annotation_added = pyqtSignal(int)   # page_num

    def __init__(self, doc: "PDFDocument", page_num: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self._page_num = page_num
        self._zoom: float = DEFAULT_ZOOM
        self._pixmap: Optional[QPixmap] = None
        self._rendered = False

        self._tool: Tool = Tool.SELECT
        self._highlight_color_name: str = "Gelb"

        # Selection state (highlight / search overlay)
        self._sel_active = False
        self._sel_start: Optional[QPoint] = None
        self._sel_end: Optional[QPoint] = None

        # Search highlights to draw as overlays
        self._search_rects: list[tuple[float, float, float, float]] = []

        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

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
        """rects: list of fitz.Rect (PDF coordinate space)."""
        scale = self._doc._scale(self._zoom)
        self._search_rects = [
            (r.x0 * scale, r.y0 * scale, r.x1 * scale, r.y1 * scale)
            for r in rects
        ]
        self.update()

    def invalidate(self) -> None:
        """Force re-render (e.g. after annotation added)."""
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
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Lädt...")

        # Draw live selection rect
        if self._sel_active and self._sel_start and self._sel_end:
            r = self._sel_qrect()
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(0, 120, 215, 40))
            painter.drawRect(r)

        # Draw search highlights
        for (x0, y0, x1, y1) in self._search_rects:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 160, 0, 120))
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
    # Annotation actions
    # ------------------------------------------------------------------

    def _apply_highlight(self, rect: QRect) -> None:
        color = HIGHLIGHT_QT_COLORS.get(self._highlight_color_name, (255, 255, 0, 140))
        fitz_color = (color[0] / 255, color[1] / 255, color[2] / 255)
        widget_rect = (
            float(rect.x()), float(rect.y()),
            float(rect.x() + rect.width()), float(rect.y() + rect.height()),
        )
        ok = self._doc.add_highlight(self._page_num, widget_rect, self._zoom, fitz_color)
        if ok:
            self.invalidate()
            self.annotation_added.emit(self._page_num)

    def _request_freetext(self, pos: QPoint) -> None:
        from .dialogs import TextAnnotDialog
        dlg = TextAnnotDialog(self)
        if dlg.exec():
            text, size = dlg.result_text, dlg.result_size
            if text.strip():
                ok = self._doc.add_freetext(
                    self._page_num, (float(pos.x()), float(pos.y())), self._zoom, text, size
                )
                if ok:
                    self.invalidate()
                    self.annotation_added.emit(self._page_num)

    def _request_note(self, pos: QPoint) -> None:
        from .dialogs import NoteDialog
        dlg = NoteDialog(self)
        if dlg.exec():
            content = dlg.result_text
            if content.strip():
                ok = self._doc.add_note(
                    self._page_num, (float(pos.x()), float(pos.y())), self._zoom, content
                )
                if ok:
                    self.invalidate()
                    self.annotation_added.emit(self._page_num)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _sel_qrect(self) -> QRect:
        if not self._sel_start or not self._sel_end:
            return QRect()
        x0 = min(self._sel_start.x(), self._sel_end.x())
        y0 = min(self._sel_start.y(), self._sel_end.y())
        x1 = max(self._sel_start.x(), self._sel_end.x())
        y1 = max(self._sel_start.y(), self._sel_end.y())
        return QRect(x0, y0, x1 - x0, y1 - y0)


# ---------------------------------------------------------------------------
# Scroll-based multi-page viewer
# ---------------------------------------------------------------------------

class PDFViewer(QScrollArea):
    """Displays all PDF pages stacked vertically with lazy rendering."""

    page_changed = pyqtSignal(int)        # current visible page (0-based)
    annotation_added = pyqtSignal(int)    # page_num

    def __init__(self, doc: "PDFDocument", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self._zoom: float = DEFAULT_ZOOM
        self._tool: Tool = Tool.SELECT
        self._highlight_color: str = "Gelb"
        self._pages: list[PDFPageWidget] = []
        self._current_page: int = 0

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, PAGE_MARGIN, 0, PAGE_MARGIN)
        self._layout.setSpacing(PAGE_MARGIN)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._container.setStyleSheet(f"background: {PAGE_BG_COLOR};")

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setStyleSheet(f"QScrollArea {{ background: {PAGE_BG_COLOR}; border: none; }}")

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # Debounce lazy-render checks
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(80)
        self._render_timer.timeout.connect(self._render_visible)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_document(self) -> None:
        """Rebuild the page list for the currently open document."""
        self._clear()
        for i in range(self._doc.page_count):
            pw = PDFPageWidget(self._doc, i)
            pw.set_zoom(self._zoom)
            pw.set_tool(self._tool)
            pw.set_highlight_color(self._highlight_color)
            pw.annotation_added.connect(self.annotation_added)
            self._layout.addWidget(pw, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._pages.append(pw)
        # Render first two pages immediately
        QTimer.singleShot(0, lambda: self._render_range(0, min(2, len(self._pages))))

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        # Remember scroll ratio so we can restore position
        vbar = self.verticalScrollBar()
        total = vbar.maximum() or 1
        ratio = vbar.value() / total
        for pw in self._pages:
            pw.set_zoom(self._zoom)
        self._container.adjustSize()
        # Restore approximate scroll position
        QTimer.singleShot(10, lambda: self._restore_scroll(ratio))
        self._render_timer.start()

    def set_tool(self, tool: Tool) -> None:
        self._tool = tool
        for pw in self._pages:
            pw.set_tool(tool)

    def set_highlight_color(self, name: str) -> None:
        self._highlight_color = name
        for pw in self._pages:
            pw.set_highlight_color(name)

    def go_to_page(self, page_num: int) -> None:
        if not self._pages or not (0 <= page_num < len(self._pages)):
            return
        pw = self._pages[page_num]
        self.ensureWidgetVisible(pw, 0, 0)

    def zoom_in(self) -> None:
        from .constants import ZOOM_STEP
        self.set_zoom(self._zoom + ZOOM_STEP)

    def zoom_out(self) -> None:
        from .constants import ZOOM_STEP
        self.set_zoom(self._zoom - ZOOM_STEP)

    def current_zoom(self) -> float:
        return self._zoom

    def show_search_results(self, results: dict[int, list]) -> None:
        for i, pw in enumerate(self._pages):
            pw.set_search_rects(results.get(i, []))

    def clear_search(self) -> None:
        for pw in self._pages:
            pw.set_search_rects([])

    def invalidate_page(self, page_num: int) -> None:
        if 0 <= page_num < len(self._pages):
            self._pages[page_num].invalidate()

    # ------------------------------------------------------------------
    # Wheel zoom (Ctrl+Scroll)
    # ------------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            from .constants import ZOOM_STEP
            if delta > 0:
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
            bottom = top + pw.height()
            overlap = max(0, min(bottom, vp_bottom) - max(top, vp_top))
            if overlap > best_overlap:
                best_overlap = overlap
                best = i
        if best != self._current_page:
            self._current_page = best
            self.page_changed.emit(best)

    def _render_visible(self) -> None:
        vp_top = self.verticalScrollBar().value()
        vp_bottom = vp_top + self.viewport().height()
        # Render pages within viewport + one page buffer above/below
        for i, pw in enumerate(self._pages):
            top = pw.mapTo(self._container, QPoint(0, 0)).y()
            bottom = top + pw.height()
            if bottom >= vp_top - pw.height() and top <= vp_bottom + pw.height():
                pw.ensure_rendered()

    def _render_range(self, start: int, end: int) -> None:
        for i in range(start, end):
            if 0 <= i < len(self._pages):
                self._pages[i].ensure_rendered()

    def _restore_scroll(self, ratio: float) -> None:
        vbar = self.verticalScrollBar()
        vbar.setValue(int(ratio * vbar.maximum()))
