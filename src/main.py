import json
import sys

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from brainflow_controller import BrainFlowController
from widgets.fft_widget import FftWidget
from widgets.setting_widget import SettingWidget
from widgets.eeg_widget import EegWidget
_PARAMS_VERSION = 3


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroWorkbench - EEG Analysis Platform")
        self.resize(1400, 900)

        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)

        self._controller = BrainFlowController()

        self._init_docks()
        self._connect_param_signals()
        self._setup_menubar()
        self._setup_statusbar()
        self._connect_controller_signals()
        self._restore_settings()

    def _init_docks(self):
        # 左下角区域归属给左侧 dock
        # self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)

        self.left_dock = QDockWidget("控制面板")
        self.left_dock.setObjectName("left_dock")
        self.left_dock.setTitleBarWidget(QWidget())
        self.left_dock.setMinimumWidth(220)
        self.left_dock.setMaximumWidth(300)
        left_widget = self._setup_left_panel()
        self.left_dock.setWidget(left_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        center_widget = self._setup_center_panel()
        self.setCentralWidget(center_widget)

        self.right_dock = QDockWidget("右侧面板")
        self.right_dock.setObjectName("right_dock")
        self.right_dock.setTitleBarWidget(QWidget())
        right_widget = self._setup_right_panel()
        self.right_dock.setWidget(right_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)
        self.right_dock.hide()

        self.bottom_dock = QDockWidget("底部面板")
        self.bottom_dock.setObjectName("bottom_dock")
        self.bottom_dock.setTitleBarWidget(QWidget())
        bottom_widget = self._setup_bottom_panel()
        self.bottom_dock.setWidget(bottom_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottom_dock)
        self.bottom_dock.hide()

    def _setup_menubar(self):
        menubar = self.menuBar()

        view_menu = menubar.addMenu("视图(&V)")

        view_menu.addAction(self.left_dock.toggleViewAction())
        view_menu.addAction(self.right_dock.toggleViewAction())
        view_menu.addAction(self.bottom_dock.toggleViewAction())


    def _setup_left_panel(self):
        widget = SettingWidget()
        self.params = widget.params
        widget.acquisition_started.connect(self._on_acquisition_started)
        widget.acquisition_stopped.connect(self._on_acquisition_stopped)
        widget.recording_started.connect(self._on_recording_started)
        widget.theme_changed.connect(self._on_theme_changed)
        return widget

    def _setup_center_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.tab_widget = QTabWidget()
        self.eeg_widget = EegWidget()
        self.fft_widget = FftWidget()

        self.tab_widget.addTab(self.eeg_widget, "EEG 时序图")
        self.tab_widget.addTab(self.fft_widget, "FFT 频谱图")

        layout.addWidget(self.tab_widget)
        return widget

    def _setup_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        label = QLabel("右侧面板 — 待设计")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return widget

    def _setup_bottom_panel(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        label = QLabel("底部面板 — 待设计")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return widget

    def _setup_statusbar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._status_light = QLabel()
        self._status_light.setFixedSize(12, 12)
        self._set_light_color("#808080")

        self._status_text = QLabel("未采集")

        self._recording_duration = QLabel("00:00:00")

        status_bar.addWidget(self._status_light)
        status_bar.addWidget(self._status_text)
        status_bar.addPermanentWidget(self._recording_duration)

        self._recording_seconds = 0
        self._recording_timer = QTimer()
        self._recording_timer.timeout.connect(self._on_recording_tick)

        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._on_blink_tick)
        self._blink_on = False

    def _set_light_color(self, color):
        self._status_light.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;"
        )

    def _on_acquisition_started(self):
        device_name = self.params.child("设备选择", "设备类型").value()
        serial_port = self.params.child("设备选择", "串口").value()
        self._controller.connect(device_name, serial_port=serial_port)
        self._controller.start_stream()
        self._set_light_color("#00c853")
        self._status_text.setText("采集中")

    def _on_acquisition_stopped(self):
        self._controller.disconnect()
        self._blink_timer.stop()
        self._recording_timer.stop()
        self._recording_seconds = 0
        self._recording_duration.setText("00:00:00")
        self._set_light_color("#808080")
        self._status_text.setText("未采集")

    def _on_recording_started(self):
        if not self._controller.is_connected:
            return
        if self._recording_timer.isActive():
            self._recording_timer.stop()
            self._blink_timer.stop()
            self._recording_seconds = 0
            self._recording_duration.setText("00:00:00")
            self._set_light_color("#00c853")
            self._status_text.setText("采集中")
            self.left_dock.widget().btn_record.setText("开始记录")
        else:
            self._recording_timer.start(1000)
            self._blink_timer.start(500)
            self._blink_on = True
            self._set_light_color("#ff1744")
            self._status_text.setText("录制中")
            self.left_dock.widget().btn_record.setText("停止记录")

    def _on_recording_tick(self):
        self._recording_seconds += 1
        h = self._recording_seconds // 3600
        m = (self._recording_seconds % 3600) // 60
        s = self._recording_seconds % 60
        self._recording_duration.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _on_blink_tick(self):
        if self._blink_on:
            self._set_light_color("#ff1744")
        else:
            self._set_light_color("#4a0000")
        self._blink_on = not self._blink_on

    def _connect_param_signals(self):
        y_range_param = self.params.child("显示设置", "Y轴范围 (μV)")
        y_range_param.sigValueChanged.connect(self._on_y_range_changed)
        self._on_y_range_changed(y_range_param, y_range_param.value())

    def _on_y_range_changed(self, param, value):
        self.eeg_widget.set_y_range(value)

    def _connect_controller_signals(self):
        self._controller.data_ready.connect(self._on_data_ready)
        self._controller.board_connected.connect(self._on_board_connected)
        self._controller.error_occurred.connect(self._on_controller_error)

    def _on_data_ready(self, data):
        self.eeg_widget.update_data(data)

    def _on_board_connected(self, connected):
        self.left_dock.widget().btn_start.setEnabled(not connected)
        self.left_dock.widget().btn_stop.setEnabled(connected)
        self.left_dock.widget().btn_record.setEnabled(connected)

    def _on_controller_error(self, message):
        print(f"[BrainFlow Error] {message}")

    def _on_theme_changed(self, value):
        QApplication.instance().setStyle(value)
        QApplication.instance().setProperty("theme_name", value)

    def _settings(self):
        return QSettings("NeuroWorkbench", "NeuroWorkbench")

    def _restore_settings(self):
        s = self._settings()
        geometry = s.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = s.value("window/state")
        if state:
            self.restoreState(state)

        param_state = s.value("params/state")
        params_version = s.value("params/version", 0, type=int)
        if param_state is not None and params_version == _PARAMS_VERSION:
            self.params.restoreState(json.loads(param_state))

        theme = self.params.child("显示设置", "UI 主题").value()
        QApplication.instance().setStyle(theme)
        QApplication.instance().setProperty("theme_name", theme)

    def _save_settings(self):
        s = self._settings()
        s.setValue("window/geometry", self.saveGeometry())
        s.setValue("window/state", self.saveState())
        s.setValue("params/state", json.dumps(self.params.saveState()))
        s.setValue("params/version", _PARAMS_VERSION)

    def closeEvent(self, event):
        self._recording_timer.stop()
        self._blink_timer.stop()
        self._controller.disconnect()
        self._save_settings()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NeuroWorkbench")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
