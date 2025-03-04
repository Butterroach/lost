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

import markdown
import os
import platform
import re
import requests
import subprocess
import sys
from packaging.version import Version
from PySide6.QtCore import Qt, QUrl, QStringListModel, QTimer, QSize
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QDialog,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
)
from typing import Optional, List
from ui_form import Ui_App  # generate ui_form.py: pyside6-uic form.ui -o ui_form.py
from validateHosts import validateHostsFile

__version__ = "1.3.0"

TIMEOUT = 60
ALL_EXCEPTIONS = (
    requests.exceptions.RequestException,
    requests.exceptions.ConnectionError,
    requests.exceptions.HTTPError,
    requests.exceptions.SSLError,
    requests.exceptions.InvalidSchema,
    requests.exceptions.ContentDecodingError,
    requests.exceptions.TooManyRedirects,
    requests.exceptions.UnrewindableBodyError,
)

session = requests.Session()

session.headers[
    "User-Agent"
] += f" Lost/{__version__} I am Butterroach, and I made Lost. Lost's source code is at https://github.com/Butterroach/lost. \
Please contact me at butterroach@outlook.com if you have any inquiries or issues. I am not responsible for any spam, the users are. \
No, I do not know who my users are. Please don't ask about that. I have absolutely no data on my users."


def showStyledMessageBox(
    parent: QWidget,
    title: str,
    text: str,
    icon: QMessageBox.Icon,
    buttons: QMessageBox.StandardButton = None,
    defaultButton: QMessageBox.StandardButton = None,
):
    # i hate qt :D
    if not defaultButton:
        if not buttons:
            msgBox = QMessageBox(parent, icon=icon)
        else:
            msgBox = QMessageBox(parent, icon=icon, standardButtons=buttons)
    else:
        msgBox = QMessageBox(
            parent,
            icon=icon,
            standardButtons=buttons,
            defaultButton=defaultButton,
        )
    msgBox.setWindowTitle(title)
    msgBox.setText(text)
    msgBox.setStyleSheet(
        "QMessageBox {background-color: #1e1e1e;} QLabel {color: white;} \
        QPushButton { background-color: #101010; border-style: solid; border-color: #575757; \
        border-width: 1px; border-radius: 5px; color: white; qproperty-icon: none; }"
    )
    return msgBox.exec()


def showInformation(
    parent: QWidget,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = None,
    defaultButton: QMessageBox.StandardButton = None,
):
    return showStyledMessageBox(
        parent, title, text, QMessageBox.Icon.Information, buttons, defaultButton
    )


def showQuestion(
    parent: QWidget,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = None,
    defaultButton: QMessageBox.StandardButton = None,
):
    return showStyledMessageBox(
        parent, title, text, QMessageBox.Icon.Question, buttons, defaultButton
    )


def showWarning(
    parent: QWidget,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = None,
    defaultButton: QMessageBox.StandardButton = None,
):
    return showStyledMessageBox(
        parent, title, text, QMessageBox.Icon.Warning, buttons, defaultButton
    )


def showCritical(
    parent: QWidget,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = None,
    defaultButton: QMessageBox.StandardButton = None,
):
    return showStyledMessageBox(
        parent, title, text, QMessageBox.Icon.Critical, buttons, defaultButton
    )


class QHTMLWindow(QDialog):
    def __init__(self, html_content, title, parent=None):
        super().__init__(parent)

        self.setMinimumSize(1024, 384)

        self.setWindowTitle(title)
        self.setStyleSheet(
            "QLabel, QDialog { background-color: #1e1e1e; } QScrollArea { border: none }"
        )

        layout = QVBoxLayout()

        label = QLabel(self)
        label.setTextFormat(Qt.RichText)
        label.setText(html_content)
        label.setWordWrap(True)
        label.linkActivated.connect(self.openLink)

        scrollArea = QScrollArea(self)
        scrollArea.setWidget(label)
        scrollArea.setWidgetResizable(True)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(scrollArea)

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
            showCritical(
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
            showCritical(
                self,
                "Root required",
                "Lost requires root to run! I tried implementing some pkexec stuff for this but that didn't work out well, so...",
            )
            sys.exit(127)

        with open(self.HOSTS_FILE, "r") as f:
            self.hostsFile = f.read()

        self.hostsFileParts = self.hostsFile.split(self.HOSTS_SEPARATOR)

        if len(self.hostsFileParts) == 1:
            if "\n# LOST URL" in self.hostsFileParts[0]:
                showCritical(
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
            showCritical(
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
            release_data = session.get(
                "https://api.github.com/repos/Butterroach/lost/releases",
                timeout=5,
            ).json()
            latest_ver = Version(release_data["tag_name"])
            current_ver = Version(__version__)
            if current_ver < latest_ver:
                showInformation(
                    self,
                    "Update available",
                    f"An update is available! You are on {__version__}, the latest version is {latest_ver}. Please update!",
                )
        except:
            pass

        self.ui = Ui_App()
        self.ui.setupUi(self)

        with open("README_LOCAL.md", "r") as f:
            self.aboutDialog = QHTMLWindow(
                "<html><body><style> p, h1, h2, h3, h4, h5, h6, li, li::marker { color: white; } a { color: #00da75; }</style>"
                + markdown.markdown(f.read())
                + "</body></html>",
                "About",
                self,
            )

        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self.aboutDialog.show)
        self.ui.lineEdit.returnPressed.connect(self.addSource)
        self.ui.addButton.clicked.connect(self.addSource)

        self.model = QStringListModel()
        self.ui.listView.setModel(self.model)

        self.populateListView()

        self.ui.saveButton.clicked.connect(self.saveChanges)
        self.ui.removeButton.clicked.connect(self.removeSource)
        self.ui.updateButton.clicked.connect(self.updateSource)
        self.ui.updateAllButton.clicked.connect(self.updateAllSources)

    def maliciousHostsFileWarning(
        self, entries: List[str], hosts: Optional[str] = None
    ) -> QMessageBox.StandardButton:
        bigScaryWarning = QMessageBox(self)
        bigScaryWarning.setWindowTitle("YOUR HOSTS FILE IS MALICIOUS!!!!!!!!!!!")
        bigScaryWarning.setTextFormat(Qt.RichText)
        if hosts:
            bigScaryWarning.setText(
                f"<font color='red'>ONE OF YOUR HOSTS FILE HAS NOW BECOME MALICIOUS!!!!!: {hosts}</font><br />Your hosts file contains entries that redirect domains to <b><font color='red'>PUBLIC IPs THAT COULD POINT TO PHISHING WEBSITES TO STEAL YOUR INFO!!!!!</font></b><br />{'<br />'.join(entries)}<br />ARE YOU SURE YOU WANNA UPDATE IT TO THE MALICIOUS VERSION??? (wait 10 seconds before you can interact with the buttons)"
            )
        else:
            bigScaryWarning.setText(
                f"<font color='red'>YOUR HOSTS FILE IS MALICIOUS!!!!!</font><br />Your hosts file contains entries that redirect domains to <b><font color='red'>PUBLIC IPs THAT COULD POINT TO PHISHING WEBSITES TO STEAL YOUR INFO!!!!!</font></b><br />{'<br />'.join(entries)}<br />ARE YOU SURE YOU WANNA CONTINUE WITH ADDING THIS HOSTS FILE????? (wait 10 seconds before you can interact with the buttons)"
            )
        bigScaryWarning.setStandardButtons(
            QMessageBox.StandardButton.Ignore | QMessageBox.StandardButton.Abort
        )
        bigScaryWarning.setDefaultButton(QMessageBox.StandardButton.Abort)
        bigScaryWarning.button(QMessageBox.StandardButton.Ignore).setEnabled(False)

        def enableIgnore():
            bigScaryWarning.button(QMessageBox.StandardButton.Ignore).setEnabled(True)

        QTimer.singleShot(10_000, enableIgnore)

        return bigScaryWarning.exec()

    def getSelectedURL(self) -> Optional[str]:
        model = self.ui.listView.selectionModel()
        indexes = model.selectedIndexes()

        if indexes:
            data = self.ui.listView.model().data(indexes[0])
            if data:
                return data
        showCritical(self, "No URL selected", "You need to select a URL!")

    def addSource(self):
        url = self.ui.lineEdit.text()
        for i in range(0, len(self.losts), 2):
            if url in self.losts[i]:
                showCritical(
                    self,
                    "URL already exists",
                    "That URL already exists in the hosts file!",
                )
                return
        if not QUrl(url).isValid():
            showCritical(self, "Invalid URL", "You entered an invalid URL.")
            return
        try:
            contents = session.get(url, timeout=TIMEOUT).text
        except requests.exceptions.Timeout:
            showCritical(
                self,
                "Your internet is terrible",
                "The request to the source URL timed out! Please check your internet connection and try again.",
            )
            return
        except ALL_EXCEPTIONS as e:
            showCritical(
                self,
                "Connection error!",
                f"Connection error! Please try again later.\n{e}",
            )
            return
        isValid = validateHostsFile(contents)
        if not isValid[0]:
            showCritical(
                self,
                "Invalid hosts file",
                "The contents of that hosts file is NOT valid!",
            )
            return
        if len(isValid) > 1:
            response = self.maliciousHostsFileWarning(isValid[1])
            if response == QMessageBox.StandardButton.Abort:
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
                    contents = session.get(url, timeout=TIMEOUT).text
                except requests.exceptions.Timeout:
                    if notUpdateAll:
                        showCritical(
                            self,
                            "Your internet is terrible",
                            "The update timed out! Please check your internet connection and try again.",
                        )
                    else:
                        showCritical(
                            self,
                            "Your internet is terrible",
                            f"The update for {url} timed out! Please check your internet connection. Update will proceed with the other sources...",
                        )
                    return
                except ALL_EXCEPTIONS as e:
                    if notUpdateAll:
                        showCritical(
                            self,
                            "Connection error!",
                            f"Connection error! Please try again later.\n{e}",
                        )
                    else:
                        showCritical(
                            self,
                            "Connection error!",
                            f"Connection error with {url}! Update will proceed with the other sources...\n{e}",
                        )
                    return
                if contents.strip().replace("\n", "").replace("\r", "") == self.losts[
                    i + 1
                ].strip().replace("\n", "").replace("\r", ""):
                    if notUpdateAll:
                        showInformation(
                            self,
                            "Nothing to update",
                            "There was nothing to update. If you are SURE that there is an update, try restarting NetworkManager.",
                        )
                    return
                isValid = validateHostsFile(contents)
                if not isValid[0]:
                    if notUpdateAll:
                        showCritical(
                            self,
                            "Invalid hosts file",
                            "The contents of the hosts file that you tried to update has now become invalid. You will need to stay on the older version. Please contact the hosts file maintainer about this.",
                        )
                    else:
                        showCritical(
                            self,
                            "Invalid hosts file",
                            f"One of your hosts files has become invalid: {url}. You will need to stay on the older version of that hosts file. Please contact the hosts file maintainer about this. Update will continue with the other hosts files after you click OK or close this message box.",
                        )
                    return
                if len(isValid) > 1:
                    if notUpdateAll:
                        response = self.maliciousHostsFileWarning(isValid[1], url)
                    else:
                        response = self.maliciousHostsFileWarning(isValid[1], url)
                    if response == QMessageBox.StandardButton.Abort:
                        showWarning(
                            self,
                            "Aborted",
                            "Please remove the now malicious hosts file!!!",
                        )
                        return
                self.losts[i + 1] = contents
                self.populateListView()
                self.unsavedChanges = True
                if notUpdateAll:
                    showInformation(self, "Update done", "Done updating!")
                return
        showWarning(
            self,
            "...What",
            "Idk how to explain this just urgently open a github issue now the url provided to update wasn't found",
        )

    def updateAllSources(self):
        for i in range(0, len(self.losts), 2):
            self.updateSource(self.losts[i].split(" ")[3])
        showInformation(self, "Update done", "Done updating!")

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

        showInformation(self, "Saved", "Changes have been saved to the hosts file!")

    def closeEvent(self, event):
        if self.unsavedChanges:
            response = showQuestion(
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
