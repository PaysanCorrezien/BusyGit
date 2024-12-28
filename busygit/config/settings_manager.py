import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from .settings import Settings, CommandConfig, BindingConfig

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages application settings with file persistence."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.expanduser(
            "~/.config/busygit/config.json"
        )
        self.settings = Settings()  # Start with defaults from Settings class
        self.load_settings()

    def load_settings(self) -> None:
        """Load settings from file, overriding defaults where specified."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config_data = json.load(f)

                    # Handle command configurations
                    if "commands" in config_data:
                        config_data["commands"] = {
                            k: CommandConfig(**v) if isinstance(v, dict) else v
                            for k, v in config_data["commands"].items()
                        }

                    # Handle custom key bindings
                    if "bindings" in config_data:
                        # Convert dictionary values to BindingConfig objects
                        custom_bindings = {}
                        for action, binding_data in config_data["bindings"].items():
                            if isinstance(binding_data, dict):
                                custom_bindings[action] = BindingConfig(**binding_data)
                            else:
                                custom_bindings[action] = binding_data
                        self.settings.custom_bindings = custom_bindings

                    # Update settings with config file values
                    for key, value in config_data.items():
                        if hasattr(self.settings, key) and key != "bindings":
                            setattr(self.settings, key, value)

                logger.info(f"Settings loaded from {self.config_path}")
            else:
                self.save_settings()  # Save defaults if no config exists
                logger.info("Default settings created")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Keep defaults if loading fails

    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Prepare settings dict
            settings_dict = {}
            for field in self.settings.__dataclass_fields__:
                if field != "BINDINGS":  # Skip the bindings property
                    value = getattr(self.settings, field)
                    if field == "custom_bindings":
                        # Convert BindingConfig objects to dictionaries
                        settings_dict["bindings"] = {
                            k: vars(v) if isinstance(v, BindingConfig) else v
                            for k, v in value.items()
                        }
                    else:
                        settings_dict[field] = value

            with open(self.config_path, "w") as f:
                json.dump(settings_dict, f, indent=2, default=lambda x: vars(x))

            logger.info(f"Settings saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get_watched_paths(self) -> List[str]:
        """Get list of watched paths."""
        return self.settings.watched_paths

    def add_watched_path(self, path: str) -> None:
        """Add a new path to watch."""
        if path not in self.settings.watched_paths:
            self.settings.watched_paths.append(path)
            self.save_settings()

    def remove_watched_path(self, path: str) -> None:
        """Remove a path from watch list."""
        if path in self.settings.watched_paths:
            self.settings.watched_paths.remove(path)
            self.save_settings()

    def set_theme(self, theme: str) -> None:
        """Set the UI theme."""
        self.settings.theme = theme
        self.save_settings()

    def update_settings(self, **kwargs) -> None:
        """Update multiple settings at once."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save_settings()

    def get_binding_key(self, component: str, action: str) -> str:
        """Get the key binding for a specific component and action.

        Args:
            component: The component identifier (e.g., 'repo_table')
            action: The action identifier (e.g., 'cursor_up')

        Returns:
            str: The key binding (e.g., 'k' or 'ctrl+g')
        """
        # First check custom bindings
        binding_config = self.settings.get_binding(action)
        if binding_config and binding_config.component == component:
            return binding_config.key

        # Fall back to default bindings if no custom binding found
        defaults = {
            "repo_table": {
                "cursor_up": "k",
                "cursor_down": "j",
                "open_gitclient": "ctrl+g",
                "open_editor": "ctrl+o",
                "open_remote_url": "ctrl+u",
            },
            "repo_table_search": {
                "focus_search": "f",
            },
        }

        return defaults.get(component, {}).get(action, "")
