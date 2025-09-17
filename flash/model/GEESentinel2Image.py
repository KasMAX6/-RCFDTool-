from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List
from typing import Union

import ee
import geemap

from flash.model.SentinelImage import SentinelImage
from flash.model.VectorFile import VectorFile

CLOUDY_PIXEL_PERCENTAGE = 'CLOUDY_PIXEL_PERCENTAGE'


# ========== 主类：组合属性 ==========
@dataclass
class Sentinel2Image(SentinelImage):


    roi: VectorFile  # ROI 属性，默认为 None

    def sort_key(self):
        return CLOUDY_PIXEL_PERCENTAGE


