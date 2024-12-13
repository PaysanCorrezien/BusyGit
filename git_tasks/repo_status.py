from git import Repo, InvalidGitRepositoryError, NoSuchPathError
import os
from typing import List, Tuple, Optional
from pathlib import Path
from urllib.parse import urlparse
from .status import RepoStatusLocal, SyncStatus, SyncStatusType


class RepoStatus:
    """Class to handle Git repository status using enum-based status types."""

    def __init__(
        self,
        repo_path: str,
        use_ssh_agent: bool = True,
        fetch_https_status: bool = False,
    ):
        self.repo_path = repo_path
        self.use_ssh_agent = use_ssh_agent
        self.fetch_https_status = fetch_https_status
        try:
            self.repo = Repo(repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise ValueError(f"Invalid git repository at {repo_path}: {str(e)}")

    def is_remote_url_ssh(self, url: str) -> bool:
        """Check if the remote URL is SSH."""
        return url.startswith(("git@", "ssh://"))

    def should_check_remote_status(self, remote_url: str) -> bool:
        """Determine if we should check remote status based on URL type and settings."""
        if not remote_url or remote_url == "No remote configured":
            return False

        is_ssh = self.is_remote_url_ssh(remote_url)
        return (is_ssh and self.use_ssh_agent) or (
            not is_ssh and self.fetch_https_status
        )

    @property
    def repo_status(self) -> RepoStatusLocal:
        """Get repository status as enum."""
        try:
            if self.repo.is_dirty(untracked_files=True):
                return RepoStatusLocal.DIRTY
            return RepoStatusLocal.CLEAN
        except Exception as e:
            return RepoStatusLocal.ERROR

    @property
    def remote_url(self) -> str:
        """Get remote URL if available."""
        try:
            if not self.repo.remotes:
                return "No remote configured"
            return self.repo.remotes.origin.url
        except Exception as e:
            return f"Error: {str(e)}"

    @property
    def current_branch(self) -> str:
        """Get current branch name."""
        try:
            return self.repo.active_branch.name
        except Exception as e:
            return f"Error: {str(e)}"

    def get_sync_status(self) -> SyncStatus:
        """Get synchronization status with remote using SyncStatus object."""
        try:
            if not self.repo.remotes:
                return SyncStatus(type=SyncStatusType.NO_REMOTE)

            remote_url = self.remote_url
            if not self.should_check_remote_status(remote_url):
                is_ssh = self.is_remote_url_ssh(remote_url)
                if is_ssh and not self.use_ssh_agent:
                    return SyncStatus(type=SyncStatusType.DISABLED_SSH)
                elif not is_ssh and not self.fetch_https_status:
                    return SyncStatus(type=SyncStatusType.DISABLED_HTTPS)
                return SyncStatus(type=SyncStatusType.DISABLED_GENERAL)

            origin = self.repo.remotes.origin
            origin.fetch()

            active_branch = self.repo.active_branch
            tracking_branch = active_branch.tracking_branch()

            if not tracking_branch:
                return SyncStatus(type=SyncStatusType.NO_UPSTREAM)

            commits_behind = list(
                self.repo.iter_commits(f"{active_branch.name}..{tracking_branch.name}")
            )
            commits_ahead = list(
                self.repo.iter_commits(f"{tracking_branch.name}..{active_branch.name}")
            )

            ahead_count = len(commits_ahead)
            behind_count = len(commits_behind)

            if ahead_count == 0 and behind_count == 0:
                return SyncStatus(type=SyncStatusType.SYNCED)
            elif ahead_count > 0 and behind_count > 0:
                return SyncStatus(
                    type=SyncStatusType.DIVERGED,
                    ahead_count=ahead_count,
                    behind_count=behind_count,
                )
            elif ahead_count > 0:
                return SyncStatus(type=SyncStatusType.AHEAD, ahead_count=ahead_count)
            else:
                return SyncStatus(type=SyncStatusType.BEHIND, behind_count=behind_count)

        except Exception as e:
            return SyncStatus(type=SyncStatusType.ERROR, error_message=str(e))

    def get_status_info(self) -> Tuple[str, RepoStatusLocal, str, SyncStatus]:
        """Get all status information for the repository."""
        return (
            self.repo_path,
            self.repo_status,
            self.remote_url,
            self.get_sync_status(),
        )

    @staticmethod
    def find_git_repos(
        root_folder: str,
        max_depth: int = 3,
        show_hidden: bool = False,
        log_manager=None,
    ) -> List[str]:
        """
        Find all git repositories under the given root folder, respecting max_depth.

        Args:
            root_folder: The path to search for repositories
            max_depth: Maximum directory depth to search
            show_hidden: Whether to include hidden directories in the search
            log_manager: Optional log manager for detailed logging

        Returns:
            List of paths to git repositories found
        """
        git_repos = []
        root_path = Path(root_folder)
        base_depth = len(root_path.parts)

        for root, dirs, _ in os.walk(root_folder):
            current_depth = len(Path(root).parts) - base_depth

            # Stop if we've exceeded max_depth
            if current_depth > max_depth:
                if log_manager:
                    log_manager.debug(
                        f"Reached max depth {max_depth} at {root}, stopping descent"
                    )
                dirs.clear()
                continue

            # Filter out hidden directories if show_hidden is False
            if not show_hidden:
                original_dirs = dirs.copy()
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                if log_manager and len(original_dirs) != len(dirs):
                    filtered = set(original_dirs) - set(dirs)
                    log_manager.debug(
                        f"Filtered hidden directories at {root}: {filtered}"
                    )

            # Check if current directory is a git repo
            if ".git" in dirs:
                git_repos.append(root)
                dirs.remove(".git")  # Don't recurse into .git directories

        return sorted(git_repos)

    @staticmethod
    def is_git_repo(path: str) -> bool:
        """Check if the given path is a git repository."""
        try:
            Repo(path)
            return True
        except (InvalidGitRepositoryError, NoSuchPathError):
            return False

    @staticmethod
    def process_path(
        path: str, max_depth: int = 3, show_hidden: bool = False
    ) -> List[str]:
        """
        Process a path to find git repositories, handling both direct repos and container folders.

        Args:
            path: The path to process
            max_depth: Maximum directory depth to search for repos
            show_hidden: Whether to include hidden directories in the search

        Returns:
            List of repository paths found
        """
        expanded_path = os.path.expanduser(path)

        # If path doesn't exist, return empty list
        if not os.path.exists(expanded_path):
            return []

        # If path is directly a git repo, return it
        if RepoStatus.is_git_repo(expanded_path):
            return [expanded_path]

        # Otherwise, search for git repos under this path
        return RepoStatus.find_git_repos(expanded_path, max_depth, show_hidden)
