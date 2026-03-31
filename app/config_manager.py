import json
import os


DEFAULT_CONFIG = {
    "streams": [],
    "grid_columns": 4,
    "recording_directory": "./recordings",
}


class ConfigManager:
    """Manages loading and saving application configuration from/to a JSON file."""

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = {}

    def load(self):
        """Load configuration from the JSON file. Creates default if not found."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.config["streams"] = []
            self.save()
        return self.config

    def save(self, config=None):
        """Save configuration to the JSON file."""
        if config is not None:
            self.config = config
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get_streams(self):
        return self.config.get("streams", [])

    def set_streams(self, streams):
        self.config["streams"] = streams
        self.save()

    def add_stream(self, name, url, enabled=True):
        stream = {"name": name, "url": url, "enabled": enabled}
        self.config.setdefault("streams", []).append(stream)
        self.save()
        return stream

    def remove_stream(self, index):
        streams = self.config.get("streams", [])
        if 0 <= index < len(streams):
            removed = streams.pop(index)
            self.save()
            return removed
        return None

    def update_stream(self, index, name=None, url=None, enabled=None):
        streams = self.config.get("streams", [])
        if 0 <= index < len(streams):
            if name is not None:
                streams[index]["name"] = name
            if url is not None:
                streams[index]["url"] = url
            if enabled is not None:
                streams[index]["enabled"] = enabled
            self.save()

    def get_grid_columns(self):
        return self.config.get("grid_columns", 4)

    def set_grid_columns(self, columns):
        self.config["grid_columns"] = columns
        self.save()

    def get_recording_directory(self):
        return self.config.get("recording_directory", "./recordings")

    def set_recording_directory(self, directory):
        self.config["recording_directory"] = directory
        self.save()
