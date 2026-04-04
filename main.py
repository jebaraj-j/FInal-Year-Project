"""
GestureVox — Desktop Application Entry Point
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import QFont

from ui.main_window          import MainWindow
from controller.app_controller import AppController


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("GestureVox")
    app.setFont(QFont("Segoe UI", 10))

    window     = MainWindow()
    controller = AppController(window)   # noqa: F841
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
