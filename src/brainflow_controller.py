import time
from threading import Event, Thread

import numpy as np
from brainflow import BoardIds, BoardShim, BrainFlowInputParams
from PySide6.QtCore import QObject, Signal

_DEVICE_MAP = {
    "Simulated": BoardIds.SYNTHETIC_BOARD,
    "OpenBCI Cyton": BoardIds.CYTON_BOARD,
    "OpenBCI Cyton+Desin": BoardIds.CYTON_DAISY_BOARD,
}


class BrainFlowController(QObject):
    data_ready = Signal(np.ndarray)
    board_connected = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._board = None
        self._board_id = -1
        self._sampling_rate = 0
        self._channel_count = 0
        self._running = False
        self._stop_event = Event()
        self._thread = None

    @property
    def is_connected(self):
        return self._board is not None and self._board.is_prepared()

    @property
    def sampling_rate(self):
        return self._sampling_rate

    @property
    def channel_count(self):
        return self._channel_count

    @staticmethod
    def device_names():
        return list(_DEVICE_MAP.keys())

    def connect(self, device_name, serial_port=""):
        if device_name not in _DEVICE_MAP:
            self.error_occurred.emit(f"Unknown device: {device_name}")
            return False

        self._board_id = _DEVICE_MAP[device_name]

        try:
            params = BrainFlowInputParams()
            if serial_port:
                params.serial_port = serial_port

            self._board = BoardShim(self._board_id, params)
            self._board.prepare_session()

            self._sampling_rate = BoardShim.get_sampling_rate(self._board_id)
            exg_channels = BoardShim.get_exg_channels(self._board_id)
            self._channel_count = len(exg_channels)

            self.board_connected.emit(True)
            return True
        except Exception as e:
            self._board = None
            self.error_occurred.emit(str(e))
            return False

    def disconnect(self):
        if self._running:
            self.stop_stream()

        if self._board is not None:
            try:
                if self._board.is_prepared():
                    self._board.release_session()
            except Exception as e:
                self.error_occurred.emit(str(e))
            finally:
                self._board = None

        self.board_connected.emit(False)

    def start_stream(self, ring_buffer_size=450000):
        if not self.is_connected:
            self.error_occurred.emit("Board not connected")
            return False

        try:
            self._board.start_stream(ring_buffer_size)
            self._running = True
            self._stop_event.clear()
            self._thread = Thread(target=self._polling_loop, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def stop_stream(self):
        self._running = False
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._board is not None and self._board.is_prepared():
            try:
                self._board.stop_stream()
            except Exception as e:
                self.error_occurred.emit(str(e))

    def _polling_loop(self):
        sampling_period = 1.0 / self._sampling_rate if self._sampling_rate > 0 else 0.001

        while self._running and not self._stop_event.is_set():
            try:
                data = self._board.get_board_data()
                if data.shape[1] > 0:
                    exg_channels = BoardShim.get_exg_channels(self._board_id)
                    exg_data = data[exg_channels, :]
                    if exg_data.shape[1] > 0:
                        self.data_ready.emit(exg_data)
            except Exception as e:
                self.error_occurred.emit(str(e))

            time.sleep(sampling_period)
