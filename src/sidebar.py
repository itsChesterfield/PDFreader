"""Tabbed sidebar: page thumbnails + PDF bookmarks / TOC."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from .pdf_document import PDFDocument

THUMB_W = 112
THUMB_ZOOM = 36 / 72   # Low-res zoom for thumbnails

_STYLE = """
QTabWidget::pane  { border: none; background: #282828; }
QTabBar            { background: #282828; }
QTabBar::tab {
    background: #333333;
    color: #999999;
    padding: 6px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    min-width: 70px;
}
QTabBar::tab:selected {
    color: #EEEEEE;
    border-bottom: 2px solid #1473E6;
    background: #282828;
}
QTabBar::tab:hover:!selected { color: #CCCCCC; background: #2F2F2F; }

QListWidget {
    background: #282828;
    border: none;
    outline: none;
}
QListWidget::item {
    color: #AAAAAA;
    padding: 3px 0px;
    font-size: 11px;
    text-align: center;
}
QListWidget::item:selected { background: #1473E6; color: white; }
QListWidget::item:hover:!selected { background: #353535; }

QTreeWidget {
    background: #282828;
    border: none;
    color: #CCCCCC;
    outline: none;
    font-size: 12px;
}
QTreeWidget::item { padding: 4px 2px; border-radius: 2px; }
QTreeWidget::item:selected { background: #1473E6; color: white; }
QTreeWidget::item:hover:!selected { background: #353535; }
QTreeWidget::branch { background: transparent; }

QLabel#empty { color: #666666; font-size: 12px; padding: 20px; }
QScrollBar:vertical {
    background: #282828; width: 6px; margin: 0;
}
QScrollBar::handle:vertical { background: #555555; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #777777; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class _ThumbnailList(QListWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, doc: "PDFDocument", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self.setViewMode(QListWidget.ViewMode.ListMode)
        from PyQt6.QtCore import QSize
        self.setIconSize(QSize(THUMB_W, 160))
        self.setFixedWidth(THUMB_W + 28)
        self.setSpacing(3)
        self.itemClicked.connect(
            lambda item: self.page_selected.emit(item.data(Qt.ItemDataRole.UserRole))
        )

    def load_document(self) -> None:
        self.clear()
        for i in range(self._doc.page_count):
            item = QListWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.addItem(item)
            QTimer.singleShot(i * 20, lambda idx=i: self._render(idx))

    def set_current(self, page_num: int) -> None:
        self.setCurrentRow(page_num)

    def refresh(self, page_num: int) -> None:
        QTimer.singleShot(0, lambda: self._render(page_num))

    def _render(self, page_num: int) -> None:
        if not self._doc.is_open:
            return
        item = self.item(page_num)
        if item is None:
            return
        data = self._doc.render_page(page_num, zoom=THUMB_ZOOM)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            scaled = px.scaledToWidth(THUMB_W, Qt.TransformationMode.SmoothTransformation)
            item.setIcon(QIcon(scaled))


class _BookmarksTree(QWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, doc: "PDFDocument", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemClicked.connect(self._on_clicked)
        layout.addWidget(self._tree)

        self._empty = QLabel("Keine Lesezeichen vorhanden")
        self._empty.setObjectName("empty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty)

    def load_document(self) -> None:
        self._tree.clear()
        toc = self._doc.get_toc()
        if not toc:
            self._tree.setVisible(False)
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        self._tree.setVisible(True)

        items_by_level: dict[int, QTreeWidgetItem] = {
            0: self._tree.invisibleRootItem()
        }
        for entry in toc:
            level, title, page = entry[0], entry[1], entry[2]
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, max(0, page - 1))
            parent = items_by_level.get(level - 1, self._tree.invisibleRootItem())
            parent.addChild(item)
            items_by_level[level] = item
            for k in list(items_by_level.keys()):
                if k > level:
                    del items_by_level[k]
        self._tree.expandToDepth(1)

    def _on_clicked(self, item: QTreeWidgetItem) -> None:
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page is not None:
            self.page_selected.emit(page)


class Sidebar(QWidget):
    """Collapsible tabbed sidebar: Seiten (thumbnails) + Lesezeichen (TOC)."""

    page_selected = pyqtSignal(int)

    def __init__(self, doc: "PDFDocument", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self.setStyleSheet(_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._thumbs = _ThumbnailList(doc)
        self._thumbs.page_selected.connect(self.page_selected)
        self._tabs.addTab(self._thumbs, "Seiten")

        self._bookmarks = _BookmarksTree(doc)
        self._bookmarks.page_selected.connect(self.page_selected)
        self._tabs.addTab(self._bookmarks, "Lesezeichen")

        self.setFixedWidth(self._thumbs.width() + 4)

    def load_document(self) -> None:
        self._thumbs.load_document()
        self._bookmarks.load_document()

    def set_current_page(self, page_num: int) -> None:
        self._thumbs.set_current(page_num)

    def refresh_page(self, page_num: int) -> None:
        self._thumbs.refresh(page_num)
