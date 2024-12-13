from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Header, Input, Footer, Tabs, Tab
from textual.binding import Binding
from textual import work
from config.settings_manager import SettingsManager
from git_tasks.git_manager import GitManager
from git_tasks import RepoStatus
from ui.components.settings_view import SettingsView
from ui.toast_app import ToastApp
from textual.message import Message
from textual import events
from ui.components.repo_data_table import RepoDataTable
from git_tasks.log_manager import LogManager
from ui.components.log_view import LogView
from git_tasks.git_manager import RefreshMode


class ThemeChanged(Message):
    """Message sent when theme changes."""

    def __init__(self, theme: str) -> None:
        self.theme = theme
        super().__init__()


class GitTrackerApp(App):
    CSS = """
    Tabs {
        dock: top;
    }

    DataTable {
        height: 1fr;
        margin: 1 0;
    }

    #repositories-content,
    #settings-content,
    #logs-content {
        height: 1fr;
    }

    .hide {
        display: none;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f", "focus_search", "Search", show=True),
        Binding("p", "focus_path", "Add Path", show=True),
        Binding("ctrl+b", "focus_repositories", "Back to Repositories", show=True),
        Binding("ctrl+d", "focus_logs", "View Logs", show=True),
        ("ctrl+c", "quit", "Quit"),
        Binding("t", "toggle_theme", "Toggle Theme", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.log_manager = LogManager()
        self.git_manager = GitManager(
            settings_manager=self.settings_manager, log_manager=self.log_manager
        )

        # Load initial theme
        initial_theme = self.settings_manager.settings.theme or "tokyo-night"
        self.dark = "dark" in initial_theme.lower()
        self.theme = initial_theme

        # Initialize log view
        self.log_view = None

        # Do an initial repository scan in background after app is mounted
        self.log_manager.info("GitTrackerApp initialized with theme: %s", self.theme)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tabs(
            Tab("Repositories", id="repositories"),
            Tab("Settings", id="settings"),
            Tab("Logs", id="logs"),
        )
        # Container for repositories tab
        with Container(id="repositories-content"):
            self.repo_data_table = RepoDataTable(self.log_manager)
            yield self.repo_data_table
            yield Input(placeholder="Search repositories...", id="search")

        # Container for settings tab
        with Container(id="settings-content", classes="hide"):
            yield SettingsView(self.settings_manager, self.log_manager)

        # Container for logs tab
        with Container(id="logs-content", classes="hide"):
            pass  # LogView will be added dynamically

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mounting"""
        self.repo_data_table.focus()
        self.log_manager.info("App mounted, focusing on repository data table.")
        # Only call load_initial_data, not refresh_data
        self.load_initial_data()

    @work(thread=True)
    def load_initial_data(self):
        """Load initial repository data in background"""
        self.log_manager.info("Loading initial repository data.")
        repos_data = self.git_manager.get_all_repositories()

        def update_ui():
            self.repo_data_table.update_table(repos_data)
            self.log_manager.info("Initial repository data loaded successfully.")

        self.call_after_refresh(update_ui)

    def handle_theme_change(self, theme: str) -> None:
        """Handle theme changes"""
        self.settings_manager.set_theme(theme)
        self.post_message(ThemeChanged(theme))
        self.notify(f"Theme changed to: {theme}")

    def action_toggle_theme(self) -> None:
        """Toggle between built-in Textual themes"""
        themes = ["tokyo-night", "dracula", "monokai", "nord"]
        try:
            current_index = themes.index(self.theme)
            next_index = (current_index + 1) % len(themes)
        except ValueError:
            next_index = 0

        new_theme = themes[next_index]
        self.theme = new_theme
        self.call_after_refresh(self.handle_theme_change, new_theme)

    def on_theme_changed(self, event: ThemeChanged) -> None:
        """Handle theme changed messages"""
        self.theme = event.theme
        self.settings_manager.set_theme(event.theme)

    def on_app_theme_changed(self, event) -> None:
        """Handle Textual's built-in theme changes from command palette"""
        self.settings_manager.set_theme(event.theme)
        self.notify(f"Theme changed to: {event.theme}")

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching"""
        self.log_manager.info("Tab activated: %s", event.tab.id)
        # Get all content containers
        repos_content = self.query_one("#repositories-content")
        settings_content = self.query_one("#settings-content")
        logs_content = self.query_one("#logs-content")

        # Hide all containers first
        repos_content.add_class("hide")
        settings_content.add_class("hide")
        logs_content.add_class("hide")

        # Show and focus appropriate container
        if event.tab.id == "settings":
            settings_content.remove_class("hide")
            settings_content.query_one(Input).focus()
        elif event.tab.id == "logs":
            logs_content.remove_class("hide")
            if self.log_view is None:
                self.log_view = LogView(self.log_manager)
                logs_content.mount(self.log_view)
            self.log_view.load_logs()
            self.log_view.focus()
        else:  # repositories tab
            repos_content.remove_class("hide")
            self.repo_data_table.focus()
            # Use cached refresh when switching back to repositories
            self.refresh_data(mode=RefreshMode.CACHED)

    @work(thread=True)
    def refresh_data(self, mode: RefreshMode = RefreshMode.FULL):
        """
        Refresh repository data in background

        Args:
            mode: RefreshMode determining refresh type:
                CACHED - Use cached data (for UI updates)
                SMART - Check local changes but use cached remote status
                FULL - Complete refresh (default for manual refresh)
        """
        self.log_manager.info(
            f"Starting to refresh repository data (mode: {mode.name})"
        )

        # Force reload settings before getting repositories
        self.settings_manager.load_settings()
        self.log_manager.info("Settings reloaded.")

        # Fetch the latest repository data with specified mode
        repos_data = self.git_manager.refresh_repositories(mode=mode)
        self.log_manager.info(f"Retrieved repository data with mode {mode.name}")

        def update_ui():
            self.repo_data_table.clear()
            self.repo_data_table.update_table(repos_data)
            self.notify(f"{mode.name} refresh complete!")
            self.log_manager.info("UI updated with new repository data.")

        self.call_after_refresh(update_ui)

    def action_refresh(self):
        """Handle manual refresh (R key) - always do full refresh"""
        self.log_manager.info("Manual refresh requested - doing full refresh...")
        self.refresh_data(mode=RefreshMode.FULL)

    def action_add_path(self, path: str) -> None:
        """Add a new path and refresh the repository data"""
        self.log_manager.info("Adding new path: %s", path)
        self.git_manager.add_watched_path(path)
        self.settings_manager.load_settings()
        self.log_manager.info("Path added, starting smart refresh")
        self.refresh_data(mode=RefreshMode.SMART)  # Smart refresh for path changes

    def action_remove_path(self, path: str) -> None:
        """Remove a path from the settings and refresh the UI."""
        self.log_manager.info("Removing path: %s", path)
        self.settings_manager.remove_watched_path(path)
        self.refresh_data(mode=RefreshMode.SMART)  # Smart refresh for path changes

    def action_focus_path(self) -> None:
        """Switch to settings tab when 'p' is pressed"""
        tabs = self.query_one(Tabs)
        tabs.active = "settings"

    def action_focus_repositories(self) -> None:
        """Switch back to repositories tab when 'ctrl+b' is pressed"""
        tabs = self.query_one(Tabs)
        tabs.active = "repositories"

    def action_focus_logs(self) -> None:
        """Switch to logs tab when 'ctrl+d' is pressed"""
        tabs = self.query_one(Tabs)
        tabs.active = "logs"

    def action_focus_search(self):
        self.query_one("#search").focus()


if __name__ == "__main__":
    app = GitTrackerApp()
    app.run()