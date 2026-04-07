"""G-Vox desktop application entry point."""

import os
import sys
from pathlib import Path

# Keep backend ML libraries quiet in console output.
# Must be set before importing modules that load TensorFlow/MediaPipe.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from controller.app_controller import AppController
from ui.main_window import MainWindow

PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("G-Vox")
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow()
    _controller = AppController(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
