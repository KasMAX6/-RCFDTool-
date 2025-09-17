# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/13 21:07
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from qfluentwidgets import PushButton, LineEdit
from typing_extensions import overload

from flash.components.widgets.FilePicker import FilePicker


class ROIFilePicker(FilePicker,QWidget):


    def __init__(self, parent=None):
        super().__init__(self.FILE_MODE,parent)

    def open_dialog(self):
        selected_path = ""

        if self.mode == self.FILE_MODE:
            # 选择文件
            selected_path, _ = QFileDialog.getOpenFileName(
                self, "选择文件", "", "shp文件 (*.shp)"
            )
        if selected_path:
            self.line_edit.setText(selected_path)
            self.emit_path_selected.emit(selected_path)


# 测试用
if __name__ == "__main__":
    app = QApplication([])
    w = FilePicker()
    w.show()
    app.exec()
