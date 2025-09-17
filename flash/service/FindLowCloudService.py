# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/11 9:36
import abc
from typing import List

from PySide6.QtCore import QObject

from flash.model.RemoteSensingImage import RemoteSensingImage


class FindLowCloud(QObject):
    def __init__(self, remote_sensing_image: List[RemoteSensingImage]):
        super().__init__()
        self.remote_sensing_image = remote_sensing_image

        pass

    def filter(self, image: RemoteSensingImage):
        pass

    def find(self):
        pass

    def sort_images(self):
        pass
