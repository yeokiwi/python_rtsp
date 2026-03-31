import cv2
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QFileDialog,
    QLabel,
)
from PyQt6.QtCore import Qt


class StreamDialog(QDialog):
    """Dialog for adding or editing an RTSP stream configuration."""

    def __init__(self, parent=None, name="", url="", enabled=True):
        super().__init__(parent)
        self.setWindowTitle("Stream Configuration")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("e.g., Front Door Camera")
        form.addRow("Name:", self.name_edit)

        self.url_edit = QLineEdit(url)
        self.url_edit.setPlaceholderText("rtsp://user:pass@192.168.1.100:554/stream")
        form.addRow("RTSP URL:", self.url_edit)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(enabled)
        form.addRow("", self.enabled_check)

        layout.addLayout(form)

        # Test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a stream name.")
            return
        if not self.url_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an RTSP URL.")
            return
        self.accept()

    def _test_connection(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Test Connection", "Please enter a URL first.")
            return

        self.setCursor(Qt.CursorShape.WaitCursor)
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        success = cap.isOpened()
        if success:
            ret, _ = cap.read()
            success = ret
        cap.release()
        self.unsetCursor()

        if success:
            QMessageBox.information(self, "Test Connection", "Connection successful!")
        else:
            QMessageBox.warning(
                self, "Test Connection", "Could not connect to the stream.\nPlease check the URL."
            )

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "url": self.url_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),
        }


class SettingsDialog(QDialog):
    """Dialog for global application settings."""

    def __init__(self, parent=None, grid_columns=4, recording_directory="./recordings"):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.grid_spin = QSpinBox()
        self.grid_spin.setRange(1, 4)
        self.grid_spin.setValue(grid_columns)
        form.addRow("Grid Columns:", self.grid_spin)

        # Recording directory
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit(recording_directory)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)
        form.addRow("Recording Dir:", dir_layout)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Recording Directory", self.dir_edit.text()
        )
        if directory:
            self.dir_edit.setText(directory)

    def get_data(self):
        return {
            "grid_columns": self.grid_spin.value(),
            "recording_directory": self.dir_edit.text().strip(),
        }
