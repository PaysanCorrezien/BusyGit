import os
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .repo_status import RepoStatus
from .status import RepoStatusLocal, SyncStatus, SyncStatusType
from ..utils import is_git_repo
from .git_cache import GitCache
from enum import Enum, auto
from ..config.settings_manager import SettingsManager


class RefreshMode(Enum):
    CACHED = auto()  # Use cache where possible (for UI updates, tab switches)
    SMART = auto()  # Always check local status, use cached remote status
    FULL = auto()  # Full refresh, ignore all caches (for manual refresh)


class GitManager:
    def __init__(self, settings_manager=None, log_manager=None, max_workers=None):

        self.settings_manager = settings_manager or SettingsManager()
        self.log_manager = log_manager
        # Default to number of CPUs * 2 for max workers
        self.max_workers = max_workers or (os.cpu_count() or 1) * 2
        self.cache = GitCache()

    def check_path_for_repo(self, path: str) -> Tuple[str, bool]:
        """Check if a path is a git repository with caching."""
        try:
            # Check cache first
            cached_result = self.cache.is_git_repo(path)
            if cached_result is not None:
                if self.log_manager:
                    self.log_manager.debug(f"Cache hit for repo check: {path}")
                return path, cached_result

            # Cache miss - do the actual check
            is_repo = is_git_repo(path)
            self.cache.update_repo_check(path, is_repo)
            return path, is_repo
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"Error checking path {path}: {str(e)}")
            return path, False

    def scan_directory(
        self,
        base_path: str,
        max_depth: int,
        show_hidden: bool,
        skip_cached: bool = True,
    ) -> List[str]:
        """Scan a directory for git repositories up to max_depth."""
        repos = []
        base_path = os.path.expanduser(base_path)

        if not os.path.exists(base_path):
            if self.log_manager:
                self.log_manager.warning(f"Path does not exist: {base_path}")
            return repos

        # Get cached repos to skip if needed
        cached_repos = (
            set(self.cache.get_all_cached_repos().keys()) if skip_cached else set()
        )

        # First check if base path itself is a git repo
        if base_path not in cached_repos and is_git_repo(base_path):
            if self.log_manager:
                self.log_manager.debug(f"Base path is a git repository: {base_path}")
            repos.append(base_path)
            return repos

        if max_depth < 1:
            return repos

        try:
            # Get all potential repository paths to check
            to_check = []
            entries = os.listdir(base_path)
            for entry in entries:
                if not show_hidden and entry.startswith("."):
                    continue

                full_path = os.path.join(base_path, entry)
                if os.path.isdir(full_path) and full_path not in cached_repos:
                    to_check.append(full_path)

            if not to_check:
                return repos

            # Check all paths in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_path = {
                    executor.submit(self.check_path_for_repo, path): path
                    for path in to_check
                }

                for future in as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        checked_path, is_repo = future.result()
                        if is_repo and checked_path not in cached_repos:
                            if self.log_manager:
                                self.log_manager.debug(
                                    f"Found git repository: {checked_path}"
                                )
                            repos.append(checked_path)
                    except Exception as e:
                        if self.log_manager:
                            self.log_manager.error(
                                f"Error processing path {path}: {str(e)}"
                            )

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(
                    f"Error scanning directory {base_path}: {str(e)}"
                )

        return repos

    def get_repository_status(
        self,
        repo_path: str,
        use_ssh_agent: bool,
        fetch_https_status: bool,
        refresh_mode: RefreshMode = RefreshMode.SMART,
    ) -> Tuple[str, RepoStatusLocal, str, SyncStatus]:
        """Get status information for a specific repository."""
        try:
            if refresh_mode == RefreshMode.CACHED:
                # Try to use fully cached status if available
                cached = self.cache.get_repo_status(repo_path)
                if cached:
                    if self.log_manager:
                        self.log_manager.debug(
                            f"Using fully cached status for: {repo_path}"
                        )
                    # Convert cached strings to enum types
                    from .status import StatusParser

                    repo_status = StatusParser.parse_repo_status(cached.status)
                    sync_status = StatusParser.parse_sync_status(cached.sync_status)
                    return (repo_path, repo_status, cached.remote_url, sync_status)

            # Always get fresh local status in SMART and FULL modes
            repo_status = RepoStatus(
                repo_path,
                use_ssh_agent=use_ssh_agent,
                fetch_https_status=fetch_https_status,
            )
            status = repo_status.repo_status  # Now returns RepoStatusLocal enum

            if refresh_mode == RefreshMode.SMART:
                # Try to use cached remote status
                cached_remote = self.cache.get_cached_remote_status(repo_path)
                if cached_remote:
                    if self.log_manager:
                        self.log_manager.debug(
                            f"Using cached remote status for: {repo_path}"
                        )
                    remote_url, sync_status_str = cached_remote
                    sync_status = StatusParser.parse_sync_status(sync_status_str)
                else:
                    remote_url, sync_status = self._get_fresh_remote_status(repo_status)
            else:  # FULL refresh
                remote_url, sync_status = self._get_fresh_remote_status(repo_status)

            # Cache the results (convert enums to strings for cache)
            self.cache.update_repo_status(
                repo_path, status.name, remote_url, str(sync_status)
            )
            return (repo_path, status, remote_url, sync_status)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(
                    f"Error getting status for {repo_path}: {str(e)}"
                )
            return (
                repo_path,
                RepoStatusLocal.ERROR,
                "Error",
                SyncStatus(type=SyncStatusType.ERROR, error_message=str(e)),
            )

    def process_repositories_parallel(
        self,
        repo_paths: List[str],
        use_ssh_agent: bool,
        fetch_https_status: bool,
        mode: RefreshMode,
        progress_callback=None,
    ) -> List[Tuple[str, RepoStatusLocal, str, SyncStatus, str]]:
        """Process repositories in parallel with optional progress reporting."""
        results = []
        processed = 0
        total = len(repo_paths)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(
                    self._process_single_repo,
                    path,
                    use_ssh_agent,
                    fetch_https_status,
                    mode,
                ): path
                for path in repo_paths
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                    processed += 1

                    # Report progress if callback provided
                    if progress_callback:
                        progress_callback(processed, total)

                except Exception as e:
                    if self.log_manager:
                        self.log_manager.error(
                            f"Error processing repo {path}: {str(e)}"
                        )
                    # Add error status
                    results.append(
                        (
                            path,
                            RepoStatusLocal.ERROR,
                            str(e),
                            SyncStatus(type=SyncStatusType.ERROR, error_message=str(e)),
                            "Error",
                        )
                    )

        return results

    def get_all_repositories(
        self, mode: RefreshMode = RefreshMode.SMART, progress_callback=None
    ) -> List[Tuple[str, RepoStatusLocal, str, SyncStatus, str]]:
        """Get all repositories with progress tracking."""
        # Reload settings
        self.settings_manager.load_settings()
        watched_paths = self.settings_manager.get_watched_paths()
        max_depth = self.settings_manager.settings.max_depth
        show_hidden = self.settings_manager.settings.show_hidden
        use_ssh_agent = self.settings_manager.settings.use_ssh_agent
        fetch_https_status = self.settings_manager.settings.fetch_https_status

        # Discovery phase
        all_repo_paths = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self.scan_directory, path, max_depth, show_hidden): path
                for path in watched_paths
            }

            # Collect results
            for future in as_completed(future_to_path):
                try:
                    repo_paths = future.result()
                    all_repo_paths.extend(repo_paths)
                except Exception as e:
                    if self.log_manager:
                        self.log_manager.error(f"Error scanning directory: {str(e)}")

        # Process repositories with progress tracking
        repos_data = self.process_repositories_parallel(
            all_repo_paths, use_ssh_agent, fetch_https_status, mode, progress_callback
        )

        return sorted(repos_data, key=lambda x: x[0].lower())

    def _get_fresh_remote_status(
        self, repo_status: RepoStatus
    ) -> Tuple[str, SyncStatus]:
        """Get fresh remote status information."""
        return repo_status.remote_url, repo_status.get_sync_status()

    def refresh_repositories(
        self, mode: RefreshMode = RefreshMode.FULL, progress_callback=None
    ) -> List[Tuple[str, RepoStatusLocal, str, SyncStatus, str]]:
        """Refresh and return status for all repositories."""
        if self.log_manager:
            self.log_manager.debug(
                f"Starting repository refresh with mode: {mode.name}"
            )

        # Try to use cached data for CACHED and SMART modes
        if mode in [RefreshMode.CACHED, RefreshMode.SMART]:
            cached_repos = self.cache.get_all_cached_repos()
            if cached_repos:
                results = []
                for repo_path, cached_status in cached_repos.items():
                    if os.path.exists(repo_path):
                        from .status import StatusParser

                        if mode == RefreshMode.CACHED:
                            # Use fully cached data
                            repo_status = StatusParser.parse_repo_status(
                                cached_status.status
                            )
                            sync_status = StatusParser.parse_sync_status(
                                cached_status.sync_status
                            )
                        else:  # SMART mode
                            # Update local status but use cached remote status
                            try:
                                repo = RepoStatus(
                                    repo_path,
                                    use_ssh_agent=self.settings_manager.settings.use_ssh_agent,
                                    fetch_https_status=self.settings_manager.settings.fetch_https_status,
                                )
                                repo_status = repo.repo_status
                                sync_status = StatusParser.parse_sync_status(
                                    cached_status.sync_status
                                )
                            except Exception as e:
                                if self.log_manager:
                                    self.log_manager.error(
                                        f"Error updating local status for {repo_path}: {str(e)}"
                                    )
                                continue

                        branch = getattr(cached_status, "branch", "")
                        results.append(
                            (
                                repo_path,
                                repo_status,
                                cached_status.remote_url,
                                sync_status,
                                branch,
                            )
                        )
                if results:  # Only return if we have valid cached results
                    return sorted(results, key=lambda x: x[0].lower())

        # If we reach here, we need to do a full repository discovery
        self.settings_manager.load_settings()
        watched_paths = self.settings_manager.get_watched_paths()
        max_depth = self.settings_manager.settings.max_depth
        show_hidden = self.settings_manager.settings.show_hidden
        use_ssh_agent = self.settings_manager.settings.use_ssh_agent
        fetch_https_status = self.settings_manager.settings.fetch_https_status

        # Discovery phase - use ThreadPoolExecutor for parallel scanning
        all_repo_paths = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(
                    self.scan_directory,
                    path,
                    max_depth,
                    show_hidden,
                    skip_cached=(
                        mode != RefreshMode.FULL
                    ),  # Only skip cached repos for non-FULL modes
                ): path
                for path in watched_paths
            }

            # Collect results
            for future in as_completed(future_to_path):
                try:
                    repo_paths = future.result()
                    all_repo_paths.extend(repo_paths)
                except Exception as e:
                    if self.log_manager:
                        self.log_manager.error(f"Error scanning directory: {str(e)}")

        # For FULL refresh, include cached repositories not in current paths
        if mode == RefreshMode.FULL:
            cached_repos = self.cache.get_all_cached_repos()
            for repo_path in cached_repos:
                if repo_path not in all_repo_paths and os.path.exists(repo_path):
                    all_repo_paths.append(repo_path)

        # Process repositories with progress tracking
        results = self.process_repositories_parallel(
            all_repo_paths, use_ssh_agent, fetch_https_status, mode, progress_callback
        )

        return sorted(results, key=lambda x: x[0].lower())

    def add_watched_path(self, path: str) -> None:
        """Add a new path to watch."""
        if self.log_manager:
            self.log_manager.debug(f"Adding new watched path: {path}")
        self.settings_manager.add_watched_path(path)
        self.settings_manager.load_settings()
        # Invalidate cache for added path
        self.cache.invalidate_repo(path)

    def remove_watched_path(self, path: str) -> None:
        """Remove a path from watch list."""
        if self.log_manager:
            self.log_manager.debug(f"Removing watched path: {path}")
        self.settings_manager.remove_watched_path(path)
        # Invalidate cache for removed path
        self.cache.invalidate_repo(path)

    def _process_single_repo(
        self,
        repo_path: str,
        use_ssh_agent: bool,
        fetch_https_status: bool,
        mode: RefreshMode,
    ) -> Tuple[str, RepoStatusLocal, str, SyncStatus, str]:
        """Process a single repository and return its status."""
        try:
            repo_status = RepoStatus(
                repo_path,
                use_ssh_agent=use_ssh_agent,
                fetch_https_status=fetch_https_status,
            )
            # Get status info directly from properties
            return (
                repo_status.repo_path,
                repo_status.repo_status,
                repo_status.remote_url,
                repo_status.get_sync_status(),
                repo_status.current_branch,
            )

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(
                    f"Error processing repository {repo_path}: {str(e)}"
                )
            return (
                repo_path,
                RepoStatusLocal.ERROR,
                str(e),
                SyncStatus(type=SyncStatusType.ERROR, error_message=str(e)),
                "Error",
            )
