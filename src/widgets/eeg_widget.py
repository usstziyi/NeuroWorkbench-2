import pyqtgraph as pg
import numpy as np


CET_R3 = [
    (214, 68, 60),
    (239, 143, 44),
    (200, 202, 52),
    (65, 183, 130),
    (50, 138, 190),
    (80, 82, 185),
    (139, 61, 159),
    (197, 50, 120),
]

CET_R3_DEFAULT = CET_R3 * 4


class EegWidget(pg.GraphicsLayoutWidget):
    def __init__(self, n_channels=8, parent=None):
        super().__init__(parent)
        self.setBackground("k")
        self._plots = {}
        self._curves = {}
        self._n_channels = n_channels
        self._sampling_rate = 250
        self._time_window = 5.0
        self._buffer_size = int(self._sampling_rate * self._time_window)
        self._ring_buffers = {}

        for i in range(n_channels):
            color = CET_R3_DEFAULT[i % len(CET_R3)]
            plot = self.addPlot(row=i, col=0)
            plot.setLabel("left", f"CH{i + 1}(μV)")
            plot.getAxis("left").setWidth(60)
            plot.getAxis("left").autoSIPrefix = False
            plot.setDownsampling(auto=True, mode="peak")
            plot.setClipToView(True)
            plot.addLine(y=0, pen=pg.mkPen((255, 255, 255, 60), width=1, style=pg.QtCore.Qt.PenStyle.DashLine))

            curve = plot.plot(pen=pg.mkPen(color, width=1))
            self._curves[i] = curve
            self._ring_buffers[i] = np.zeros(self._buffer_size, dtype=np.float64)

            if i == 0:
                self._first_plot = plot
            else:
                plot.setXLink(self._first_plot)

            if i < n_channels - 1:
                plot.hideAxis("bottom")
            else:
                plot.setLabel("bottom", "时长(s)")
                plot.getAxis("bottom").autoSIPrefix = False

            self._plots[i] = plot

        # 环形缓冲区当前写入位置
        self._write_pos = 0
        # 已接收的总样本数（用于判断缓冲区是否已填满）
        self._total_samples = 0

    def set_y_range(self, value):
        for plot in self._plots.values():
            plot.setYRange(-value, value)

    def set_time_window(self, value):
        self._time_window = value
        self._resize_buffers()

    def set_sampling_rate(self, value):
        self._sampling_rate = value
        self._resize_buffers()

    def _resize_buffers(self):
        new_size = int(self._sampling_rate * self._time_window)
        if new_size == self._buffer_size:
            return

        old_size = self._buffer_size
        self._buffer_size = new_size

        total = min(self._total_samples, old_size)
        keep = min(total, new_size)

        for ch in self._ring_buffers:
            old = self._ring_buffers[ch]
            if total == 0:
                self._ring_buffers[ch] = np.zeros(new_size, dtype=np.float64)
                continue

            if total <= old_size:
                y = old[:total]
            else:
                start = self._write_pos
                y = np.concatenate([old[start:], old[:start]])

            latest = y[-keep:]
            buf = np.zeros(new_size, dtype=np.float64)
            buf[:keep] = latest
            self._ring_buffers[ch] = buf

        self._write_pos = keep

    @property
    def channel_count(self):
        return self._n_channels

    def update_data(self, data: np.ndarray):
        n_ch, n_samples = data.shape
        ch_count = min(n_ch, self._n_channels)

        for i in range(ch_count):
            buf = self._ring_buffers[i]
            for j in range(n_samples):
                buf[self._write_pos] = data[i, j]
                self._write_pos = (self._write_pos + 1) % self._buffer_size
                self._total_samples += 1

        visible = min(self._total_samples, self._buffer_size)
        x = np.arange(visible)

        for i in range(ch_count):
            buf = self._ring_buffers[i]
            if self._total_samples <= self._buffer_size:
                y = buf[:self._total_samples]
            else:
                start = self._write_pos
                y = np.concatenate([buf[start:], buf[:start]])

            if len(y) > 0:
                self._curves[i].setData(x[-len(y):], y)
