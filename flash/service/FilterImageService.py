# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/11 8:03
import abc
import geemap
import ee

from ..model.Condition import Condition


class FilterImageService(abc.ABC):

    @abc.abstractmethod
    def filter(self,data_src:ee.ImageCollection, condition:ee.Filter)->ee.ImageCollection:
        pass

