# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 21:43
import abc
import dataclasses

import ee
import geemap

@dataclasses.dataclass
class RemoteSensingImage(abc.ABC):
    # 通用元信息
    type: str
    id: str

    @abc.abstractmethod
    def sort_key(self):
        pass


    def area_eq_roi(self):
        roi = geemap.shp_to_ee(self.roi.file_path).geometry()
        # 求 ROI 中未被影像覆盖的区域
        img = ee.Image(self.id)
        uncovered = roi.difference(img.geometry(), 1)

        # 计算未覆盖面积（m²）
        uncovered_area = uncovered.area().getInfo()
        return uncovered_area == 0

