import os
import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class StreamThread(QThread):
    """Worker thread that captures frames from an RTSP stream."""

    frame_received = pyqtSignal(np.ndarray)
    status_changed = pyqtSignal(str)  # "connecting", "connected", "disconnected", "error"
    error_occurred = pyqtSignal(str)

    def __init__(self, url, name="Stream", parent=None):
        # Do NOT parent to a widget — prevents "destroyed while running" when
        # the parent widget is deleted before the thread finishes.
        super().__init__(None)
        self.url = url
        self.name = name
        self._running = False
        self._reconnect_delay = 2  # seconds

    def _open_capture(self):
        """Open a VideoCapture with RTSP-over-TCP and short timeouts."""
        # Force RTSP over TCP and set short timeouts via FFmpeg options
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|stimeout;5000000"
        )

        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def run(self):
        self._running = True

        while self._running:
            self.status_changed.emit("connecting")

            cap = self._open_capture()

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
        # Wait long enough for the FFmpeg stimeout (5s) + margin
        if not self.wait(8000):
            self.terminate()
            self.wait(2000)
