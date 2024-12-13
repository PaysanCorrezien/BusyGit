from dataclasses import dataclass
import os
from time import time
from typing import Dict, Optional, Tuple
from .repo_status import RepoStatus


@dataclass
class CachedStatus:
    """Represents cached status information for a repository."""

    status: str
    remote_url: str
    sync_status: str
    last_check: float
    last_modified: float
    is_valid: bool = True

    def is_fresh(self, timeout: float) -> bool:
        """Check if the cached status is still fresh."""
        return (time() - self.last_check) < timeout


class GitCache:
    def __init__(self, cache_timeout: float = 300):  # 5 minutes default
        self._repo_cache: Dict[str, CachedStatus] = {}
        self._path_cache: Dict[str, bool] = {}  # Cache for is_git_repo checks
        self.cache_timeout = cache_timeout

    def _get_repo_mtime(self, repo_path: str) -> float:
        """Get the latest modification time of important git files."""
        try:
            git_dir = os.path.join(repo_path, ".git")
            key_files = [
                os.path.join(git_dir, "HEAD"),  # Branch changes
                os.path.join(git_dir, "index"),  # Staging changes
                os.path.join(git_dir, "refs/heads"),  # Local commits
                os.path.join(git_dir, "refs/remotes"),  # Remote changes
            ]

            mtimes = []
            for path in key_files:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        # For directories like refs/heads, check all files inside
                        for root, _, files in os.walk(path):
                            for file in files:
                                full_path = os.path.join(root, file)
                                mtimes.append(os.path.getmtime(full_path))
                    else:
                        mtimes.append(os.path.getmtime(path))

            return max(mtimes) if mtimes else 0
        except Exception:
            return 0

    def get_repo_status(self, repo_path: str) -> Optional[CachedStatus]:
        """Get cached repository status if valid."""
        cached = self._repo_cache.get(repo_path)
        if not cached or not cached.is_valid:
            return None

        if not cached.is_fresh(self.cache_timeout):
            return None

        current_mtime = self._get_repo_mtime(repo_path)
        if current_mtime > cached.last_modified:
            return None

        return cached

    def update_repo_status(
        self, repo_path: str, status: str, remote_url: str, sync_status: str
    ) -> None:
        """Update cached status for a repository."""
        self._repo_cache[repo_path] = CachedStatus(
            status=status,
            remote_url=remote_url,
            sync_status=sync_status,
            last_check=time(),
            last_modified=self._get_repo_mtime(repo_path),
        )

    def is_git_repo(self, path: str) -> Optional[bool]:
        """Get cached repository check if available."""
        if path in self._path_cache:
            return self._path_cache[path]
        return None

    def update_repo_check(self, path: str, is_repo: bool) -> None:
        """Update cached repository check."""
        self._path_cache[path] = is_repo

    def invalidate_repo(self, repo_path: str) -> None:
        """Invalidate cache for a specific repository."""
        if repo_path in self._repo_cache:
            self._repo_cache[repo_path].is_valid = False

    def invalidate_all(self) -> None:
        """Invalidate all cached data."""
        self._repo_cache.clear()
        self._path_cache.clear()

    def set_timeout(self, timeout: float) -> None:
        """Update cache timeout."""
        self.cache_timeout = timeout

    def get_all_cached_repos(self) -> Dict[str, CachedStatus]:
        """Get all cached repository statuses that are still valid."""
        current_time = time()
        return {
            path: status
            for path, status in self._repo_cache.items()
            if status.is_valid
            and status.is_fresh(self.cache_timeout)
            and self._get_repo_mtime(path) <= status.last_modified
        }
