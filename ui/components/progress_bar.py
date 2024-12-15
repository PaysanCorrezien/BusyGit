from textual.widgets import ProgressBar
from textual.reactive import reactive
from textual.widget import Widget


class RepoProgressBar(Widget):
    """Simple progress bar for repository operations."""

    DEFAULT_CSS = """
    RepoProgressBar {
        height: 1;
        margin: 0 1;
        padding: 0;
    }
    """

    def compose(self):
        yield ProgressBar()

    def start(self):
        """Start or reset the progress bar."""
        self.visible = True
        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(total=100, progress=0)

    def complete(self):
        """Complete and hide the progress bar."""
        self.visible = False

    def advance(self, current: int, total: int):
        """Update progress based on current/total values."""
        if total > 0:
            percentage = min((current / total) * 100, 100)
            self.query_one(ProgressBar).update(progress=percentage)
