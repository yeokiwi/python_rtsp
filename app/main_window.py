import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QMenuBar,
    QMenu,
    QToolBar,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

from app.config_manager import ConfigManager
from app.stream_widget import StreamWidget
from app.stream_pool import StreamPool
from app.dialogs import StreamDialog, SettingsDialog


class MainWindow(QMainWindow):
    """Main application window with grid layout for multiple RTSP streams."""

    MAX_STREAMS = 16

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.stream_widgets = []
        self._grid_columns = config_manager.get_grid_columns()

        self._detector = None
        self._detection_enabled = False
        self._model_path = "yolov9c.pt"
        self._conf_threshold = 0.25
        self._det_device = None  # auto-select

        self._sidebar_items = {}   # StreamWidget → StreamSidebarItem
        self._focused_widget = None

        # Single shared executor for all RTSP capture workers.
        self._stream_pool = StreamPool(max_workers=self.MAX_STREAMS)

        self._setup_window()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._load_streams()

    def _setup_window(self):
        self.setWindowTitle("RTSP Multi-Stream Viewer")
        self.setMinimumSize(800, 600)
        self.resize(1280, 960)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f23; }
            QMenuBar { background-color: #1a1a2e; color: #e0e0e0; }
            QMenuBar::item:selected { background-color: #16213e; }
            QMenu { background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #333; }
            QMenu::item:selected { background-color: #16213e; }
            QToolBar { background-color: #1a1a2e; border: none; spacing: 5px; padding: 3px; }
            QStatusBar { background-color: #1a1a2e; color: #aaaaaa; }
            QPushButton { background-color: #16213e; color: #e0e0e0; border: 1px solid #333;
                          padding: 5px 12px; border-radius: 3px; }
            QPushButton:hover { background-color: #1a3a5e; }
        """)

    def _setup_menus(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        reload_action = QAction("&Reload Config", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self._reload_config)
        file_menu.addAction(reload_action)

        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Streams menu
        streams_menu = menubar.addMenu("&Streams")

        add_action = QAction("&Add Stream...", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self._add_stream)
        streams_menu.addAction(add_action)

        edit_action = QAction("&Edit Stream...", self)
        edit_action.triggered.connect(self._edit_stream)
        streams_menu.addAction(edit_action)

        remove_action = QAction("&Remove Stream...", self)
        remove_action.triggered.connect(self._remove_stream)
        streams_menu.addAction(remove_action)

        streams_menu.addSeparator()

        start_all = QAction("Start &All Streams", self)
        start_all.triggered.connect(self._start_all_streams)
        streams_menu.addAction(start_all)

        stop_all = QAction("S&top All Streams", self)
        stop_all.triggered.connect(self._stop_all_streams)
        streams_menu.addAction(stop_all)

        # Recording menu
        rec_menu = menubar.addMenu("&Recording")

        rec_all = QAction("Record &All Streams", self)
        rec_all.triggered.connect(self._start_all_recording)
        rec_menu.addAction(rec_all)

        stop_rec_all = QAction("&Stop All Recording", self)
        stop_rec_all.triggered.connect(self._stop_all_recording)
        rec_menu.addAction(stop_rec_all)

        rec_menu.addSeparator()

        open_rec_dir = QAction("&Open Recordings Folder", self)
        open_rec_dir.triggered.connect(self._open_recordings_folder)
        rec_menu.addAction(open_rec_dir)

        # Detection menu
        det_menu = menubar.addMenu("&Detection")

        self._det_toggle_action = QAction("&Enable Detection", self)
        self._det_toggle_action.setCheckable(True)
        self._det_toggle_action.triggered.connect(self._toggle_detection)
        det_menu.addAction(self._det_toggle_action)

        load_model_action = QAction("&Load Model...", self)
        load_model_action.triggered.connect(self._load_model)
        det_menu.addAction(load_model_action)

        det_settings_action = QAction("Detection &Settings...", self)
        det_settings_action.triggered.connect(self._show_detection_settings)
        det_menu.addAction(det_settings_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        for cols in range(1, 5):
            action = QAction(f"&{cols} Column{'s' if cols > 1 else ''}", self)
            action.triggered.connect(lambda checked, c=cols: self._set_grid_columns(c))
            view_menu.addAction(action)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        add_btn = QAction("+ Add Stream", self)
        add_btn.triggered.connect(self._add_stream)
        toolbar.addAction(add_btn)

        toolbar.addSeparator()

        start_btn = QAction("Start All", self)
        start_btn.triggered.connect(self._start_all_streams)
        toolbar.addAction(start_btn)

        stop_btn = QAction("Stop All", self)
        stop_btn.triggered.connect(self._stop_all_streams)
        toolbar.addAction(stop_btn)

        toolbar.addSeparator()

        rec_btn = QAction("Record All", self)
        rec_btn.triggered.connect(self._start_all_recording)
        toolbar.addAction(rec_btn)

        stop_rec_btn = QAction("Stop Recording", self)
        stop_rec_btn.triggered.connect(self._stop_all_recording)
        toolbar.addAction(stop_rec_btn)

        toolbar.addSeparator()

        self._det_btn = QAction("Detection OFF", self)
        self._det_btn.triggered.connect(self._toggle_detection)
        toolbar.addAction(self._det_btn)

    def _setup_central_widget(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        outer = QHBoxLayout(self.central_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Left sidebar ---
        self._sidebar_inner = QWidget()
        self._sidebar_inner.setStyleSheet("background-color: #12122a;")
        self._sidebar_vbox = QVBoxLayout(self._sidebar_inner)
        self._sidebar_vbox.setContentsMargins(4, 4, 4, 4)
        self._sidebar_vbox.setSpacing(4)
        self._sidebar_vbox.addStretch()   # sidebar items inserted before this

        self._sidebar_scroll = QScrollArea()
        self._sidebar_scroll.setWidget(self._sidebar_inner)
        self._sidebar_scroll.setWidgetResizable(True)
        self._sidebar_scroll.setFixedWidth(210)
        self._sidebar_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._sidebar_scroll.setStyleSheet(
            "QScrollArea { border: none; border-right: 1px solid #333; }"
        )

        # --- Main view area ---
        self._view_area = QWidget()
        self.grid_layout = QGridLayout(self._view_area)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)

        outer.addWidget(self._sidebar_scroll)
        outer.addWidget(self._view_area, 1)

    def _setup_statusbar(self):
        self.statusBar().showMessage("Ready")

    def _load_streams(self):
        """Load streams from config and create widgets (without connecting)."""
        streams = self.config_manager.get_streams()
        for stream_config in streams:
            self._create_stream_widget(stream_config)
        self._rebuild_grid()

    def _create_stream_widget(self, stream_config):
        """Create a stream widget and add it to the list."""
        if len(self.stream_widgets) >= self.MAX_STREAMS:
            QMessageBox.warning(
                self, "Maximum Streams", f"Maximum of {self.MAX_STREAMS} streams supported."
            )
            return None

        from app.sidebar_item import StreamSidebarItem

        rec_dir = self.config_manager.get_recording_directory()
        widget = StreamWidget(stream_config, recording_dir=rec_dir, parent=self)
        widget.set_pool(self._stream_pool)
        widget.recording_started.connect(self._on_recording_started)
        widget.recording_stopped.connect(self._on_recording_stopped)
        widget.double_clicked.connect(self._set_focused_stream)
        widget.detection_enable_requested.connect(
            lambda w: self._on_per_stream_detection_toggled(w, True)
        )
        if self._detection_enabled and self._detector is not None:
            widget.set_detector(self._detector)

        # Create a matching sidebar thumbnail item
        item = StreamSidebarItem(widget)
        item.stream_selected.connect(self._set_focused_stream)
        item.detection_toggled.connect(self._on_per_stream_detection_toggled)
        item.connection_toggled.connect(self._on_per_stream_connection_toggled)
        widget.thumbnail_ready.connect(item.update_thumbnail)
        widget.detection_changed.connect(item.update_detection_state)
        widget.connection_changed.connect(item.update_connection_state)
        widget.connection_changed.connect(lambda _: self._update_status())
        # Insert before the trailing stretch
        self._sidebar_vbox.insertWidget(self._sidebar_vbox.count() - 1, item)
        self._sidebar_items[widget] = item

        self.stream_widgets.append(widget)
        return widget

    def _rebuild_grid(self):
        """Rearrange all stream widgets in the grid layout."""
        self._focused_widget = None
        self._update_sidebar_selection(None)

        # Remove all widgets from grid without changing parent
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()

        # Reset stretch factors so all rows/columns share space equally
        for i in range(self.grid_layout.rowCount()):
            self.grid_layout.setRowStretch(i, 0)
        for i in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(i, 0)

        # Add widgets back in grid order
        cols = self._grid_columns
        rows_needed = (len(self.stream_widgets) + cols - 1) // cols if self.stream_widgets else 0
        for i, widget in enumerate(self.stream_widgets):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(widget, row, col)
            widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            widget.show()

        # Set equal stretch for all active rows and columns
        for r in range(rows_needed):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)

        self._update_status()

    def _add_stream(self):
        if len(self.stream_widgets) >= self.MAX_STREAMS:
            QMessageBox.warning(
                self, "Maximum Streams", f"Maximum of {self.MAX_STREAMS} streams supported."
            )
            return

        dialog = StreamDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            self.config_manager.add_stream(data["name"], data["url"], data["enabled"])
            widget = self._create_stream_widget(data)
            if widget:
                self._rebuild_grid()

    def _edit_stream(self):
        if not self.stream_widgets:
            QMessageBox.information(self, "Edit Stream", "No streams to edit.")
            return

        names = [w.name for w in self.stream_widgets]
        name, ok = QInputDialog.getItem(self, "Edit Stream", "Select stream:", names, 0, False)
        if not ok:
            return

        index = names.index(name)
        widget = self.stream_widgets[index]
        config = widget.stream_config

        dialog = StreamDialog(
            self,
            name=config.get("name", ""),
            url=config.get("url", ""),
            enabled=config.get("enabled", True),
        )
        if dialog.exec():
            data = dialog.get_data()
            self.config_manager.update_stream(index, data["name"], data["url"], data["enabled"])
            widget.update_config(data)
            sidebar_item = self._sidebar_items.get(widget)
            if sidebar_item is not None:
                sidebar_item.update_enabled_state(widget.enabled)
            self._update_status()

    def _remove_stream(self):
        if not self.stream_widgets:
            QMessageBox.information(self, "Remove Stream", "No streams to remove.")
            return

        names = [w.name for w in self.stream_widgets]
        name, ok = QInputDialog.getItem(self, "Remove Stream", "Select stream:", names, 0, False)
        if not ok:
            return

        index = names.index(name)
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove stream '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            widget = self.stream_widgets.pop(index)
            # Remove sidebar item
            sidebar_item = self._sidebar_items.pop(widget, None)
            if sidebar_item is not None:
                self._sidebar_vbox.removeWidget(sidebar_item)
                sidebar_item.deleteLater()
            # Stop stream and disconnect signals before removing from layout
            widget.stop()
            self.grid_layout.removeWidget(widget)
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
            self.config_manager.remove_stream(index)
            self._rebuild_grid()

    def _start_all_streams(self):
        for widget in self.stream_widgets:
            if widget.enabled and not widget.is_connected():
                widget.start()
        self._update_status()

    def _stop_all_streams(self):
        for widget in self.stream_widgets:
            if widget.is_connected():
                widget.stop()
        self._update_status()

    def _start_all_recording(self):
        count = 0
        for widget in self.stream_widgets:
            if widget._status == "connected" and not widget.is_recording():
                if widget.start_recording():
                    count += 1
        self.statusBar().showMessage(f"Started recording {count} stream(s)")

    def _stop_all_recording(self):
        count = 0
        for widget in self.stream_widgets:
            if widget.is_recording():
                widget.stop_recording()
                count += 1
        self.statusBar().showMessage(f"Stopped recording {count} stream(s)")

    def _set_grid_columns(self, columns):
        self._grid_columns = columns
        self.config_manager.set_grid_columns(columns)
        self._rebuild_grid()

    def _set_focused_stream(self, widget):
        """Expand a single stream to fill the main view, or return to grid."""
        if self._focused_widget is widget:
            # Clicking the same stream again → restore grid
            self._rebuild_grid()
            return

        self._focused_widget = widget

        # Clear grid layout, hide all other streams
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w and w is not widget:
                w.hide()

        # Reset stretch factors then place the focused stream
        for i in range(self.grid_layout.rowCount()):
            self.grid_layout.setRowStretch(i, 0)
        for i in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(i, 0)

        self.grid_layout.addWidget(widget, 0, 0)
        self.grid_layout.setRowStretch(0, 1)
        self.grid_layout.setColumnStretch(0, 1)
        widget.show()

        self._update_sidebar_selection(widget)

    def _update_sidebar_selection(self, focused_widget):
        """Highlight the sidebar item whose stream is currently focused."""
        for sw, item in self._sidebar_items.items():
            item.set_selected(sw is focused_widget)

    def _show_settings(self):
        dialog = SettingsDialog(
            self,
            grid_columns=self._grid_columns,
            recording_directory=self.config_manager.get_recording_directory(),
        )
        if dialog.exec():
            data = dialog.get_data()
            self._set_grid_columns(data["grid_columns"])
            self.config_manager.set_recording_directory(data["recording_directory"])
            for widget in self.stream_widgets:
                widget.set_recording_dir(data["recording_directory"])

    def _reload_config(self):
        """Reload configuration from file and refresh all streams."""
        self._stop_all_streams()

        # Clear sidebar items
        for item in self._sidebar_items.values():
            self._sidebar_vbox.removeWidget(item)
            item.deleteLater()
        self._sidebar_items.clear()

        # Clear existing stream widgets
        for widget in self.stream_widgets:
            widget.stop()
            widget.deleteLater()
        self.stream_widgets.clear()

        # Reload
        self.config_manager.load()
        self._grid_columns = self.config_manager.get_grid_columns()
        self._load_streams()
        self.statusBar().showMessage("Configuration reloaded")

    def _open_recordings_folder(self):
        rec_dir = self.config_manager.get_recording_directory()
        os.makedirs(rec_dir, exist_ok=True)
        # Cross-platform open folder
        import subprocess
        import sys

        if sys.platform == "win32":
            os.startfile(os.path.abspath(rec_dir))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", rec_dir])
        else:
            subprocess.Popen(["xdg-open", rec_dir])

    def _on_recording_started(self, name):
        self.statusBar().showMessage(f"Recording started: {name}")

    def _on_recording_stopped(self, name, filepath):
        self.statusBar().showMessage(f"Recording saved: {filepath}")

    def _update_status(self):
        total = len(self.stream_widgets)
        active = sum(1 for w in self.stream_widgets if w._status == "connected")
        recording = sum(1 for w in self.stream_widgets if w.is_recording())
        msg = f"Streams: {active}/{total} connected"
        if recording:
            msg += f" | Recording: {recording}"
        self.statusBar().showMessage(msg)

    def _on_per_stream_connection_toggled(self, widget, connect):
        """Connect or disconnect a single stream from the sidebar CONN button."""
        if connect:
            if not widget.enabled:
                # Defensive: button should be disabled, but bail out cleanly anyway.
                item = self._sidebar_items.get(widget)
                if item is not None:
                    item.update_connection_state(False)
                return
            widget.start()
            self.statusBar().showMessage(f"Connecting: {widget.name}")
        else:
            widget.stop()
            self.statusBar().showMessage(f"Disconnected: {widget.name}")
        self._update_status()

    def _on_per_stream_detection_toggled(self, widget, enable):
        """Enable or disable detection for a single stream."""
        if enable:
            if self._detector is None:
                from app.yolov9_detector import YOLOv9Detector
                self.statusBar().showMessage("Loading YOLOv9 model…")
                try:
                    self._detector = YOLOv9Detector(
                        self._model_path, self._conf_threshold, self._det_device
                    )
                except Exception as exc:
                    QMessageBox.critical(self, "Detection Error", str(exc))
                    self.statusBar().showMessage("Failed to load detection model")
                    # Revert the sidebar DET button state
                    item = self._sidebar_items.get(widget)
                    if item:
                        item.update_detection_state(False)
                    return
            widget.set_detector(self._detector)
            self.statusBar().showMessage(f"Detection enabled: {widget.name}")
        else:
            widget.clear_detector()
            self.statusBar().showMessage(f"Detection disabled: {widget.name}")

    def _toggle_detection(self):
        """Enable or disable YOLOv9 detection on all streams."""
        self._detection_enabled = not self._detection_enabled
        if self._detection_enabled:
            from app.yolov9_detector import YOLOv9Detector
            self.statusBar().showMessage("Loading YOLOv9 model…")
            try:
                self._detector = YOLOv9Detector(
                    self._model_path, self._conf_threshold, self._det_device
                )
            except Exception as exc:
                QMessageBox.critical(self, "Detection Error", str(exc))
                self._detection_enabled = False
                self._det_toggle_action.setChecked(False)
                self.statusBar().showMessage("Failed to load detection model")
                return
            for widget in self.stream_widgets:
                widget.set_detector(self._detector)
            self._det_btn.setText("Detection ON")
            self.statusBar().showMessage("Detection enabled")
        else:
            for widget in self.stream_widgets:
                widget.clear_detector()
            self._detector = None
            self._det_btn.setText("Detection OFF")
            self.statusBar().showMessage("Detection disabled")
        self._det_toggle_action.setChecked(self._detection_enabled)

    def _load_model(self):
        """Open a file dialog to select a YOLOv9 .pt or .onnx model file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select YOLOv9 Model", "", "Model Files (*.pt *.onnx);;All Files (*)"
        )
        if not path:
            return
        self._model_path = path
        if self._detection_enabled:
            # Reload with the new model file
            for widget in self.stream_widgets:
                widget.clear_detector()
            self._detector = None
            self._detection_enabled = False
            self._toggle_detection()

    def _show_detection_settings(self):
        """Dialog to configure confidence threshold and inference device."""
        conf, ok = QInputDialog.getDouble(
            self,
            "Detection Settings",
            "Confidence threshold (0.01 – 0.99):",
            self._conf_threshold,
            0.01,
            0.99,
            2,
        )
        if not ok:
            return
        self._conf_threshold = conf

        devices = ["auto", "cpu", "cuda", "cuda:0", "mps"]
        current = "auto" if self._det_device is None else self._det_device
        device, ok = QInputDialog.getItem(
            self, "Detection Settings", "Inference device:", devices,
            devices.index(current) if current in devices else 0, False
        )
        if not ok:
            return
        self._det_device = None if device == "auto" else device

        if self._detection_enabled:
            # Reload with updated settings
            for widget in self.stream_widgets:
                widget.clear_detector()
            self._detector = None
            self._detection_enabled = False
            self._toggle_detection()

    def closeEvent(self, event):
        """Clean shutdown: stop all streams, drain pool, then exit."""
        from concurrent.futures import wait as futures_wait

        futures = []
        for widget in self.stream_widgets:
            widget.clear_detector()
            future = widget._future
            if future is not None:
                futures.append(future)
        self._stop_all_streams()

        # Give workers up to ~8s to unwind FFmpeg's 5s stimeout.
        if futures:
            futures_wait(futures, timeout=8)

        self._stream_pool.shutdown(wait=True)
        event.accept()
