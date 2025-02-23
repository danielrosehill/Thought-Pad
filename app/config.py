import os
import json
from pathlib import Path

class Config:
    def __init__(self):
        self.app_name = "thought-pad"
        self.config_dir = Path(os.path.expanduser(f"~/.config/{self.app_name}"))
        self.config_file = self.config_dir / "config.json"
        self.default_config = {
            "openai_api_key": "",
            "preferred_audio_device": None,
            "auto_save_interval": 300,  # 5 minutes in seconds
            "gpt_temperature": 0.3,
            "whisper_model": "base",
            "download_path": str(Path(os.path.expanduser("~/Desktop"))),
            "include_raw_text": False  # Default to not including raw text in downloads
        }
        self.current_config = {}
        self._ensure_config_exists()
        self.load_config()

    def _ensure_config_exists(self):
        """Create config directory and file if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.current_config = self.default_config.copy()
            self.save_config()

    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                self.current_config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            self.current_config = self.default_config.copy()
            self.save_config()

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.current_config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        """Get a configuration value."""
        return self.current_config.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save."""
        self.current_config[key] = value
        self.save_config()

    @property
    def api_key(self):
        """Get the OpenAI API key."""
        return self.get('openai_api_key', '')

    @api_key.setter
    def api_key(self, value):
        """Set the OpenAI API key."""
        self.set('openai_api_key', value)

    def get_preferred_audio_device(self):
        """Get the preferred audio device."""
        return self.get('preferred_audio_device')

    def set_preferred_audio_device(self, device):
        """Set the preferred audio device."""
        self.set('preferred_audio_device', device)