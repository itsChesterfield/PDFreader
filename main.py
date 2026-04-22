import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("PDFreader")
    app.setOrganizationName("PDFreader")
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    window = MainWindow()
    window.resize(1200, 800)
    window.show()

    # Open file passed as CLI argument
    if len(sys.argv) > 1:
        import pathlib
        path = pathlib.Path(sys.argv[1])
        if path.is_file() and path.suffix.lower() == ".pdf":
            if window._doc.open(str(path)):
                window._viewer.load_document()
                window._thumbs.load_document()
                window._set_actions_enabled(True)
                window._update_status(0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
