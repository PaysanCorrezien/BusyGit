from textual.widgets import DataTable
from textual.binding import Binding
from rich.text import Text
import sys
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
        Binding("ctrl+u", "open_remote_url", "Open Remote URL", show=True),
        Binding("k", "cursor_up", show=False),
        Binding("j", "cursor_down", show=False),
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

    async def _restore_ui(self) -> None:
        """Helper method to restore UI state after suspension."""
        # Force a refresh of the terminal
        self.app.refresh()
        # Ensure the screen is properly redrawn
        await self.app.screen.mount(self.app.screen)
        # Force a refresh of our data table
        self.refresh()

    async def _run_external_program(self, command: list[str], repo_path: str) -> None:
        """Helper method to run external program with proper UI handling."""
        try:
            # Clear input buffer and ensure terminal is in a clean state
            os.system("clear")

            # Suspend TUI and run the external program
            with self.app.suspend():
                # Use TERM=xterm-256color for better compatibility
                env = os.environ.copy()
                env["TERM"] = "xterm-256color"

                subprocess.run(
                    command,
                    cwd=repo_path,
                    env=env,
                    # Ensure proper terminal handling
                    stdin=subprocess.DEVNULL if command[0] == "lazygit" else None,
                )

            # Small delay to ensure terminal is ready
            await self.app.sleep(0.1)

            # Restore UI state
            await self._restore_ui()

        except Exception as e:
            self.log_manager.error(f"Failed to run {command[0]}: {str(e)}")
            # Still try to restore UI in case of error
            await self._restore_ui()

    def _convert_ssh_to_https_url(self, remote_url: str) -> str:
        """Convert SSH git URL to HTTPS URL."""
        if not remote_url or "Error" in remote_url or "No remote" in remote_url:
            return ""

        # Handle ssh:// format
        if remote_url.startswith("ssh://"):
            # Remove ssh:// and replace : with /
            url = remote_url.replace("ssh://", "")
            if "@" in url:
                # Remove user@ part
                url = url.split("@", 1)[1]
            return f"https://{url}"

        # Handle git@ format
        if remote_url.startswith("git@"):
            # Convert git@github.com:user/repo.git to https://github.com/user/repo
            url = remote_url.replace("git@", "")
            url = url.replace(":", "/")
            return f"https://{url}"

        # If it's already https, return as is
        if remote_url.startswith("https://"):
            return remote_url

        return ""

    async def action_open_remote_url(self) -> None:
        """Open the remote repository URL in default browser."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            remote_url = self.get_row(row_key)[2].plain

            https_url = self._convert_ssh_to_https_url(remote_url)
            if not https_url:
                self.log_manager.warning(f"No valid remote URL found: {remote_url}")
                return

            # Clean up the URL (remove .git suffix if present)
            https_url = https_url.rstrip(".git")

            self.log_manager.info(f"Opening remote URL: {https_url}")

            # Use xdg-open on Linux, start on Windows, or open on macOS
            if os.name == "nt":
                os.startfile(https_url)
            elif sys.platform == "darwin":
                subprocess.run(["open", https_url])
            else:
                subprocess.run(["xdg-open", https_url])

        except Exception as e:
            self.log_manager.error(f"Failed to open remote URL: {str(e)}")

    async def action_open_gitclient(self) -> None:
        """Open lazygit in the current terminal, blocking until closed."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain
            self.log_manager.info(f"Opening lazygit for repository: {repo_path}")
            await self._run_external_program(["lazygit"], repo_path)
        except Exception as e:
            self.log_manager.error(f"Failed to open git client: {str(e)}")

    async def action_open_editor(self) -> None:
        """Open the editor in the current terminal, blocking until closed."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain
            editor = os.environ.get("EDITOR", "nvim")
            self.log_manager.info(
                f"Opening editor ({editor}) for repository: {repo_path}"
            )
            await self._run_external_program([editor], repo_path)
        except Exception as e:
            self.log_manager.error(f"Failed to open editor: {str(e)}")
