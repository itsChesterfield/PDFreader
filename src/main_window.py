from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QIcon, QKeySequence, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    DEFAULT_ZOOM,
    HIGHLIGHT_COLORS,
    MAX_ZOOM,
    MIN_ZOOM,
    ZOOM_STEP,
    Tool,
)
from .pdf_document import PDFDocument
from .pdf_viewer import PDFViewer
from .thumbnail_panel import ThumbnailPanel


_MAIN_STYLE = """
QMainWindow { background: #2b2b2b; }
QMenuBar {
    background: #3c3f41;
    color: #cccccc;
    border-bottom: 1px solid #555555;
}
QMenuBar::item:selected { background: #4b6eaf; }
QMenu {
    background: #3c3f41;
    color: #cccccc;
    border: 1px solid #555555;
}
QMenu::item:selected { background: #4b6eaf; }
QToolBar {
    background: #3c3f41;
    border-bottom: 1px solid #555555;
    spacing: 4px;
    padding: 2px 6px;
}
QToolButton {
    background: transparent;
    color: #cccccc;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
}
QToolButton:hover { background: #4b6eaf; color: white; }
QToolButton:checked { background: #4b6eaf; color: white; }
QComboBox {
    background: #3c3f41;
    color: #cccccc;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px 6px;
    min-width: 70px;
}
QComboBox QAbstractItemView {
    background: #3c3f41;
    color: #cccccc;
    selection-background-color: #4b6eaf;
}
QStatusBar {
    background: #3c3f41;
    color: #aaaaaa;
    border-top: 1px solid #555555;
    font-size: 12px;
}
QSplitter::handle { background: #555555; width: 1px; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._doc = PDFDocument()
        self._current_tool = Tool.SELECT
        self._highlight_color = "Gelb"

        self.setWindowTitle("PDFreader")
        self.setMinimumSize(900, 640)
        self.setStyleSheet(_MAIN_STYLE)

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()
        self._set_actions_enabled(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._viewer = PDFViewer(self._doc)
        self._viewer.page_changed.connect(self._on_page_changed)
        self._viewer.annotation_added.connect(self._on_annotation_added)

        self._thumbs = ThumbnailPanel(self._doc)
        self._thumbs.page_selected.connect(self._viewer.go_to_page)
        self._thumbs.page_selected.connect(self._on_page_changed)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._thumbs)
        splitter.addWidget(self._viewer)
        splitter.setSizes([150, 750])
        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        self._splitter = splitter

        self.setCentralWidget(splitter)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # --- File ---
        file_menu = mb.addMenu("Datei")

        act_open = QAction("Öffnen …", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_file)
        file_menu.addAction(act_open)

        self._act_save = QAction("Speichern", self)
        self._act_save.setShortcut(QKeySequence.StandardKey.Save)
        self._act_save.triggered.connect(self.save_file)
        file_menu.addAction(self._act_save)

        self._act_save_as = QAction("Speichern unter …", self)
        self._act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._act_save_as.triggered.connect(self.save_file_as)
        file_menu.addAction(self._act_save_as)

        file_menu.addSeparator()

        self._act_export = QAction("Exportieren / Format ändern …", self)
        self._act_export.setShortcut(QKeySequence("Ctrl+E"))
        self._act_export.triggered.connect(self.export_file)
        file_menu.addAction(self._act_export)

        file_menu.addSeparator()

        act_close = QAction("Schließen", self)
        act_close.triggered.connect(self.close_file)
        file_menu.addAction(act_close)

        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(act_quit)

        # --- View ---
        view_menu = mb.addMenu("Ansicht")

        self._act_zoom_in = QAction("Vergrößern", self)
        self._act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self._act_zoom_in.triggered.connect(self._viewer.zoom_in)
        view_menu.addAction(self._act_zoom_in)

        self._act_zoom_out = QAction("Verkleinern", self)
        self._act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self._act_zoom_out.triggered.connect(self._viewer.zoom_out)
        view_menu.addAction(self._act_zoom_out)

        self._act_zoom_reset = QAction("Originalgröße", self)
        self._act_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        self._act_zoom_reset.triggered.connect(lambda: self._viewer.set_zoom(DEFAULT_ZOOM))
        view_menu.addAction(self._act_zoom_reset)

        view_menu.addSeparator()

        self._act_toggle_thumbs = QAction("Seitenleiste anzeigen", self)
        self._act_toggle_thumbs.setCheckable(True)
        self._act_toggle_thumbs.setChecked(True)
        self._act_toggle_thumbs.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(self._act_toggle_thumbs)

        view_menu.addSeparator()

        self._act_goto = QAction("Zur Seite …", self)
        self._act_goto.setShortcut(QKeySequence("Ctrl+G"))
        self._act_goto.triggered.connect(self._goto_page)
        view_menu.addAction(self._act_goto)

        # --- Tools ---
        tools_menu = mb.addMenu("Werkzeuge")

        self._act_tool_select = QAction("Auswahl / Blättern", self)
        self._act_tool_select.setCheckable(True)
        self._act_tool_select.setChecked(True)
        self._act_tool_select.triggered.connect(lambda: self._set_tool(Tool.SELECT))
        tools_menu.addAction(self._act_tool_select)

        self._act_tool_highlight = QAction("Markieren", self)
        self._act_tool_highlight.setCheckable(True)
        self._act_tool_highlight.triggered.connect(lambda: self._set_tool(Tool.HIGHLIGHT))
        tools_menu.addAction(self._act_tool_highlight)

        self._act_tool_text = QAction("Text einfügen", self)
        self._act_tool_text.setCheckable(True)
        self._act_tool_text.triggered.connect(lambda: self._set_tool(Tool.TEXT))
        tools_menu.addAction(self._act_tool_text)

        self._act_tool_note = QAction("Notiz hinzufügen", self)
        self._act_tool_note.setCheckable(True)
        self._act_tool_note.triggered.connect(lambda: self._set_tool(Tool.NOTE))
        tools_menu.addAction(self._act_tool_note)

        tools_menu.addSeparator()

        self._act_search = QAction("Suchen …", self)
        self._act_search.setShortcut(QKeySequence.StandardKey.Find)
        self._act_search.triggered.connect(self._toggle_search)
        tools_menu.addAction(self._act_search)

        self._tool_actions = [
            self._act_tool_select,
            self._act_tool_highlight,
            self._act_tool_text,
            self._act_tool_note,
        ]

    def _build_toolbar(self) -> None:
        tb = QToolBar("Hauptleiste", self)
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        # Open / Save
        btn_open = QToolButton()
        btn_open.setText("📂 Öffnen")
        btn_open.clicked.connect(self.open_file)
        tb.addWidget(btn_open)

        self._btn_save = QToolButton()
        self._btn_save.setText("💾 Speichern")
        self._btn_save.clicked.connect(self.save_file)
        tb.addWidget(self._btn_save)

        tb.addSeparator()

        # Tools
        self._btn_select = QToolButton()
        self._btn_select.setText("↖ Auswahl")
        self._btn_select.setCheckable(True)
        self._btn_select.setChecked(True)
        self._btn_select.clicked.connect(lambda: self._set_tool(Tool.SELECT))
        tb.addWidget(self._btn_select)

        self._btn_highlight = QToolButton()
        self._btn_highlight.setText("🖊 Markieren")
        self._btn_highlight.setCheckable(True)
        self._btn_highlight.clicked.connect(lambda: self._set_tool(Tool.HIGHLIGHT))
        tb.addWidget(self._btn_highlight)

        # Highlight color picker
        self._color_combo = QComboBox()
        for name in HIGHLIGHT_COLORS:
            self._color_combo.addItem(name)
        self._color_combo.setFixedWidth(80)
        self._color_combo.currentTextChanged.connect(self._on_color_changed)
        tb.addWidget(self._color_combo)

        self._btn_text = QToolButton()
        self._btn_text.setText("T Text")
        self._btn_text.setCheckable(True)
        self._btn_text.clicked.connect(lambda: self._set_tool(Tool.TEXT))
        tb.addWidget(self._btn_text)

        self._btn_note = QToolButton()
        self._btn_note.setText("📌 Notiz")
        self._btn_note.setCheckable(True)
        self._btn_note.clicked.connect(lambda: self._set_tool(Tool.NOTE))
        tb.addWidget(self._btn_note)

        tb.addSeparator()

        # Zoom
        btn_zoom_out = QToolButton()
        btn_zoom_out.setText("−")
        btn_zoom_out.clicked.connect(self._viewer.zoom_out)
        tb.addWidget(btn_zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(46)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet("color: #cccccc; font-size: 13px;")
        tb.addWidget(self._zoom_label)

        btn_zoom_in = QToolButton()
        btn_zoom_in.setText("+")
        btn_zoom_in.clicked.connect(self._viewer.zoom_in)
        tb.addWidget(btn_zoom_in)

        tb.addSeparator()

        # Search
        self._btn_search = QToolButton()
        self._btn_search.setText("🔍 Suchen")
        self._btn_search.setCheckable(True)
        self._btn_search.clicked.connect(self._toggle_search)
        tb.addWidget(self._btn_search)

        tb.addSeparator()

        # Export
        btn_export = QToolButton()
        btn_export.setText("⬆ Exportieren")
        btn_export.clicked.connect(self.export_file)
        tb.addWidget(btn_export)

        self._tool_buttons = {
            Tool.SELECT:    self._btn_select,
            Tool.HIGHLIGHT: self._btn_highlight,
            Tool.TEXT:      self._btn_text,
            Tool.NOTE:      self._btn_note,
        }

        # Search bar (hidden by default)
        from .dialogs import SearchBar
        self._search_bar = SearchBar()
        self._search_bar.setVisible(False)
        self._search_bar.search_requested.connect(self._do_search)
        self._search_bar.closed.connect(self._close_search)

        # Add search bar as a second toolbar row
        tb2 = QToolBar("Suche", self)
        tb2.setMovable(False)
        tb2.addWidget(self._search_bar)
        tb2.setVisible(False)
        self._search_toolbar = tb2
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb2)

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        self._lbl_page = QLabel("Keine Datei geöffnet")
        self._lbl_page.setStyleSheet("padding: 0 8px;")
        sb.addWidget(self._lbl_page)

        self._lbl_file = QLabel("")
        self._lbl_file.setStyleSheet("padding: 0 8px; color: #888888;")
        sb.addPermanentWidget(self._lbl_file)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open_file(self) -> None:
        if self._doc.modified:
            if not self._confirm_discard():
                return
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF öffnen", "", "PDF-Dateien (*.pdf)"
        )
        if not path:
            return
        if self._doc.is_open:
            self._doc.close()
        if self._doc.open(path):
            self._viewer.load_document()
            self._thumbs.load_document()
            self._set_actions_enabled(True)
            self._update_status(0)
            self._viewer.go_to_page(0)
        else:
            QMessageBox.critical(self, "Fehler", f"PDF konnte nicht geöffnet werden:\n{path}")

    def save_file(self) -> None:
        if not self._doc.is_open:
            return
        if self._doc.save():
            self.statusBar().showMessage("Gespeichert.", 3000)
        else:
            QMessageBox.warning(self, "Fehler", "Speichern fehlgeschlagen.")

    def save_file_as(self) -> None:
        if not self._doc.is_open:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Speichern unter", str(self._doc.path or ""), "PDF-Dateien (*.pdf)"
        )
        if path:
            if not path.endswith(".pdf"):
                path += ".pdf"
            if self._doc.save(path):
                self.statusBar().showMessage(f"Gespeichert: {path}", 3000)
            else:
                QMessageBox.warning(self, "Fehler", "Speichern fehlgeschlagen.")

    def close_file(self) -> None:
        if not self._doc.is_open:
            return
        if self._doc.modified and not self._confirm_discard():
            return
        self._doc.close()
        self._viewer._clear()
        self._thumbs._list.clear()
        self._set_actions_enabled(False)
        self._lbl_page.setText("Keine Datei geöffnet")
        self._lbl_file.setText("")
        self.setWindowTitle("PDFreader")

    def export_file(self) -> None:
        if not self._doc.is_open:
            return
        from .dialogs import ExportDialog
        dlg = ExportDialog(self)
        if not dlg.exec():
            return

        fmt = dlg.selected_format
        stem = self._doc.path.stem if self._doc.path else "export"
        parent_dir = str(self._doc.path.parent) if self._doc.path else ""

        if fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(
                self, "PDF speichern unter", f"{parent_dir}/{stem}_kopie.pdf",
                "PDF-Dateien (*.pdf)"
            )
            if path:
                self._doc.save(path)

        elif fmt == "txt":
            path, _ = QFileDialog.getSaveFileName(
                self, "Als Text speichern", f"{parent_dir}/{stem}.txt",
                "Textdateien (*.txt)"
            )
            if path:
                ok = self._doc.export_text(path)
                self._show_export_result(ok, path)

        elif fmt == "docx":
            path, _ = QFileDialog.getSaveFileName(
                self, "Als Word speichern", f"{parent_dir}/{stem}.docx",
                "Word-Dokumente (*.docx)"
            )
            if path:
                ok = self._doc.export_docx(path)
                self._show_export_result(ok, path)

        elif fmt in ("png", "jpg"):
            directory = QFileDialog.getExistingDirectory(
                self, "Ordner für Bildexport wählen", parent_dir
            )
            if directory:
                ok = self._doc.export_images(directory, fmt=fmt)
                self._show_export_result(ok, directory)

    def _show_export_result(self, ok: bool, path: str) -> None:
        if ok:
            self.statusBar().showMessage(f"Exportiert nach: {path}", 4000)
        else:
            QMessageBox.warning(self, "Export fehlgeschlagen",
                                "Der Export konnte nicht abgeschlossen werden.\n"
                                "Prüfe, ob alle benötigten Pakete installiert sind.")

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def _set_tool(self, tool: Tool) -> None:
        self._current_tool = tool
        self._viewer.set_tool(tool)
        for t, btn in self._tool_buttons.items():
            btn.setChecked(t == tool)
        for act in self._tool_actions:
            act.setChecked(False)
        tool_to_act = {
            Tool.SELECT:    self._act_tool_select,
            Tool.HIGHLIGHT: self._act_tool_highlight,
            Tool.TEXT:      self._act_tool_text,
            Tool.NOTE:      self._act_tool_note,
        }
        if tool in tool_to_act:
            tool_to_act[tool].setChecked(True)

    def _on_color_changed(self, name: str) -> None:
        self._highlight_color = name
        self._viewer.set_highlight_color(name)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _toggle_search(self) -> None:
        visible = not self._search_bar.isVisible()
        self._search_bar.setVisible(visible)
        self._search_toolbar.setVisible(visible)
        self._btn_search.setChecked(visible)
        if visible:
            self._search_bar.focus_input()
        else:
            self._viewer.clear_search()

    def _close_search(self) -> None:
        self._search_bar.setVisible(False)
        self._search_toolbar.setVisible(False)
        self._btn_search.setChecked(False)
        self._viewer.clear_search()

    def _do_search(self, query: str) -> None:
        if not query or not self._doc.is_open:
            self._viewer.clear_search()
            return
        results = self._doc.search(query)
        self._viewer.show_search_results(results)
        total = sum(len(v) for v in results.values())
        self.statusBar().showMessage(
            f'Suche: {total} Treffer fuer "{query}"' if total else f'Kein Ergebnis fuer "{query}"',
            4000,
        )
        if results:
            first_page = next(iter(results))
            self._viewer.go_to_page(first_page)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _goto_page(self) -> None:
        if not self._doc.is_open:
            return
        from .dialogs import GoToPageDialog
        current = getattr(self._viewer, "_current_page", 0)
        dlg = GoToPageDialog(current, self._doc.page_count, self)
        if dlg.exec():
            self._viewer.go_to_page(dlg.result_page)

    def _toggle_sidebar(self, checked: bool) -> None:
        self._thumbs.setVisible(checked)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_page_changed(self, page_num: int) -> None:
        self._update_status(page_num)
        self._thumbs.set_current_page(page_num)

    def _on_annotation_added(self, page_num: int) -> None:
        self._thumbs.refresh_page(page_num)
        self.setWindowTitle(f"PDFreader — {self._doc.path.name} *" if self._doc.path else "PDFreader *")

    def _update_status(self, page_num: int) -> None:
        total = self._doc.page_count
        zoom = int(self._viewer.current_zoom() * 100)
        self._lbl_page.setText(f"Seite {page_num + 1} / {total}   |   {zoom}%")
        self._zoom_label.setText(f"{zoom}%")
        if self._doc.path:
            self._lbl_file.setText(self._doc.path.name)
            self.setWindowTitle(f"PDFreader — {self._doc.path.name}")

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._doc.modified:
            reply = QMessageBox.question(
                self, "Ungespeicherte Änderungen",
                "Es gibt ungespeicherte Änderungen. Vor dem Beenden speichern?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_actions_enabled(self, enabled: bool) -> None:
        for act in (self._act_save, self._act_save_as, self._act_export,
                    self._act_zoom_in, self._act_zoom_out, self._act_zoom_reset,
                    self._act_goto, self._act_search,
                    self._act_tool_select, self._act_tool_highlight,
                    self._act_tool_text, self._act_tool_note):
            act.setEnabled(enabled)
        self._btn_save.setEnabled(enabled)
        for btn in self._tool_buttons.values():
            btn.setEnabled(enabled)
        self._color_combo.setEnabled(enabled)

    def _confirm_discard(self) -> bool:
        reply = QMessageBox.question(
            self, "Änderungen verwerfen?",
            "Es gibt ungespeicherte Änderungen. Trotzdem fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes
