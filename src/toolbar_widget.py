"""Custom toolbar widget (replaces QToolBar) — Verdant style."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget,
)

from .theme import (
    ACCENT, ACCENT2, ACCENT_DIM, BORDER, MUTED, SURFACE, SURFACE2,
    SURFACE3, TEXT, TOOLBAR_H,
)

_BTN = (
    f"QPushButton{{background:transparent;color:{MUTED};border:none;"
    f"border-radius:6px;padding:5px 9px;font-size:12px;}}"
    f"QPushButton:hover{{background:{SURFACE3};color:{TEXT};}}"
    f"QPushButton:checked{{background:{ACCENT_DIM};color:{ACCENT};}}"
    f"QPushButton:checked:hover{{background:{ACCENT_DIM};color:{ACCENT2};}}"
)
_BTN_ICON = (
    f"QPushButton{{background:transparent;color:{MUTED};border:none;"
    f"border-radius:6px;padding:4px;font-size:14px;min-width:28px;min-height:28px;}}"
    f"QPushButton:hover{{background:{SURFACE3};color:{TEXT};}}"
    f"QPushButton:checked{{background:{ACCENT_DIM};color:{ACCENT};}}"
)
_SEP = f"QFrame{{background:{BORDER};width:1px;max-width:1px;margin:8px 4px;}}"

_PAGE_INPUT = (
    f"QLineEdit{{background:{SURFACE2};color:{TEXT};border:1px solid {BORDER};"
    f"border-radius:4px;padding:2px 4px;font-family:'DM Mono','Consolas';"
    f"font-size:11px;text-align:center;}}"
    f"QLineEdit:focus{{border-color:{ACCENT};}}"
)


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet(_SEP)
    f.setFixedWidth(1)
    return f


def _icon_btn(text: str, tip: str = "", checkable: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setToolTip(tip)
    btn.setCheckable(checkable)
    btn.setStyleSheet(_BTN_ICON)
    return btn


class ToolBar(QWidget):
    """
    Signals:
      prev_page, next_page, page_jumped(int 0-based)
      zoom_in, zoom_out, zoom_reset, fit_width
      tool_changed(str)  — "highlight" | "comment" | "pen" | ""
      annotations_toggled(bool)
      open_file, save_file, download
    """

    prev_page            = pyqtSignal()
    next_page            = pyqtSignal()
    page_jumped          = pyqtSignal(int)    # 0-based
    zoom_in              = pyqtSignal()
    zoom_out             = pyqtSignal()
    zoom_reset           = pyqtSignal()
    fit_width_requested  = pyqtSignal()
    tool_changed         = pyqtSignal(str)
    annotations_toggled  = pyqtSignal(bool)
    open_file            = pyqtSignal()
    save_file            = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_H)
        self.setStyleSheet(
            f"QWidget{{background:{SURFACE};border-bottom:1px solid {BORDER};}}"
        )

        self._total_pages = 0
        self._current_page = 0
        self._active_tool: str = ""

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 8, 0)
        row.setSpacing(2)

        # ── File actions ──────────────────────────────────────────────
        btn_open = _icon_btn("⊕", "Datei oeffnen (Ctrl+O)")
        btn_open.clicked.connect(self.open_file)
        row.addWidget(btn_open)

        btn_save = _icon_btn("⬇", "Speichern (Ctrl+S)")
        btn_save.clicked.connect(self.save_file)
        row.addWidget(btn_save)
        self._btn_save = btn_save

        row.addWidget(_sep())

        # ── Document title ────────────────────────────────────────────
        self._title = QLabel("Kein Dokument")
        self._title.setStyleSheet(
            f"color:{TEXT};font-size:12px;font-weight:500;"
            f"background:transparent;border:none;"
        )
        self._title.setMaximumWidth(260)
        self._title.setSizePolicy(
            self._title.sizePolicy().horizontalPolicy(),
            self._title.sizePolicy().verticalPolicy(),
        )
        row.addWidget(self._title)
        row.addStretch(1)

        row.addWidget(_sep())

        # ── Page navigation ───────────────────────────────────────────
        btn_prev = _icon_btn("‹", "Vorherige Seite (←)")
        btn_prev.clicked.connect(self.prev_page)
        row.addWidget(btn_prev)

        self._page_input = QLineEdit("1")
        self._page_input.setFixedWidth(36)
        self._page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_input.setStyleSheet(_PAGE_INPUT)
        self._page_input.returnPressed.connect(self._on_page_entered)
        self._page_input.editingFinished.connect(self._on_page_entered)
        row.addWidget(self._page_input)

        self._page_total = QLabel("/ 0")
        self._page_total.setStyleSheet(
            f"color:{MUTED};font-family:'DM Mono','Consolas';font-size:11px;"
            f"background:transparent;border:none;"
        )
        row.addWidget(self._page_total)

        btn_next = _icon_btn("›", "Naechste Seite (→)")
        btn_next.clicked.connect(self.next_page)
        row.addWidget(btn_next)

        row.addWidget(_sep())

        # ── Zoom ──────────────────────────────────────────────────────
        btn_zm = _icon_btn("−", "Verkleinern (−)")
        btn_zm.clicked.connect(self.zoom_out)
        row.addWidget(btn_zm)

        self._zoom_btn = QPushButton("100%")
        self._zoom_btn.setToolTip("Klicken: Zoom zuruecksetzen")
        self._zoom_btn.setStyleSheet(
            f"QPushButton{{background:{SURFACE2};color:{ACCENT};border:1px solid {BORDER};"
            f"border-radius:4px;padding:3px 8px;font-family:'DM Mono','Consolas';"
            f"font-size:10px;font-weight:600;min-width:42px;}}"
            f"QPushButton:hover{{background:{SURFACE3};color:{ACCENT2};}}"
        )
        self._zoom_btn.clicked.connect(self.zoom_reset)
        row.addWidget(self._zoom_btn)

        btn_zp = _icon_btn("+", "Vergroessern (+)")
        btn_zp.clicked.connect(self.zoom_in)
        row.addWidget(btn_zp)

        btn_fit = _icon_btn("↔", "Breite anpassen")
        btn_fit.clicked.connect(self.fit_width_requested)
        row.addWidget(btn_fit)

        row.addWidget(_sep())

        # ── Annotation tools ──────────────────────────────────────────
        self._tool_btns: dict[str, QPushButton] = {}
        for tid, icon, tip in [
            ("highlight", "▨", "Markieren"),
            ("comment",   "◎", "Kommentar"),
            ("pen",       "✎", "Zeichnen"),
        ]:
            btn = _icon_btn(icon, tip, checkable=True)
            btn.clicked.connect(lambda _, t=tid: self._on_tool(t))
            self._tool_btns[tid] = btn
            row.addWidget(btn)

        row.addWidget(_sep())

        # ── Annotations panel toggle ──────────────────────────────────
        self._btn_annots = QPushButton("Anmerkungen")
        self._btn_annots.setCheckable(True)
        self._btn_annots.setStyleSheet(
            f"QPushButton{{background:transparent;color:{MUTED};"
            f"border:1px solid transparent;border-radius:6px;"
            f"padding:4px 10px;font-size:11px;}}"
            f"QPushButton:hover{{border-color:{BORDER};color:{TEXT};}}"
            f"QPushButton:checked{{border-color:{ACCENT};color:{ACCENT};"
            f"background:{ACCENT_DIM};}}"
        )
        self._btn_annots.toggled.connect(self.annotations_toggled)
        row.addWidget(self._btn_annots)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_document(self, title: str, total_pages: int) -> None:
        self._total_pages = total_pages
        # Truncate long titles
        display = title if len(title) <= 32 else title[:29] + "..."
        self._title.setText(display)
        self._title.setToolTip(title)
        self._page_total.setText(f"/ {total_pages}")
        self._page_input.setText("1")
        self._btn_save.setEnabled(True)

    def set_page(self, page: int) -> None:
        """Update display without emitting signal (0-based)."""
        self._current_page = page
        self._page_input.blockSignals(True)
        self._page_input.setText(str(page + 1))
        self._page_input.blockSignals(False)

    def set_zoom(self, zoom: float) -> None:
        self._zoom_btn.setText(f"{int(zoom * 100)}%")

    def set_annotations_visible(self, visible: bool) -> None:
        self._btn_annots.blockSignals(True)
        self._btn_annots.setChecked(visible)
        self._btn_annots.blockSignals(False)

    def deselect_tool(self) -> None:
        for btn in self._tool_btns.values():
            btn.setChecked(False)
        self._active_tool = ""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_page_entered(self) -> None:
        try:
            p = int(self._page_input.text()) - 1
            p = max(0, min(p, self._total_pages - 1))
        except ValueError:
            p = self._current_page
        self.set_page(p)
        self.page_jumped.emit(p)

    def _on_tool(self, tid: str) -> None:
        if self._active_tool == tid:
            self._active_tool = ""
            self._tool_btns[tid].setChecked(False)
        else:
            self._active_tool = tid
            for t, btn in self._tool_btns.items():
                btn.setChecked(t == tid)
        self.tool_changed.emit(self._active_tool)
