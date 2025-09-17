# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/15 15:22
import os
from PySide6.QtCore import QThread, Signal, QObject
import ee
import geemap

from flash.util.S2_Util import generate_md5_filename


class ImageDownloadThread(QThread):
    """图像下载线程"""

    # 信号定义
    progress_updated = Signal(str)  # 进度更新信号
    download_completed = Signal()  # 下载完成信号
    download_failed = Signal(str)  # 下载失败信号
    status_changed = Signal(str)  # 状态变化信号

    def __init__(self, data_source_configure, image_data, parent=None):
        """
        初始化下载线程

        Args:
            data_source_configure: 数据源配置对象
            image_data: 图像数据，包含 item_ids
            parent: 父对象
        """
        super().__init__(parent)
        self.data_source_configure = data_source_configure
        self.image_data = image_data
        self._is_cancelled = False

    def run(self):
        """线程主执行方法"""
        try:
            self.status_changed.emit("开始下载图片...")
            self._download_image()

            if not self._is_cancelled:
                self.status_changed.emit("下载完成")
                self.download_completed.emit()
            else:
                self.status_changed.emit("下载已取消")

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            self.status_changed.emit(error_msg)
            self.download_failed.emit(error_msg)

    def _download_image(self):
        """下载图片的具体实现"""
        # 创建下载目录
        download_dir = os.path.join(
            self.data_source_configure.data_path_config.download_path,
            self.data_source_configure.data_path_config.roi_name
        )
        os.makedirs(download_dir, exist_ok=True)
        self.progress_updated.emit(f"创建下载目录: {download_dir}")

        if self._is_cancelled:
            return

        # 解析图片ID
        ids = self.image_data['item_ids'].split(',')
        self.progress_updated.emit(f"准备下载 {len(ids)} 张图片")

        # 创建图片集合
        images = []
        for i, item_id in enumerate(ids):
            if self._is_cancelled:
                return

            self.progress_updated.emit(f"处理图片 {i + 1}/{len(ids)}: {item_id}")
            # 目前仅支持S2
            images.append(ee.Image('COPERNICUS/S2_SR_HARMONIZED/' + item_id))

        if self._is_cancelled:
            return

        self.progress_updated.emit("合并图片集合...")

        # 获取网格数据
        grids = self.data_source_configure.roi.gdf
        grids = geemap.gdf_to_ee(grids)

        # 合并图片并进行处理
        self.progress_updated.emit("创建镶嵌图像...")
        image = ee.ImageCollection(images).mosaic().select('B.*').clip(grids).divide(10000)

        if self._is_cancelled:
            return

        self.progress_updated.emit("开始下载瓦片...")

        # 下载图片瓦片
        geemap.download_ee_image_tiles(
            image=image,
            features=grids,
            out_dir=download_dir,
            prefix='s2_sr_harmonized_'+generate_md5_filename(self.image_data['item_ids']),
            crs='EPSG:4326',
            scale=10,
        )

        self.progress_updated.emit("图片下载完成")

    def cancel_download(self):
        """取消下载"""
        self._is_cancelled = True
        self.status_changed.emit("正在取消下载...")


class ImageDownloadManager(QObject):
    """图像下载管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_thread = None

    def start_download(self, data_source_configure, image_data):
        """
        开始下载

        Args:
            data_source_configure: 数据源配置
            image_data: 图像数据
        """
        # 如果有正在运行的线程，先停止
        if self.download_thread and self.download_thread.isRunning():
            self.cancel_download()
            self.download_thread.wait()  # 等待线程结束

        # 创建新的下载线程
        self.download_thread = ImageDownloadThread(data_source_configure, image_data, self)

        # 连接信号
        self.download_thread.progress_updated.connect(self.on_progress_updated)
        self.download_thread.download_completed.connect(self.on_download_completed)
        self.download_thread.download_failed.connect(self.on_download_failed)
        self.download_thread.status_changed.connect(self.on_status_changed)

        # 启动线程
        self.download_thread.start()

    def cancel_download(self):
        """取消下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel_download()
            self.download_thread.quit()

    def on_progress_updated(self, message):
        """进度更新处理"""
        print(f"进度: {message}")
        # 这里可以更新UI进度条或状态标签

    def on_download_completed(self):
        """下载完成处理"""
        print("下载完成!")
        # 这里可以显示完成消息，更新UI状态等

    def on_download_failed(self, error_message):
        """下载失败处理"""
        print(f"下载失败: {error_message}")
        # 这里可以显示错误消息

    def on_status_changed(self, status):
        """状态变化处理"""
        print(f"状态: {status}")
        # 这里可以更新状态栏