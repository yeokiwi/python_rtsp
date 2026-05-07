import os
import threading
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class StreamWorker(QObject):
    """Worker that captures frames from an RTSP stream.

    Runs on a thread owned by a shared ThreadPoolExecutor; emits Qt signals
    that are delivered to GUI-thread receivers via queued connections.
    """

    frame_received = pyqtSignal(np.ndarray)
    status_changed = pyqtSignal(str)  # "connecting", "connected", "disconnected", "error"
    error_occurred = pyqtSignal(str)

    def __init__(self, url, name="Stream", parent=None):
        super().__init__(parent)
        self.url = url
        self.name = name
        self._running = False
        self._stop_event = threading.Event()
        self._reconnect_delay = 2  # seconds
        self._cap_fps = 0.0

    def _open_capture(self):
        """Open a VideoCapture with RTSP-over-TCP and short timeouts."""
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|stimeout;5000000"
        )

        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def run(self):
        """Run the capture loop. Submitted to the shared thread pool."""
        self._running = True
        self._stop_event.clear()

        while self._running:
            self.status_changed.emit("connecting")

            cap = self._open_capture()

            if not cap.isOpened():
                self.status_changed.emit("error")
                self.error_occurred.emit(f"Cannot connect to {self.name}")
                if self._running and not self._stop_event.is_set():
                    self._wait_reconnect()
                    continue
                break

            try:
                self._cap_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            except Exception:
                self._cap_fps = 0.0

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
        """Wait before attempting reconnection (interruptible by stop)."""
        self._stop_event.wait(self._reconnect_delay)

    def stop(self):
        """Signal the worker to exit. Non-blocking; the future tracks completion."""
        self._running = False
        self._stop_event.set()
