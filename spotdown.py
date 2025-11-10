from PyQt5 import uic
from PyQt5.QtCore import QFile, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
import sys
import os
import threading
import subprocess
import csv
import re
import json
import time
import sys
import zipfile
import shutil
from datetime import timedelta
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Tags
from pathlib import PureWindowsPath
import webbrowser
import platform

SDMW = "gui/qt/MainWindow.ui"


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


CONFIG_FILE = resource_path("config.json")


def load_config():
    default = {
        "variants": [],
        "duration_min": 30,
        "duration_max": 600,
        "transcode_mp3": "false",
        "generate_m3u": "true",
        "exclude_instrumentals": "false",
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return {**default, **cfg}
        except:
            return default
    return default


class SpotDownMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print(CONFIG_FILE)
        uic.loadUi(SDMW, self)

        self.init_ui()
        self.show()

    def init_ui(self):
        self.OutputFolderLabel.hide()
        self.ConversionProgressLabel.hide()
        self.ConversionProgressBar.hide()

        self.ExportifyButton.clicked.connect(self.open_exportify)
        self.TuneMyMusicButton.clicked.connect(self.open_tunemymusic)
        self.LoadFilePath.clicked.connect(self.load_file_path)
        self.ChooseOutputFolderButton.clicked.connect(self.choose_output_folder)

    def choose_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder", "")
        if folder_path:
            self.OutputFolderLabel.setText(folder_path)
            self.OutputFolderLabel.show()

    def load_file_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Playlist File", "", "All Files (*)"
        )
        if file_path:
            self.FilenameInput.setText(file_path)

    def open_exportify(self):
        url = QUrl("https://exportify.net/")
        QDesktopServices.openUrl(url)

    def open_tunemymusic(self):
        url = QUrl("https://www.tunemymusic.com/")
        QDesktopServices.openUrl(url)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SpotDownMainWindow()
    sys.exit(app.exec())
