# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/13 12:18
import threading

import ee
from PySide6.QtCore import QThread, Signal, QObject, Slot
from geemap import geemap

from flash.common import MsgType
from flash.model.ConditionBuilder import ConditionBuilder
from flash.model.DataPathConfig import DataPathConfig
from flash.model.DataSourceConfigure import DataSourceConfigure
from flash.model.Sentinel2DataSourceConfigure import Sentinel2DataSourceConfigure
from flash.model.Sentinel2Image import parse_any
from flash.model.ThreadOperateStatus import ThreadOperateStatus
from flash.model.VectorFile import VectorFile
from flash.service.AutoFindSentinel2LowCloudDownLoadImageImpl import AutoFindSentinel2LowCloudDownLoadImageImpl


class AutoFindSentinel2LowCloudImplThread(QThread):
    emit_thumbnail_url = Signal(list)
    emit_progress = Signal(dict)
    def __init__(self, sentinel2_data_source_configure: Sentinel2DataSourceConfigure, thread_operate_status: ThreadOperateStatus):
        super().__init__()
        self.sentinel2_data_source_configure = sentinel2_data_source_configure
        self.thread_operate_status = thread_operate_status
        roi = geemap.shp_to_ee(sentinel2_data_source_configure.roi.file_path)
        # 构造条件：年份 = 2020 且 NDVI > 2000
        builder = (
            ConditionBuilder()
            .add("system:time_start", "gte", ee.Date(sentinel2_data_source_configure.start_date).millis())
            .add("system:time_start", "lt", ee.Date(sentinel2_data_source_configure.end_date).millis())
            .and_()
            .add('geometry', 'bounds', roi)
            .and_()
            .add('CLOUDY_PIXEL_PERCENTAGE', 'lt', sentinel2_data_source_configure.cloud_coverage)
            .and_()
        )

        filter_condition = builder.build()
        collection = ee.ImageCollection(sentinel2_data_source_configure.s2_sr_harmonized).filter(filter_condition)
        filtered = collection.filter(filter_condition)
        info = filtered.getInfo()
        sentinel2_image = parse_any(info, sentinel2_data_source_configure.roi)
        self.auto_find_sentinel2_low_cloud_impl = AutoFindSentinel2LowCloudDownLoadImageImpl(
            sentinel2_image=sentinel2_image,
            sentinel2_data_source_configure=self.sentinel2_data_source_configure)

        self.set_thread_operate_status(self.thread_operate_status)
        self.auto_find_sentinel2_low_cloud_impl.emit_thumbnail_url.connect(self.call_back)
        self.auto_find_sentinel2_low_cloud_impl.emit_progress.connect(self.call_back_progress_max_value)

    def set_thread_operate_status(self, thread_operate_status: ThreadOperateStatus):
        self.auto_find_sentinel2_low_cloud_impl.receive_thead_operate_status.emit(thread_operate_status)

    @Slot(list)
    def call_back(self, result):
        self.emit_thumbnail_url.emit(result)

    @Slot(dict)
    def call_back_progress_max_value(self, result):
        print(result)
        self.emit_progress.emit(result)

    def run(self):
        print("run 线程：", QThread.currentThread(), threading.get_ident())
        # if self.auto_find_sentinel2_low_cloud_impl.thread_operate_status.is_paused:
        #     self.set_thread_operate_status(self.thread_operate_status)
        # else:
        self.auto_find_sentinel2_low_cloud_impl.find()
