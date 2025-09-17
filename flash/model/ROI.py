# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 21:53
from flash.model.VectorFile import VectorFile


class ROI:
    def __init__(self, vector_file:VectorFile):
        self.roi = vector_file
