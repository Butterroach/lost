"""
Lost: a hosts file manager for Linux

Copyright (C) 2025 Butterroach

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import platform
import re
import requests
import subprocess
import sys
from packaging.version import Version
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, QUrl, QStringListModel
from typing import Optional
from ui_form import Ui_App  # generate ui_form.py: pyside6-uic form.ui -o ui_form.py
from validateHosts import validateHostsFile

__version__ = "1.2.0"

TIMEOUT = 60


class HtmlWindow(QDialog):
    def __init__(self, html_content, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout()

        label = QLabel(self)
        label.setTextFormat(Qt.RichText)
        label.setText(html_content)
        label.linkActivated.connect(self.openLink)

        layout.addWidget(label)
        self.setLayout(layout)

    def openLink(self, link: str):
        # prevent any issues with opening browsers as root
        subprocess.Popen(
            [
                "sudo",
                "-u",
                os.getlogin(),  # this will NOT return root, it will return the actual human user (source: believe me)
                "xdg-open",
                link,
            ]
        )


class App(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        if platform.system() == "Windows" or "--pretend-like-im-windows" in sys.argv:
            QMessageBox.critical(
                self,
                "Windows is unsupported",
                "You are using Windows, which is NOT supported by Lost! While Lost can technically support Windows with a few tiny modifications, I just don't wanna do it. You have a million alternatives, pick one.",
            )
            sys.exit(127)

        self.unsavedChanges = False

        self.HOSTS_FILE = "/etc/hosts"  # * PLEASE set this to a file called "lost-test-hosts" somewhere that doesn't require root to access during development and testing PLEASEE
        self.HOSTS_SEPARATOR = "\n# ENTRIES MADE BY LOST START HERE, ADD CUSTOM ENTRIES ABOVE AND DO NOT EDIT THE BELOW\n"
        self.LOSTS_SEPARATOR = (
            r"(# LOST URL https?://\S+ 192919291222//\./\./\./\./\.)\n"
        )

        if os.geteuid() != 0 and self.HOSTS_FILE.split("/")[-1] != "lost-test-hosts":
            QMessageBox.critical(
                self,
                "Root required",
                "Lost requires root to run! I tried implementing some pkexec stuff for this but that didn't work out well, so...",
            )
            QMessageBox.warning(
                self,
                "Quick warning",
                "You're gonna be blinded by light mode QT if you run this in root lol (unless you wanna maybe set dark mode in root settings?)",
            )
            sys.exit(127)

        with open(self.HOSTS_FILE, "r") as f:
            self.hostsFile = f.read()

        self.hostsFileParts = self.hostsFile.split(self.HOSTS_SEPARATOR)

        if len(self.hostsFileParts) == 1:
            if "\n# LOST URL" in self.hostsFileParts[0]:
                QMessageBox.critical(
                    self,
                    "...",
                    "Did you REALLY remove that warning? Why would you do that?",
                )
                sys.exit(127)
            self.losts = []
        elif self.hostsFileParts[1].strip().replace("\n", "").replace("\r", "") == "":
            # the warning is there, but there are no losts
            self.losts = []
        elif len(self.hostsFileParts) > 2:
            QMessageBox.critical(
                self,
                "?????",
                "Can you NOT tamper with your hosts file like that???????",
            )
            sys.exit(127)
        else:
            self.losts = re.split(self.LOSTS_SEPARATOR, self.hostsFileParts[1])
            if not self.losts[0]:
                self.losts.pop(0)

        try:
            release_data = requests.get(
                "https://api.github.com/repos/Butterroach/lost/releases",
                timeout=5,
            ).json()
            latest_ver = Version(release_data["tag_name"])
            current_ver = Version(__version__)
            if current_ver < latest_ver:
                QMessageBox.information(
                    self,
                    "Update available",
                    f"An update is available! You are on {__version__}, the latest version is {latest_ver}. Please update!",
                )
        except:
            pass

        self.ui = Ui_App()
        self.ui.setupUi(self)

        self.aboutDialog = HtmlWindow(
            f'<DOCTYPE html!><html><body><h1>Lost {__version__}</h1><p><strong>Lost</strong> is a hosts file manager made for Linux.</p><p><a href="https://github.com/Butterroach/lost">Source code</a></p></body></html>',
            "About",
        )
        self.ui.actionExit.triggered.connect(app.exit)
        self.ui.actionAbout.triggered.connect(self.aboutDialog.show)
        self.ui.lineEdit.returnPressed.connect(self.addSource)

        self.model = QStringListModel()
        self.ui.listView.setModel(self.model)

        self.populateListView()

        self.ui.saveButton.clicked.connect(self.saveChanges)
        self.ui.removeButton.clicked.connect(self.removeSource)
        self.ui.updateButton.clicked.connect(self.updateSource)
        self.ui.updateAllButton.clicked.connect(self.updateAllSources)

    def getSelectedURL(self) -> Optional[str]:
        model = self.ui.listView.selectionModel()
        indexes = model.selectedIndexes()

        if indexes:
            data = self.ui.listView.model().data(indexes[0])
            if data:
                return data
        QMessageBox.critical(self, "No URL selected", "You need to select a URL!")

    def addSource(self):
        url = self.ui.lineEdit.text()
        for i in range(0, len(self.losts), 2):
            if url in self.losts[i]:
                QMessageBox.critical(
                    self,
                    "URL already exists",
                    "That URL already exists in the hosts file!",
                )
                return
        if not QUrl(url).isValid():
            QMessageBox.critical(self, "Invalid URL", "You entered an invalid URL.")
            return
        try:
            contents = requests.get(url, timeout=TIMEOUT).text
        except requests.exceptions.Timeout:
            QMessageBox.critical(
                self,
                "Your internet is terrible",
                "The request to the source URL timed out! Please check your internet connection and try again.",
            )
            return
        if not validateHostsFile(contents):
            QMessageBox.critical(
                self,
                "Invalid hosts file",
                "The contents of that hosts file is NOT valid!",
            )
            return
        self.losts.append(f"# LOST URL {url} 192919291222//././././.")
        self.losts.append(contents)
        self.populateListView()
        self.ui.lineEdit.clear()
        self.unsavedChanges = True

    def updateSource(self, url: str = None):
        notUpdateAll = False
        if (
            isinstance(url, bool) or url is None
        ):  # qt gives this function False as a parameter for whatever reason...
            notUpdateAll = True
            url = self.getSelectedURL()
            if url is None:
                return

        for i in range(0, len(self.losts), 2):
            if self.losts[i] == f"# LOST URL {url} 192919291222//././././.":
                try:
                    contents = requests.get(url, timeout=TIMEOUT).text
                except requests.exceptions.Timeout:
                    if notUpdateAll:
                        QMessageBox.critical(
                            self,
                            "Your internet is terrible",
                            "The update timed out! Please check your internet connection and try again.",
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "Your internet is terrible",
                            f"The update for {url} timed out! Please check your internet connection. Update will proceed with the other sources...",
                        )
                    return
                if contents.strip().replace("\n", "").replace("\r", "") == self.losts[
                    i + 1
                ].strip().replace("\n", "").replace("\r", ""):
                    if notUpdateAll:
                        QMessageBox.information(
                            self,
                            "Nothing to update",
                            "There was nothing to update. If you are SURE that there is an update, try flushing your cache.",
                        )
                    return
                if not validateHostsFile(contents):
                    if notUpdateAll:
                        QMessageBox.critical(
                            self,
                            "Invalid hosts file",
                            "The contents of the hosts file that you tried to update has now become invalid. You will need to stay on the older version. Please contact the hosts file maintainer about this.",
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "Invalid hosts file",
                            f"One of your hosts files has become invalid: {url}. You will need to stay on the older version of that hosts file. Please contact the hosts file maintainer about this. Update will continue with the other hosts files after you click OK or close this message box.",
                        )
                    return
                self.losts[i + 1] = contents
                self.populateListView()
                self.unsavedChanges = True
                if notUpdateAll:
                    QMessageBox.information(self, "Update done", "Done updating!")
                return
        QMessageBox.warning(
            self,
            "...What",
            "Idk how to explain this just urgently open a github issue now the url provided to update wasn't found",
        )

    def updateAllSources(self):
        for i in range(0, len(self.losts), 2):
            self.updateSource(self.losts[i].split(" ")[3])
        QMessageBox.information(self, "Update done", "Done updating!")

    def removeSource(self):
        url = self.getSelectedURL()
        if url is None:
            return
        for i in range(0, len(self.losts), 2):
            if url in self.losts[i]:
                self.losts.pop(i)
                self.losts.pop(i)
                self.populateListView()
                self.unsavedChanges = True
                return

    def populateListView(self):
        urls = []
        for i in range(0, len(self.losts), 2):
            url_comment = self.losts[i]
            match = re.search(
                r"# LOST URL (https?://\S+) 192919291222//\./\./\./\./\.", url_comment
            )
            if match:
                urls.append(match.group(1))
        self.model.setStringList(urls)

    def saveChanges(self):
        new_hosts_file = self.hostsFileParts[0] + self.HOSTS_SEPARATOR
        for i in range(0, len(self.losts), 2):
            url_comment = self.losts[i]
            domain_data = self.losts[i + 1]
            new_hosts_file += url_comment + "\n" + domain_data + "\n"

        with open(self.HOSTS_FILE, "w") as f:
            f.write(new_hosts_file)

        self.unsavedChanges = False

        QMessageBox.information(
            self, "Saved", "Changes have been saved to the hosts file!"
        )

    def closeEvent(self, event):
        if self.unsavedChanges:
            response = QMessageBox.question(
                self,
                "Unsaved changes!!",
                "You have unsaved changes! Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if response == QMessageBox.Save:
                self.saveChanges()
                event.accept()  # exit
            elif response == QMessageBox.Discard:
                event.accept()  # exit
            else:
                event.ignore()  # user clicked cancel or closed the message box -- don't exit
        else:
            event.accept()  # exit


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = App()
    widget.show()
    sys.exit(app.exec())
