from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from .pdf_document import PDFDocument

THUMB_WIDTH = 120
THUMB_DPI = 36  # low-res for thumbnails


class ThumbnailPanel(QWidget):
    """Sidebar showing clickable page thumbnails."""

    page_selected = pyqtSignal(int)  # 0-based page number

    def __init__(self, doc: "PDFDocument", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc

        self._list = QListWidget()
        self._list.setFixedWidth(THUMB_WIDTH + 24)
        self._list.setSpacing(4)
        self._list.setIconSize(__import__("PyQt6.QtCore", fromlist=["QSize"]).QSize(THUMB_WIDTH, 180))
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setStyleSheet(
            "QListWidget { background: #3c3f41; border: none; }"
            "QListWidget::item { color: #cccccc; padding: 4px; border-radius: 3px; }"
            "QListWidget::item:selected { background: #4b6eaf; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_document(self) -> None:
        self._list.clear()
        for i in range(self._doc.page_count):
            item = QListWidgetItem(f"  {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list.addItem(item)
            # Render thumb lazily via a single-shot timer
            __import__("PyQt6.QtCore", fromlist=["QTimer"]).QTimer.singleShot(
                i * 30, lambda idx=i: self._render_thumb(idx)
            )

    def set_current_page(self, page_num: int) -> None:
        self._list.setCurrentRow(page_num)

    def refresh_page(self, page_num: int) -> None:
        self._render_thumb(page_num)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _render_thumb(self, page_num: int) -> None:
        if not self._doc.is_open:
            return
        item = self._list.item(page_num)
        if item is None:
            return
        data = self._doc.render_page(page_num, zoom=THUMB_DPI / 72.0)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            scaled = px.scaledToWidth(
                THUMB_WIDTH, Qt.TransformationMode.SmoothTransformation
            )
            from PyQt6.QtGui import QIcon
            item.setIcon(QIcon(scaled))

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        page_num = item.data(Qt.ItemDataRole.UserRole)
        self.page_selected.emit(page_num)
