from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_DIALOG_STYLE = """
QDialog {
    background: #2b2b2b;
    color: #dddddd;
}
QLabel { color: #cccccc; }
QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {
    background: #3c3f41;
    color: #dddddd;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
}
QPushButton {
    background: #4b6eaf;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
}
QPushButton:hover { background: #5c82cc; }
QPushButton[text="Abbrechen"] { background: #555555; }
"""


# ---------------------------------------------------------------------------
# Note dialog
# ---------------------------------------------------------------------------

class NoteDialog(QDialog):
    """Dialog for entering a sticky-note annotation."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.result_text = ""
        self.setWindowTitle("Notiz hinzufügen")
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Notizinhalt:"))

        self._edit = QPlainTextEdit()
        self._edit.setPlaceholderText("Notiz eingeben …")
        self._edit.setMinimumHeight(100)
        layout.addWidget(self._edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Hinzufügen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.result_text = self._edit.toPlainText().strip()
        self.accept()


# ---------------------------------------------------------------------------
# Free-text annotation dialog
# ---------------------------------------------------------------------------

class TextAnnotDialog(QDialog):
    """Dialog for entering inline text to place on the PDF."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.result_text = ""
        self.result_size = 11
        self.setWindowTitle("Text einfügen")
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)

        form = QFormLayout(self)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(10)

        self._edit = QPlainTextEdit()
        self._edit.setPlaceholderText("Text eingeben …")
        self._edit.setMinimumHeight(80)
        form.addRow("Text:", self._edit)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.setValue(11)
        self._size_spin.setSuffix(" pt")
        form.addRow("Schriftgröße:", self._size_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Einfügen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        self.result_text = self._edit.toPlainText().strip()
        self.result_size = self._size_spin.value()
        self.accept()


# ---------------------------------------------------------------------------
# Export dialog
# ---------------------------------------------------------------------------

class ExportDialog(QDialog):
    """Dialog for exporting the PDF to another format."""

    FORMATS = {
        "PDF speichern unter …":     "pdf",
        "Nur Text (.txt)":           "txt",
        "Word-Dokument (.docx)":     "docx",
        "Bilder – PNG (pro Seite)":  "png",
        "Bilder – JPEG (pro Seite)": "jpg",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportieren / Dateiformat ändern")
        self.setMinimumWidth(400)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Zielformat wählen:"))

        self._combo = QComboBox()
        for label in self.FORMATS:
            self._combo.addItem(label)
        layout.addWidget(self._combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Exportieren …")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def selected_format(self) -> str:
        return self.FORMATS[self._combo.currentText()]


# ---------------------------------------------------------------------------
# Search bar (inline widget, not a dialog)
# ---------------------------------------------------------------------------

class SearchBar(QWidget):
    """Compact search widget embedded in the toolbar area."""

    from PyQt6.QtCore import pyqtSignal
    search_requested = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QWidget { background: #3c3f41; }"
            "QLineEdit { background: #2b2b2b; color: #dddddd; border: 1px solid #555; "
            "border-radius: 3px; padding: 3px 6px; }"
            "QPushButton { background: transparent; color: #aaaaaa; border: none; padding: 2px 6px; }"
            "QPushButton:hover { color: white; }"
        )
        from PyQt6.QtWidgets import QHBoxLayout
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(4)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Suchen …")
        self._input.setFixedWidth(200)
        self._input.returnPressed.connect(self._on_search)
        row.addWidget(self._input)

        btn_find = QPushButton("Suchen")
        btn_find.clicked.connect(self._on_search)
        row.addWidget(btn_find)

        btn_close = QPushButton("✕")
        btn_close.setFixedWidth(24)
        btn_close.clicked.connect(self.closed)
        row.addWidget(btn_close)

    def focus_input(self) -> None:
        self._input.setFocus()
        self._input.selectAll()

    def _on_search(self) -> None:
        self.search_requested.emit(self._input.text().strip())


# ---------------------------------------------------------------------------
# Go-to-page dialog
# ---------------------------------------------------------------------------

class GoToPageDialog(QDialog):
    def __init__(self, current: int, total: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.result_page = current
        self.setWindowTitle("Zur Seite …")
        self.setFixedWidth(260)
        self.setStyleSheet(_DIALOG_STYLE)

        form = QFormLayout(self)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(10)

        self._spin = QSpinBox()
        self._spin.setRange(1, total)
        self._spin.setValue(current + 1)
        form.addRow(f"Seite (1–{total}):", self._spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Gehe zu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        self.result_page = self._spin.value() - 1
        self.accept()
