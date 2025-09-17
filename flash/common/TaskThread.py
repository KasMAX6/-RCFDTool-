# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/12 19:43
from PySide6.QtCore import QRunnable, QObject, Signal, QThread


class TaskThread(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))