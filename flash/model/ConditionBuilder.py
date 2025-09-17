# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 21:47
from .Condition import Condition

import ee


class ConditionBuilder:
    def __init__(self):
        self.conditions = []
        self.temp_filter = None

    def add(self, field, op, value):
        """添加一个条件"""
        self.conditions.append(Condition(field, op, value))
        return self

    def and_(self):
        """构造 AND 过滤器"""
        self.temp_filter = ee.Filter.And([c.filter for c in self.conditions])
        return self

    def or_(self):
        """构造 OR 过滤器"""
        self.temp_filter = ee.Filter.Or([c.filter for c in self.conditions])
        return self



    def build(self):
        """返回组合后的 ee.Filter"""
        if self.temp_filter is None:
            if len(self.conditions) == 1:
                return self.conditions[0].filter
            raise ValueError("请先调用 and_() 或 or_() 来组合条件")
        return self.temp_filter
