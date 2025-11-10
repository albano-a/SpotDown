from PyQt5 import uic
from PyQt5.QtCore import QFile
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys

SDMW = "gui/qt/MainWindow.ui"


class SpotDownMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi(SDMW, self)

        self.init_ui()
        self.show()

    def init_ui(self):
        self.OutputFolderLabel.hide()
        self.ConversionProgressLabel.hide()
        self.ConversionProgressBar.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SpotDownMainWindow()
    sys.exit(app.exec())
