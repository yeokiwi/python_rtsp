from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt, pyqtSignal


class StreamSidebarItem(QWidget):
    """Thumbnail entry in the left sidebar for a single RTSP stream.

    Shows a live video preview, the stream name, and a per-stream detection
    toggle button.  Clicking the item (outside the DET button) signals the
    main window to focus that stream in the main view area.
    """

    THUMB_W = 186
    THUMB_H = 105  # ~16:9

    stream_selected    = pyqtSignal(object)        # StreamWidget ref
    detection_toggled  = pyqtSignal(object, bool)  # StreamWidget ref, enable
    connection_toggled = pyqtSignal(object, bool)  # StreamWidget ref, connect

    def __init__(self, stream_widget, parent=None):
        super().__init__(parent)
        self._stream_widget = stream_widget
        self._selected = False
        self._setup_ui()
        self._apply_border()

    def _setup_ui(self):
        self.setFixedWidth(198)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        # --- Thumbnail preview ---
        self._preview = QLabel()
        self._preview.setFixedSize(self.THUMB_W, self.THUMB_H)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background-color: #0d0d1a; border: 1px solid #2a2a4a;"
        )
        self._preview.setText(self._stream_widget.name)
        self._preview.setStyleSheet(
            "background-color: #0d0d1a; border: 1px solid #2a2a4a;"
            " color: #666; font-size: 10px;"
        )
        layout.addWidget(self._preview)

        # --- Bottom bar: name label + DET button ---
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(4)

        self._name_label = QLabel(self._stream_widget.name)
        self._name_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        self._name_label.setMaximumWidth(90)
        self._name_label.setWordWrap(False)
        self._name_label.setTextFormat(Qt.TextFormat.PlainText)

        self._conn_btn = QPushButton("CONN")
        self._conn_btn.setCheckable(True)
        self._conn_btn.setFixedSize(44, 20)
        self._conn_btn.setStyleSheet(self._conn_btn_style(False))
        self._conn_btn.setEnabled(self._stream_widget.enabled)
        self._conn_btn.toggled.connect(self._on_conn_toggled)

        self._det_btn = QPushButton("DET")
        self._det_btn.setCheckable(True)
        self._det_btn.setFixedSize(38, 20)
        self._det_btn.setStyleSheet(self._det_btn_style(False))
        self._det_btn.toggled.connect(self._on_det_toggled)

        bar_layout.addWidget(self._name_label, 1)
        bar_layout.addWidget(self._conn_btn)
        bar_layout.addWidget(self._det_btn)
        layout.addWidget(bar)

    @staticmethod
    def _conn_btn_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #1a4a8a; color: #cce0ff;"
                " border: 1px solid #2a6ad0; border-radius: 3px; font-size: 9px; font-weight: bold; }"
                " QPushButton:hover { background-color: #225faa; }"
                " QPushButton:disabled { background-color: #1a1a2a; color: #555;"
                " border: 1px solid #2a2a3a; }"
            )
        return (
            "QPushButton { background-color: #2a2a3a; color: #888;"
            " border: 1px solid #3a3a5a; border-radius: 3px; font-size: 9px; }"
            " QPushButton:hover { background-color: #3a3a4a; color: #aaa; }"
            " QPushButton:disabled { background-color: #1a1a2a; color: #555;"
            " border: 1px solid #2a2a3a; }"
        )

    @staticmethod
    def _det_btn_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #1a6b1a; color: #aaffaa;"
                " border: 1px solid #2a9b2a; border-radius: 3px; font-size: 9px; font-weight: bold; }"
                " QPushButton:hover { background-color: #227722; }"
            )
        return (
            "QPushButton { background-color: #2a2a3a; color: #888;"
            " border: 1px solid #3a3a5a; border-radius: 3px; font-size: 9px; }"
            " QPushButton:hover { background-color: #3a3a4a; color: #aaa; }"
        )

    def _on_det_toggled(self, checked: bool):
        self._det_btn.setStyleSheet(self._det_btn_style(checked))
        self.detection_toggled.emit(self._stream_widget, checked)

    def _on_conn_toggled(self, checked: bool):
        self._conn_btn.setStyleSheet(self._conn_btn_style(checked))
        self.connection_toggled.emit(self._stream_widget, checked)

    # ------------------------------------------------------------------
    # Public API called by MainWindow
    # ------------------------------------------------------------------

    def update_thumbnail(self, pixmap):
        """Set a new preview frame (called from StreamWidget.thumbnail_ready signal)."""
        scaled = pixmap.scaled(
            self.THUMB_W, self.THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._preview.setPixmap(scaled)

    def update_detection_state(self, active: bool):
        """Sync the DET button state without triggering the toggled signal."""
        self._det_btn.blockSignals(True)
        self._det_btn.setChecked(active)
        self._det_btn.setStyleSheet(self._det_btn_style(active))
        self._det_btn.blockSignals(False)

    def update_connection_state(self, active: bool):
        """Sync the CONN button state without triggering the toggled signal."""
        self._conn_btn.blockSignals(True)
        self._conn_btn.setChecked(active)
        self._conn_btn.setStyleSheet(self._conn_btn_style(active))
        self._conn_btn.blockSignals(False)

    def update_enabled_state(self, enabled: bool):
        """Reflect the underlying stream's enabled flag on the CONN button."""
        self._conn_btn.setEnabled(enabled)

    def set_selected(self, selected: bool):
        """Highlight this item when its stream is focused in the main view."""
        self._selected = selected
        self._apply_border()

    def _apply_border(self):
        if self._selected:
            self.setStyleSheet(
                "StreamSidebarItem { background-color: #1a2a4a;"
                " border: 2px solid #4a7adf; border-radius: 4px; }"
            )
        else:
            self.setStyleSheet(
                "StreamSidebarItem { background-color: #16162e;"
                " border: 1px solid #2a2a4a; border-radius: 4px; }"
            )

    # ------------------------------------------------------------------
    # Mouse click → focus stream
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        # Only emit the focus signal if the click is NOT on the CONN or DET button.
        # Map the event position into each button's own coordinate space first.
        on_det = self._det_btn.rect().contains(
            self._det_btn.mapFrom(self, event.pos())
        )
        on_conn = self._conn_btn.rect().contains(
            self._conn_btn.mapFrom(self, event.pos())
        )
        if not (on_det or on_conn):
            self.stream_selected.emit(self._stream_widget)
        super().mousePressEvent(event)
