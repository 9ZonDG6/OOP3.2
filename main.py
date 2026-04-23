import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("DepartureMono Nerd Font Mono", 11))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
