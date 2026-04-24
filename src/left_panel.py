"""Collapsible left panel: Files · Bookmarks · Search · Settings."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QPropertyAnimation, Qt, pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .theme import (
    ACCENT, ACCENT2, ACCENT_DIM, BG, BORDER, LEFT_SM_W, LEFT_W,
    MUTED, SURFACE, SURFACE2, SURFACE3, TEXT, WARN,
)

if TYPE_CHECKING:
    from .models import Bookmark, Document, DocumentLibrary, VAnnotation

# ── Shared styles ─────────────────────────────────────────────────────────
_HEADER = f"font-size:9px;font-weight:600;color:{MUTED};letter-spacing:0.08em;text-transform:uppercase;"

_LIST_STYLE = f"""
QListWidget {{
    background: {SURFACE}; border: none; outline: none;
}}
QListWidget::item {{
    border-bottom: 1px solid {BORDER}; padding: 0; margin: 0;
    background: transparent;
}}
QListWidget::item:selected {{ background: {ACCENT_DIM}; border-left: 2px solid {ACCENT}; }}
QListWidget::item:hover:!selected {{ background: {SURFACE3}; }}
"""

_SEARCH_INPUT = f"""
QLineEdit {{
    background: {SURFACE2}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 10px; font-size: 11px;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
    background: {SURFACE2};
}}
"""

_BTN_ACCENT = f"""
QPushButton {{
    background: {ACCENT}; color: {BG};
    border: none; border-radius: 6px;
    padding: 7px 0; font-weight: 600; font-size: 11px;
}}
QPushButton:hover {{ background: {ACCENT2}; }}
"""

_SCROLLBAR = (
    f"QScrollBar:vertical{{background:{SURFACE};width:4px;margin:0;}}"
    f"QScrollBar::handle:vertical{{background:{BORDER};border-radius:2px;min-height:16px;}}"
    f"QScrollBar::handle:vertical:hover{{background:{MUTED};}}"
    f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
)


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(_HEADER)
    return lbl


# ── Files panel ───────────────────────────────────────────────────────────
class _DocItem(QWidget):
    """A single document entry with icon, title and progress bar."""

    def __init__(self, doc: "Document", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc = doc
        self.setFixedHeight(56)
        self.setStyleSheet(f"background: transparent;")

        h = QHBoxLayout(self)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(8)

        # Mini PDF icon
        icon = QLabel()
        icon.setFixedSize(22, 30)
        icon.setStyleSheet(
            f"background: {SURFACE2}; border: 1px solid {BORDER};"
            f"border-radius: 3px; color: {ACCENT}; font-size: 8px; font-weight:600;"
        )
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setText("PDF")
        h.addWidget(icon)

        v = QVBoxLayout()
        v.setSpacing(2)
        title = QLabel(doc.title)
        title.setStyleSheet(f"font-size:11px;font-weight:500;color:{TEXT};")
        title.setMaximumWidth(LEFT_W - 70)
        title.setWordWrap(False)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        v.addWidget(title)

        meta = QLabel(f"{doc.pages} Seiten  ·  {doc.modified}")
        meta.setStyleSheet(f"font-size:9px;font-family:'DM Mono','Consolas';color:{MUTED};")
        v.addWidget(meta)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(doc.progress * 100))
        bar.setFixedHeight(2)
        bar.setTextVisible(False)
        bar.setStyleSheet(
            f"QProgressBar{{background:{BORDER};border-radius:1px;border:none;}}"
            f"QProgressBar::chunk{{background:{ACCENT};border-radius:1px;}}"
        )
        v.addWidget(bar)
        self._bar = bar

        h.addLayout(v)

    def refresh(self, doc: "Document") -> None:
        self._bar.setValue(int(doc.progress * 100))


class FilesPanel(QWidget):
    document_selected = pyqtSignal(int)   # doc.id
    open_requested    = pyqtSignal()

    def __init__(self, library: "DocumentLibrary", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lib = library
        self._item_widgets: dict[int, _DocItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.addWidget(_section_label("Dokumente"))
        hl.addStretch()
        layout.addWidget(hdr)

        # List
        self._list = QListWidget()
        self._list.setStyleSheet(_LIST_STYLE + _SCROLLBAR)
        self._list.setSpacing(0)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"background:{SURFACE};border-top:1px solid {BORDER};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(10, 8, 10, 8)
        btn = QPushButton("+ Datei oeffnen")
        btn.setStyleSheet(_BTN_ACCENT)
        btn.clicked.connect(self.open_requested)
        fl.addWidget(btn)
        layout.addWidget(footer)

    def refresh(self) -> None:
        self._list.clear()
        self._item_widgets.clear()
        active = self._lib.active()
        for doc in self._lib.all_docs():
            widget = _DocItem(doc)
            item = QListWidgetItem(self._list)
            item.setData(Qt.ItemDataRole.UserRole, doc.id)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
            self._item_widgets[doc.id] = widget
            if active and doc.id == active.id:
                self._list.setCurrentItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        doc_id = item.data(Qt.ItemDataRole.UserRole)
        self.document_selected.emit(doc_id)


# ── Bookmarks panel ───────────────────────────────────────────────────────
class BookmarksPanel(QWidget):
    page_selected = pyqtSignal(int)   # 0-based page
    add_bookmark  = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.addWidget(_section_label("Lesezeichen"))
        hl.addStretch()
        btn_add = QPushButton("+")
        btn_add.setFixedSize(24, 24)
        btn_add.setToolTip("Lesezeichen hinzufuegen")
        btn_add.setStyleSheet(
            f"QPushButton{{background:{ACCENT_DIM};color:{ACCENT};border:none;"
            f"border-radius:4px;font-size:14px;font-weight:600;}}"
            f"QPushButton:hover{{background:{ACCENT};color:{BG};}}"
        )
        btn_add.clicked.connect(self.add_bookmark)
        hl.addWidget(btn_add)
        layout.addWidget(hdr)

        self._list = QListWidget()
        self._list.setStyleSheet(_LIST_STYLE + _SCROLLBAR)
        self._list.itemClicked.connect(
            lambda it: self.page_selected.emit(it.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self._list)

        self._empty = QLabel("Noch keine Lesezeichen.\nFuege welche mit + hinzu.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet(f"color:{MUTED};font-size:11px;padding:20px;")
        layout.addWidget(self._empty)

    def load(self, bookmarks: list["Bookmark"], current_page: int = -1) -> None:
        self._list.clear()
        if not bookmarks:
            self._list.setVisible(False)
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        self._list.setVisible(True)
        for bm in bookmarks:
            w = QWidget()
            w.setFixedHeight(52)
            hl = QHBoxLayout(w)
            hl.setContentsMargins(10, 6, 10, 6)
            hl.setSpacing(8)

            icon = QLabel("◈")
            icon.setFixedWidth(16)
            icon.setStyleSheet(f"color: {ACCENT if bm.page == current_page else MUTED}; font-size:13px;")
            hl.addWidget(icon)

            v = QVBoxLayout()
            v.setSpacing(2)
            title_lbl = QLabel(bm.title)
            title_lbl.setStyleSheet(f"font-size:11px;font-weight:500;color:{TEXT};")
            v.addWidget(title_lbl)
            if bm.note:
                note_lbl = QLabel(bm.note)
                note_lbl.setStyleSheet(f"font-size:10px;color:{MUTED};")
                v.addWidget(note_lbl)
            hl.addLayout(v)

            page_lbl = QLabel(str(bm.page + 1))
            page_lbl.setStyleSheet(
                f"font-family:'DM Mono','Consolas';font-size:10px;color:{ACCENT};font-weight:600;"
            )
            hl.addWidget(page_lbl)

            item = QListWidgetItem(self._list)
            item.setData(Qt.ItemDataRole.UserRole, bm.page)
            item.setSizeHint(w.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, w)


# ── Search panel ──────────────────────────────────────────────────────────
class SearchPanel(QWidget):
    result_selected = pyqtSignal(int)    # 0-based page
    search_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.addWidget(_section_label("Suche"))
        layout.addWidget(hdr)

        inp_wrap = QWidget()
        inp_wrap.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        il = QVBoxLayout(inp_wrap)
        il.setContentsMargins(10, 8, 10, 8)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Dokument durchsuchen ...")
        self._input.setStyleSheet(_SEARCH_INPUT)
        self._input.textChanged.connect(self._on_text_changed)
        il.addWidget(self._input)
        layout.addWidget(inp_wrap)

        self._results = QListWidget()
        self._results.setStyleSheet(_LIST_STYLE + _SCROLLBAR)
        self._results.itemClicked.connect(
            lambda it: self.result_selected.emit(it.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self._results)

        self._empty = QLabel("Gib mindestens 3 Zeichen ein.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet(f"color:{MUTED};font-size:11px;padding:20px;")
        layout.addWidget(self._empty)

    def show_results(self, results: dict[int, list]) -> None:
        self._results.clear()
        if not results:
            self._results.setVisible(False)
            self._empty.setVisible(True)
            self._empty.setText("Kein Ergebnis gefunden.")
            return
        self._empty.setVisible(False)
        self._results.setVisible(True)
        for page_num, rects in results.items():
            w = QWidget()
            w.setFixedHeight(48)
            hl = QHBoxLayout(w)
            hl.setContentsMargins(10, 6, 10, 6)
            v = QVBoxLayout()
            v.setSpacing(2)
            pg = QLabel(f"Seite {page_num + 1}")
            pg.setStyleSheet(f"font-family:'DM Mono','Consolas';font-size:10px;color:{ACCENT};font-weight:600;")
            v.addWidget(pg)
            hits = QLabel(f"{len(rects)} Treffer auf dieser Seite")
            hits.setStyleSheet(f"font-size:10px;color:{MUTED};")
            v.addWidget(hits)
            hl.addLayout(v)
            item = QListWidgetItem(self._results)
            item.setData(Qt.ItemDataRole.UserRole, page_num)
            item.setSizeHint(w.sizeHint())
            self._results.addItem(item)
            self._results.setItemWidget(item, w)

    def clear_results(self) -> None:
        self._results.clear()
        self._results.setVisible(False)
        self._empty.setVisible(True)
        self._empty.setText("Gib mindestens 3 Zeichen ein.")

    def focus_input(self) -> None:
        self._input.setFocus()
        self._input.selectAll()

    def _on_text_changed(self, text: str) -> None:
        if len(text) >= 3:
            self.search_requested.emit(text)
        else:
            self.clear_results()


# ── Settings panel ────────────────────────────────────────────────────────
class SettingsPanel(QWidget):
    zoom_reset    = pyqtSignal()
    fit_width     = pyqtSignal()
    bg_changed    = pyqtSignal(str)   # "dark" | "sepia" | "light"

    _SHORTCUTS = [
        ("← / →",    "Seite vor/zurueck"),
        ("+ / -",     "Zoom erhoehen/verringern"),
        ("Ctrl+0",    "Zoom zuruecksetzen"),
        ("Ctrl+O",    "Datei oeffnen"),
        ("Ctrl+S",    "Speichern"),
        ("Ctrl+F",    "Suche oeffnen"),
        ("Ctrl+B",    "Lesezeichen"),
        ("Esc",       "Werkzeug abwaehlen"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet(f"background:{SURFACE};border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.addWidget(_section_label("Einstellungen"))
        outer.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(_SCROLLBAR + f"QScrollArea{{background:{SURFACE};}}")

        content = QWidget()
        content.setStyleSheet(f"background:{SURFACE};")
        v = QVBoxLayout(content)
        v.setContentsMargins(12, 14, 12, 14)
        v.setSpacing(16)

        # Background mode
        v.addWidget(_section_label("Lesemodus"))
        mode_row = QHBoxLayout()
        for label, val in [("Dunkel", "dark"), ("Sepia", "sepia"), ("Hell", "light")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(val == "dark")
            btn.setStyleSheet(
                f"QPushButton{{background:{SURFACE2};color:{MUTED};border:1px solid {BORDER};"
                f"border-radius:6px;padding:5px 8px;font-size:10px;}}"
                f"QPushButton:checked{{background:{ACCENT_DIM};color:{ACCENT};"
                f"border-color:{ACCENT};}}"
                f"QPushButton:hover:!checked{{background:{SURFACE3};color:{TEXT};}}"
            )
            btn.clicked.connect(lambda _, v2=val: self.bg_changed.emit(v2))
            mode_row.addWidget(btn)
        v.addLayout(mode_row)

        # Quick actions
        v.addWidget(_section_label("Ansicht"))
        btn_fit = QPushButton("Breite anpassen")
        btn_fit.setStyleSheet(
            f"QPushButton{{background:{SURFACE2};color:{TEXT};border:1px solid {BORDER};"
            f"border-radius:6px;padding:6px 10px;font-size:11px;}}"
            f"QPushButton:hover{{background:{SURFACE3};}}"
        )
        btn_fit.clicked.connect(self.fit_width)
        v.addWidget(btn_fit)

        btn_reset = QPushButton("Zoom zuruecksetzen (100%)")
        btn_reset.setStyleSheet(btn_fit.styleSheet())
        btn_reset.clicked.connect(self.zoom_reset)
        v.addWidget(btn_reset)

        # Keyboard shortcuts
        v.addWidget(_section_label("Tastenkuerzel"))
        for keys, desc in self._SHORTCUTS:
            row = QWidget()
            row.setStyleSheet(f"background:transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            key_lbl = QLabel(keys)
            key_lbl.setFixedWidth(72)
            key_lbl.setStyleSheet(
                f"background:{SURFACE2};color:{ACCENT};border:1px solid {BORDER};"
                f"border-radius:4px;padding:3px 6px;"
                f"font-family:'DM Mono','Consolas';font-size:10px;"
            )
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color:{MUTED};font-size:10px;background:transparent;")
            rl.addWidget(key_lbl)
            rl.addWidget(desc_lbl)
            rl.addStretch()
            v.addWidget(row)

        v.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)


# ── Main collapsible panel ────────────────────────────────────────────────
class LeftPanel(QWidget):
    """Animated collapsible panel that hosts all four sub-panels."""

    document_selected  = pyqtSignal(int)   # doc id
    open_requested     = pyqtSignal()
    page_selected      = pyqtSignal(int)   # 0-based
    search_requested   = pyqtSignal(str)
    add_bookmark       = pyqtSignal()
    zoom_reset         = pyqtSignal()
    fit_width          = pyqtSignal()
    bg_changed         = pyqtSignal(str)

    _WIDTHS = {"files": LEFT_W, "bookmarks": LEFT_SM_W, "search": LEFT_W, "settings": LEFT_SM_W}

    def __init__(self, library: "DocumentLibrary", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lib = library
        self._current_tab: str = ""
        self._anim: Optional[QPropertyAnimation] = None

        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.setStyleSheet(f"background:{SURFACE};border-right:1px solid {BORDER};")

        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet(f"background:{SURFACE};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._stack)

        self._files = FilesPanel(library)
        self._files.document_selected.connect(self.document_selected)
        self._files.open_requested.connect(self.open_requested)

        self._bookmarks = BookmarksPanel()
        self._bookmarks.page_selected.connect(self.page_selected)
        self._bookmarks.add_bookmark.connect(self.add_bookmark)

        self._search = SearchPanel()
        self._search.result_selected.connect(self.page_selected)
        self._search.search_requested.connect(self.search_requested)

        self._settings = SettingsPanel()
        self._settings.zoom_reset.connect(self.zoom_reset)
        self._settings.fit_width.connect(self.fit_width)
        self._settings.bg_changed.connect(self.bg_changed)

        for w in (self._files, self._bookmarks, self._search, self._settings):
            self._stack.addWidget(w)

        self._panel_map = {
            "files": self._files, "bookmarks": self._bookmarks,
            "search": self._search, "settings": self._settings,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_tab(self, tab_id: str) -> None:
        if not tab_id:
            self._collapse()
            return
        already_open = self._current_tab == tab_id and self.maximumWidth() > 10
        self._current_tab = tab_id
        self._stack.setCurrentWidget(self._panel_map[tab_id])
        if already_open:
            self._collapse()
        else:
            self._expand(self._WIDTHS.get(tab_id, LEFT_W))

    def refresh_files(self) -> None:
        self._files.refresh()

    def load_bookmarks(self, bookmarks: list, current_page: int = -1) -> None:
        self._bookmarks.load(bookmarks, current_page)

    def show_search_results(self, results: dict) -> None:
        self._search.show_results(results)

    def clear_search(self) -> None:
        self._search.clear_results()

    def focus_search(self) -> None:
        self._search.focus_input()

    def is_open(self) -> bool:
        return self.maximumWidth() > 10

    # ------------------------------------------------------------------
    # Animation helpers
    # ------------------------------------------------------------------

    def _expand(self, target: int) -> None:
        if self._anim:
            self._anim.stop()
        current = self.width()
        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setStartValue(current if current > 0 else 0)
        self._anim.setEndValue(target)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _collapse(self) -> None:
        if self._anim:
            self._anim.stop()
        self._current_tab = ""
        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(0)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
