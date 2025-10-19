# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/14 21:18
import dataclasses
import os
import shutil

from osgeo import gdal
import osgeo_utils

@dataclasses.dataclass
class DataPathConfig:
    base_path: str = os.path.join(os.getcwd(),'flash')
    roi_name: str = None
    gdal_bin_path: str = None
    download_path: str = os.path.join(base_path,'downloads')
    def __post_init__(self):
        self.__mkdirs()
        pass

    def __mkdirs(self):
        os.makedirs(self.thumbnail_path, exist_ok=True)
        os.makedirs(self.download_path, exist_ok=True)

    @property
    def thumbnail_path(self):
        return os.path.join(self.base_path, 'thumbnails')

    @property
    def roi_path(self):
        return os.path.join(self.thumbnail_path, self.roi_name)

    @property
    def key_path(self):
        return os.path.join(self.base_path, 'key')

    @property
    def mosaic_path(self):
        return os.path.join(self.roi_path, 'mosaic')

    def all_not_empty(self):
        return all([self.base_path, self.roi_name, self.gdal_bin_path]) and self.download_path is not None