import os

from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt, QDate, Slot, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    ComboBox, BodyLabel, DoubleSpinBox, SpinBox, DateEdit, InfoBar,
    InfoBarPosition
)

from flash.components.widgets.FilePicker import FilePicker
from flash.components.widgets.ROIFilePicker import ROIFilePicker
from flash.model.DataSourceConfigure import SATELLITE_TYPE_LIST, DataSourceConfigure
from flash.model.Sentinel2DataSourceConfigure import Sentinel2DataSourceConfigure


class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        # self.setStyleSheet("""
        #                  QWidget {
        #                      border: 2px solid #0078d7;
        #                      border-radius: 8px;
        #                      padding: 5px;
        #                  }
        #              """)


class ConfigureDataSource(Widget):
    data_source_config_event = Signal(DataSourceConfigure)
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setup_ui()
        # 使用 QTimer 延迟触发，确保界面完全初始化后再触发


    @Slot(str)
    def on_selected_satellite_type(self, satellite):
        if satellite == 'Sentinel2':
            self.sentinel2DataSourceConfigure = Sentinel2DataSourceConfigure()
            self.sentinel2DataSourceConfigure.set_satellite_type(satellite)
            self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

            print('Sentinel2')
        else:
            InfoBar.warning(
                title='警告',
                content="目前仅支持 Sentinel2 卫星数据源，其他卫星数据源正在开发中，敬请期待！",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM,
                duration=5000,  # 3秒后自动消失
                parent=self
            )

            self.sentinel2DataSourceConfigure = Sentinel2DataSourceConfigure()
            self.sentinel2DataSourceConfigure.set_satellite_type(satellite)
            self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)


    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # 创建水平布局
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)

        # 第一组：卫星类型
        label = BodyLabel("卫星类型")
        comboBox = ComboBox(self)
        comboBox.setFixedWidth(150)
        items = SATELLITE_TYPE_LIST
        comboBox.addItems(items)

        controls_layout.addWidget(label, 1, Qt.AlignmentFlag.AlignVCenter)
        controls_layout.addWidget(comboBox, 1, Qt.AlignmentFlag.AlignTop)

        # 添加分隔符
        controls_layout.addSpacing(30)

        # 第二组：云量
        cloud_label = BodyLabel("云量")
        cloud_edit = DoubleSpinBox(self)
        cloud_edit.setRange(0, 100)
        cloud_edit.setSingleStep(0.5)
        cloud_edit.setValue(20)

        controls_layout.addWidget(cloud_label, 1, Qt.AlignmentFlag.AlignVCenter)
        controls_layout.addWidget(cloud_edit, 1, Qt.AlignmentFlag.AlignTop)

        # 添加分隔符
        controls_layout.addSpacing(30)

        # 第三组：批镶嵌大小
        pixel_size_label = BodyLabel("像素分辨率")
        spinBox = SpinBox(self)
        spinBox.setRange(128, 4096)
        spinBox.setValue(512)


        controls_layout.addWidget(pixel_size_label, 1, Qt.AlignmentFlag.AlignVCenter)

        controls_layout.addWidget(spinBox, 1, Qt.AlignmentFlag.AlignTop)

        # 水平方向：添加弹性空间，让控件左对齐
        controls_layout.addStretch()
        # 添加分隔符
        controls_layout.addSpacing(30)

        # 第四组：日期
        start_date_label = BodyLabel("影像开始日期")
        end_date_label = BodyLabel("影像结束日期")
        row2 = QHBoxLayout()
        start_dateEdit = DateEdit()

        # 设置取值范围
        start_dateEdit.setDateRange(QDate(2000, 1, 1), QDate(2024, 11, 11))
        start_dateEdit.setMaximumDate(QDate.currentDate())
        # 设置当前值
        start_dateEdit.setDate(QDate.currentDate())
        start_dateEdit.setDisplayFormat('yyyy-MM-dd')
        start_dateEdit.setDisplayFormat('yyyy-MM-dd')

        dateEdit = DateEdit()
        dateEdit.setDisplayFormat('yyyy-MM-dd')
        dateEdit.setDisplayFormat('yyyy-MM-dd')
        # 设置取值范围
        dateEdit.setDateRange(QDate(2000, 1, 1), QDate(2024, 11, 11))
        dateEdit.setMaximumDate(QDate.currentDate())
        # 设置当前值
        dateEdit.setDate(QDate.currentDate())

        # 监听数值改变信号
        row2.addWidget(start_date_label, 1, Qt.AlignmentFlag.AlignVCenter)
        row2.addWidget(start_dateEdit, 1, Qt.AlignmentFlag.AlignTop)
        row2.addWidget(end_date_label, 1, Qt.AlignmentFlag.AlignVCenter)
        row2.addWidget(dateEdit, 1, Qt.AlignmentFlag.AlignTop)
        # 水平方向：添加弹性空间，让控件左对齐
        row2.addStretch()
        row2.addSpacing(30)

        row3 = QHBoxLayout()
        roi_label = BodyLabel("感兴趣区")
        file_picker= ROIFilePicker(self)
        file_picker.setFixedWidth(300)
        row3.addWidget(roi_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row3.addWidget(file_picker, 1, Qt.AlignmentFlag.AlignTop)
        row3.addStretch()
        row3.addSpacing(30)


        roi_label = BodyLabel("GDAL 工具链路径")
        file_picker_gdal = FilePicker(FilePicker.DIRECTORY_MODE)
        file_picker_gdal.setFixedWidth(300)
        row3.addWidget(roi_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row3.addWidget(file_picker_gdal, 1, Qt.AlignmentFlag.AlignTop)
        row3.addStretch()
        row3.addSpacing(30)

        row4 = QHBoxLayout()
        # roi_label = BodyLabel("缩略图路径")
        # roi_label.setHidden(True)
        # file_picker_thumb = FilePicker(FilePicker.DIRECTORY_MODE)
        # file_picker_thumb.setFixedWidth(300)
        # file_picker_thumb.setHidden(True)
        # row4.addWidget(roi_label, 0, Qt.AlignmentFlag.AlignVCenter)
        # row4.addWidget(file_picker_thumb, 1, Qt.AlignmentFlag.AlignTop)
        # row4.addStretch()
        # row4.addSpacing(30)

        roi_label = BodyLabel("基础数据路径")
        file_picker_base = FilePicker(FilePicker.DIRECTORY_MODE)
        file_picker_base.setFixedWidth(300)
        row4.addWidget(roi_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row4.addWidget(file_picker_base, 1, Qt.AlignmentFlag.AlignTop)
        row4.addStretch()
        row4.addSpacing(30)

        #row5 = QHBoxLayout()
        roi_label = BodyLabel("影像下载保存路径")
        file_picker_download = FilePicker(FilePicker.DIRECTORY_MODE)
        file_picker_download.setFixedWidth(300)
        row4.addWidget(roi_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row4.addWidget(file_picker_download, 1, Qt.AlignmentFlag.AlignTop)
        row4.addStretch()
        row4.addSpacing(30)

        development_group = BodyLabel("开发者：曾祥权 Beijing Forestry University \n"
                                      "ajax13279@gmail.com")
        h_box_layout = QHBoxLayout()
        h_box_layout.addStretch(1)
        h_box_layout.addWidget(development_group)
        main_v_layout = QVBoxLayout()
        main_v_layout.addStretch(1)
        main_v_layout.addLayout(h_box_layout)

        # 将控件布局添加到主布局
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(row2)
        main_layout.addLayout(row3)
        main_layout.addLayout(row4)

        main_layout.addStretch(1)
        main_layout.addLayout(main_v_layout)

        # 垂直方向：添加弹性空间，让控件顶部对齐



        ### 信号通知
        dateEdit.dateChanged.connect(self.on_end_date_edited)
        start_dateEdit.dateChanged.connect(self.on_start_date_edited)
        cloud_edit.valueChanged.connect(self.cloud_edited)
        file_picker.emit_path_selected.connect(self.on_roi_file_path)

        file_picker_gdal.emit_path_selected.connect(self.on_gdal_path_edited)
        ##file_picker_thumb.emit_path_selected.connect(self.on_thumb_path_edited)
        file_picker_base.emit_path_selected.connect(self.on_base_path_edited)
        file_picker_download.emit_path_selected.connect(self.on_download_path_edited)

        comboBox.currentTextChanged.connect(self.on_selected_satellite_type)

        spinBox.valueChanged.connect(self.on_mosaic_value_change)
        QTimer.singleShot(100, lambda: self.trigger_initial_signals(
            comboBox, cloud_edit, start_dateEdit, dateEdit,spinBox
        ))

    def on_download_path_edited(self, download_path):
        self.sentinel2DataSourceConfigure.data_path_config.download_path = download_path
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_mosaic_value_change(self,b_size):
        self.sentinel2DataSourceConfigure.set_batch_size(b_size)
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_roi_file_path(self, file_path):
        self.sentinel2DataSourceConfigure.set_roi(file_path)
        self.sentinel2DataSourceConfigure.data_path_config.roi_name = os.path.basename(file_path).split('.')[0]
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_gdal_path_edited(self, gdal_path):
        self.sentinel2DataSourceConfigure.data_path_config.gdal_bin_path = gdal_path
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_thumb_path_edited(self, thumb_path):
        self.sentinel2DataSourceConfigure.data_path_config.thumb_path = thumb_path
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_base_path_edited(self, base_path):
        self.sentinel2DataSourceConfigure.data_path_config.base_path = base_path
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_start_date_edited(self, start_date):
        self.sentinel2DataSourceConfigure.set_start_date(start_date.toString("yyyy-MM-dd"))
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def on_end_date_edited(self, end_date):
        self.sentinel2DataSourceConfigure.set_end_date(end_date.toString("yyyy-MM-dd"))
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)

    def cloud_edited(self, cloud_coverage):
        self.sentinel2DataSourceConfigure.set_cloud_coverage(cloud_coverage)
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)


    def trigger_initial_signals(self, comboBox, cloud_edit, start_dateEdit, dateEdit,spinBox):
        """首次进入界面时触发所有信号"""
        # 触发卫星类型选择
        self.on_selected_satellite_type(comboBox.currentText())

        # 触发云量设置
        self.sentinel2DataSourceConfigure.set_cloud_coverage(cloud_edit.value())

        # 触发开始日期设置
        self.sentinel2DataSourceConfigure.set_start_date(start_dateEdit.date().toString("yyyy-MM-dd"))

        # 触发结束日期设置
        self.sentinel2DataSourceConfigure.set_end_date(dateEdit.date().toString("yyyy-MM-dd"))

        # 触发批镶嵌大小设置
        self.sentinel2DataSourceConfigure.set_batch_size(spinBox.value())
        self.data_source_config_event.emit(self.sentinel2DataSourceConfigure)
        print("所有初始信号已触发")
