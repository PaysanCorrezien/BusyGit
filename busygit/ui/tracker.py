from ..config.settings_manager import SettingsManager
from ..git_tasks.git_manager import GitManager
from .components.settings_view import (
    SettingsView,
)  # Note: single dot for same directory
from ..git_tasks.log_manager import LogManager
from .components.log_view import LogView
from ..git_tasks.git_manager import RefreshMode
from .components.repo_data_table_search import RepoDataTableSearch
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Tabs, Tab, Input
from textual.binding import Binding
from textual import work
from textual.message import Message


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

    RepoDataTableSearch {
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

        # Track the previous tab
        self._previous_tab = None

        self.log_manager.info("GitTrackerApp initialized with theme: %s", self.theme)

    # def compose(self) -> ComposeResult:
    #     yield Header()
    #     yield Tabs(
    #         Tab("Repositories", id="repositories"),
    #         Tab("Settings", id="settings"),
    #         Tab("Logs", id="logs"),
    #     )
    #     # Container for repositories tab
    #     with Container(id="repositories-content"):
    #         self.repo_table_search = RepoDataTableSearch(self.log_manager)
    #         yield self.repo_table_search
    #
    #     # Container for settings tab
    #     with Container(id="settings-content", classes="hide"):
    #         yield SettingsView(self.settings_manager, self.log_manager)
    #
    #     # Container for logs tab
    #     with Container(id="logs-content", classes="hide"):
    #         pass  # LogView will be added dynamically
    #
    #     yield Footer()
    def compose(self) -> ComposeResult:
        yield Header()
        yield Tabs(
            Tab("Repositories", id="repositories"),
            Tab("Settings", id="settings"),
            Tab("Logs", id="logs"),
        )
        # Container for repositories tab
        with Container(id="repositories-content"):
            self.repo_table_search = RepoDataTableSearch(
                log_manager=self.log_manager,
                settings_manager=self.settings_manager,  # Pass settings_manager here
            )
            yield self.repo_table_search

        # Container for settings tab
        with Container(id="settings-content", classes="hide"):
            yield SettingsView(self.settings_manager, self.log_manager)

        # Container for logs tab
        with Container(id="logs-content", classes="hide"):
            pass  # LogView will be added dynamically

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mounting"""
        self.log_manager.info("App mounted")
        # Start with repositories tab
        self.query_one(Tabs).active = "repositories"
        # Focus the table within the search component
        self.repo_table_search.focus_table()
        # Do initial load with SMART mode to populate cache
        self.load_initial_data()

    @work(thread=True)
    def load_initial_data(self):
        """Load initial repository data in background"""
        self.log_manager.info("Loading initial repository data.")
        # Use SMART mode for initial load to populate cache
        repos_data = self.git_manager.get_all_repositories(mode=RefreshMode.SMART)

        def update_ui():
            self.repo_table_search.update_table(repos_data)
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
            self.repo_table_search.focus()
            # If coming back from settings, we need to refresh to reflect any changes
            if event.tab.id == "repositories" and self._previous_tab == "settings":
                self.refresh_data(mode=RefreshMode.SMART)
            # Otherwise only refresh if we have no data
            elif not self.repo_table_search._raw_data:
                self.refresh_data(mode=RefreshMode.CACHED)

        # Update previous tab
        self._previous_tab = event.tab.id

    @work(thread=True)
    def refresh_data(self, mode: RefreshMode = RefreshMode.FULL):
        """Refresh repository data in background."""
        self.log_manager.info(
            f"Starting to refresh repository data (mode: {mode.name})"
        )

        # Show progress at start
        def start_progress():
            self.repo_table_search.show_progress(True)

        self.call_after_refresh(start_progress)

        # Progress update callback
        def update_progress(processed: int, total: int):
            def do_update():
                self.repo_table_search.show_progress(True, processed, total)

            self.call_after_refresh(do_update)

        # Load settings and get repositories with progress tracking
        self.settings_manager.load_settings()
        repos_data = self.git_manager.refresh_repositories(
            mode=mode, progress_callback=update_progress
        )

        # Update UI and complete progress
        def update_ui():
            self.repo_table_search.update_table(repos_data)
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
        self.refresh_data(mode=RefreshMode.SMART)

    def action_remove_path(self, path: str) -> None:
        """Remove a path from the settings and refresh the UI."""
        self.log_manager.info("Removing path: %s", path)
        self.settings_manager.remove_watched_path(path)
        self.refresh_data(mode=RefreshMode.SMART)

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

    def action_focus_search(self) -> None:
        """Focus the search input in the repository table"""
        self.repo_table_search.action_focus_search()


if __name__ == "__main__":
    app = GitTrackerApp()
    app.run()
