import sys
import os

from PyQt6.QtWidgets import QApplication

from app.config_manager import ConfigManager
from app.main_window import MainWindow


def main():
    # Resolve config path relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

    config_manager = ConfigManager(config_path)
    config_manager.load()

    app = QApplication(sys.argv)
    app.setApplicationName("RTSP Multi-Stream Viewer")

    window = MainWindow(config_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
