import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QGridLayout,
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
from app.dialogs import StreamDialog, SettingsDialog


class MainWindow(QMainWindow):
    """Main application window with grid layout for multiple RTSP streams."""

    MAX_STREAMS = 16

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.stream_widgets = []
        self._fullscreen_widget = None
        self._grid_columns = config_manager.get_grid_columns()

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

    def _setup_central_widget(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.grid_layout = QGridLayout(self.central_widget)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)

    def _setup_statusbar(self):
        self.statusBar().showMessage("Ready")

    def _load_streams(self):
        """Load streams from config and create widgets."""
        streams = self.config_manager.get_streams()
        for stream_config in streams:
            self._create_stream_widget(stream_config)
        self._rebuild_grid()
        self._start_all_streams()

    def _create_stream_widget(self, stream_config):
        """Create a stream widget and add it to the list."""
        if len(self.stream_widgets) >= self.MAX_STREAMS:
            QMessageBox.warning(
                self, "Maximum Streams", f"Maximum of {self.MAX_STREAMS} streams supported."
            )
            return None

        rec_dir = self.config_manager.get_recording_directory()
        widget = StreamWidget(stream_config, recording_dir=rec_dir, parent=self)
        widget.recording_started.connect(self._on_recording_started)
        widget.recording_stopped.connect(self._on_recording_stopped)
        widget.double_clicked.connect(self._toggle_fullscreen)
        self.stream_widgets.append(widget)
        return widget

    def _rebuild_grid(self):
        """Rearrange all stream widgets in the grid layout."""
        # Remove all widgets from grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Add widgets back in grid order
        cols = self._grid_columns
        for i, widget in enumerate(self.stream_widgets):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(widget, row, col)
            widget.show()

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
                widget.start()

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
            widget.stop()
            widget.deleteLater()
            self.config_manager.remove_stream(index)
            self._rebuild_grid()

    def _start_all_streams(self):
        for widget in self.stream_widgets:
            widget.start()
        self._update_status()

    def _stop_all_streams(self):
        for widget in self.stream_widgets:
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

    def _toggle_fullscreen(self, widget):
        """Toggle a single stream to fill the entire grid or return to grid view."""
        if self._fullscreen_widget is not None:
            # Restore grid view
            self._fullscreen_widget = None
            self._rebuild_grid()
        else:
            # Show only the clicked widget
            self._fullscreen_widget = widget
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget() and item.widget() != widget:
                    item.widget().hide()
            self.grid_layout.addWidget(widget, 0, 0)
            widget.show()

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

        # Clear existing widgets
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

    def closeEvent(self, event):
        """Clean shutdown: stop all streams and recording."""
        self._stop_all_streams()
        event.accept()
