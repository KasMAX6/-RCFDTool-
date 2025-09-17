# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/12 14:35
"""
Google Earth Engine 缩略图核心功能
简化版本：传入image获取缩略图URL，并提供下载功能
"""

import ee
import requests
import os
from typing import Dict, Optional, Tuple


class GEEThumbnail:
    """GEE 缩略图核心功能类"""

    def __init__(self):
        self.vis_params = {
            'bands': ['B4', 'B3', 'B2'],  # 真彩色
            'min': 0,
            'max': 3000
        }

    def get_thumbnail_url(
            self,
            image: ee.Image,
            region: ee.Geometry,
            dimensions: Tuple[int, int] = (512, 512)
    ) -> str:
        """
        获取缩略图URL

        Args:
            image: GEE影像对象
            region: 感兴趣区域
            dimensions: 缩略图尺寸 (width, height)

        Returns:
            缩略图URL
        """
        try:
            # 更新可视化参数
            thumb_params = self.vis_params.copy()
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

    def download_thumbnail(self, url: str, image_id: str) -> str:
        """
        下载缩略图到thumb文件夹

        Args:
            url: 缩略图URL
            image_id: 影像ID，用作文件名

        Returns:
            保存的文件路径
        """
        try:
            # 创建thumb文件夹
            thumb_dir = "thumb"
            os.makedirs(thumb_dir, exist_ok=True)

            # 文件路径
            file_path = os.path.join(thumb_dir, f"{image_id}.png")

            # 下载文件
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"缩略图已保存: {file_path}")
            return file_path

        except Exception as e:
            print(f"下载缩略图失败: {e}")
            raise


# 使用示例
def example_usage():
    """使用示例"""

    # 初始化
    thumbnail_gen = GEEThumbnail()

    # 定义区域（以北京为例）
    region = ee.Geometry.Rectangle([116.2, 39.8, 116.6, 40.2])

    # 获取Sentinel-2影像
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterDate('2023-06-01', '2023-08-31')
                  .filterBounds(region)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))

    image = collection.median()

    # 获取缩略图URL
    thumbnail_url = thumbnail_gen.get_thumbnail_url(
        image=image,
        region=region,
        dimensions=(512, 512)
    )

    print(f"缩略图URL: {thumbnail_url}")

    # 下载缩略图
    file_path = thumbnail_gen.download_thumbnail(
        url=thumbnail_url,
        image_id="beijing_s2_202306_202308"
    )

    return thumbnail_url, file_path


if __name__ == "__main__":
    # 运行示例
    url, path = example_usage()
    print(f"完成！URL: {url}")
    print(f"文件保存至: {path}")
