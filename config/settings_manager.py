import os
import json
from typing import Optional, List
from pathlib import Path
from .settings import Settings
from utils import is_git_repo
from dataclasses import dataclass, asdict
from git_tasks.log_manager import LogManager


class SettingsManager:
    DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/git-tracker/config.json")
    DEFAULT_SETTINGS = Settings(
        watched_paths=[],
        auto_refresh_interval=300,
        max_depth=3,
        show_hidden=False,
        theme="tokyo-night",
    )

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._settings = None
        self._ensure_config_dir()
        self.log_manager = LogManager(
            os.path.dirname(self.config_path)
        )  # Share the same config directory
        self.load_settings()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        config_dir = os.path.dirname(self.config_path)
        os.makedirs(config_dir, exist_ok=True)

    def load_settings(self) -> None:
        """Load settings from the configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    if not data:  # Check if the data is empty
                        self._settings = self.DEFAULT_SETTINGS
                    else:
                        # Convert dictionary to Settings object
                        self._settings = Settings(**data)
            else:
                # Create default settings file if it doesn't exist
                self._settings = self.DEFAULT_SETTINGS
                self.save_settings()  # Save default settings
        except (json.JSONDecodeError, ValueError, TypeError):
            print("Error loading settings: Invalid settings format.")
            self._settings = self.DEFAULT_SETTINGS  # Use default settings
            self.save_settings()  # Create a new settings file with default values
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._settings = (
                self.DEFAULT_SETTINGS
            )  # Use default settings if loading fails

    def save_settings(self) -> None:
        """Save current settings to the configuration file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(asdict(self._settings), f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def update_settings(self, **kwargs) -> None:
        """Update settings with new values."""
        current_settings = asdict(self._settings)
        current_settings.update(kwargs)
        self._settings = Settings(**current_settings)
        self.save_settings()

    @property
    def settings(self) -> Settings:
        """Get current settings."""
        return self._settings

    def add_watched_path(self, path: str) -> None:
        """Add a new path to watch."""
        if path not in self.settings.watched_paths:
            self.settings.watched_paths.append(path)
            self.save_settings()
            self.log_manager.info(f"Added new watched path: {path}")
            self.log_manager.info(f"Current watched paths: {self.settings.watched_paths}")
        else:
            self.log_manager.warning(f"Path already exists in watched paths: {path}")

    def remove_watched_path(self, path: str) -> None:
        """Remove a path from watch list."""
        expanded_path = os.path.expanduser(path)
        if expanded_path in self._settings.watched_paths:
            self._settings.watched_paths.remove(expanded_path)
            self.save_settings()

    def get_repository_paths(self) -> List[str]:
        """Get all repository paths from watched directories."""
        repo_paths = []

        for path in self._settings.watched_paths:
            expanded_path = os.path.expanduser(path)
            if not os.path.exists(expanded_path):
                continue

            # Check if the path itself is a git repository
            if is_git_repo(expanded_path):
                repo_paths.append(expanded_path)
            else:
                # Find git repositories under this path
                max_depth = self._settings.max_depth
                base_depth = len(Path(expanded_path).parts)

                for root, dirs, _ in os.walk(expanded_path):
                    # Skip hidden directories unless configured otherwise
                    if not self._settings.show_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]

                    # Check depth
                    current_depth = len(Path(root).parts) - base_depth
                    if current_depth > max_depth:
                        dirs.clear()  # Stop descending
                        continue

                    if ".git" in dirs:
                        repo_paths.append(root)
                        dirs.remove(".git")  # Don't descend into .git directories

        return sorted(set(repo_paths))  # Remove duplicates and sort

    def get_watched_paths(self) -> List[str]:
        """Get list of watched paths."""
        return self._settings.watched_paths

    def set_theme(self, theme: str) -> None:
        """Set the theme and save it."""
        if theme != self._settings.theme:  # Only update if theme actually changed
            self._settings.theme = theme
            self.save_settings()
            print(f"Theme saved: {theme}")  # Debug print to confirm saving
