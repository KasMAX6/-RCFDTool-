# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/12 9:02
from typing import Dict, Tuple

import ee
import geemap

from flash.model.VectorFile import VectorFile


def calculate_pixel_coverage(image: ee.Image, roi, scale=30):
    """核心：基于像素的真实覆盖计算 - 修复版"""
    roi_geom = roi.geometry() if hasattr(roi, 'geometry') else roi

    # 镶嵌并获取有效像素遮罩
    valid_mask = image.select(0).mask()

    # 计算面积 - 添加ErrorMargin
    roi_area = roi_geom.area(ee.ErrorMargin(1))
    covered_area = ee.Image.pixelArea().updateMask(valid_mask).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=roi_geom,
        scale=scale,
        maxPixels=1e9,
        tileScale=4  # 添加tileScale避免内存问题
    ).values().get(0)

    covered = ee.Number(covered_area).max(0)
    coverage_ratio = covered.divide(roi_area)

    return {
        'uncovered_area_km2': roi_area.subtract(covered).divide(1e6),
        'coverage_percent': coverage_ratio.multiply(100),
        'is_fully_covered': coverage_ratio.gte(0.999)
    }


def get_uncovered_area_gee(image, roi):
    """GEE版本简化函数"""
    return calculate_pixel_coverage(image, roi)['uncovered_area_km2'].getInfo()


def is_img_cover_roi(image, roi):
    """GEE版本简化函数"""
    return calculate_pixel_coverage(image, roi)['is_fully_covered'].getInfo()


def is_img_cover_roi_ret_area(image: ee.Image, roi: VectorFile):
    """GEE版本简化函数"""
    roi = geemap.shp_to_ee(roi.file_path)
    coverage = calculate_pixel_coverage(image, roi)
    return coverage['is_fully_covered'].getInfo(), coverage['uncovered_area_km2'].getInfo()


def get_thumbnail_url(
        self,
        image: ee.Image,
        region: ee.Geometry,
        vis_params: Dict,
        dimensions: Tuple[int, int] = (512, 512)
) -> str:
    """
    获取缩略图URL

    Args:
        image: GEE影像对象
        region: 感兴趣区域
        vis_params: 可视化参数，如 {'bands': ['B4','B3','B2'], 'min': 0, 'max': 3000}
        dimensions: 缩略图尺寸 (width, height)

    Returns:
        缩略图URL
    """
    try:
        # 更新可视化参数
        thumb_params = vis_params.copy()
        thumb_params.update({
            'dimensions': dimensions,
            'region': region,
            'format': 'png'
        })

        # 获取缩略图URL
        thumbnail_url = image.getThumbURL(thumb_params)
        return thumbnail_url

    except Exception as e:
        print(f"获取缩略图URL失败: {e}")
        raise
