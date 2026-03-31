import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PyQt6.QtGui import QImage, QPixmap, QAction, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal

from app.stream_thread import StreamThread
from app.recorder import VideoRecorder


class StreamWidget(QWidget):
    """Widget that displays a single RTSP video stream with recording support."""

    recording_started = pyqtSignal(str)  # stream name
    recording_stopped = pyqtSignal(str, str)  # stream name, filepath
    double_clicked = pyqtSignal(object)  # self

    def __init__(self, stream_config, recording_dir="./recordings", parent=None):
        super().__init__(parent)
        self.stream_config = stream_config
        self.name = stream_config.get("name", "Unknown")
        self.url = stream_config.get("url", "")
        self.enabled = stream_config.get("enabled", True)

        self._status = "idle"
        self._last_frame = None
        self._thread = None
        self._recorder = VideoRecorder(recording_dir)
        self._frame_size = None
        self._fps = 20.0

        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumSize(160, 120)
        self.setStyleSheet("background-color: #1a1a2e; border: 1px solid #333;")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("border: none;")
        layout.addWidget(self.video_label)

        self._update_placeholder()

    def _update_placeholder(self):
        """Show status text when no video is playing."""
        status_text = {
            "idle": f"{self.name}\nReady",
            "connecting": f"{self.name}\nConnecting...",
            "connected": f"{self.name}\nConnected",
            "disconnected": f"{self.name}\nDisconnected\nReconnecting...",
            "error": f"{self.name}\nConnection Error\nRetrying...",
            "disabled": f"{self.name}\nDisabled",
        }
        text = status_text.get(self._status, self.name)
        self.video_label.setText(text)
        self.video_label.setStyleSheet(
            "border: none; color: #aaaaaa; font-size: 14px; padding: 10px;"
        )

    def start(self):
        """Start receiving the RTSP stream."""
        if not self.enabled:
            self._status = "disabled"
            self._update_placeholder()
            return

        if self._thread is not None:
            self.stop()

        self._thread = StreamThread(self.url, self.name, parent=self)
        self._thread.frame_received.connect(self._on_frame)
        self._thread.status_changed.connect(self._on_status_changed)
        self._thread.start()

    def stop(self):
        """Stop the stream and any active recording."""
        if self._recorder.is_recording:
            self.stop_recording()

        if self._thread is not None:
            self._thread.stop()
            self._thread = None

        self._last_frame = None
        self._status = "idle"
        self._update_placeholder()

    def _on_frame(self, frame):
        """Handle a new frame from the stream thread."""
        self._last_frame = frame
        h, w = frame.shape[:2]
        self._frame_size = (w, h)

        # Estimate FPS from capture if possible
        if self._thread and hasattr(self._thread, "_cap_fps"):
            self._fps = self._thread._cap_fps or 20.0

        # Record frame if recording
        if self._recorder.is_recording:
            self._recorder.write_frame(frame)

        # Convert BGR to RGB for display
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Scale to widget size while maintaining aspect ratio
        label_size = self.video_label.size()
        pixmap = QPixmap.fromImage(q_img).scaled(
            label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        # Draw overlays
        self._draw_overlays(pixmap)
        self.video_label.setPixmap(pixmap)

    def _draw_overlays(self, pixmap):
        """Draw stream name and recording indicator on the video frame."""
        painter = QPainter(pixmap)

        # Stream name background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawRect(0, 0, pixmap.width(), 25)

        # Stream name text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.drawText(5, 17, self.name)

        # Recording indicator
        if self._recorder.is_recording:
            painter.setBrush(QColor(255, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(pixmap.width() - 20, 7, 12, 12)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(pixmap.width() - 60, 17, "REC")

        painter.end()

    def _on_status_changed(self, status):
        self._status = status
        if status != "connected":
            self._update_placeholder()

    def start_recording(self):
        """Start recording the current stream to an MP4 file."""
        if self._frame_size is None:
            return False
        success = self._recorder.start(self.name, self._fps, self._frame_size)
        if success:
            self.recording_started.emit(self.name)
        return success

    def stop_recording(self):
        """Stop recording and return the file path."""
        filepath = self._recorder.stop()
        if filepath:
            self.recording_stopped.emit(self.name, filepath)
        return filepath

    def is_recording(self):
        return self._recorder.is_recording

    def take_snapshot(self, output_dir="./snapshots"):
        """Save the current frame as a JPEG image."""
        if self._last_frame is None:
            return None
        import os
        import time

        os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in self.name)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"{safe_name}_{timestamp}.jpg")
        cv2.imwrite(filepath, self._last_frame)
        return filepath

    def _show_context_menu(self, pos):
        menu = QMenu(self)

        if self._recorder.is_recording:
            stop_rec = QAction("Stop Recording", self)
            stop_rec.triggered.connect(self.stop_recording)
            menu.addAction(stop_rec)
        else:
            start_rec = QAction("Start Recording", self)
            start_rec.triggered.connect(self.start_recording)
            menu.addAction(start_rec)

        snapshot = QAction("Take Snapshot", self)
        snapshot.triggered.connect(lambda: self.take_snapshot())
        menu.addAction(snapshot)

        menu.addSeparator()

        fullscreen = QAction("Toggle Fullscreen", self)
        fullscreen.triggered.connect(lambda: self.double_clicked.emit(self))
        menu.addAction(fullscreen)

        menu.exec(self.mapToGlobal(pos))

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self)

    def update_config(self, stream_config):
        """Update the stream configuration. Restarts if URL changed."""
        old_url = self.url
        self.stream_config = stream_config
        self.name = stream_config.get("name", "Unknown")
        self.url = stream_config.get("url", "")
        self.enabled = stream_config.get("enabled", True)

        if self.url != old_url:
            self.stop()
            self.start()
        elif not self.enabled:
            self.stop()
            self._status = "disabled"
            self._update_placeholder()

    def set_recording_dir(self, directory):
        self._recorder.output_dir = directory
