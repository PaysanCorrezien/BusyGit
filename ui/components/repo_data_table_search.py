from textual.widgets import Input, Static
from textual.containers import Container
from textual.binding import Binding
from textual.message import Message
from textual import on

from git_tasks.log_manager import LogManager
from .repo_data_table import RepoDataTable


class RepoDataTableSearch(Container):
    """A component combining repository table with search functionality."""

    DEFAULT_CSS = """
    RepoDataTableSearch {
        width: 100%;
        height: 100%;
    }

    #search {
        dock: top;
        margin: 1 1;
        border: solid $primary;
        background: $boost;
    }

    RepoDataTable {
        height: 1fr;
    }
    """

    class SearchChanged(Message):
        """Search text has changed."""

        def __init__(self, search_text: str) -> None:
            self.search_text = search_text
            super().__init__()

    def __init__(self, log_manager: LogManager, settings_manager=None):
        super().__init__()
        self.log_manager = log_manager
        self.settings_manager = settings_manager
        self._raw_data = []  # Store the unfiltered data
        self.search_text = ""

    def compose(self):
        """Create child widgets."""
        yield Input(placeholder="Search repositories...", id="search")
        yield RepoDataTable(
            log_manager=self.log_manager, settings_manager=self.settings_manager
        )

    def on_mount(self):
        """Handle mount event."""
        self.query_one(RepoDataTable).focus()
        # Set up bindings if settings manager is available
        if self.settings_manager:
            self.bindings = [
                Binding(
                    self.settings_manager.get_binding_key("repo_table_search", action),
                    action,
                    description,
                    show=show,
                )
                for key, action, description, show in [
                    ("f", "focus_search", "Search", True),
                ]
            ]

    def focus_table(self) -> None:
        """Focus the data table explicitly."""
        self.query_one(RepoDataTable).focus()

    @on(Input.Changed, "#search")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        self.search_text = event.value.strip().lower()
        self._apply_filter()
        self.post_message(self.SearchChanged(self.search_text))

    def _apply_filter(self) -> None:
        """Apply the current search filter to the data."""
        table = self.query_one(RepoDataTable)

        if not self.search_text:
            # If search is empty, show all data
            filtered_data = self._raw_data
        else:
            # Filter data based on repository path and remote URL
            filtered_data = [
                row
                for row in self._raw_data
                if self.search_text in str(row[0]).lower()  # Repository path
                or self.search_text in str(row[2]).lower()  # Remote URL
            ]

        # Update the table with filtered data
        table.update_table(filtered_data)

        # Move cursor to first result if we have results
        if filtered_data:
            table.cursor_coordinate = (0, 0)  # Select first row

    async def _handle_shortcut_action(self, action_name: str) -> None:
        """Handle shortcut actions when in search."""
        table = self.query_one(RepoDataTable)
        if self.query_one("#search").has_focus and table.row_count > 0:
            # Ensure first row is selected
            table.cursor_coordinate = (0, 0)
            # Get the action method
            action = getattr(table, f"action_{action_name}")
            # Call the action
            await action()
        else:
            # Forward to table's action directly
            action = getattr(table, f"action_{action_name}")
            await action()

    def update_table(self, repos_data):
        """Update table with new repository data."""
        # Store the raw data
        self._raw_data = repos_data
        # Apply current filter
        self._apply_filter()

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search").focus()

    async def action_open_gitclient(self) -> None:
        """Handle git client action, considering search context."""
        await self._handle_shortcut_action("open_gitclient")

    async def action_open_editor(self) -> None:
        """Handle editor action, considering search context."""
        await self._handle_shortcut_action("open_editor")

    async def action_open_remote_url(self) -> None:
        """Handle remote URL action, considering search context."""
        await self._handle_shortcut_action("open_remote_url")
