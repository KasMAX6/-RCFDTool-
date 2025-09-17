import sys

import ee
import geemap
from PySide6.QtCore import Qt, QUrl, Slot, Signal, QEasingCurve
from PySide6.QtGui import QIcon, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QGridLayout, QVBoxLayout, QWidget, QScrollArea, \
    QWizardPage
from qfluentwidgets import (
    NavigationItemPosition, MessageBox, FluentWindow,
    NavigationAvatarWidget, SubtitleLabel, setFont, InfoBadge,
    InfoBadgePosition, PushButton, FlowLayout, SingleDirectionScrollArea, ScrollArea, ProgressBar, SwitchButton,
    InfoBarPosition, InfoBar
)

from flash.common import MsgType
from flash.common.AutoFindSentinel2LowCloudImplThread import AutoFindSentinel2LowCloudImplThread
from flash.components.widgets.AutoLoadingImage import ImageViewerWidget
from flash.model.ConditionBuilder import ConditionBuilder
from flash.model.DataSourceConfigure import DataSourceConfigure
from flash.model.Sentinel2Image import parse_any
from flash.model.ThreadOperateStatus import ThreadOperateStatus
from flash.model.VectorFile import VectorFile
from flash.service.AutoFindSentinel2LowCloudImpl import AutoFindSentinel2LowCloudImpl


class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        # self.setStyleSheet("""
        #          QWidget {
        #              border: 2px solid #0078d7;
        #              border-radius: 8px;
        #              padding: 5px;
        #          }
        #      """)
        self.setObjectName(text.replace(' ', '-'))
        # 主垂直布局
        main_layout = QVBoxLayout(self)

        # 控制Label 的水平布局
        label_layout = QHBoxLayout()
        label_layout.addStretch()

        self.progressBar = ProgressBar()

        label_layout.addWidget(self.progressBar)
        self.progress_value_badge = InfoBadge.attension('-/-')
        label_layout.addWidget(self.progress_value_badge)
        # 创建滚动区域
        self.scrollArea = ScrollArea()
        # 按钮区域的容器 widget
        self.button_container = QWidget()
        self.button_flow_layout = FlowLayout(self.button_container, needAni=False)
        #self.button_flow_layout.setAnimation(0, QEasingCurve.Type.OutQuad)
        self.button_flow_layout.setContentsMargins(0, 0, 0, 0)
        self.button_flow_layout.setVerticalSpacing(20)
        self.button_flow_layout.setHorizontalSpacing(10)
        self.start_button = SwitchButton()
        self.start_button.setOffText("开始")
        self.start_button.setOnText("暂停")
        self.stop_button = PushButton('停止')
        self.test_button = PushButton('创建窗口测试')
        self.clear_button = PushButton('清空查看器')

        # 添加按钮到 FlowLayout
        label_layout.addWidget(self.start_button)
        label_layout.addWidget(self.stop_button)
        label_layout.addWidget(self.clear_button)
        #label_layout.addWidget(self.test_button)

        # 将按钮容器设置到滚动区域
        self.scrollArea.setWidget(self.button_container)
        self.scrollArea.setWidgetResizable(True)
        # 组装布局
        main_layout.addLayout(label_layout)
        # 滚动区域添加到主布局
        main_layout.addWidget(self.scrollArea)

    def clear_button_layout(self):
        """彻底清空按钮布局 - 通过重新创建容器"""
        # 创建新的按钮容器
        self.button_container = QWidget()

        # 重新创建 FlowLayout
        self.button_flow_layout = FlowLayout(self.button_container, needAni=False)
        self.button_flow_layout.setContentsMargins(0, 0, 0, 0)
        self.button_flow_layout.setVerticalSpacing(20)
        self.button_flow_layout.setHorizontalSpacing(10)

        # 将新的容器设置到滚动区域
        self.scrollArea.setWidget(self.button_container)
        self.scrollArea.setWidgetResizable(True)



class AutoFindLowCloudView(Widget):

    def __init__(self, text: str,  parent=None):
        super().__init__(text, parent)
        self.clear_button.clicked.connect(self.on_clear)

        self.stop_button.clicked.connect(self.on_stop)
        self.start_button.checkedChanged.connect(self.on_switch_button_clicked)
        self.test_button.clicked.connect(self.test)
        self.data_source_configure: DataSourceConfigure = None
        self.worker = None
        self.thread_operate_status = ThreadOperateStatus()

    @Slot()
    def on_clear(self):
        """清空按钮点击"""
        self.clear_button_layout()
        self.progressBar.setValue(0)
        self.progress_value_badge.setText('-/-')

    @Slot()
    def on_stop(self):
        """停止按钮点击"""
        if self.worker is None:
            return
        self.thread_operate_status.stop_task()
        self.start_button.setChecked(False)
        self.worker.set_thread_operate_status(self.thread_operate_status)


    @Slot(bool)
    def on_switch_button_clicked(self, checked):
        """开始/暂停按钮点击"""
        if not self.data_source_configure.data_path_config.all_not_empty():
            ## 提示
            InfoBar.error(
                title='错误',
                content="数据配置必须填写完整！",
                orient=Qt.Orientation.Vertical,  # 内容太长时可使用垂直布局
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=3000,
                parent=self
            )
            return

        if checked:  # 要开始运行
            if self.thread_operate_status.is_stopped:
                # 从停止状态开始新任务
                self.thread_operate_status.start_new_task()
                self.find()  # 启动新任务
            elif self.thread_operate_status.is_paused:
                # 从暂停状态恢复
                self.thread_operate_status.resume_task()

            # 通知worker
            self.worker.set_thread_operate_status(self.thread_operate_status)

        else:  # 要暂停
            self.thread_operate_status.pause_task()
            self.worker.set_thread_operate_status(self.thread_operate_status)


    @Slot(list)
    def thumbnail_url_callback(self, msg):
        self.show_pic_to_label(msg)

    @Slot(dict)
    def progress_max_value_callback(self, result):
        self.progressBar.setRange(0, result['max_tile_num'])
        self.progressBar.setValue(result['current_mosaic_num'])
        current = result['current_mosaic_num']
        max = result['max_tile_num']
        self.progress_value_badge.setText(str(f'current_mosaic_num:{current}:max_tile_num:{max}'))

    @Slot()
    def find(self):
        InfoBar.info(
            title='提示',
            content="开始寻找无云影像，请等待结果展示...",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_LEFT,
            duration=3000,
            parent=self
        )

        # 创建线程
        self.worker = AutoFindSentinel2LowCloudImplThread(self.data_source_configure,self.thread_operate_status)
        self.worker.emit_thumbnail_url.connect(self.thumbnail_url_callback)
        self.worker.emit_progress.connect(self.progress_max_value_callback)

        self.worker.start()

    def test(self):
        self.show_pic_to_label(
            [{'thumbnail_url': 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/thumbnails/b1e1f370582d9fb4aa69384a87528ac2-300a82ec318e7c6faac1671afba9816b:getPixels'}])

    def show_pic_to_label(self, thumbUrl: list[dict]):
        # 创建多个查看器
        for image in thumbUrl:
            print(image)
            viewer = ImageViewerWidget(
                image=image,
                title="🔍 自动加载 - 查看器",
                show_controls=True,
                dataSourceConfigure=self.data_source_configure
            )
            self.button_flow_layout.addWidget(viewer)
