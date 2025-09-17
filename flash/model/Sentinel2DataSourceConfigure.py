import dataclasses
from typing import Optional

from flash.model.DataPathConfig import DataPathConfig
from flash.model.DataSourceConfigure import DataSourceConfigure
from flash.model.VectorFile import VectorFile


# -*- coding: utf-8 -*-
# @Author : ZXQ
# @Time : 2025/9/13 18:42

@dataclasses.dataclass
class Sentinel2DataSourceConfigure(DataSourceConfigure):
    s2_sr_harmonized: str = 'COPERNICUS/S2_SR_HARMONIZED'
    cloud_coverage: Optional[float] = None

    def __post_init__(self):
        self.data_path_config = DataPathConfig()
    def set_end_date(self, end_date: str):
        self.end_date = end_date
        print(self)
    def set_start_date(self, start_date: str):
        self.start_date = start_date
    def set_cloud_coverage(self, cloud_coverage: float):
        self.cloud_coverage = cloud_coverage
    def set_satellite_type(self, satellite_type: str):
        self.satellite_type = satellite_type
    def set_batch_size(self, batch_size: int):
        self.batch_size = batch_size

    def set_roi(self, roi_file_path: str):
        self.roi = VectorFile(roi_file_path)

    def __str__(self):
        return (f'Sentinel2DataSourceConfigure(satellite_type={self.satellite_type},'
                f' cloud_coverage={self.cloud_coverage}, start_date={self.start_date}, end_date={self.end_date}, '
                f'batch_size={self.batch_size}, roi={self.roi})')
