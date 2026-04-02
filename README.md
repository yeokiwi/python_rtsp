# RTSP Multi-Stream Viewer

A Python desktop application for receiving, displaying, recording, and analysing multiple RTSP video streams simultaneously. Built with PyQt6 and OpenCV, with optional YOLOv9 real-time object detection powered by Ultralytics.

## Features

- **Multi-stream display** — View up to 16 RTSP streams in a configurable grid layout (1×1 to 4×4)
- **YOLOv9 object detection** — Toggle real-time bounding-box detection on all streams with a single click; detection overlays are drawn on the display only and do not affect recordings
- **MP4 recording** — Record individual or all streams to MP4 files with timestamped filenames
- **Snapshot capture** — Save the current frame of any stream as a JPEG image
- **Flexible configuration** — Add, edit, and remove streams via the GUI or by editing `config.json` directly
- **Auto-reconnect** — Streams automatically reconnect on disconnection
- **Fullscreen view** — Double-click any stream to expand it; double-click again to return to grid view
- **Dark theme** — Modern dark UI with stream name overlays and red recording indicator

## Requirements

- Python 3.10 or later
- Windows 10/11, Linux, or macOS
- (Optional) NVIDIA GPU with CUDA for accelerated YOLOv9 inference

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yeokiwi/python_rtsp.git
   cd python_rtsp
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # Linux / macOS
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** The `ultralytics` package is included in `requirements.txt`.  
   > On first use, Ultralytics will automatically download the default YOLOv9 model weights (`yolov9c.pt`, ~51 MB) from the internet.  
   > To use GPU acceleration install the matching PyTorch CUDA build before running — see [pytorch.org/get-started](https://pytorch.org/get-started/locally/).

## Running the Application

```bash
python main.py
```

The application window opens with a dark-themed interface. Any streams configured in `config.json` will start connecting automatically.

## Usage

### Adding a Stream

**Via the GUI:**

1. Click **"+ Add Stream"** in the toolbar, or go to **Streams > Add Stream** (`Ctrl+N`)
2. Enter a name and the RTSP URL (e.g., `rtsp://user:pass@192.168.1.100:554/stream`)
3. Optionally click **"Test Connection"** to verify the URL
4. Click **OK**

**Via the config file:**

Edit `config.json` and add entries to the `"streams"` array:

```json
{
    "streams": [
        {
            "name": "Front Door",
            "url": "rtsp://admin:password@192.168.1.100:554/stream1",
            "enabled": true
        },
        {
            "name": "Backyard",
            "url": "rtsp://admin:password@192.168.1.101:554/stream1",
            "enabled": true
        }
    ],
    "grid_columns": 4,
    "recording_directory": "./recordings"
}
```

Then reload the config from the app: **File > Reload Config** (`Ctrl+R`).

### Object Detection (YOLOv9)

Detection is off by default. To enable it:

1. Click **"Detection OFF"** in the toolbar — the button label changes to **"Detection ON"** and green bounding boxes with class labels appear on all active streams.
2. Click the button again to disable detection on all streams.

Additional options are available in the **Detection** menu:

| Menu item | Description |
|-----------|-------------|
| **Enable Detection** | Toggle detection on all streams (same as the toolbar button) |
| **Load Model…** | Open a file dialog to select a custom `.pt` or `.onnx` weights file |
| **Detection Settings…** | Set the confidence threshold (default `0.25`) and inference device (`auto`, `cpu`, `cuda`, `mps`) |

**Per-stream control:** Right-click any stream and select **"Disable Detection"** to turn off detection for that stream individually without affecting others.

**Performance notes:**

- A single model instance is shared across all streams; inference is serialised by an internal lock so GPU memory usage stays constant regardless of stream count.
- Each stream has its own frame queue (capacity 1). When inference is slower than the stream frame rate, excess frames are dropped — the display stays smooth and no memory backlog builds up.
- Recordings always capture the raw video frame; detection overlays are never written to disk.

### Recording Video

- **Single stream:** Right-click a stream → **"Start Recording"**. A red **REC** indicator appears on the overlay. Right-click again → **"Stop Recording"** to save.
- **All streams:** Click **"Record All"** in the toolbar, or go to **Recording > Record All Streams**. Stop with **"Stop Recording"** or **Recording > Stop All Recording**.

Recordings are saved as MP4 files in the configured recording directory (default: `./recordings/`). Filenames include the stream name and timestamp, e.g., `Front_Door_20260401_143025.mp4`.

### Taking Snapshots

Right-click a stream → **"Take Snapshot"**. The image is saved as a JPEG in `./snapshots/`.

### Changing the Grid Layout

- Go to **View** and select the number of columns (1–4)
- Or go to **File > Settings** to change the grid column count

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Add a new stream |
| `Ctrl+R` | Reload configuration from file |
| `Ctrl+Q` | Quit the application |

## Configuration Reference

The `config.json` file supports the following fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `streams` | array | `[]` | List of stream objects |
| `grid_columns` | integer | `4` | Number of columns in the grid (1–4) |
| `recording_directory` | string | `"./recordings"` | Directory where recordings are saved |

Each stream object:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name for the stream |
| `url` | string | RTSP URL of the video stream |
| `enabled` | boolean | Whether the stream should connect on startup |

## Project Structure

```
python_rtsp/
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── config.json               # Stream and app configuration
├── app/
│   ├── __init__.py
│   ├── main_window.py        # Main window with grid layout, menus, toolbar
│   ├── stream_widget.py      # Video display widget with overlays and context menu
│   ├── stream_thread.py      # QThread worker for RTSP capture
│   ├── recorder.py           # MP4 video recording via OpenCV
│   ├── config_manager.py     # JSON configuration management
│   ├── dialogs.py            # Stream and Settings dialogs
│   ├── yolov9_detector.py    # Thread-safe YOLOv9 model wrapper (Ultralytics)
│   └── detection_thread.py   # Per-stream async inference QThread worker
├── recordings/               # Recorded video files (created automatically)
└── snapshots/                # Snapshot images (created automatically)
```

## Troubleshooting

- **Stream not connecting:** Verify the RTSP URL using the "Test Connection" button in the Add Stream dialog. Ensure the camera is reachable on the network.
- **Black screen with "Connecting...":** The stream may use a codec not supported by your OpenCV build. Ensure FFmpeg is available on your system or try `opencv-python-headless`.
- **Recording files are 0 bytes:** Recording only works while a stream is actively connected. Ensure the stream shows "connected" before starting recording.
- **High CPU usage (no GPU):** YOLOv9 inference on CPU is compute-intensive. Reduce the number of detection-enabled streams, lower the confidence threshold to skip post-processing overhead, or use a lighter model (e.g., `yolov9t.pt`).
- **Detection model fails to load:** Ensure `ultralytics` is installed (`pip install ultralytics`) and that the machine has internet access for the initial model weight download. Custom model files must be a supported Ultralytics format (`.pt` or `.onnx`).
- **CUDA out of memory:** Use a smaller model variant (`yolov9t.pt` or `yolov9s.pt`) or set the inference device to `cpu` in **Detection > Detection Settings**.

## License

This project is provided as-is for personal and educational use.
