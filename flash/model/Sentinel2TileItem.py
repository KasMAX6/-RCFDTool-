# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/11 19:40
from datetime import datetime

from flash.model.Sentinel2Image import Sentinel2Image
from flash.model.TileGroup import TileGroup


class Sentinel2TileItem(TileGroup):
    def __init__(self, tile: str, id: str = None, start_date: str = None, end_date: str = None,
                 sentinel2Image: Sentinel2Image = None):
        super().__init__(tile, id)
        self.start_date = datetime.fromtimestamp(start_date / 1000).strftime("%Y-%m-%d")
        self.end_date = datetime.fromtimestamp(end_date / 1000).strftime("%Y-%m-%d")
        self.sentinel2Image = sentinel2Image
