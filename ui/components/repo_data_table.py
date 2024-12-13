from textual.widgets import DataTable
from textual.binding import Binding
from rich.text import Text
import os
import subprocess
from git_tasks.log_manager import LogManager
from git_tasks.status import RepoStatusLocal, SyncStatusType, SyncStatus


class RepoDataTable(DataTable):
    """Enhanced DataTable for repository management with enum-based status types."""

    BINDINGS = [
        *DataTable.BINDINGS,
        Binding("ctrl+g", "open_gitclient", "Open Git Client", show=True),
        Binding("ctrl+o", "open_editor", "Open Editor", show=True),
    ]

    # Define styles based on enum values
    REPO_STATUS_STYLES = {
        RepoStatusLocal.CLEAN: "green",
        RepoStatusLocal.DIRTY: "yellow",
        RepoStatusLocal.ERROR: "red italic",
        RepoStatusLocal.UNKNOWN: "white",
    }

    SYNC_STATUS_STYLES = {
        SyncStatusType.SYNCED: "bright_green",
        SyncStatusType.AHEAD: "yellow",
        SyncStatusType.BEHIND: "red",
        SyncStatusType.DIVERGED: "magenta",
        SyncStatusType.NO_REMOTE: "dim italic",
        SyncStatusType.NO_UPSTREAM: "dim italic",
        SyncStatusType.DISABLED_SSH: "dim italic",
        SyncStatusType.DISABLED_HTTPS: "dim italic",
        SyncStatusType.DISABLED_GENERAL: "dim italic",
        SyncStatusType.ERROR: "red italic",
        SyncStatusType.UNKNOWN: "white",
    }

    def __init__(self, log_manager: LogManager):
        super().__init__()
        self.log_manager = log_manager
        self.cursor_type = "row"

        self.add_columns("Repository", "Status", "Remote", "Sync Status", "Branch")

    def style_repo_status(self, status: RepoStatusLocal) -> Text:
        """Apply styling to repository status based on enum value."""
        style = self.REPO_STATUS_STYLES.get(
            status, self.REPO_STATUS_STYLES[RepoStatusLocal.UNKNOWN]
        )
        return Text(status.name.title(), style=style)

    def style_sync_status(self, status: SyncStatus) -> Text:
        """Apply styling to sync status based on enum value."""
        style = self.SYNC_STATUS_STYLES.get(
            status.type, self.SYNC_STATUS_STYLES[SyncStatusType.UNKNOWN]
        )
        return Text(str(status), style=style)

    def update_table(self, repos_data):
        """Update table with repository data using enum-based status values."""
        self.clear()
        self.log_manager.info(f"Updating table with data: {repos_data}")

        for repo_path, status, remote, sync_status, *rest in repos_data:
            # Style each column using the enum-based styling
            styled_path = Text(repo_path, style="bright_blue")
            styled_status = self.style_repo_status(status)
            styled_remote = Text(remote, style="cyan")
            styled_sync = self.style_sync_status(sync_status)

            self.add_row(
                styled_path,
                styled_status,
                styled_remote,
                styled_sync,
                rest[0] if rest else "",  # Branch column
            )

    def action_open_gitclient(self) -> None:
        """Open lazygit in the selected repository."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain

            self.log_manager.info(f"Opening lazygit for repository: {repo_path}")
            terminal_cmd = "kitty"  # TODO: Make configurable
            subprocess.Popen([terminal_cmd, "-e", "lazygit"], cwd=repo_path)

        except Exception as e:
            self.log_manager.error(f"Failed to open git client: {str(e)}")

    def action_open_editor(self) -> None:
        """Open the editor in the selected repository."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain

            editor = os.environ.get("EDITOR", "nvim")  # TODO: Make configurable
            self.log_manager.info(
                f"Opening editor ({editor}) for repository: {repo_path}"
            )

            terminal_cmd = "kitty"  # TODO: Make configurable
            subprocess.Popen([terminal_cmd, "-e", editor], cwd=repo_path)

        except Exception as e:
            self.log_manager.error(f"Failed to open editor: {str(e)}")
