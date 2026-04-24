"""Verdant PDF Reader — main application window."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from .constants import Tool
from .dialogs import ExportDialog
from .left_panel import LeftPanel
from .minimap import MiniMap
from .models import Bookmark, DocumentLibrary, VAnnotation
from .pdf_document import PDFDocument
from .pdf_viewer import PDFViewer
from .right_panel import AnnotationsPanel
from .sidenav import SideNav
from .theme import (
    ACCENT, BG, BORDER, MUTED, RIGHT_W, STATUSBAR_H, SURFACE, SURFACE2,
    TEXT, WARN,
)
from .toolbar_widget import ToolBar


_STATUS_STYLE = f"""
QWidget {{ background: {SURFACE}; border-top: 1px solid {BORDER}; }}
QLabel  {{ color: {MUTED}; font-size: 10px; font-family: 'DM Mono','Consolas';
           background: transparent; border: none; padding: 0 8px; }}
"""


class _StatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(STATUSBAR_H)
        self.setStyleSheet(_STATUS_STYLE)

        from PyQt6.QtWidgets import QProgressBar
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Reading progress bar (full width, 2 px)
        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(2)
        self._bar.setStyleSheet(
            f"QProgressBar{{background:{BORDER};border:none;border-radius:0;}}"
            f"QProgressBar::chunk{{background:{ACCENT};border-radius:0;}}"
        )

        from PyQt6.QtWidgets import QVBoxLayout as _VBox
        outer = _VBox()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._bar)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        # Pulse dot + label
        from PyQt6.QtWidgets import QLabel
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{ACCENT};font-size:8px;padding:0 4px 0 8px;")
        row.addWidget(dot)

        self._app_label = QLabel("Verdant Reader")
        self._app_label.setStyleSheet(f"color:{ACCENT};font-weight:600;")
        row.addWidget(self._app_label)
        row.addStretch(1)

        self._read_label = QLabel("0 % gelesen")
        row.addWidget(self._read_label)

        self._zoom_label = QLabel("Zoom 100 %")
        row.addWidget(self._zoom_label)

        outer.addLayout(row)
        layout.addLayout(outer)

    def set_progress(self, progress: float, zoom: float) -> None:
        self._bar.setValue(int(progress * 1000))
        self._read_label.setText(f"{int(progress * 100)} % gelesen")
        self._zoom_label.setText(f"Zoom {int(zoom * 100)} %")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._doc      = PDFDocument()
        self._library  = DocumentLibrary()
        self._show_annotations = False
        self._anim_right: Optional[QPropertyAnimation] = None

        self.setWindowTitle("Verdant Reader")
        self.setMinimumSize(960, 640)

        self._build_central()
        self._build_menu()
        self._connect_signals()
        self._set_doc_actions_enabled(False)

    # ──────────────────────────────────────────────────────────────────────
    # Layout construction
    # ──────────────────────────────────────────────────────────────────────

    def _build_central(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        # Outer vertical: [main row] + [status bar]
        outer_v = QVBoxLayout(root)
        outer_v.setContentsMargins(0, 0, 0, 0)
        outer_v.setSpacing(0)

        # Main horizontal row
        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)

        # 1 · Sidenav
        self._sidenav = SideNav()
        main_row.addWidget(self._sidenav)

        # 2 · Left panel (collapsible)
        self._left = LeftPanel(self._library)
        main_row.addWidget(self._left)

        # 3 · Centre: toolbar + viewer (with minimap overlay)
        centre = QWidget()
        centre.setStyleSheet(f"background:{BG};")
        cv = QVBoxLayout(centre)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        self._toolbar = ToolBar()
        cv.addWidget(self._toolbar)

        # Viewer wrapper (to position minimap absolutely)
        viewer_wrap = QWidget()
        viewer_wrap.setStyleSheet(f"background:{BG};")
        vw_layout = QVBoxLayout(viewer_wrap)
        vw_layout.setContentsMargins(0, 0, 0, 0)
        vw_layout.setSpacing(0)

        self._viewer = PDFViewer(self._doc)
        vw_layout.addWidget(self._viewer)

        self._minimap = MiniMap(self._doc, viewer_wrap)
        self._minimap.hide()

        cv.addWidget(viewer_wrap)
        main_row.addWidget(centre, stretch=1)

        # 4 · Right panel (annotations, collapsible)
        self._right = AnnotationsPanel()
        self._right.setMaximumWidth(0)
        main_row.addWidget(self._right)

        outer_v.addLayout(main_row)

        # Status bar
        self._status = _StatusBar()
        outer_v.addWidget(self._status)

        # Position minimap after layout is ready
        QTimer.singleShot(0, self._position_minimap)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        file_menu = mb.addMenu("Datei")
        self._act_open    = QAction("Oeffnen ...",           self, shortcut="Ctrl+O", triggered=self._open_file)
        self._act_save    = QAction("Speichern",             self, shortcut="Ctrl+S", triggered=self._save_file)
        self._act_save_as = QAction("Speichern unter ...",   self, shortcut="Ctrl+Shift+S", triggered=self._save_as)
        self._act_export  = QAction("Exportieren ...",       self, shortcut="Ctrl+E", triggered=self._export)
        self._act_close   = QAction("Schliessen",            self, triggered=self._close_file)
        act_quit          = QAction("Beenden",               self, shortcut="Ctrl+Q",
                                    triggered=QApplication.instance().quit)
        for act in (self._act_open, self._act_save, self._act_save_as,
                    self._act_export, self._act_close, act_quit):
            file_menu.addAction(act)

        view_menu = mb.addMenu("Ansicht")
        QAction("Vergrossern",     self, shortcut="Ctrl++", triggered=self._viewer.zoom_in,  parent=self)
        QAction("Verkleinern",     self, shortcut="Ctrl+-", triggered=self._viewer.zoom_out, parent=self)
        for act in (
            QAction("Vergrossern",   self, shortcut="Ctrl++", triggered=self._viewer.zoom_in),
            QAction("Verkleinern",   self, shortcut="Ctrl+-", triggered=self._viewer.zoom_out),
            QAction("Zoom Reset",    self, shortcut="Ctrl+0", triggered=self._zoom_reset),
            QAction("Breite",        self, shortcut="Ctrl+W", triggered=self._viewer.fit_width),
            QAction("Suche",         self, shortcut="Ctrl+F", triggered=self._open_search),
            QAction("Lesezeichen",   self, shortcut="Ctrl+B", triggered=self._toggle_bookmarks),
        ):
            view_menu.addAction(act)
            self.addAction(act)

        # Keyboard navigation
        for key, fn in [
            ("Left",  self._prev_page), ("Right", self._next_page),
            ("H",     self._prev_page), ("L",     self._next_page),
            ("+",     self._viewer.zoom_in), ("-", self._viewer.zoom_out),
            ("Escape", self._toolbar.deselect_tool),
        ]:
            act = QAction(self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(fn)
            self.addAction(act)

    def _connect_signals(self) -> None:
        # Sidenav
        self._sidenav.tab_changed.connect(self._on_tab_changed)

        # Left panel
        self._left.document_selected.connect(self._switch_document)
        self._left.open_requested.connect(self._open_file)
        self._left.page_selected.connect(self._viewer.go_to_page)
        self._left.search_requested.connect(self._do_search)
        self._left.add_bookmark.connect(self._add_bookmark)
        self._left.zoom_reset.connect(self._zoom_reset)
        self._left.fit_width.connect(self._viewer.fit_width)
        self._left.bg_changed.connect(self._on_bg_changed)

        # Toolbar
        self._toolbar.prev_page.connect(self._prev_page)
        self._toolbar.next_page.connect(self._next_page)
        self._toolbar.page_jumped.connect(self._viewer.go_to_page)
        self._toolbar.zoom_in.connect(self._viewer.zoom_in)
        self._toolbar.zoom_out.connect(self._viewer.zoom_out)
        self._toolbar.zoom_reset.connect(self._zoom_reset)
        self._toolbar.fit_width_requested.connect(self._viewer.fit_width)
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._toolbar.annotations_toggled.connect(self._toggle_annotations)
        self._toolbar.open_file.connect(self._open_file)
        self._toolbar.save_file.connect(self._save_file)

        # Viewer
        self._viewer.page_changed.connect(self._on_page_changed)
        self._viewer.annotation_added.connect(self._on_pdf_annotation_added)
        self._viewer.zoom_changed.connect(self._on_zoom_changed)

        # Right panel
        self._right.annotation_navigate.connect(self._viewer.go_to_page)
        self._right.add_annotation.connect(self._add_v_annotation)

        # Minimap
        self._minimap.page_selected.connect(self._viewer.go_to_page)

    # ──────────────────────────────────────────────────────────────────────
    # File operations
    # ──────────────────────────────────────────────────────────────────────

    def _open_file(self) -> None:
        if self._doc.modified and not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF oeffnen", "", "PDF-Dateien (*.pdf)"
        )
        if not path:
            return
        self._load_path(path)

    def _load_path(self, path: str) -> None:
        if self._doc.is_open:
            self._doc.close()
        if not self._doc.open(path):
            QMessageBox.critical(self, "Fehler", f"Konnte nicht geoeffnet werden:\n{path}")
            return

        title = Path(path).stem
        lib_doc = self._library.open(path, title, self._doc.page_count)

        self._viewer.load_document()
        self._minimap.load_document()
        self._minimap.show()
        self._position_minimap()

        self._toolbar.set_document(title, self._doc.page_count)
        self._left.refresh_files()
        self._left.load_bookmarks(lib_doc.bookmarks)
        self._right.load(lib_doc.v_annotations)
        self._set_doc_actions_enabled(True)
        self._update_status(0, self._viewer.current_zoom())
        self.setWindowTitle(f"Verdant Reader  —  {title}")

    def _save_file(self) -> None:
        if not self._doc.is_open:
            return
        if not self._doc.save():
            QMessageBox.warning(self, "Fehler", "Speichern fehlgeschlagen.")

    def _save_as(self) -> None:
        if not self._doc.is_open:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Speichern unter", str(self._doc.path or ""), "PDF-Dateien (*.pdf)"
        )
        if path:
            if not path.endswith(".pdf"):
                path += ".pdf"
            self._doc.save(path)

    def _export(self) -> None:
        if not self._doc.is_open:
            return
        dlg = ExportDialog(self)
        if not dlg.exec():
            return
        fmt = dlg.selected_format
        stem = self._doc.path.stem if self._doc.path else "export"
        parent_dir = str(self._doc.path.parent) if self._doc.path else ""
        if fmt == "txt":
            p, _ = QFileDialog.getSaveFileName(self, "Als Text", f"{parent_dir}/{stem}.txt", "*.txt")
            if p:
                self._doc.export_text(p)
        elif fmt == "docx":
            p, _ = QFileDialog.getSaveFileName(self, "Als Word", f"{parent_dir}/{stem}.docx", "*.docx")
            if p:
                self._doc.export_docx(p)
        elif fmt in ("png", "jpg"):
            d = QFileDialog.getExistingDirectory(self, "Ordner fuer Bilder", parent_dir)
            if d:
                self._doc.export_images(d, fmt=fmt)
        elif fmt == "pdf":
            p, _ = QFileDialog.getSaveFileName(self, "PDF speichern unter", f"{parent_dir}/{stem}_kopie.pdf", "*.pdf")
            if p:
                self._doc.save(p)

    def _close_file(self) -> None:
        if not self._doc.is_open:
            return
        if self._doc.modified and not self._confirm_discard():
            return
        self._doc.close()
        self._viewer._clear()
        self._minimap.hide()
        self._set_doc_actions_enabled(False)
        self.setWindowTitle("Verdant Reader")

    def _switch_document(self, doc_id: int) -> None:
        lib_doc = self._library.activate(doc_id)
        if lib_doc and lib_doc.path != (str(self._doc.path) if self._doc.path else ""):
            self._load_path(lib_doc.path)

    # ──────────────────────────────────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────────────────────────────────

    def _prev_page(self) -> None:
        p = self._viewer.current_page()
        if p > 0:
            self._viewer.go_to_page(p - 1)

    def _next_page(self) -> None:
        p = self._viewer.current_page()
        if p < self._doc.page_count - 1:
            self._viewer.go_to_page(p + 1)

    # ──────────────────────────────────────────────────────────────────────
    # Panel management
    # ──────────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, tab_id: str) -> None:
        self._left.show_tab(tab_id)
        if tab_id == "search":
            self._left.focus_search()

    def _toggle_annotations(self, show: bool) -> None:
        self._show_annotations = show
        target = RIGHT_W if show else 0
        if self._anim_right:
            self._anim_right.stop()
        self._anim_right = QPropertyAnimation(self._right, b"maximumWidth", self)
        self._anim_right.setStartValue(self._right.maximumWidth())
        self._anim_right.setEndValue(target)
        self._anim_right.setDuration(200)
        self._anim_right.setEasingCurve(
            QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic
        )
        self._anim_right.start()

    def _open_search(self) -> None:
        self._sidenav.set_active("search")
        self._left.show_tab("search")
        self._left.focus_search()

    def _toggle_bookmarks(self) -> None:
        self._sidenav.set_active("bookmarks")
        self._left.show_tab("bookmarks")

    # ──────────────────────────────────────────────────────────────────────
    # Tools & zoom
    # ──────────────────────────────────────────────────────────────────────

    def _on_tool_changed(self, tid: str) -> None:
        tool_map = {
            "highlight": Tool.HIGHLIGHT,
            "comment":   Tool.NOTE,
            "pen":       Tool.TEXT,
            "":          Tool.SELECT,
        }
        self._viewer.set_tool(tool_map.get(tid, Tool.SELECT))

    def _zoom_reset(self) -> None:
        self._viewer.set_zoom(1.0)

    def _on_bg_changed(self, mode: str) -> None:
        colors = {
            "dark":  "#0d1a13",
            "sepia": "#1a1508",
            "light": "#2a2a2a",
        }
        bg = colors.get(mode, "#0d1a13")
        self._viewer._container.setStyleSheet(f"background:{bg};")

    # ──────────────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────────────

    def _do_search(self, query: str) -> None:
        if not self._doc.is_open or not query:
            self._viewer.clear_search()
            self._left.clear_search()
            return
        results = self._doc.search(query)
        self._viewer.show_search_results(results)
        self._left.show_search_results(results)
        if results:
            self._viewer.go_to_page(next(iter(results)))

    # ──────────────────────────────────────────────────────────────────────
    # Bookmarks & annotations
    # ──────────────────────────────────────────────────────────────────────

    def _add_bookmark(self) -> None:
        if not self._doc.is_open:
            return
        lib_doc = self._library.active()
        if not lib_doc:
            return
        page = self._viewer.current_page()
        title, ok = QInputDialog.getText(
            self, "Lesezeichen hinzufuegen",
            f"Titel (Seite {page + 1}):",
            text=f"Seite {page + 1}",
        )
        if ok and title.strip():
            bm = Bookmark(title.strip(), page)
            lib_doc.bookmarks.append(bm)
            self._left.load_bookmarks(lib_doc.bookmarks, page)

    def _add_v_annotation(self, color: str) -> None:
        if not self._doc.is_open:
            return
        lib_doc = self._library.active()
        if not lib_doc:
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Anmerkung hinzufuegen",
            f"Text (Seite {self._viewer.current_page() + 1}):",
        )
        if ok and text.strip():
            ann = VAnnotation(self._viewer.current_page(), text.strip(), color=color)
            lib_doc.v_annotations.append(ann)
            self._right.load(lib_doc.v_annotations, self._viewer.current_page())

    # ──────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────

    def _on_page_changed(self, page: int) -> None:
        self._toolbar.set_page(page)
        self._minimap.set_current_page(page)
        self._right.set_current_page(page)

        lib_doc = self._library.active()
        if lib_doc:
            lib_doc.update_progress(page)
            self._update_status(lib_doc.progress, self._viewer.current_zoom())
            self._left.load_bookmarks(lib_doc.bookmarks, page)

    def _on_zoom_changed(self, zoom: float) -> None:
        self._toolbar.set_zoom(zoom)
        lib_doc = self._library.active()
        progress = lib_doc.progress if lib_doc else 0.0
        self._update_status(progress, zoom)

    def _on_pdf_annotation_added(self, page_num: int) -> None:
        self.setWindowTitle(
            f"Verdant Reader  —  {self._doc.path.name} *" if self._doc.path
            else "Verdant Reader *"
        )

    def _update_status(self, progress: float, zoom: float) -> None:
        self._status.set_progress(progress, zoom)

    # ──────────────────────────────────────────────────────────────────────
    # Misc
    # ──────────────────────────────────────────────────────────────────────

    def _position_minimap(self) -> None:
        if not self._minimap.isVisible():
            return
        vw = self._viewer
        mm = self._minimap
        mm.adjustSize()
        x = vw.width() - mm.width() - 20
        y = vw.height() - mm.height() - 20
        mm.move(vw.mapTo(vw.parent(), vw.rect().topLeft()) + __import__("PyQt6.QtCore", fromlist=["QPoint"]).QPoint(x, y))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._position_minimap)

    def _set_doc_actions_enabled(self, on: bool) -> None:
        for act in (self._act_save, self._act_save_as, self._act_export, self._act_close):
            act.setEnabled(on)

    def _confirm_discard(self) -> bool:
        return QMessageBox.question(
            self, "Aenderungen verwerfen?",
            "Es gibt ungespeicherte Aenderungen. Trotzdem fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

    def closeEvent(self, event) -> None:
        if self._doc.modified:
            reply = QMessageBox.question(
                self, "Ungespeicherte Aenderungen",
                "Vor dem Beenden speichern?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
