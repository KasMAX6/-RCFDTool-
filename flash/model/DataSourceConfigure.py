from dataclasses import dataclass
from typing import Optional, List, Any

from flash.model.DataPathConfig import DataPathConfig
from flash.model.VectorFile import VectorFile

SATELLITE_TYPE_LIST = ['Sentinel2', 'Landsat8', 'Gaofen1', 'Gaofen2', 'Gaofen6', 'Ziyuan3', 'Ziyuan4', 'HJ1A/B']


@dataclass
class DataSourceConfigure:
    satellite_type: str = None
    start_date: str = None
    end_date: str = None
    selected_bands: Optional[List[str]] = None
    roi: VectorFile = None
    data_collection: str = None
    batch_size: Optional[int] = 10
    data_path_config: DataPathConfig = None
