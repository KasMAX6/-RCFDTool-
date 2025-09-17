import os.path
import sys

import ee
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                               QWidget, QPushButton, QHBoxLayout, QFrame, QGridLayout, QSizePolicy)
from PySide6.QtCore import QThread, Signal, Qt, QPoint, Slot
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QPainter, QGuiApplication
from geemap import geemap
from qfluentwidgets import PushButton, FlowLayout, SingleDirectionScrollArea, InfoBar, InfoBarPosition

from flash.common.ImageDownloadThread import ImageDownloadManager
from flash.model.DataSourceConfigure import DataSourceConfigure
from flash.model.Initializer import Initializer


class DownloadThread(QThread):
    """图片下载线程"""
    finished = Signal(bytes)
    error = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            print(f"开始下载图片: {self.url}")

            response = requests.get(
                self.url,
                headers=headers,
                timeout=30,
                stream=True,
                verify=True
            )

            print(f"HTTP状态码: {response.status_code}")
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            print(f"内容类型: {content_type}")

            if not content_type.startswith('image/'):
                self.error.emit(f"不是图片格式: {content_type}")
                return

            content_length = len(response.content)
            print(f"下载完成，数据大小: {content_length} bytes")

            if content_length == 0:
                self.error.emit("下载的数据为空")
                return

            self.finished.emit(response.content)

        except requests.exceptions.Timeout:
            print("请求超时")
            self.error.emit("请求超时")
        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: {e}")
            self.error.emit("连接错误")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误: {e}")
            self.error.emit(f"HTTP错误: {e}")
        except Exception as e:
            print(f"下载失败: {e}")
            self.error.emit(f"下载失败: {str(e)}")


class ZoomableImageLabel(QLabel):
    """可缩放的图片标签 - 支持直接滚轮缩放"""

    zoom_changed = Signal(float)
    position_changed = Signal(QPoint)

    def __init__(self, text=""):
        super().__init__(text)
        self.setMinimumSize(500, 500)
        # self.setStyleSheet("""
        #     QLabel {
        #         border: 1px solid #ddd;
        #         background-color: #f9f9f9;
        #         text-align: center;
        #         color: #666;
        #     }
        # """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 缩放相关属性
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.scale_factor = 1.0
        self.min_scale = 0.05
        self.max_scale = 50.0

        # 拖拽相关属性
        self.dragging = False
        self.last_pan_point = QPoint()
        self.image_position = QPoint(0, 0)
        self.last_mouse_pos = QPoint()

        # 启用鼠标跟踪和焦点
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setMouseTracking(True)

    def setPixmap(self, pixmap):
        """设置原始图片并重置缩放和位置"""
        if not pixmap.isNull():
            self.original_pixmap = pixmap
            self.scale_factor = 0.45  ## 初始缩放比例
            self.image_position = QPoint(0, 0)
            self.update_displayed_pixmap()
            self.zoom_changed.emit(self.scale_factor)
            print(f"图片设置成功: {pixmap.width()}x{pixmap.height()}")
        else:
            self.original_pixmap = None
            self.scaled_pixmap = None
            super().setPixmap(pixmap)
            print("设置了空的图片")

    def update_displayed_pixmap(self):
        """根据当前缩放因子和位置更新显示的图片"""
        if self.original_pixmap is None:
            return

        scaled_size = self.original_pixmap.size() * self.scale_factor
        self.scaled_pixmap = self.original_pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.update()

    def paintEvent(self, event):
        """自定义绘制事件"""
        if self.scaled_pixmap is None:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        widget_rect = self.rect()
        pixmap_size = self.scaled_pixmap.size()

        center_x = (widget_rect.width() - pixmap_size.width()) // 2
        center_y = (widget_rect.height() - pixmap_size.height()) // 2

        draw_x = center_x + self.image_position.x()
        draw_y = center_y + self.image_position.y()

        painter.drawPixmap(draw_x, draw_y, self.scaled_pixmap)
        self.update_cursor()

    def update_cursor(self):
        """根据图片状态更新鼠标光标"""
        if self.scaled_pixmap is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.dragging:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self.can_drag():
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def can_drag(self):
        """检查是否可以拖拽"""
        if self.scaled_pixmap is None:
            return False
        return (self.scaled_pixmap.width() > self.width() or
                self.scaled_pixmap.height() > self.height())

    def get_image_coordinates(self, widget_point):
        """将控件坐标转换为图片坐标系"""
        if self.scaled_pixmap is None:
            return None

        widget_rect = self.rect()
        pixmap_size = self.scaled_pixmap.size()

        center_x = (widget_rect.width() - pixmap_size.width()) // 2
        center_y = (widget_rect.height() - pixmap_size.height()) // 2

        image_left = center_x + self.image_position.x()
        image_top = center_y + self.image_position.y()

        image_x = widget_point.x() - image_left
        image_y = widget_point.y() - image_top

        return QPoint(image_x, image_y)

    def zoom_at_point(self, zoom_point, new_scale):
        """在指定点进行缩放"""
        if self.original_pixmap is None:
            return

        old_image_pos = self.get_image_coordinates(zoom_point)
        if old_image_pos is None:
            return

        if self.scaled_pixmap:
            ratio_x = old_image_pos.x() / self.scaled_pixmap.width()
            ratio_y = old_image_pos.y() / self.scaled_pixmap.height()
        else:
            ratio_x = 0.5
            ratio_y = 0.5

        old_scale = self.scale_factor
        self.scale_factor = max(self.min_scale, min(self.max_scale, new_scale))

        if self.scale_factor == old_scale:
            return

        self.update_displayed_pixmap()

        if self.scaled_pixmap:
            new_image_x = ratio_x * self.scaled_pixmap.width()
            new_image_y = ratio_y * self.scaled_pixmap.height()

            widget_rect = self.rect()
            pixmap_size = self.scaled_pixmap.size()

            center_x = (widget_rect.width() - pixmap_size.width()) // 2
            center_y = (widget_rect.height() - pixmap_size.height()) // 2

            new_image_left = zoom_point.x() - new_image_x
            new_image_top = zoom_point.y() - new_image_y

            self.image_position.setX(int(new_image_left - center_x))
            self.image_position.setY(int(new_image_top - center_y))

        self.zoom_changed.emit(self.scale_factor)
        self.position_changed.emit(self.image_position)

    def wheelEvent(self, event: QWheelEvent):
        """处理鼠标滚轮缩放 - 直接滚轮缩放"""
        if self.original_pixmap is None:
            super().wheelEvent(event)
            return

        mouse_pos = event.position().toPoint()
        delta = event.angleDelta().y()

        zoom_factor = 1.15
        if delta > 0:
            new_scale = self.scale_factor * zoom_factor
        else:
            new_scale = self.scale_factor / zoom_factor

        self.zoom_at_point(mouse_pos, new_scale)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.can_drag():
            self.dragging = True
            self.last_pan_point = event.position().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        self.last_mouse_pos = event.position().toPoint()

        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position().toPoint() - self.last_pan_point
            self.image_position += delta
            self.last_pan_point = event.position().toPoint()

            self.update()
            self.position_changed.emit(self.image_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

        self.update_cursor()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.update_cursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def zoom_in(self):
        """放大"""
        if self.original_pixmap is not None:
            zoom_point = self.last_mouse_pos if not self.last_mouse_pos.isNull() else QPoint(
                self.width() // 2, self.height() // 2)
            new_scale = self.scale_factor * 1.2
            self.zoom_at_point(zoom_point, new_scale)

    def zoom_out(self):
        """缩小"""
        if self.original_pixmap is not None:
            zoom_point = self.last_mouse_pos if not self.last_mouse_pos.isNull() else QPoint(
                self.width() // 2, self.height() // 2)
            new_scale = self.scale_factor / 1.2
            self.zoom_at_point(zoom_point, new_scale)

    def reset_zoom(self):
        """重置缩放和位置"""
        if self.original_pixmap is not None:
            self.scale_factor = 1.0
            self.image_position = QPoint(0, 0)
            self.update_displayed_pixmap()
            self.zoom_changed.emit(self.scale_factor)
            self.position_changed.emit(self.image_position)

    def fit_to_window(self):
        """适应窗口大小"""
        if self.original_pixmap is not None:
            label_size = self.size()
            pixmap_size = self.original_pixmap.size()

            scale_x = (label_size.width() - 20) / pixmap_size.width()
            scale_y = (label_size.height() - 20) / pixmap_size.height()

            self.scale_factor = min(scale_x, scale_y)
            self.image_position = QPoint(0, 0)
            self.update_displayed_pixmap()
            self.zoom_changed.emit(self.scale_factor)
            self.position_changed.emit(self.image_position)


class ImageViewerWidget(QFrame):
    """自动加载图片的查看器小部件"""
    download_started = Signal()
    download_progress = Signal(str)
    download_finished = Signal()
    download_error = Signal(str)
    def __init__(self, image=None, title="图片查看器", show_controls=True, parent=None,
                 dataSourceConfigure: DataSourceConfigure = None):
        super().__init__(parent)
        self.dataSourceConfigure = dataSourceConfigure
        self.title = title
        self.show_controls = show_controls
        self.download_thread = None
        self.image = image
        self.download_manager = ImageDownloadManager(self)
        self.setup_download_connections()
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                margin: 5px;
            }
        """)

        self.setup_ui()

        # 如果提供了URL，自动加载图片
        if self.image['thumbnail_url']:
            print(f"准备自动加载图片: {self.image['thumbnail_url']}")
            self.load_image_from_file(self.image['thumbnail_url'])
    def setup_download_connections(self):
        """设置下载管理器的信号连接"""
        # 这里可以连接到您的 UI 更新方法
        pass
    def pop_to_window_call_back(self):
        # 将新窗口存储为实例变量，防止被垃圾回收
        self.popup_window = ImageViewerWidget(self.image, self.title, self.show_controls)

        # 设置为顶级窗口
        self.popup_window.setWindowFlags(Qt.WindowType.Window)
        self.popup_window.setWindowTitle("弹出窗口")
        self.popup_window.resize(700, 800)

        # 获取主屏幕中心点
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        center_point = screen_geometry.center()

        # 计算窗口左上角位置
        x = center_point.x() - self.popup_window.width() // 2
        y = center_point.y() - self.popup_window.height() // 2
        self.popup_window.move(x, y)

        # 显示窗口
        self.popup_window.show()

        # 可选：将焦点设置到新窗口
        self.popup_window.raise_()
        self.popup_window.activateWindow()

    def create_scrollable_title(self):
        """创建可滚动的标题"""
        # 创建容器
        title_container = QWidget()
        title_container.setMaximumHeight(80)
        title_container.setMinimumHeight(40)

        container_layout = QVBoxLayout(title_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # 创建qfluentwidgets的滚动区域
        scroll_area = SingleDirectionScrollArea()
        # qfluentwidgets的SingleDirectionScrollArea默认是垂直滚动
        scroll_area.setWidgetResizable(True)

        # 创建标题标签
        title_text = f"低云镶嵌的影像ID-->[{self.image['item_ids']}]"
        title_label = QLabel(title_text)
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # 设置标签的尺寸策略
        title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                background-color: #f5f5f5;
                padding: 8px;
                border-radius: 3px;
                border: none;
            }
        """)

        # 组装
        scroll_area.setWidget(title_label)
        container_layout.addWidget(scroll_area)

        return title_container

    def setup_ui(self):
        """设置用户界面"""
        # 主垂直布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(5)

        title_widget = self.create_scrollable_title()

        main_layout.addWidget(title_widget)
        # 第二行：图片显示区域（可伸缩）
        if self.image['thumbnail_url']:
            initial_text = "正在加载图片...\n\n🎯 操作说明:\n• 鼠标滚轮: 直接缩放\n• 左键拖拽: 移动图片\n• 双击: 重置视图"
        else:
            initial_text = "点击加载按钮载入图片\n\n🎯 操作说明:\n• 鼠标滚轮: 直接缩放\n• 左键拖拽: 移动图片\n• 双击: 重置视图"

        self.image_label = ZoomableImageLabel(initial_text)
        self.image_label.zoom_changed.connect(self.on_zoom_changed)
        # 图片区域可以伸缩，占据剩余空间
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.image_label, 1)  # stretch factor = 1，让图片区域占据剩余空间

        # 第三行：控制面板（如果需要显示）
        if self.show_controls:
            control_panel = self.create_control_panel()
            # 控制面板高度固定
            control_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            main_layout.addWidget(control_panel)

        # 第四行：状态栏
        self.status_label = QLabel("准备就绪...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f0f8ff;
                padding: 3px 8px;
                border-radius: 3px;
                color: #555;
                font-size: 11px;
                border: 1px solid #ddd;
            }
        """)
        # 状态栏高度固定
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.status_label)

    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # 加载按钮行
        load_row = QHBoxLayout()

        if self.image['thumbnail_url']:
            self.reload_button = PushButton("🔄 重新加载")
            self.download_button = PushButton("💾 下载影像至GoogleDrive")
            self.reload_button.clicked.connect(self.reload_image)
            self.download_button.clicked.connect(self.download_image)
        else:
            self.reload_button = PushButton("📁 加载图片")
            self.reload_button.clicked.connect(self.load_default_image)

        self.reload_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        load_row.addWidget(self.reload_button)

        # 缩放显示
        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setStyleSheet("""
            QLabel {
                background-color: #2196F3;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 50px;
                text-align: center;
            }
        """)
        load_row.addWidget(self.zoom_label)
        load_row.addStretch()
        layout.addLayout(load_row)

        # 控制按钮行
        control_row = QHBoxLayout()

        self.zoom_in_btn = PushButton("🔍+")
        self.zoom_out_btn = PushButton("🔍-")
        self.reset_btn = PushButton("🎯")
        self.fit_btn = PushButton("📐")
        self.pop_window_btn = PushButton("↗️")

        buttons = [self.zoom_in_btn, self.zoom_out_btn, self.reset_btn, self.fit_btn, self.pop_window_btn,
                   self.download_button]
        button_style = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 8px;
                font-size: 11px;
                border-radius: 3px;
                min-width: 30px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #cccccc; }
        """

        for btn in buttons:
            ##btn.setStyleSheet(button_style)
            btn.setEnabled(False)
            control_row.addWidget(btn)

        # 连接信号
        self.zoom_in_btn.clicked.connect(self.image_label.zoom_in)
        self.zoom_out_btn.clicked.connect(self.image_label.zoom_out)
        self.reset_btn.clicked.connect(self.image_label.reset_zoom)
        self.fit_btn.clicked.connect(self.image_label.fit_to_window)
        self.pop_window_btn.clicked.connect(self.pop_to_window_call_back)

        control_row.addStretch()
        layout.addLayout(control_row)

        return panel

    def load_image_from_url(self, url):
        """从URL加载图片"""
        if self.download_thread and self.download_thread.isRunning():
            print("已有下载任务在进行中，跳过")
            return

        print(f"开始加载图片从URL: {url}")

        if self.show_controls:
            self.reload_button.setEnabled(False)
        self.status_label.setText("下载中...")
        self.image_label.setText("正在下载图片...")

        self.download_thread = DownloadThread(url)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def load_image_from_file(self, file_path):
        """从文件加载图片"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap)
                self.status_label.setText(f"已加载: {pixmap.width()}×{pixmap.height()}px")
                self.enable_controls(True)
            else:
                self.status_label.setText("加载失败: 不支持的图片格式")
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")

    def load_image_from_pixmap(self, pixmap):
        """从QPixmap加载图片"""
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap)
            self.status_label.setText(f"已加载: {pixmap.width()}×{pixmap.height()}px")
            self.enable_controls(True)

    def load_default_image(self):
        """加载默认示例图片"""
        url = r"https://earthengine.googleapis.com/v1/projects/earthengine-legacy/thumbnails/685c4327cdae14ff9399d7e1f24e8e50-7c66b4f2fbef5dd9478f9e8a9a16e508:getPixels"
        self.image['thumbnail_url'] = url
        self.load_image_from_url(url)

    def reload_image(self):
        """重新加载图片"""
        if self.image['thumbnail_url']:
            self.load_image_from_file(self.image['thumbnail_url'])

    def download_image(self):
        """
        下载图片 - 修改为使用线程
        原来的同步下载改为异步线程下载
        """
        try:
            # 验证必要的数据
            if not hasattr(self, 'image') or 'item_ids' not in self.image:
                self.download_error.emit("缺少必要的图像数据")
                return

            if not hasattr(self, 'dataSourceConfigure'):
                self.download_error.emit("缺少数据源配置")
                return

            # 发出开始下载信号
            self.download_started.emit()

            # 使用线程管理器开始下载
            self.download_manager.start_download(
                self.dataSourceConfigure,
                self.image
            )
            InfoBar.info(
                title='下载',
                content="开始下载影像，请注意保存路径！",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM,
                duration=5000,  # 3秒后自动消失
                parent=self
            )
        except Exception as e:
            error_msg = f"启动下载失败: {str(e)}"
            self.download_error.emit(error_msg)

    def cancel_download(self):
        """取消下载"""
        self.download_manager.cancel_download()

    def on_download_progress(self, message):
        """下载进度回调"""
        print(f"下载进度: {message}")
        self.download_progress.emit(message)
        # 这里可以更新进度条或状态标签

    def on_download_completed(self):
        """下载完成回调"""
        print("图片下载完成!")
        self.download_finished.emit()
        InfoBar.success(
            title='下载',
            content="下载完成！关注影像下载保存路径",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM,
            duration=5000,  # 3秒后自动消失
            parent=self
        )
        # 这里可以执行下载完成后的操作
        # 比如更新UI状态、显示成功消息等

    def on_download_failed(self, error_message):
        """下载失败回调"""
        print(f"下载失败: {error_message}")
        InfoBar.error(
            title='下载',
            content=f"{error_message}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM,
            duration=5000,  # 3秒后自动消失
            parent=self
        )
        self.download_error.emit(error_message)
        # 这里可以显示错误消息给用户

    def on_download_status_changed(self, status):
        """下载状态变化回调"""
        InfoBar.info(
            title='下载',
            content=f"{status}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM,
            duration=5000,  # 3秒后自动消失
            parent=self
        )
        print(f"下载状态: {status}")
        # 这里可以更新状态栏

    def on_download_finished(self, data):
        """下载完成处理"""
        try:
            print(f"收到下载数据，大小: {len(data)} bytes")

            pixmap = QPixmap()
            success = pixmap.loadFromData(data)

            print(f"图片加载结果: {success}")

            if success and not pixmap.isNull():
                print(f"图片尺寸: {pixmap.width()}x{pixmap.height()}")
                self.image_label.setPixmap(pixmap)
                self.status_label.setText(f"✅ 加载成功: {pixmap.width()}×{pixmap.height()}px - 🎯 滚轮直接缩放")
                self.enable_controls(True)
            else:
                self.on_download_error("无法解析图片数据")
        except Exception as e:
            print(f"处理图片时出错: {e}")
            self.on_download_error(f"处理图片时出错: {str(e)}")
        finally:
            if self.show_controls:
                self.reload_button.setEnabled(True)

    def on_download_error(self, error_msg):
        """下载错误处理"""
        print(f"下载错误: {error_msg}")
        self.image_label.setText(f"❌ 加载失败:\n{error_msg}")
        self.image_label.setPixmap(QPixmap())
        self.status_label.setText("❌ 加载失败")
        if self.show_controls:
            self.reload_button.setEnabled(True)
        self.enable_controls(False)

    def enable_controls(self, enabled):
        """启用/禁用控制按钮"""
        if self.show_controls:
            controls = [self.zoom_in_btn, self.zoom_out_btn, self.reset_btn, self.fit_btn, self.pop_window_btn,
                        self.download_button]
            for control in controls:
                control.setEnabled(enabled)

    def on_zoom_changed(self, scale_factor):
        """缩放改变时更新显示"""
        if self.show_controls:
            self.zoom_label.setText(f"{scale_factor:.2f}x")

            # 根据缩放级别改变颜色
            if scale_factor > 5.0:
                color = "#F44336"
            elif scale_factor > 2.0:
                color = "#FF9800"
            elif scale_factor < 0.5:
                color = "#9C27B0"
            else:
                color = "#4CAF50"

            self.zoom_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                    min-width: 50px;
                    text-align: center;
                }}
            """)

    def mouseDoubleClickEvent(self, event):
        """双击重置视图"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.image_label.reset_zoom()


class MultiImageViewerDemo(QMainWindow):
    """演示多个图片查看器的窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎯 直接滚轮缩放 - 多图片查看器演示")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建网格布局
        layout = QGridLayout(central_widget)
        layout.setSpacing(10)

        # 示例图片URL
        sample_url = r"https://earthengine.googleapis.com/v1/projects/earthengine-legacy/thumbnails/685c4327cdae14ff9399d7e1f24e8e50-7c66b4f2fbef5dd9478f9e8a9a16e508:getPixels"

        # 创建多个查看器
        self.viewer1 = ImageViewerWidget(
            image=sample_url,
            title="🔍 自动加载 - 查看器 1",
            show_controls=True
        )

        self.viewer2 = ImageViewerWidget(
            image=sample_url,
            title="🔍 自动加载 - 查看器 2",
            show_controls=True
        )

        self.viewer3 = ImageViewerWidget(
            image=sample_url,
            title="🔍 无控制面板 - 查看器 3",
            show_controls=False
        )

        self.viewer4 = ImageViewerWidget(
            title="🔍 手动加载 - 查看器 4",
            show_controls=True
        )

        # 布局安排
        layout.addWidget(self.viewer1, 0, 0)
        layout.addWidget(self.viewer2, 0, 1)
        layout.addWidget(self.viewer3, 1, 0)
        layout.addWidget(self.viewer4, 1, 1)


def main():
    app = QApplication(sys.argv)

    # 测试单个查看器
    # url = r"https://earthengine.googleapis.com/v1/projects/earthengine-legacy/thumbnails/685c4327cdae14ff9399d7e1f24e8e50-7c66b4f2fbef5dd9478f9e8a9a16e508:getPixels"
    # single_viewer = ImageViewerWidget(
    #     image['thumbnail_url']=url,
    #     title="🎯 测试图片查看器",
    #     show_controls=True
    # )
    # single_viewer.show()

    # 多个查看器演示
    multi_demo = MultiImageViewerDemo()
    multi_demo.show()

    return app.exec()


if __name__ == "__main__":
    Initializer().initialize()
    sys.exit(main())
