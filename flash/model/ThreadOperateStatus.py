# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/15 9:33


class ThreadOperateStatus:
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.is_stopped = True

    def start_new_task(self):
        """开始新任务"""
        self.is_running = True
        self.is_paused = False
        self.is_stopped = False

    def resume_task(self):
        """恢复暂停的任务"""
        if self.is_paused:
            self.is_running = True
            self.is_paused = False
            # is_stopped 保持 False

    def pause_task(self):
        """暂停任务"""
        if self.is_running:
            self.is_running = False
            self.is_paused = True
            # is_stopped 保持 False

    def stop_task(self):
        """停止任务"""
        self.is_running = False
        self.is_paused = False
        self.is_stopped = True

    def get_status_text(self):
        """获取状态描述"""
        if self.is_running:
            return "运行中"
        elif self.is_paused:
            return "已暂停"
        elif self.is_stopped:
            return "已停止"
        else:
            return "未知状态"

