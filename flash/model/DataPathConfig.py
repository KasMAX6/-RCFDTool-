# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/14 21:18
import dataclasses
import os


@dataclasses.dataclass
class DataPathConfig:
    base_path: str = None
    roi_name: str = None
    gdal_bin_path: str = None
    download_path: str = None
    def __post_init__(self):
        pass

    def __mkdirs(self):
        os.makedirs(self.thumbnail_path, exist_ok=True)
        os.makedirs(self.roi_path, exist_ok=True)

    @property
    def thumbnail_path(self):
        return os.path.join(self.base_path, 'thumbnails')

    @property
    def roi_path(self):
        return os.path.join(self.thumbnail_path, self.roi_name)

    @property
    def mosaic_path(self):
        return os.path.join(self.roi_path, 'mosaic')
    def all_not_empty(self):
        return all([self.base_path, self.roi_name, self.gdal_bin_path]) and self.download_path is not None