import threading

from ultralytics import YOLO


class YOLOv9Detector:
    """Wraps a YOLOv9 (Ultralytics) model with thread-safe inference.

    A single instance is shared across all stream detection threads.
    The internal lock ensures only one inference call runs at a time,
    which keeps GPU memory usage predictable regardless of stream count.
    """

    def __init__(self, model_path="yolov9c.pt", conf_threshold=0.25, device=None):
        """Load the YOLOv9 model.

        Args:
            model_path: Path to a .pt or .onnx model file.  If a bare filename
                        like "yolov9c.pt" is given, Ultralytics will download it
                        automatically on first use.
            conf_threshold: Minimum confidence score for reported detections.
            device: Inference device string — "cpu", "cuda", "cuda:0", "mps", or
                    None to let Ultralytics auto-select.
        """
        self.conf_threshold = conf_threshold
        self.device = device
        self._lock = threading.Lock()
        self._model = YOLO(model_path)

    def detect(self, frame):
        """Run inference on a BGR numpy frame (thread-safe).

        Returns:
            List of tuples: (x1, y1, x2, y2, conf, class_name)
            Coordinates are in the original frame's pixel space.
        """
        with self._lock:
            results = self._model(
                frame,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )

        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detections.append((x1, y1, x2, y2, conf, r.names[cls]))
        return detections
