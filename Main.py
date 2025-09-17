# coding:utf-8
import sys
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtGui import QIcon, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout
from qfluentwidgets import (
    NavigationItemPosition, MessageBox, FluentWindow,
    NavigationAvatarWidget, SubtitleLabel, setFont, InfoBadge,
    InfoBadgePosition
)
from qfluentwidgets import FluentIcon as FIF

from flash.model import Initializer
from flash.model.DataSourceConfigure import DataSourceConfigure
from flash.view.AutoFindLowCloudView import AutoFindLowCloudView
from flash.view.ConfigureDataSourceView import ConfigureDataSource
from flash.view.DownloadManagerView import DownloadManagerView
from flash.view.ManualFindLowCloudView import ManualFindLowCloudView
from flash.view.UserSettingView import UserSettingView


# -------- 页面通用控件 --------
class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)
        self.setObjectName(text.replace(' ', '-'))


# -------- 主窗口 --------
class Window(FluentWindow):

    def __init__(self):
        super().__init__()
        # -------- create sub interface --------
        self.dataSourceInterface = ConfigureDataSource('配置数据源', self)
        self.dataSourceInterface.data_source_config_event.connect(self.on_data_source_config)
        self.autoSearchInterface = AutoFindLowCloudView(text='自动化寻找无云影像', parent=self)
        self.manualSearchInterface = ManualFindLowCloudView('手动寻找无云影像', self)
        self.downloadInterface = DownloadManagerView('下载管理', self)
        self.settingsInterface = UserSettingView('用户设置', self)

        self.initNavigation()
        self.initWindow()

    @Slot(DataSourceConfigure)
    def on_data_source_config(self, config: DataSourceConfigure):
        self.autoSearchInterface.data_source_configure = config
        if config.data_path_config.base_path is not None:
            self.initServices( self.autoSearchInterface.data_source_configure)


    # -------- 注册导航项 --------
    def initNavigation(self):
        self.addSubInterface(self.dataSourceInterface, FIF.TRAIN, '配置数据源')
        self.addSubInterface(self.autoSearchInterface, FIF.CLOUD, '自动化寻找无云影像')
        self.addSubInterface(self.manualSearchInterface, FIF.CLOUD, '手动寻找无云影像')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.downloadInterface, FIF.DOWNLOAD, '下载管理', NavigationItemPosition.SCROLL)

        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=NavigationAvatarWidget('zxq', 'resource/2.png'),
            onClick=self.showMessageBox,
            position=NavigationItemPosition.BOTTOM,
        )

        self.addSubInterface(self.settingsInterface, FIF.SETTING, '用户设置', NavigationItemPosition.BOTTOM)

        # 给“手动寻找无云影像”添加消息角标
        item = self.navigationInterface.widget(self.manualSearchInterface.objectName())
        # InfoBadge.attension(
        #     text=9,
        #     parent=item.parent(),
        #     target=item,
        #     position=InfoBadgePosition.NAVIGATION_ITEM
        # )

    def initServices(self, data_source_configure: DataSourceConfigure):
        Initializer().initialize(data_source_configure)

    # -------- 初始化窗口属性 --------
    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        self.setWindowTitle('遥感无云影像寻找下载器 v1.0.0')

        desktop = QGuiApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    # -------- 点击头像弹出消息框 --------
    def showMessageBox(self):
        w = MessageBox(
            '提示',
            '个人开发不易，如果这个项目帮助到了您，可以考虑关注一下我的博客，感谢支持！\n'
            ,
            self
        )
        w.yesButton.setText('访问博客')
        w.cancelButton.setText('下次一定')

        if w.exec():
            QDesktopServices.openUrl(QUrl("https://blog.csdn.net/weixin_43310839"))


# -------- 程序入口 --------
if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()
