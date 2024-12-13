from textual.widgets import DataTable
from git_tasks.repo_status import RepoStatus
from git_tasks.log_manager import LogManager


class RepoDataTable(DataTable):
    def __init__(self, log_manager: LogManager):
        super().__init__()
        self.log_manager = log_manager
        self.add_columns("Repository", "Status", "Remote", "Sync Status", "Branch")

    def update_table(self, repos_data):
        """Update table with repository data"""
        self.clear()
        self.log_manager.info(f"Updating table with data: {repos_data}")
        for repo_path, status, remote, sync_status in repos_data:
            self.add_row(
                repo_path,
                status,
                remote,
                sync_status,
                "",  # Branch column (currently unused)
            )
