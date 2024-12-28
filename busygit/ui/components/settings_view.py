from textual.widgets import Static, Input, ListView, ListItem
from textual.containers import Container, Vertical, ScrollableContainer
from textual.validation import Validator
from textual.message import Message
from textual import on, events
from textual.binding import Binding
from textual.reactive import reactive
import os

from .path_input import PathValidator


class PathList(ListView):
    DEFAULT_CSS = """
    PathList {
        height: 1fr;  /* Take remaining space */
        border: solid $primary;
        padding: 1;
        margin: 1;
    }

    PathList > ListItem {
        padding: 1;
    }

    PathList > ListItem:hover {
        background: $accent;
    }
    """

    BINDINGS = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("up", "cursor_up", "Cursor up", show=False),
        Binding("down", "cursor_down", "Cursor down", show=False),
        Binding("d", "remove_selected", "Remove Selected Path", show=True),
    ]

    paths = reactive([])

    def add_path(self, path: str) -> None:
        """Add a path as a ListItem."""
        item = ListItem(Static(path))
        self.append(item)

    def watch_paths(self, new_paths: list) -> None:
        """React to changes in the paths list."""
        self.clear()
        for path in new_paths:
            self.add_path(path)
        # If we have paths, highlight the first one
        if self.children:
            self.index = 0  # Set highlight to first item

    def on_mount(self) -> None:
        """Handle component mounting."""
        # If we have items, highlight the first one
        if self.children:
            self.index = 0  # Set highlight to first item

    def action_remove_selected(self) -> None:
        """Remove the currently selected item."""
        selected_item = self.highlighted_child
        if selected_item:
            path = selected_item.children[0].renderable
            self.app.log_manager.info(f"Key 'd' pressed for removal of: {path}")
            # Find the SettingsView parent
            current = self
            while current and not isinstance(current, SettingsView):
                current = current.parent
            if current:
                current.remove_path(path)


class SettingsView(Container):
    DEFAULT_CSS = """
    SettingsView {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    .section-title {
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $accent;
    }

    .path-input-container {
        height: auto;
        margin: 1;
    }

    Input {
        margin: 1;
    }

    .validation-message {
        color: $error;
        margin: 1;
        text-align: center;
    }

    ScrollableContainer {
        height: 1fr;
        border: solid $primary;
    }
    """

    # Reactive property for watched paths
    watched_paths = reactive([])

    def __init__(self, settings_manager, log_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.log_manager = log_manager
        self.input = Input(
            placeholder="Enter path to track...",
            validators=[PathValidator()],
        )

    def compose(self):
        """Create child widgets."""
        with Vertical():
            yield Static("Managed Paths", classes="section-title")
            with Container(classes="path-input-container"):
                yield self.input
                yield Static(classes="validation-message")
            yield PathList()

    def on_mount(self) -> None:
        """Handle component mounting."""
        self.reload_paths()
        self.query_one(PathList).focus()

    def reload_paths(self) -> None:
        """Reload paths from settings and update UI."""
        paths = self.settings_manager.get_watched_paths()
        self.watched_paths = paths
        path_list = self.query_one(PathList)
        path_list.paths = paths
        self.log_manager.info(f"Paths reloaded: {paths}")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input validation."""
        message = self.query_one(".validation-message")
        if not event.validation_result.is_valid:
            message.update("\n".join(event.validation_result.failure_descriptions))
        else:
            message.update("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle new path submission."""
        if event.validation_result.is_valid:
            path = os.path.expanduser(event.value.strip())
            self.add_path(path)
            self.input.value = ""

    def add_path(self, path: str) -> None:
        """Add a new path to watch."""
        self.log_manager.info(f"Adding path: {path}")
        self.settings_manager.add_watched_path(path)
        self.reload_paths()
        # Trigger app-level refresh
        self.app.refresh_data()

    def remove_path(self, path: str) -> None:
        """Remove a path from watch list."""
        self.log_manager.info(f"Removing path: {path}")
        self.settings_manager.remove_watched_path(path)
        self.reload_paths()
        # Trigger app-level refresh
        self.app.refresh_data()

    def watch_watched_paths(self, paths: list) -> None:
        """React to changes in watched paths."""
        self.log_manager.info(f"Watched paths updated: {paths}")
        path_list = self.query_one(PathList)
        path_list.paths = paths.copy()  # Use copy to ensure change detection
