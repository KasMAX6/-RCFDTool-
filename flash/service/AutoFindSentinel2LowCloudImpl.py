# -*- coding: utf-8 -*-
# @Author : ZXQ
# @Time : 2025/9/11 9:35
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
from matplotlib.image import thumbnail

from flash.common.QtExecutor import QtExecutor
from flash.common.TaskThread import TaskThread
from flash.model.RemoteSensingImage import RemoteSensingImage
from flash.model.Sentinel2Image import Sentinel2Image
from flash.model.Sentinel2TileItem import Sentinel2TileItem
from flash.model.VectorFile import VectorFile
from flash.service.FindLowCloudService import FindLowCloud
from flash.util.GEEScriptFunUtil import is_img_cover_roi_ret_area, calculate_pixel_coverage


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


class AutoFindSentinel2LowCloudImpl(FindLowCloud):
    emit_thumbnail_url = Signal(list)
    emit_progress = Signal(dict)

    def __init__(self, sentinel2_image: List[Sentinel2Image], roi: VectorFile,
                 batch_size=40):
        super().__init__(sentinel2_image)
        self.roi = roi
        self.low_cld_coverage_images = []
        self.batch_size = batch_size

    def filter(self, image: RemoteSensingImage):
        image: Sentinel2Image
        return super().filter(image)

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

    # 自适应并发版本
    def try_multi_tile_mosaic_adaptive(self, tile_dict):
        """自适应并发版本"""
        combinations = self._get_all_combinations(tile_dict)
        self.emit_progress.emit({'max': len(combinations), 'current': 0})
        pre_num =  0
        for i in range(0, len(combinations), self.batch_size):
            batch_combinations = combinations[i:i + self.batch_size]
            ee_results = self._create_ee_batch_computation(batch_combinations)
            results = ee_results.getInfo()
            covereds = list(filter(lambda x: x['is_covered'], results))
            # 先做一个 covered id 集合
            # 根据covereds的id筛选对应的combinations
            covered_ids = [covered['id'] for covered in covereds]
            filtered_combinations = [batch_combinations[i] for i in covered_ids if i < len(batch_combinations)]

            for i in range(0, len(filtered_combinations), self.batch_size):
                batch_combinations = filtered_combinations[i:i + self.batch_size]
                thumbnail_urls = self.get_thumbnail_urls_for_covered_results(batch_combinations).getInfo()
                pre_num += len(thumbnail_urls)
                self.emit_progress.emit({'max': len(combinations), 'current': pre_num})
                self.emit_thumbnail_url.emit(thumbnail_urls)

    def _create_ee_batch_computation(self, all_combinations):
        """创建Earth Engine批量计算，同时获取缩略图"""
        roi_ee = geemap.shp_to_ee(self.roi.file_path)

        results_list = []

        for i, combo in enumerate(all_combinations):
            try:
                # 修复：正确提取 ee.Image 对象
                ee_images = []
                for item in combo['items']:
                    ee_images.append(ee.Image(item.id))

                # 创建镶嵌
                clipped_mosaic = ee.ImageCollection(ee_images).mosaic().clip(roi_ee.geometry())

                # 使用新的覆盖率计算函数
                coverage_info = calculate_pixel_coverage(clipped_mosaic, roi_ee)
                is_covered = coverage_info['is_fully_covered']

                result = ee.Dictionary({
                    'id': i,
                    'tile_count': combo['tile_count'],
                    'tiles': ee.List(combo['tile_combo']),
                    'item_ids': ee.List([item.id for item in combo['items']]),
                    'is_covered': is_covered,
                    'coverage_percentage': coverage_info['coverage_percent'],
                    'uncovered_area_km2': coverage_info['uncovered_area_km2'],
                })
                results_list.append(result)

            except Exception as e:
                print(f"处理组合 {i} 失败: {e}")
                # 添加错误记录
                error_result = ee.Dictionary({
                    'id': i,
                    'error': str(e),
                    'is_covered': False,
                    'coverage_percentage': 0,
                    'uncovered_area_km2': 999999,
                    'thumbnail_url': ''
                })
                results_list.append(error_result)

        return ee.List(results_list)

    def get_thumbnail_urls_for_covered_results(self, all_combinations):
        """只获取覆盖结果的缩略图URL"""
        roi_ee = geemap.shp_to_ee(self.roi.file_path)

        results_list = []

        for i, combo in enumerate(all_combinations):
            try:
                # 提取 ee.Image 对象
                ee_images = []
                for item in combo['items']:
                    ee_images.append(ee.Image(item.id))

                # 创建镶嵌
                clipped_mosaic = ee.ImageCollection(ee_images).mosaic().clip(roi_ee.geometry())

                # 计算覆盖率
                coverage_info = calculate_pixel_coverage(clipped_mosaic, roi_ee)
                is_covered = coverage_info['is_fully_covered']

                # 只为覆盖的结果获取缩略图URL
                thumbnail_url = ''
                if is_covered:
                    try:
                        thumbnail_url = clipped_mosaic.getThumbURL({
                            'bands': ['B4', 'B3', 'B2'],
                            'min': 0, 'max': 3000,
                            'gamma': 1.4,
                            'dimensions': 256,
                            'region': roi_ee.geometry(),
                            'format': 'png'
                        })
                    except Exception as thumb_error:
                        print(f"获取缩略图失败 (组合 {i}): {thumb_error}")
                        thumbnail_url = ''

                result = ee.Dictionary({
                    'id': i,
                    'item_ids': ee.List([item.id for item in combo['items']]),
                    'thumbnail_url': thumbnail_url
                })
                results_list.append(result)

            except Exception as e:
                print(f"处理组合 {i} 失败: {e}")
                error_result = ee.Dictionary({
                    'id': i,
                    'thumbnail_url': ''
                })
                results_list.append(error_result)

        return ee.List(results_list)
    def _get_all_combinations(self, tile_dict):
        """获取所有组合"""
        loc_combinations = []
        sorted_tile_dict = self._sort_tiles_by_priority(tile_dict)

        for tile_count in range(1, len(tile_dict) + 1):
            for tile_combo in combinations(sorted_tile_dict.keys(), tile_count):
                tile_items = [sorted_tile_dict[name] for name in tile_combo]
                limited_items = [sorted(items, key=lambda x: x.sentinel2Image.CLOUDY_PIXEL_PERCENTAGE)
                                 for items in tile_items]

                for items_combo in product(*limited_items):
                    loc_combinations.append({
                        'items': items_combo,
                        'tile_combo': tile_combo,
                        'tile_count': tile_count
                    })

        return loc_combinations

    def fined_call_back(self, url):
        """您的原始回调函数，现在在主线程中安全执行。"""
        print(f"主线程接收到新结果: {url}")


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

    def _process_combination_safe(self, items_combination, tile_combination, tile_count):
        """安全的组合处理，包含异常处理"""
        try:
            return self._process_combination(items_combination, tile_combination, tile_count)
        except Exception as e:
            print(f"组合处理异常: {e}")
            return None

    def _process_combination(self, items_combination, tile_combination, tile_count):
        """处理单个组合的镶嵌和覆盖检查"""
        try:

            mosaic_result = self.try_mosaic_coverage(items_combination)
            if mosaic_result['success']:
                return {
                    'type': 'mosaic_cover',
                    'tile_count': tile_count,
                    'tiles': list(tile_combination),
                    'items': items_combination,
                    'item_ids': [item.id for item in items_combination],
                    'mosaic_result': mosaic_result,
                    'action': 'mosaic_and_display',

                }
        except Exception as e:
            print(f"组合处理失败: {e}")

        return None

    def try_mosaic_coverage(self, items_combination):
        """
        尝试将多个item镶嵌后检查是否覆盖研究区
        返回镶嵌结果和是否成功覆盖
        """
        try:
            # 执行镶嵌操作 - 优化版本
            mosaic_image = self.mosaic_images_optimized([item.sentinel2Image for item in items_combination])

            # 检查镶嵌后的影像是否覆盖研究区
            is_coverage, area_km2 = is_img_cover_roi_ret_area(roi=self.roi, image=mosaic_image)

            return {
                'success': is_coverage,
                'mosaic_image': mosaic_image,
                'coverage_info': area_km2
            }

        except Exception as e:
            print(f"镶嵌失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'mosaic_image': None
            }

    def mosaic_images_optimized(self, sentinel2_images):
        """
        优化的镶嵌方法：批量处理，减少GEE API调用
        """
        # 提取影像id列表
        image_ids = [item.id for item in sentinel2_images]

        # 使用批量方式创建ImageCollection
        ee_collection = ee.ImageCollection(image_ids).mosaic()

        # 镶嵌成一张影像，添加质量排序
        # mosaic_image = ee_collection.qualityMosaic('CLOUDY_PIXEL_PERCENTAGE')  # 按云量质量镶嵌

        return ee_collection

    def mosaic_images(self, sentinel2_images):
        """
        原始镶嵌方法（保持兼容性）
        """
        return self.mosaic_images_optimized(sentinel2_images)

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

    def get_coverage_info(self, mosaic_image):
        """获取镶嵌后影像的覆盖信息"""
        try:
            # 使用更高效的覆盖信息计算
            coverage_info = {
                'mosaic_bands': mosaic_image.bandNames().getInfo(),
                'mosaic_projection': mosaic_image.projection().getInfo(),
                'pixel_count': mosaic_image.select(0).reduceRegion(
                    reducer=ee.Reducer.count(),
                    geometry=self.roi.geometry(),
                    scale=30,
                    maxPixels=1e9
                ).getInfo()
            }
            return coverage_info
        except Exception as e:
            print(f"获取覆盖信息失败: {e}")
            return {}

    def sort_images(self):
        """
        按云量百分比排序影像
        """
        self.remote_sensing_image.sort(key=lambda x: x.CLOUDY_PIXEL_PERCENTAGE)

    def get_optimization_stats(self):
        """获取优化统计信息"""
        return {
            'total_images': len(self.remote_sensing_image),
            'max_workers': self.max_workers,
            'results_found': len(self.low_cld_coverage_images)
        }
