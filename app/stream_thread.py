import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class StreamThread(QThread):
    """Worker thread that captures frames from an RTSP stream."""

    frame_received = pyqtSignal(np.ndarray)
    status_changed = pyqtSignal(str)  # "connecting", "connected", "disconnected", "error"
    error_occurred = pyqtSignal(str)

    # Short timeout (in microseconds) so cap.open/read don't block for 30s
    _OPEN_TIMEOUT_US = 5_000_000   # 5 seconds
    _READ_TIMEOUT_US = 5_000_000   # 5 seconds

    def __init__(self, url, name="Stream", parent=None):
        # Do NOT parent to a widget — prevents "destroyed while running" when
        # the parent widget is deleted before the thread finishes.
        super().__init__(None)
        self.url = url
        self.name = name
        self._running = False
        self._reconnect_delay = 2  # seconds

    def run(self):
        self._running = True

        while self._running:
            self.status_changed.emit("connecting")

            cap = cv2.VideoCapture(
                self.url,
                cv2.CAP_FFMPEG,
                [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self._OPEN_TIMEOUT_US // 1000,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC, self._READ_TIMEOUT_US // 1000,
                    cv2.CAP_PROP_BUFFERSIZE, 1,
                ],
            )

            if not cap.isOpened():
                self.status_changed.emit("error")
                self.error_occurred.emit(f"Cannot connect to {self.name}")
                if self._running:
                    self._wait_reconnect()
                    continue
                break

            self.status_changed.emit("connected")

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    self.status_changed.emit("disconnected")
                    self.error_occurred.emit(f"Lost connection to {self.name}")
                    break
                self.frame_received.emit(frame)

            cap.release()

            if self._running:
                self._wait_reconnect()

        self.status_changed.emit("disconnected")

    def _wait_reconnect(self):
        """Wait before attempting reconnection."""
        delay = self._reconnect_delay
        end_time = time.time() + delay
        while self._running and time.time() < end_time:
            time.sleep(0.1)

    def stop(self):
        """Signal the thread to stop and wait for it to finish."""
        self._running = False
        # Wait long enough for the OpenCV timeout + some margin
        if not self.wait(8000):
            # Thread still running — force terminate as last resort
            self.terminate()
            self.wait(2000)
