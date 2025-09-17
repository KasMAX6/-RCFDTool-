# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/11 20:02
from flash.model.Sentinel2Image import Sentinel2Image


class CloudCheck:

    def __init__(self, image: Sentinel2Image):
        self.image = image
    def check(self):
        cloud_coverage = self.image.get_cloud_coverage()
        return cloud_coverage

    def is_low_cloud(self, threshold=0.00001):
        cloud_coverage = self.check()
        return cloud_coverage < threshold