import sys
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout
from qfluentwidgets import (
    NavigationItemPosition, MessageBox, FluentWindow,
    NavigationAvatarWidget, SubtitleLabel, setFont, InfoBadge,
    InfoBadgePosition
)
class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName(text.replace(' ', '-'))

class UserSettingView(Widget):
    pass

