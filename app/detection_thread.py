import queue

from PyQt6.QtCore import QThread, pyqtSignal


class DetectionThread(QThread):
    """Asynchronous inference worker for a single RTSP stream.

    Frames are submitted via submit_frame().  When the queue is full (i.e.
    inference is slower than the stream frame rate) the incoming frame is
    silently dropped so the queue never grows unbounded.

    A shared YOLOv9Detector instance is passed in; its internal lock
    serialises GPU access across threads that share the same detector.
    """

    # Emitted after each successful inference pass.
    # Payload: (detections, original_frame_width, original_frame_height)
    detections_ready = pyqtSignal(list, int, int)

    def __init__(self, detector, parent=None):
        # Do NOT parent to a widget — avoids "destroyed while running" errors.
        super().__init__(None)
        self._detector = detector
        self._queue = queue.Queue(maxsize=1)
        self._running = False

    def submit_frame(self, frame, w, h):
        """Submit a frame for detection.  Non-blocking; drops frame if busy."""
        try:
            self._queue.put_nowait((frame.copy(), w, h))
        except queue.Full:
            pass

    def run(self):
        self._running = True
        while self._running:
            try:
                frame, w, h = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            detections = self._detector.detect(frame)
            self.detections_ready.emit(detections, w, h)

    def stop(self):
        """Signal the thread to stop and wait for it to finish."""
        self._running = False
        self.wait(5000)
