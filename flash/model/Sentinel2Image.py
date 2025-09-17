from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List
from typing import Union

import ee
import geemap

from flash.model.SentinelImage import SentinelImage
from flash.model.VectorFile import VectorFile

CLOUDY_PIXEL_PERCENTAGE = 'CLOUDY_PIXEL_PERCENTAGE'


# ========== 基础结构 ==========
@dataclass
class PixelType:
    type: str
    precision: str
    min: int
    max: int


@dataclass
class BandInfo:
    id: str
    data_type: PixelType
    dimensions: List[int] | None
    crs: str
    crs_transform: List[float]


class OrbitDirection(Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


# ========== 主类：组合属性 ==========
@dataclass
class Sentinel2Image(SentinelImage):

    version: int
    bands: List[BandInfo]
    properties: Dict[str, Any]

    # 核心 Sentinel-2 属性
    CLOUDY_PIXEL_PERCENTAGE: float
    SPACECRAFT_NAME: str
    SENSING_ORBIT_DIRECTION: OrbitDirection
    SENSING_ORBIT_NUMBER: int
    MGRS_TILE: str
    PROCESSING_BASELINE: str
    GENERATION_TIME: int
    system_asset_size: int
    system_time_start: int
    system_time_end: int

    roi: VectorFile  # ROI 属性，默认为 None

    def sort_key(self):
        return CLOUDY_PIXEL_PERCENTAGE



def parse_sentinel2_metadata(info: dict, roi: VectorFile) -> Sentinel2Image:
    """解析单个 Image"""

    def to_enum(enum_cls, value):
        if value is None: return None
        try:
            return enum_cls(value)
        except:
            return None

    def parse_pixel_type(d):
        return PixelType(
            type=d.get("type"),
            precision=d.get("precision"),
            min=d.get("min"),
            max=d.get("max")
        )

    def parse_band_info(b):
        return BandInfo(
            id=b.get("id"),
            data_type=parse_pixel_type(b.get("data_type")),
            dimensions=b.get("dimensions"),
            crs=b.get("crs"),
            crs_transform=b.get("crs_transform"),
        )

    p = info.get("properties", {})

    return Sentinel2Image(
        type=info.get("type"),
        id=info.get("id"),
        version=info.get("version"),
        bands=[parse_band_info(b) for b in info.get("bands", [])],
        properties=p,
        CLOUDY_PIXEL_PERCENTAGE=p.get("CLOUDY_PIXEL_PERCENTAGE"),
        SPACECRAFT_NAME=p.get("SPACECRAFT_NAME"),
        SENSING_ORBIT_DIRECTION=to_enum(OrbitDirection, p.get("SENSING_ORBIT_DIRECTION")),
        SENSING_ORBIT_NUMBER=p.get("SENSING_ORBIT_NUMBER"),
        MGRS_TILE=p.get("MGRS_TILE"),
        PROCESSING_BASELINE=p.get("PROCESSING_BASELINE"),
        GENERATION_TIME=p.get("GENERATION_TIME"),
        system_asset_size=p.get("system:asset_size"),
        system_time_start=p.get("system:time_start"),
        system_time_end=p.get("system:time_end"),
        roi=roi
    )


def parse_any(info: dict,roi:VectorFile) -> Union[Sentinel2Image, List[Sentinel2Image]]:
    """统一入口：支持 Image / ImageCollection"""
    if info.get("type") == "ImageCollection":
        return [parse_sentinel2_metadata(f,roi) for f in info.get("features", [])]
    elif info.get("type") == "Image":
        return parse_sentinel2_metadata(info,roi)
    else:
        raise ValueError(f"不支持的类型: {info.get('type')}")
