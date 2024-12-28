from textual.widgets import DataTable
from textual.binding import Binding
from rich.text import Text
import sys
import os
import subprocess
from ...git_tasks.log_manager import LogManager
from ...git_tasks.status import RepoStatusLocal, SyncStatusType, SyncStatus
from ...git_tasks.remote_convert import RemoteConverter


class RepoDataTable(DataTable):
    """Enhanced DataTable for repository management with enum-based status types."""

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

    def __init__(self, log_manager: LogManager, settings_manager=None):
        super().__init__()
        self.log_manager = log_manager
        self.settings_manager = settings_manager
        self.cursor_type = "row"
        self.add_columns("Repository", "Status", "Remote", "Sync Status", "Branch")

    # Default bindings
    BINDINGS = [
        Binding("ctrl+g", "open_gitclient", "Open Git Client", show=True),
        Binding("ctrl+o", "open_editor", "Open Editor", show=True),
        Binding("ctrl+u", "open_remote_url", "Open Remote URL", show=True),
        Binding("ctrl+r", "convert_remote_url", "Convert Remote URL", show=True),
        Binding("k", "cursor_up", show=False),
        Binding("j", "cursor_down", show=False),
    ]

    def on_mount(self):
        """Set up bindings from settings."""
        if self.settings_manager:
            # Create new bindings list from settings
            self.bindings = [
                Binding(
                    self.settings_manager.get_binding_key("repo_table", b.action),
                    b.action,
                    b.description,
                    show=b.show,
                )
                for b in self.BINDINGS
            ]

    # Rest of the class remains the same...
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

        for repo_path, status, remote, sync_status, branch in repos_data:
            styled_path = Text(repo_path, style="bright_blue")
            styled_status = self.style_repo_status(status)
            styled_remote = Text(remote, style="cyan")
            styled_sync = self.style_sync_status(sync_status)
            styled_branch = Text(branch if branch else "", style="bright_magenta")

            self.add_row(
                styled_path,
                styled_status,
                styled_remote,
                styled_sync,
                styled_branch,
            )

    async def action_open_remote_url(self) -> None:
        """Open the remote repository URL in default browser."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            remote_url = self.get_row(row_key)[2].plain

            https_url = self._convert_ssh_to_https_url(remote_url)
            if not https_url:
                self.log_manager.warning(f"No valid remote URL found: {remote_url}")
                return

            https_url = https_url.rstrip(".git")
            self.log_manager.info(f"Opening remote URL: {https_url}")

            if os.name == "nt":
                os.startfile(https_url)
            elif sys.platform == "darwin":
                subprocess.run(["open", https_url])
            else:
                subprocess.run(["xdg-open", https_url])

        except Exception as e:
            self.log_manager.error(f"Failed to open remote URL: {str(e)}")

    async def action_open_gitclient(self) -> None:
        """Open git client in the current terminal, blocking until closed."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain
            self.log_manager.info(f"Opening git client for repository: {repo_path}")
            await self._run_external_program("git_client", repo_path)
        except Exception as e:
            self.log_manager.error(f"Failed to open git client: {str(e)}")

    async def action_open_editor(self) -> None:
        """Open the configured editor in the current terminal, blocking until closed."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain
            self.log_manager.info(f"Opening editor for repository: {repo_path}")
            await self._run_external_program("editor", repo_path)
        except Exception as e:
            self.log_manager.error(f"Failed to open editor: {str(e)}")

    async def _run_external_program(self, command_type: str, repo_path: str) -> None:
        """Helper method to run external program with proper UI handling."""
        try:
            os.system("clear")

            cmd_config = self.settings_manager.settings.get_command(command_type)
            command = [cmd_config.command] + cmd_config.args

            with self.app.suspend():
                env = os.environ.copy()
                env.update(cmd_config.env)
                env["TERM"] = "xterm-256color"

                subprocess.run(
                    command,
                    cwd=repo_path,
                    env=env,
                    stdin=subprocess.DEVNULL if command_type == "git_client" else None,
                )

            await self.app.sleep(0.1)
            await self._restore_ui()

        except Exception as e:
            self.log_manager.error(f"Failed to run {command_type}: {str(e)}")
            await self._restore_ui()

    async def _restore_ui(self) -> None:
        """Helper method to restore UI state after suspension."""
        self.app.refresh()
        await self.app.screen.mount(self.app.screen)
        self.refresh()

    def _convert_ssh_to_https_url(self, remote_url: str) -> str:
        """Convert SSH git URL to HTTPS URL."""
        if not remote_url or "Error" in remote_url or "No remote" in remote_url:
            return ""

        if remote_url.startswith("ssh://"):
            url = remote_url.replace("ssh://", "")
            if "@" in url:
                url = url.split("@", 1)[1]
            return f"https://{url}"

        if remote_url.startswith("git@"):
            url = remote_url.replace("git@", "")
            url = url.replace(":", "/")
            return f"https://{url}"

        if remote_url.startswith("https://"):
            return remote_url

        return ""

    async def action_convert_remote_url(self) -> None:
        """Convert the remote URL between HTTPS and SSH formats."""
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            repo_path = self.get_row(row_key)[0].plain
            current_url = self.get_row(row_key)[2].plain

            # Initialize converter
            converter = RemoteConverter(self.log_manager)

            # Convert URL
            new_url = converter.convert_url(current_url)
            if not new_url:
                return

            # Update remote URL
            if converter.update_remote_url(repo_path, new_url):
                # Refresh the data to show the new URL
                self.app.refresh_data()
                self.notify(f"{repo_path} updated to {new_url} !")

        except Exception as e:
            self.log_manager.error(f"Error converting remote URL: {str(e)}")
