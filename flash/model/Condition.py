# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 21:47
import abc
import ee

import ee


class Condition:
    def __init__(self, field, op, value):
        """
        单个条件封装
        field:   字段名 (str)
        op:      操作符 (str, 例如 "eq", "lt", "gt", "lte", "gte")
        value:   值
        """
        self.field = field
        self.op = op
        self.value = value
        self.filter = self._build_filter()

    def _build_filter(self):
        # 根据 op 构造对应的 ee.Filter
        ops = {
            "eq": ee.Filter.eq,
            "lt": ee.Filter.lt,
            "gt": ee.Filter.gt,
            "lte": ee.Filter.lte,
            "gte": ee.Filter.gte,
            "neq": ee.Filter.neq,
            "in": ee.Filter.inList,
            "bounds": ee.Filter.bounds,
            "not_in": lambda f, v: ee.Filter.Not(ee.Filter.inList(f, v)),
        }
        if self.op not in ops:
            raise ValueError(f"Unsupported operator: {self.op}")

        if self.op == "bounds":
            # bounds 操作符不需要 field 参数
            return ops[self.op](self.value)
        return ops[self.op](self.field, self.value)
