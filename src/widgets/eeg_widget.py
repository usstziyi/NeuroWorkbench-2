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
        self._buffer_size = 5000
        self._ring_buffers = {}

        for i in range(n_channels):
            color = CET_R3_DEFAULT[i % len(CET_R3)]
            plot = self.addPlot(row=i, col=0)
            plot.setLabel("left", f"CH{i + 1}", color=color)
            plot.getAxis("left").setWidth(40)
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

            self._plots[i] = plot

        self._write_pos = 0
        self._total_samples = 0

    @property
    def channel_count(self):
        return self._n_channels

    def channel_plot(self, index):
        if index < 0 or index >= self._n_channels:
            raise IndexError(f"channel index {index} out of range (0-{self._n_channels - 1})")
        return self._plots[index]

    def channel_color(self, index):
        if index < 0 or index >= self._n_channels:
            raise IndexError(f"channel index {index} out of range (0-{self._n_channels - 1})")
        return CET_R3_DEFAULT[index % len(CET_R3)]

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

    def __getitem__(self, index):
        return self.channel_plot(index)

    def __len__(self):
        return self._n_channels

    def __iter__(self):
        for i in range(self._n_channels):
            yield self._plots[i]

    def plots(self):
        return iter(self)
