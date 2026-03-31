import os
import time
import cv2


class VideoRecorder:
    """Records video frames to an MP4 file using OpenCV VideoWriter."""

    def __init__(self, output_dir="./recordings"):
        self.output_dir = output_dir
        self.writer = None
        self.filepath = None
        self.is_recording = False
        self.frame_count = 0

    def start(self, stream_name, fps=20.0, frame_size=(640, 480)):
        """Start recording to a new MP4 file."""
        if self.is_recording:
            return False

        os.makedirs(self.output_dir, exist_ok=True)

        # Generate filename with timestamp
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in stream_name)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.mp4"
        self.filepath = os.path.join(self.output_dir, filename)

        # Try H264 first, fall back to mp4v
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(self.filepath, fourcc, fps, frame_size)

        if not self.writer.isOpened():
            self.writer = None
            self.filepath = None
            return False

        self.is_recording = True
        self.frame_count = 0
        return True

    def write_frame(self, frame):
        """Write a single frame to the video file."""
        if not self.is_recording or self.writer is None:
            return False

        # Resize frame if needed to match writer dimensions
        self.writer.write(frame)
        self.frame_count += 1
        return True

    def stop(self):
        """Stop recording and release the writer."""
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        self.is_recording = False
        filepath = self.filepath
        self.filepath = None
        return filepath

    def get_filepath(self):
        return self.filepath

    def get_frame_count(self):
        return self.frame_count
