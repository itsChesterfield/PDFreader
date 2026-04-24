"""Right annotations panel (220 px)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from .theme import ACCENT, ACCENT2, ACCENT_DIM, BG, BORDER, DANGER, MUTED, RIGHT_W, SURFACE, SURFACE2, SURFACE3, TEXT, WARN

if TYPE_CHECKING:
    from .models import VAnnotation

_SCROLLBAR = (
    f"QScrollBar:vertical{{background:{SURFACE};width:4px;margin:0;}}"
    f"QScrollBar::handle:vertical{{background:{BORDER};border-radius:2px;min-height:16px;}}"
    f"QScrollBar::handle:vertical:hover{{background:{MUTED};}}"
    f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
)

_FILTER_BTN = (
    f"QPushButton{{background:transparent;color:{MUTED};border:none;"
    f"border-bottom:2px solid transparent;padding:6px 12px;font-size:11px;border-radius:0;}}"
    f"QPushButton:checked{{color:{ACCENT};border-bottom:2px solid {ACCENT};}}"
    f"QPushButton:hover:!checked{{color:{TEXT};}}"
)


class _AnnotCard(QWidget):
    navigate = pyqtSignal(int)   # page num

    COLOR_MAP = {
        "green":  ACCENT,
        "yellow": WARN,
        "red":    DANGER,
    }

    def __init__(self, ann: "VAnnotation", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = ann.page
        color = self.COLOR_MAP.get(ann.color, ACCENT)

        self.setStyleSheet(
            f"background:{SURFACE2};border-radius:6px;"
            f"border-left:3px solid {color};"
        )
        self.setFixedHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        pg = QLabel(f"Seite {ann.page + 1}")
        pg.setStyleSheet(
            f"font-family:'DM Mono','Consolas';font-size:9px;"
            f"color:{color};font-weight:600;background:transparent;"
        )
        top.addWidget(pg)
        top.addStretch()
        btn = QPushButton("→")
        btn.setFixedSize(20, 20)
        btn.setStyleSheet(
            f"QPushButton{{background:{SURFACE2};color:{MUTED};border:none;"
            f"border-radius:4px;font-size:12px;}}"
            f"QPushButton:hover{{background:{SURFACE3};color:{TEXT};}}"
        )
        btn.clicked.connect(lambda: self.navigate.emit(self._page))
        top.addWidget(btn)
        layout.addLayout(top)

        text = QLabel(ann.text)
        text.setWordWrap(True)
        text.setStyleSheet(
            f"font-size:10px;color:{TEXT};background:transparent;"
            f"line-height:1.5;"
        )
        text.setMaximumHeight(36)
        layout.addWidget(text)


class AnnotationsPanel(QWidget):
    """Right-side panel listing VAnnotations for the open document."""

    annotation_navigate = pyqtSignal(int)   # page 0-based
    add_annotation      = pyqtSignal(str)   # color

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(RIGHT_W)
        self.setStyleSheet(
            f"QWidget{{background:{SURFACE};border-left:1px solid {BORDER};}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        title = QLabel("Anmerkungen")
        title.setStyleSheet(f"font-size:11px;font-weight:600;color:{TEXT};")
        hl.addWidget(title)
        hl.addStretch()
        layout.addWidget(hdr)

        # Filter tabs
        filter_bar = QWidget()
        filter_bar.setFixedHeight(36)
        filter_bar.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(4, 0, 4, 0)
        fl.setSpacing(0)

        self._btn_all  = QPushButton("Alle")
        self._btn_page = QPushButton("Diese Seite")
        for btn in (self._btn_all, self._btn_page):
            btn.setCheckable(True)
            btn.setStyleSheet(_FILTER_BTN)
            fl.addWidget(btn)
        fl.addStretch()
        self._btn_all.setChecked(True)
        self._btn_all.clicked.connect(lambda: self._set_filter("all"))
        self._btn_page.clicked.connect(lambda: self._set_filter("page"))
        layout.addWidget(filter_bar)

        # Add annotation buttons
        add_row = QWidget()
        add_row.setFixedHeight(40)
        add_row.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        al = QHBoxLayout(add_row)
        al.setContentsMargins(10, 6, 10, 6)
        al.addWidget(QLabel("Neu:"))
        for color, label, hex_col in [("green", "●", ACCENT), ("yellow", "●", WARN), ("red", "●", DANGER)]:
            cb = QPushButton(label)
            cb.setFixedSize(24, 24)
            cb.setToolTip({"green": "Wichtig", "yellow": "Referenz", "red": "Ueberpruefen"}[color])
            cb.setStyleSheet(
                f"QPushButton{{background:transparent;color:{hex_col};border:none;"
                f"font-size:16px;border-radius:4px;}}"
                f"QPushButton:hover{{background:{SURFACE3};}}"
            )
            cb.clicked.connect(lambda _, c=color: self.add_annotation.emit(c))
            al.addWidget(cb)
        al.addStretch()
        layout.addWidget(add_row)

        # List
        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget{{background:{SURFACE};border:none;outline:none;}}"
            f"QListWidget::item{{border:none;padding:4px 8px;background:transparent;}}"
            f"QListWidget::item:hover{{background:{SURFACE3};}}"
            + _SCROLLBAR
        )
        self._list.setSpacing(3)
        layout.addWidget(self._list)

        self._empty = QLabel("Noch keine Anmerkungen.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet(f"color:{MUTED};font-size:11px;padding:20px;")
        layout.addWidget(self._empty)

        self._all_annotations: list["VAnnotation"] = []
        self._current_page: int = 0
        self._filter: str = "all"

    # ------------------------------------------------------------------
    def load(self, annotations: list["VAnnotation"], current_page: int = 0) -> None:
        self._all_annotations = annotations
        self._current_page = current_page
        self._refresh_list()

    def set_current_page(self, page: int) -> None:
        self._current_page = page
        if self._filter == "page":
            self._refresh_list()

    def _set_filter(self, f: str) -> None:
        self._filter = f
        self._btn_all.setChecked(f == "all")
        self._btn_page.setChecked(f == "page")
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        data = (
            self._all_annotations if self._filter == "all"
            else [a for a in self._all_annotations if a.page == self._current_page]
        )
        if not data:
            self._list.setVisible(False)
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        self._list.setVisible(True)
        for ann in data:
            card = _AnnotCard(ann)
            card.navigate.connect(self.annotation_navigate)
            item = QListWidgetItem(self._list)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
