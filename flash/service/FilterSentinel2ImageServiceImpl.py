# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/11 8:06
import ee

from .FilterSentinelImageService import FilterSentinelImageService


class FilterSentinel2ImageServiceImpl(FilterSentinelImageService):
    def __init__(self):
        pass

    def filter(self, data_src: ee.ImageCollection, condition: ee.Filter) -> ee.ImageCollection:
        filtered = data_src.filter(condition)
        return filtered
