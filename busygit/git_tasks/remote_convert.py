from typing import Optional
import subprocess
from dataclasses import dataclass


@dataclass
class RemoteUrl:
    """Represents a parsed Git remote URL."""

    protocol: str  # 'ssh' or 'https'
    host: str
    path: str
    original_url: str

    @staticmethod
    def parse(url: str) -> Optional["RemoteUrl"]:
        """Parse a Git remote URL into its components.

        Args:
            url: The Git remote URL to parse

        Returns:
            RemoteUrl object if successful, None if parsing fails
        """
        if not url or "Error" in url or "No remote" in url:
            return None

        # Handle SSH URLs
        if url.startswith("git@"):
            try:
                parts = url.split("@")[1].split(":")
                if len(parts) != 2:
                    return None
                host, path = parts
                path = path.removesuffix(".git")
                return RemoteUrl("ssh", host, path, url)
            except Exception:
                return None

        # Handle ssh:// format
        if url.startswith("ssh://"):
            try:
                url = url.replace("ssh://", "")
                if "@" in url:
                    url = url.split("@", 1)[1]
                # Split into host and path
                parts = url.split("/", 1)
                if len(parts) != 2:
                    return None
                host, path = parts
                path = path.removesuffix(".git")
                return RemoteUrl("ssh", host, path, url)
            except Exception:
                return None

        # Handle HTTPS URLs
        if url.startswith("https://"):
            try:
                url = url.removesuffix(".git")
                parts = url.replace("https://", "").split("/", 1)
                if len(parts) != 2:
                    return None
                host, path = parts
                return RemoteUrl("https", host, path, url)
            except Exception:
                return None

        return None

    def to_https(self) -> str:
        """Convert to HTTPS URL format."""
        return f"https://{self.host}/{self.path}"

    def to_ssh(self) -> str:
        """Convert to SSH URL format based on the hosting service."""
        # Handle Azure DevOps special case
        if "dev.azure.com" in self.host:
            return f"git@ssh.dev.azure.com:v3/{self.path}"
        # Standard SSH format for most services
        return f"git@{self.host}:{self.path}"


class RemoteConverter:
    """Handles Git remote URL conversion operations."""

    def __init__(self, log_manager=None):
        self.log_manager = log_manager

    def convert_url(self, current_url: str) -> Optional[str]:
        """Convert a URL between HTTPS and SSH formats.

        Args:
            current_url: The current Git remote URL

        Returns:
            The converted URL or None if conversion fails
        """
        remote = RemoteUrl.parse(current_url)
        if not remote:
            if self.log_manager:
                self.log_manager.warning(f"Failed to parse URL: {current_url}")
            return None

        # Convert based on current protocol
        if remote.protocol == "https":
            return remote.to_ssh()
        else:
            return remote.to_https()

    def update_remote_url(self, repo_path: str, new_url: str) -> bool:
        """Update the remote URL for a repository.

        Args:
            repo_path: Path to the Git repository
            new_url: New remote URL to set

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "remote", "set-url", "origin", new_url],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                if self.log_manager:
                    self.log_manager.info(
                        f"Successfully updated remote URL to: {new_url}"
                    )
                return True
            else:
                if self.log_manager:
                    self.log_manager.error(
                        f"Failed to update remote URL: {result.stderr}"
                    )
                return False

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"Error updating remote URL: {str(e)}")
            return False
