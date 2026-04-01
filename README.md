# RTSP Multi-Stream Viewer

A Python desktop application for receiving, displaying, and recording multiple RTSP video streams simultaneously. Built with PyQt6 and OpenCV, designed for surveillance and monitoring use cases on Windows.

## Features

- **Multi-stream display** — View up to 16 RTSP streams in a configurable grid layout (1x1 to 4x4)
- **MP4 recording** — Record individual or all streams to MP4 files with timestamped filenames
- **Snapshot capture** — Save the current frame of any stream as a JPEG image
- **Flexible configuration** — Add, edit, and remove streams via the GUI or by editing `config.json` directly
- **Auto-reconnect** — Streams automatically reconnect on disconnection
- **Fullscreen view** — Double-click any stream to expand it to fill the window; double-click again to return to grid view
- **Dark theme** — Modern dark UI with stream name overlays and red recording indicator

## Requirements

- Python 3.10 or later
- Windows 10/11 (also works on Linux and macOS)

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
   # source venv/bin/activate   # Linux/macOS
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
python main.py
```

The application window will open with a dark-themed interface. If streams are configured in `config.json`, they will start connecting automatically.

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

### Recording Video

- **Single stream:** Right-click a stream and select **"Start Recording"**. A red **REC** indicator appears on the stream overlay. Right-click again and select **"Stop Recording"** to save.
- **All streams:** Click **"Record All"** in the toolbar or go to **Recording > Record All Streams**. Stop with **"Stop Recording"** or **Recording > Stop All Recording**.

Recordings are saved as MP4 files in the configured recording directory (default: `./recordings/`). Filenames include the stream name and timestamp, e.g., `Front_Door_20260401_143025.mp4`.

### Taking Snapshots

Right-click a stream and select **"Take Snapshot"**. The image is saved as a JPEG file in the `./snapshots/` directory.

### Changing the Grid Layout

- Go to **View** and select the number of columns (1-4)
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
| `grid_columns` | integer | `4` | Number of columns in the grid (1-4) |
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
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config.json             # Stream and app configuration
├── app/
│   ├── __init__.py
│   ├── main_window.py      # Main window with grid layout, menus, toolbar
│   ├── stream_widget.py    # Video display widget with overlays and context menu
│   ├── stream_thread.py    # QThread worker for RTSP capture
│   ├── recorder.py         # MP4 video recording via OpenCV
│   ├── config_manager.py   # JSON configuration management
│   └── dialogs.py          # Stream and Settings dialogs
├── recordings/             # Recorded video files (created automatically)
└── snapshots/              # Snapshot images (created automatically)
```

## Troubleshooting

- **Stream not connecting:** Verify the RTSP URL is correct using the "Test Connection" button in the Add Stream dialog. Ensure the camera is reachable on the network.
- **Black screen with "Connecting...":** The stream may be using a codec not supported by your OpenCV build. Try installing `opencv-python-headless` or ensure FFmpeg is available on your system.
- **Recording files are 0 bytes:** Recording only works while a stream is actively connected and displaying frames. Ensure the stream is in "connected" state before starting recording.
- **High CPU usage:** Reduce the number of simultaneous streams or lower the camera resolution/frame rate at the source.

## License

This project is provided as-is for personal and educational use.
