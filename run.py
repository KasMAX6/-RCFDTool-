# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 20:32
import ee
import geemap
from PySide6.QtCore import QObject, Slot, QThread

from flash.common.AutoFindSentinel2LowCloudImplThread import AutoFindSentinel2LowCloudImplThread
from flash.model.ConditionBuilder import ConditionBuilder
from flash.model.Initializer import Initializer
from flash.service.AutoFindSentinel2LowCloudDownLoadImageImpl import AutoFindSentinel2LowCloudDownLoadImageImpl
from flash.service.FilterImageService import FilterImageService
from flash.constants.GEEDataSource import *
from flash.model.VectorFile import VectorFile
from flash.model.Sentinel2Image import *


def callback(result):
    print(result)


class CallBack_Thread(QObject):
    def __init__(self):
        super().__init__()

    @Slot(list)
    def print_result(self, result):
        print('来了佬滴')
        print(result)


if __name__ == '__main__':
    Initializer().initialize()
    condition_builder = ConditionBuilder()
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    vec_file: VectorFile = VectorFile(r"E:\20250807商都项目\disaste_project\outdata\bylk\bylk.shp")
    roi = geemap.shp_to_ee(vec_file.file_path)
    # 构造条件：年份 = 2020 且 NDVI > 2000
    builder = (
        ConditionBuilder()
        .add("system:time_start", "gte", ee.Date("2025-08-30").millis())
        .add("system:time_start", "lt", ee.Date("2025-9-10").millis())
        .and_()
        .add('geometry', 'bounds', roi)
        .and_()
        .add('CLOUDY_PIXEL_PERCENTAGE', 'lt', 10)
        .and_()
    )

    filter_condition = builder.build()

    filtered = collection.filter(filter_condition)
    info = filtered.getInfo()
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    #app = QCoreApplication([])

    # 创建线程
    # worker = AutoFindSentinel2LowCloudImplThread(collection=info, roi=vec_file, batch_size=10)
    # callback = CallBack_Thread()

    #worker.gained_thumbnail_url.connect(callback.print_result)

    #worker.start()
    #print('线程开启了')
    # 保证主线程事件循环运行
    #app.exec()
    meta = parse_any(info, vec_file)

    auto_find_sentinel2_low_cloud_impl = AutoFindSentinel2LowCloudDownLoadImageImpl(sentinel2_image=meta, roi=vec_file)
    auto_find_sentinel2_low_cloud_impl.find()
    ##print(filtered.first().getInfo())  # 打印符合条件的影像数量
