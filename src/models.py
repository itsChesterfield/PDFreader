"""In-memory data models for Verdant PDF Reader."""
from __future__ import annotations

import time
from typing import Optional


class Document:
    _next_id = 1

    def __init__(self, path: str, title: str, pages: int) -> None:
        self.id = Document._next_id
        Document._next_id += 1
        self.path = path
        self.title = title
        self.pages = pages
        self.progress: float = 0.0      # 0–1
        self.current_page: int = 0      # 0-based
        self.bookmarked: bool = False
        self.category: str = "Allgemein"
        self.modified: str = time.strftime("%d.%m.%Y")
        self.bookmarks: list[Bookmark] = []
        self.v_annotations: list[VAnnotation] = []

    def update_progress(self, page: int) -> None:
        self.current_page = page
        self.progress = page / max(1, self.pages - 1) if self.pages > 1 else 0.0

    def size_label(self) -> str:
        return f"{self.pages} Seiten"


class Bookmark:
    _next_id = 1

    def __init__(self, title: str, page: int, note: str = "") -> None:
        self.id = Bookmark._next_id
        Bookmark._next_id += 1
        self.title = title
        self.page = page    # 0-based
        self.note = note


class VAnnotation:
    """Viewer annotation stored in memory and shown in the right panel."""

    _next_id = 1
    COLOR_HEX = {
        "green":  "#3dba6a",
        "yellow": "#c49a28",
        "red":    "#b94040",
    }

    def __init__(self, page: int, text: str, y: float = 0.5, color: str = "green") -> None:
        self.id = VAnnotation._next_id
        VAnnotation._next_id += 1
        self.page = page    # 0-based
        self.text = text
        self.y = y          # 0–1 relative Y position on page
        self.color = color  # "green" | "yellow" | "red"


class DocumentLibrary:
    def __init__(self) -> None:
        self._docs: dict[int, Document] = {}
        self._active_id: Optional[int] = None

    def open(self, path: str, title: str, pages: int) -> Document:
        for doc in self._docs.values():
            if doc.path == path:
                self._active_id = doc.id
                return doc
        doc = Document(path, title, pages)
        self._docs[doc.id] = doc
        self._active_id = doc.id
        return doc

    def active(self) -> Optional[Document]:
        return self._docs.get(self._active_id)

    def activate(self, doc_id: int) -> Optional[Document]:
        if doc_id in self._docs:
            self._active_id = doc_id
        return self._docs.get(doc_id)

    def all_docs(self) -> list[Document]:
        return list(self._docs.values())
