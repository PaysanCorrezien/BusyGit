from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
from textual.binding import Binding


@dataclass
class CommandConfig:
    """Configuration for external commands."""

    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class BindingConfig:
    """Configuration for a key binding."""

    key: str
    description: Optional[str]
    show: bool = True
    component: str = "default"  # Which UI component this binding belongs to


@dataclass
class Settings:
    """Application settings with default values."""

    watched_paths: List[str] = field(default_factory=list)
    auto_refresh_interval: int = 300
    max_depth: int = 3
    show_hidden: bool = False
    theme: str = "tokyo-night"
    use_ssh_agent: bool = True
    fetch_https_status: bool = False
    remote_cache_timeout: int = 120

    # Command configurations with defaults
    commands: Dict[str, CommandConfig] = field(
        default_factory=lambda: {
            "editor": CommandConfig(
                command=os.environ.get("EDITOR", "nvim"),
            ),
            "git_client": CommandConfig(
                command="lazygit",
            ),
        }
    )

    # Custom bindings that override defaults
    custom_bindings: Dict[str, BindingConfig] = field(default_factory=dict)

    def get_command(self, command_type: str) -> CommandConfig:
        """Get command configuration for a specific command type.

        Args:
            command_type: Type of command ('editor' or 'git_client')

        Returns:
            CommandConfig object with command settings

        Raises:
            ValueError if command_type is not recognized
        """
        if command_type not in self.commands:
            raise ValueError(f"Unknown command type: {command_type}")
        return self.commands[command_type]

    @staticmethod
    def default_bindings() -> Dict[str, BindingConfig]:
        """Define all default bindings for different components."""
        return {
            # Repository table bindings
            "open_gitclient": BindingConfig(
                "ctrl+g", "Open Git Client", True, "repo_table"
            ),
            "open_editor": BindingConfig("ctrl+o", "Open Editor", True, "repo_table"),
            "open_remote_url": BindingConfig(
                "ctrl+u", "Open Remote URL", True, "repo_table"
            ),
            "focus_search": BindingConfig("f", "Search", True, "repo_table"),
            "cursor_up": BindingConfig("k", None, False, "repo_table"),
            "cursor_down": BindingConfig("l", None, False, "repo_table"),
            # Log view bindings
            "clear_logs": BindingConfig("ctrl+l", "Clear Logs", True, "log_view"),
            "export_logs": BindingConfig("ctrl+e", "Export Logs", True, "log_view"),
            # Global bindings
            "quit": BindingConfig("q", "Quit", True, "global"),
            "refresh": BindingConfig("r", "Refresh", True, "global"),
            "toggle_theme": BindingConfig("t", "Toggle Theme", True, "global"),
        }

    def get_binding(self, action: str) -> Optional[BindingConfig]:
        """Get a binding configuration for an action, with custom override if exists."""
        # Check custom bindings first
        if action in self.custom_bindings:
            return self.custom_bindings[action]

        # Fall back to defaults
        return self.default_bindings().get(action)

    def get_component_bindings(self, component: str) -> List[Binding]:
        """Get all bindings for a specific component."""
        bindings = []
        all_defaults = self.default_bindings()

        # Collect all bindings for this component
        for action, default_binding in all_defaults.items():
            if default_binding.component == component:
                # Get the actual binding (possibly customized)
                binding_config = self.get_binding(action)
                if binding_config:
                    bindings.append(
                        Binding(
                            binding_config.key,
                            action,
                            binding_config.description,
                            show=binding_config.show,
                        )
                    )

        return bindings

    def override_binding(
        self,
        action: str,
        key: str,
        description: Optional[str] = None,
        show: bool = True,
    ):
        """Override a binding configuration."""
        default = self.default_bindings().get(action)
        if default:
            self.custom_bindings[action] = BindingConfig(
                key=key,
                description=description or default.description,
                show=show,
                component=default.component,
            )
