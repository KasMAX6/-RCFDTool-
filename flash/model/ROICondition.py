# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 21:51
from .ROI import ROI
from .Condition import Condition


class ROICondition(Condition):
    def __init__(self, roi: ROI):
        self.roi = roi
