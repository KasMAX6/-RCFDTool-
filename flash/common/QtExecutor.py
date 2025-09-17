# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/12 19:42
from typing import Callable, Optional
from PySide6.QtCore import QThread, Signal

from flash.common.TaskThread import TaskThread


class QtExecutor:
    def __init__(self):
        self.worker = None

    def run(self, func: Callable, *args,
            on_done: Optional[Callable] = None,
            on_error: Optional[Callable] = None, **kwargs):
        if self.worker:
            self.worker.quit()
            self.worker.wait()

        self.worker = TaskThread(func, *args, **kwargs)
        if on_done:
            self.worker.finished.connect(on_done)
        if on_error:
            self.worker.error.connect(on_error)
        self.worker.start()