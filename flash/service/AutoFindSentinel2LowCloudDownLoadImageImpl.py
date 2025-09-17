# -*- coding: utf-8 -*-
# @Author : ZXQ
# @Time : 2025/9/11 9:35
import itertools
import os
from typing import List, Dict, Tuple, Iterator
from itertools import combinations, product, groupby
from operator import attrgetter
import concurrent.futures
from threading import Lock
import time
import concurrent.futures
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import ee
import geemap
from PySide6.QtCore import QMutex, Slot, Signal
from geemap import get_image_thumbnail, get_bounds
from matplotlib.image import thumbnail

from flash.common.QtExecutor import QtExecutor
from flash.common.TaskThread import TaskThread
from flash.model.DataPathConfig import DataPathConfig
from flash.model.RemoteSensingImage import RemoteSensingImage
from flash.model.Sentinel2DataSourceConfigure import Sentinel2DataSourceConfigure
from flash.model.Sentinel2Image import Sentinel2Image
from flash.model.Sentinel2TileItem import Sentinel2TileItem
from flash.model.ThreadOperateStatus import ThreadOperateStatus
from flash.model.VectorFile import VectorFile
from flash.service.FindLowCloudService import FindLowCloud
from flash.util.GEEScriptFunUtil import is_img_cover_roi_ret_area, calculate_pixel_coverage
from flash.util.S2_Util import png_to_geotiff_with_rasterio, create_mosaic_with_gdal


class MosaicCoverResult:
    """镶嵌覆盖结果对象"""

    def __init__(self, result_dict):
        # 设置基本属性
        self.type = result_dict.get('type', 'mosaic_cover')
        self.tile_count = result_dict.get('tile_count', 0)
        self.tiles = result_dict.get('tiles', [])
        self.items = result_dict.get('items', ())
        self.item_ids = result_dict.get('item_ids', [])
        self.mosaic_result = result_dict.get('mosaic_result', {})
        self.action = result_dict.get('action', '')

        # 生成id属性（基于tiles和item_ids）
        if self.tiles and self.item_ids:
            tiles_str = '_'.join(self.tiles)
            self.id = f"{self.type}_{tiles_str}_{len(self.item_ids)}items"
        else:
            self.id = None

    def __str__(self):
        return f"MosaicCoverResult(id={self.id}, tiles={self.tiles}, tile_count={self.tile_count})"

    def __repr__(self):
        return self.__str__()


def create_mosaic_cover_object(result_dict):
    """将字典转换为MosaicCoverResult对象"""
    return MosaicCoverResult(result_dict)


class AutoFindSentinel2LowCloudDownLoadImageImpl(FindLowCloud):
    emit_thumbnail_url = Signal(list)
    emit_progress = Signal(dict)
    receive_thead_operate_status = Signal(ThreadOperateStatus)

    def __init__(self, sentinel2_image: List[Sentinel2Image],
                 sentinel2_data_source_configure: Sentinel2DataSourceConfigure):
        super().__init__(sentinel2_image)
        self.sentinel2_data_source_configure = sentinel2_data_source_configure
        self.low_cld_coverage_images = []
        self.batch_size = self.sentinel2_data_source_configure.batch_size
        self.roi = self.sentinel2_data_source_configure.roi
        self.data_path_config = sentinel2_data_source_configure.data_path_config
        self.receive_thead_operate_status.connect(self.on_thread_operate_status)  ## 接收线程操作状态信号

    def filter(self, image: RemoteSensingImage):
        image: Sentinel2Image
        return super().filter(image)

    @Slot(ThreadOperateStatus)
    def on_thread_operate_status(self, thread_operate_status: ThreadOperateStatus):
        self.thread_operate_status = thread_operate_status

    def find(self):
        # 必须先按 MGRS_TILE 排序
        sorted_list = sorted(self.remote_sensing_image, key=attrgetter('MGRS_TILE'))
        tile_dict = {}

        for key, g in groupby(sorted_list, key=attrgetter('MGRS_TILE')):
            items = list(g)
            tile_dict[key] = [
                Sentinel2TileItem(
                    tile=key,
                    id=item.id,
                    start_date=item.system_time_start,
                    end_date=item.system_time_end,
                    sentinel2Image=item
                )
                for item in items
            ]

        # 2. 逐步增加tile数量进行组合镶嵌 - 并发优化版本
        self.try_multi_tile_mosaic_adaptive(tile_dict)

    def generate_combinations(self, data_dict):
        """
        对字典中每个键的列表进行全排列组合，并考虑性能。

        Args:
            data_dict (dict): 包含列表的字典。

        Returns:
            generator: 包含所有排列组合方案的生成器。
        """
        # 获取所有的键
        keys = list(data_dict.keys())

        # 获取所有键的排列，包括单元素排列
        all_key_permutations = []
        for i in range(len(keys), 0, -1):
            all_key_permutations.extend(itertools.permutations(keys, i))

        # 遍历每个键的排列
        for key_permutation in all_key_permutations:
            # 获取对应的值列表
            lists_to_combine = [data_dict[key] for key in key_permutation]

            # 使用 itertools.product 生成笛卡尔积
            # product 返回一个生成器，性能高效且节省内存
            for combination in itertools.product(*lists_to_combine):
                yield combination

    def generate_combinations_limited(self, data_dict, limit=1000):
        """
        对字典中每个键的列表进行全排列组合，并考虑性能，最多生成指定数量的组合。

        Args:
            data_dict (dict): 包含列表的字典。
            limit (int): 需要生成的最大组合数量。

        Returns:
            generator: 包含所有排列组合方案的生成器（最多返回 limit 个）。
        """
        # 初始化一个计数器
        count = 0

        # 获取所有的键
        keys = list(data_dict.keys())

        # 获取所有键的排列，包括单元素排列
        all_key_permutations = []
        for i in range(1, len(keys) + 1):
            all_key_permutations.extend(itertools.permutations(keys, i))

        # 遍历每个键的排列
        for key_permutation in all_key_permutations:
            # 如果已经达到数量限制，可以提前跳出最外层循环
            if count >= limit:
                return

            # 获取对应的值列表
            lists_to_combine = [data_dict[key] for key in key_permutation]

            # 使用 itertools.product 生成笛卡尔积
            # product 返回一个生成器，性能高效且节省内存
            for combination in itertools.product(*lists_to_combine):
                # 检查计数器是否已达到限制
                if count >= limit:
                    return  # 退出生成器函数

                yield combination
                count += 1

    def write_thumbnail_to_file_callback(self, file_path):
        """
        写入缩略图到文件
        :param file_path:
        :return:
        """

        self.emit_thumbnail_url.emit(file_path)
        self.current_image_num += 1
        self.emit_progress.emit({'max_tile_num': self.total_combination_num, 'current_mosaic_num': self.current_image_num})

    # 自适应并发版本
    def try_multi_tile_mosaic_adaptive(self, tile_dict):
        """自适应并发版本"""
        total_tile =  len(tile_dict)

        for tile_id, images in tile_dict.items():
            ## 获取RGB缩略图url和边界点
            thumbnail_coordinates = self.get_image_thumbnail_coordinates(tile_id, images)
            ## 缩略图写入边界点转tif
            self.thumbnail_to_tif_with_crs(tile_id, thumbnail_coordinates)
        ### 所有tile的tif准备好了
        ### 生成组合方案
        all_combinations = self.generate_combinations(tile_dict)
        self.emit_progress.emit({'max_tile_num': total_tile, 'current_mosaic_num': 0})
        # self.total_combination_num = len(all_combinations)
        self.total_combination_num = total_tile
        self.current_image_num = 0
        ### 创建批量计算
        for combination in all_combinations:
            while self.thread_operate_status.is_paused:
                time.sleep(0.5)
            if self.thread_operate_status.is_stopped:
                break
            if self.thread_operate_status.is_running:
                create_mosaic_with_gdal(combination, self.data_path_config.roi_path,
                                        self.write_thumbnail_to_file_callback,
                                        self.data_path_config.gdal_bin_path,
                                        self.sentinel2_data_source_configure.batch_size)

    def thumbnail_to_tif_with_crs(self, tile_id, thumbnail_coordinates):
        """
        缩略图写入边界点转tif
        :param thumbnail_coordinates:
        :return:
        """
        for thumbnail_coordinate in thumbnail_coordinates:
            id = thumbnail_coordinate['id']
            png_path = os.path.join(self.data_path_config.roi_path,
                                    tile_id, f'{id}_{self.sentinel2_data_source_configure.batch_size}.png')
            tif_path = os.path.join(self.data_path_config.roi_path,
                                    tile_id, f'{id}_{self.sentinel2_data_source_configure.batch_size}.tif')
            png_to_geotiff_with_rasterio(png_path, thumbnail_coordinate['footprint'], tif_path)
            os.remove(png_path)
        pass

    def _sort_tiles_by_priority(self, tile_dict):
        """智能排序：按覆盖度和云量优先级排序tiles"""
        tile_scores = {}

        for tile_name, items in tile_dict.items():
            # 计算该tile的综合得分
            best_item = min(items, key=lambda x: x.sentinel2Image.CLOUDY_PIXEL_PERCENTAGE)
            cloud_score = 100 - best_item.sentinel2Image.CLOUDY_PIXEL_PERCENTAGE  # 云量越少得分越高

            # 可以添加更多评分维度，如覆盖面积、图像质量等
            tile_scores[tile_name] = cloud_score

        # 按得分排序
        sorted_tiles = sorted(tile_dict.keys(), key=lambda x: tile_scores[x], reverse=True)
        return {tile: tile_dict[tile] for tile in sorted_tiles}

    def _insufficient_data_result(self):
        """数据不足结果"""
        return {
            'type': 'insufficient_data',
            'message': 'Not enough tiles for mosaic',
            'action': 'error'
        }

    def _no_coverage_result(self):
        """无覆盖结果"""
        return {
            'type': 'no_coverage',
            'message': 'No combination can cover the study area',
            'action': 'error_no_coverage'
        }

    def sort_images(self):
        """
        按云量百分比排序影像
        """
        self.remote_sensing_image.sort(key=lambda x: x.CLOUDY_PIXEL_PERCENTAGE)

    def get_image_thumbnail_coordinates(self, tile_id, images):
        """获取影像的缩略图URL和边界坐标"""
        os.makedirs(os.path.join(self.data_path_config.roi_path, tile_id), exist_ok=True)
        thumbnail_coordinates = []
        for image in images:
            try:
                ## 存在则跳过

                if (os.path.exists(os.path.join(self.data_path_config.roi_path, tile_id,
                                                f'{image.id}_{self.sentinel2_data_source_configure.batch_size}.png')) or
                        os.path.exists(
                            os.path.join(self.data_path_config.roi_path, tile_id,
                                         f'{image.id}_{self.sentinel2_data_source_configure.batch_size}.tif'))):
                    continue
                roi = geemap.geopandas_to_ee(self.roi.gdf)
                ee_image = ee.Image(image.id).clip(roi)
                id = image.id
                file_name = f'{id}_{self.sentinel2_data_source_configure.batch_size}.png'
                get_image_thumbnail(ee_image,
                                    out_img=os.path.join(self.data_path_config.roi_path, tile_id, file_name),
                                    vis_params={
                                        'bands': ['B4', 'B3', 'B2'],
                                        'min': 0,
                                        'max': 3000
                                    },
                                    dimensions=self.sentinel2_data_source_configure.batch_size,
                                    format='png', crs='epsg:4326')
                footprint = ee_image.geometry().bounds().coordinates().get(0).getInfo()
                thumbnail_coordinates.append({'id': image.id, 'footprint': footprint})

            except Exception as e:
                print(f"获取影像 {image.id} 缩略图或边界失败: {e}")
                image.thumbnail_url = ''
                image.boundary_coordinates = []
        return thumbnail_coordinates
