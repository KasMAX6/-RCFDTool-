# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/13 21:07
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from qfluentwidgets import PushButton, LineEdit


class FilePicker(QWidget):
    # 定义两种模式
    FILE_MODE = 1
    DIRECTORY_MODE = 2

    emit_path_selected = Signal(str)

    def __init__(self, mode=FILE_MODE, parent=None):
        super().__init__(parent)
        self.mode = mode

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.line_edit = QLineEdit()
        self.button = QPushButton("浏览...")

        layout.addWidget(self.line_edit)
        layout.addWidget(self.button)

        # 根据模式设置按钮文本
        if self.mode == self.FILE_MODE:
            self.button.setText("浏览文件...")
        else:
            self.button.setText("浏览目录...")

        self.button.clicked.connect(self.open_dialog)

    def open_dialog(self):
        selected_path = ""

        if self.mode == self.FILE_MODE:
            # 选择文件
            selected_path, _ = QFileDialog.getOpenFileName(
                self, "选择文件", "", "所有文件 (*)"
            )
        elif self.mode == self.DIRECTORY_MODE:
            # 选择目录
            selected_path = QFileDialog.getExistingDirectory(
                self, "选择目录", ""
            )

        if selected_path:
            self.line_edit.setText(selected_path)
            self.emit_path_selected.emit(selected_path)

    def path(self):
        return self.line_edit.text()


# 测试用
if __name__ == "__main__":
    app = QApplication([])
    w = FilePicker()
    w.show()
    app.exec()
