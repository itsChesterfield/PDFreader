from __future__ import annotations

from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from .constants import RENDER_DPI


class PDFDocument:
    """Thin wrapper around fitz.Document that centralises all PDF operations."""

    def __init__(self) -> None:
        self._doc: Optional[fitz.Document] = None
        self._path: Optional[Path] = None
        self._modified: bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc else 0

    @property
    def path(self) -> Optional[Path]:
        return self._path

    @property
    def modified(self) -> bool:
        return self._modified

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    def open(self, path: str) -> bool:
        try:
            self._doc = fitz.open(path)
            self._path = Path(path)
            self._modified = False
            return True
        except Exception as exc:
            print(f"PDFDocument.open error: {exc}")
            return False

    def close(self) -> None:
        if self._doc:
            self._doc.close()
        self._doc = None
        self._path = None
        self._modified = False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_page(self, page_num: int, zoom: float = 1.0) -> Optional[bytes]:
        """Return the page as PNG bytes at the given zoom level."""
        page = self._get_page(page_num)
        if page is None:
            return None
        scale = zoom * RENDER_DPI / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")

    def page_size_px(self, page_num: int, zoom: float = 1.0) -> tuple[int, int]:
        """Return (width, height) in pixels for the given zoom level."""
        page = self._get_page(page_num)
        if page is None:
            return (0, 0)
        scale = zoom * RENDER_DPI / 72.0
        w = int(page.rect.width * scale)
        h = int(page.rect.height * scale)
        return (w, h)

    # ------------------------------------------------------------------
    # Annotation helpers
    # ------------------------------------------------------------------

    def add_highlight(
        self,
        page_num: int,
        widget_rect: tuple[float, float, float, float],
        zoom: float,
        color: tuple[float, float, float] = (1.0, 1.0, 0.0),
    ) -> bool:
        page = self._get_page(page_num)
        if page is None:
            return False
        pdf_rect = self._to_pdf_rect(widget_rect, zoom)
        words = page.get_text("words", clip=pdf_rect)
        if not words:
            return False
        quads = [fitz.Rect(w[0], w[1], w[2], w[3]).quad for w in words]
        annot = page.add_highlight_annot(quads)
        annot.set_colors(stroke=color)
        annot.update()
        self._modified = True
        return True

    def add_freetext(
        self,
        page_num: int,
        widget_point: tuple[float, float],
        zoom: float,
        text: str,
        font_size: int = 11,
    ) -> bool:
        page = self._get_page(page_num)
        if page is None:
            return False
        px, py = self._to_pdf_point(widget_point, zoom)
        # Build a reasonable rect for the text box (will expand automatically)
        rect = fitz.Rect(px, py, px + 180, py + 40)
        annot = page.add_freetext_annot(
            rect,
            text,
            fontsize=font_size,
            text_color=(0.0, 0.0, 0.0),
            fill_color=(1.0, 1.0, 0.8),
            border_color=(0.6, 0.6, 0.0),
        )
        annot.update()
        self._modified = True
        return True

    def add_note(
        self,
        page_num: int,
        widget_point: tuple[float, float],
        zoom: float,
        content: str,
    ) -> bool:
        page = self._get_page(page_num)
        if page is None:
            return False
        px, py = self._to_pdf_point(widget_point, zoom)
        annot = page.add_text_annot(fitz.Point(px, py), content)
        annot.update()
        self._modified = True
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> dict[int, list]:
        """Return {page_num: [fitz.Rect, ...]} for all hits."""
        if not self._doc or not query:
            return {}
        results: dict[int, list] = {}
        for i in range(self.page_count):
            hits = self._doc[i].search_for(query)
            if hits:
                results[i] = hits
        return results

    # ------------------------------------------------------------------
    # Save / export
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None) -> bool:
        if not self._doc:
            return False
        try:
            target = str(path) if path else str(self._path)
            if path and str(path) != str(self._path):
                self._doc.save(target, garbage=4, deflate=True)
                self._path = Path(target)
            else:
                # Incremental save preserves existing data
                try:
                    self._doc.saveIncr()
                except Exception:
                    self._doc.save(target, garbage=4, deflate=True)
            self._modified = False
            return True
        except Exception as exc:
            print(f"PDFDocument.save error: {exc}")
            return False

    def export_text(self, path: str) -> bool:
        if not self._doc:
            return False
        try:
            with open(path, "w", encoding="utf-8") as fh:
                for i in range(self.page_count):
                    fh.write(f"\n{'='*60}\nSeite {i + 1}\n{'='*60}\n")
                    fh.write(self._doc[i].get_text())
            return True
        except Exception as exc:
            print(f"export_text error: {exc}")
            return False

    def export_images(self, directory: str, fmt: str = "png", zoom: float = 2.0) -> bool:
        if not self._doc:
            return False
        try:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            stem = self._path.stem if self._path else "seite"
            mat = fitz.Matrix(zoom, zoom)
            for i in range(self.page_count):
                pix = self._doc[i].get_pixmap(matrix=mat, alpha=False)
                out = dir_path / f"{stem}_seite_{i + 1:03d}.{fmt}"
                pix.save(str(out))
            return True
        except Exception as exc:
            print(f"export_images error: {exc}")
            return False

    def export_docx(self, path: str) -> bool:
        if not self._doc:
            return False
        try:
            from docx import Document  # type: ignore
            from docx.shared import Pt  # type: ignore

            doc = Document()
            title = self._path.stem if self._path else "Dokument"
            doc.add_heading(title, level=0)
            for i in range(self.page_count):
                if i > 0:
                    doc.add_page_break()
                doc.add_heading(f"Seite {i + 1}", level=1)
                for block in self._doc[i].get_text("blocks"):
                    if block[6] == 0:  # text block
                        text = block[4].strip()
                        if text:
                            doc.add_paragraph(text)
            doc.save(path)
            return True
        except ImportError:
            print("python-docx nicht installiert.")
            return False
        except Exception as exc:
            print(f"export_docx error: {exc}")
            return False

    def get_toc(self) -> list:
        return self._doc.get_toc() if self._doc else []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_page(self, page_num: int) -> Optional[fitz.Page]:
        if self._doc and 0 <= page_num < self.page_count:
            return self._doc[page_num]
        return None

    def _scale(self, zoom: float) -> float:
        return zoom * RENDER_DPI / 72.0

    def _to_pdf_rect(
        self, widget_rect: tuple[float, float, float, float], zoom: float
    ) -> fitz.Rect:
        s = self._scale(zoom)
        x0, y0, x1, y1 = widget_rect
        return fitz.Rect(x0 / s, y0 / s, x1 / s, y1 / s)

    def _to_pdf_point(
        self, widget_point: tuple[float, float], zoom: float
    ) -> tuple[float, float]:
        s = self._scale(zoom)
        return (widget_point[0] / s, widget_point[1] / s)
