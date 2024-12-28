from textual.widgets import RichLog
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual import work
import asyncio


class LogView(RichLog):
    """Enhanced log view with auto-refresh and better scrolling."""

    BINDINGS = [
        Binding("gg", "scroll_to_top", "Top"),
        Binding("G", "scroll_to_bottom", "Bottom"),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear", "Clear"),
    ]

    class LogCleared(Message):
        """Sent when logs are cleared."""

    def __init__(self, log_manager, settings_manager=None):
        super().__init__(
            highlight=True, markup=True, wrap=True, min_width=80, max_lines=1000
        )
        self.log_manager = log_manager
        self.settings_manager = settings_manager
        self._refresh_timer = None

    def on_mount(self) -> None:
        """Set up the log view when mounted."""
        self.load_logs()
        self._setup_refresh_timer()

    def _setup_refresh_timer(self) -> None:
        """Set up the refresh timer based on settings."""
        if self.settings_manager:
            interval = self.settings_manager.settings.auto_refresh_interval
        else:
            interval = 1.0  # Default to 1 second if no settings manager

        async def refresh_timer():
            while True:
                await asyncio.sleep(interval)
                await self.app.call_from_thread(self.refresh_logs)

        self._refresh_timer = asyncio.create_task(refresh_timer())

    def refresh_logs(self) -> None:
        """Refresh the logs content."""
        self.load_logs()

    @work(thread=True)
    def load_logs(self):
        """Load logs into the component."""
        logs = self.log_manager.read_logs()

        def update_logs():
            self.clear()
            self.write(logs)
            if self.auto_scroll:
                self.scroll_end()

        self.call_after_refresh(update_logs)

    def action_refresh(self):
        """Manually refresh the log view."""
        self.refresh_logs()

    def action_clear(self):
        """Clear the logs."""
        self.log_manager.clear_logs()
        self.clear()
        self.post_message(self.LogCleared())

    def action_scroll_to_top(self):
        """Scroll to the top of the logs."""
        self.scroll_home()

    def action_scroll_to_bottom(self):
        """Scroll to the bottom of the logs."""
        self.scroll_end()

    def on_unmount(self) -> None:
        """Clean up when unmounted."""
        if self._refresh_timer:
            self._refresh_timer.cancel()
