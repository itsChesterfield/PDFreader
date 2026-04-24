import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow
from src.theme import APP_STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Verdant Reader")
    app.setOrganizationName("VerdantReader")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.resize(1280, 820)
    window.show()

    # Open file passed as CLI argument
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_file() and path.suffix.lower() == ".pdf":
            window._load_path(str(path))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
