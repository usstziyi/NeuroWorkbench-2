from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QPushButton,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

import serial.tools.list_ports
from pyqtgraph.parametertree import Parameter, ParameterTree


class SettingWidget(QWidget):
    acquisition_started = Signal()
    acquisition_stopped = Signal()
    recording_started = Signal()
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        children = [
            {
                "name": "设备选择",
                "type": "group",
                "children": [
                    {
                        "name": "设备名称",
                        "type": "list",
                        "values": ["Simulated", "OpenBCI Cyton", "OpenBCI Cyton+Desin"],
                        "value": "Simulated",
                    },
                    {
                        "name": "串口",
                        "type": "list",
                        "values": [],
                        "value": "",
                    },
                ],
            },
            {
                "name": "采样设置",
                "type": "group",
                "children": [
                    {"name": "采样率 (Hz)", "type": "list", "values": [125, 250], "value": 250},
                    {"name": "通道数", "type": "int", "value": 8, "limits": [0, 16]},
                ],
            },
            {
                "name": "滤波设置",
                "type": "group",
                "children": [
                    {"name": "陷波滤波器", "type": "bool", "value": True},
                    {"name": "陷波频率 (Hz)", "type": "list", "values": [50, 60], "value": 50},
                    {"name": "高通滤波器", "type": "bool", "value": True},
                    {"name": "高通截止 (Hz)", "type": "float", "value": 0.5, "limits": [0.1, 10]},
                    {"name": "低通滤波器", "type": "bool", "value": True},
                    {"name": "低通截止 (Hz)", "type": "float", "value": 45, "limits": [10, 200]},
                ],
            },
            {
                "name": "显示设置",
                "type": "group",
                "children": [
                    {
                        "name": "UI 主题",
                        "type": "list",
                        "values": QStyleFactory.keys(),
                        "value": "Fusion" if "Fusion" in QStyleFactory.keys() else QStyleFactory.keys()[0],
                    },
                    {"name": "时间窗口 (s)", "type": "float", "value": 5, "limits": [1, 30]},
                    {"name": "Y轴范围 (μV)", "type": "float", "value": 200, "limits": [10, 1000], "step": 10},
                ],
            },
        ]

        param_tree = ParameterTree(showHeader=False)
        self.params = Parameter.create(name="params", type="group", children=children)
        param_tree.setParameters(self.params, showTop=False)
        layout.addWidget(param_tree, 1)

        btn_group = QGroupBox("采集控制")
        btn_layout = QVBoxLayout(btn_group)
        self.btn_scan = QPushButton("扫描串口")
        self.btn_start = QPushButton("开始采集")
        self.btn_stop = QPushButton("停止采集")
        self.btn_record = QPushButton("开始记录")
        self.btn_stop.setEnabled(False)
        self.btn_record.setEnabled(False)
        btn_layout.addWidget(self.btn_scan)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_record)
        layout.addWidget(btn_group, 0)

    def _connect_signals(self):
        self.btn_scan.clicked.connect(self._scan_ports)
        self.btn_start.clicked.connect(self.acquisition_started.emit)
        self.btn_stop.clicked.connect(self.acquisition_stopped.emit)
        self.btn_record.clicked.connect(self.recording_started.emit)
        self.params.child("显示设置", "UI 主题").sigValueChanged.connect(
            lambda _, v: self.theme_changed.emit(v)
        )

    def _scan_ports(self):
        ports = serial.tools.list_ports.comports()
        port_names = [p.device for p in sorted(ports)]
        port_param = self.params.child("设备选择", "串口")
        current_value = port_param.value()
        if port_names:
            port_param.setLimits(port_names)
            if current_value not in port_names:
                port_param.setValue(port_names[0])
        else:
            port_param.setLimits([])
            port_param.setValue("")
