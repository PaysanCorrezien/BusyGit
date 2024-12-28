from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional
import re


class RepoStatusLocal(Enum):
    CLEAN = auto()
    DIRTY = auto()
    ERROR = auto()
    UNKNOWN = auto()


class SyncStatusType(Enum):
    SYNCED = auto()
    AHEAD = auto()
    BEHIND = auto()
    DIVERGED = auto()
    NO_REMOTE = auto()
    NO_UPSTREAM = auto()
    DISABLED_SSH = auto()
    DISABLED_HTTPS = auto()
    DISABLED_GENERAL = auto()
    ERROR = auto()
    UNKNOWN = auto()


@dataclass
class SyncStatus:
    """Represents the sync status with additional metadata."""

    type: SyncStatusType
    ahead_count: Optional[int] = None
    behind_count: Optional[int] = None
    error_message: Optional[str] = None

    def __str__(self) -> str:
        """Convert sync status to human-readable string."""
        match self.type:
            case SyncStatusType.SYNCED:
                return "Synced"
            case SyncStatusType.AHEAD:
                return f"Ahead by {self.ahead_count}"
            case SyncStatusType.BEHIND:
                return f"Behind by {self.behind_count}"
            case SyncStatusType.DIVERGED:
                return f"Diverged (↑{self.ahead_count} ↓{self.behind_count})"
            case SyncStatusType.NO_REMOTE:
                return "No remote configured"
            case SyncStatusType.NO_UPSTREAM:
                return "No upstream branch"
            case SyncStatusType.DISABLED_SSH:
                return "SSH status check disabled"
            case SyncStatusType.DISABLED_HTTPS:
                return "HTTPS status check disabled"
            case SyncStatusType.DISABLED_GENERAL:
                return "Remote status check disabled"
            case SyncStatusType.ERROR:
                return f"Error: {self.error_message}"
            case _:
                return "Unknown status"


class StatusParser:
    """Parser for converting status strings to enum types."""

    @staticmethod
    def parse_repo_status(status: str) -> RepoStatusLocal:
        """Parse repository status string into RepoStatus enum."""
        status_lower = status.lower()
        if "error" in status_lower:
            return RepoStatusLocal.ERROR
        elif "dirty" in status_lower:
            return RepoStatusLocal.DIRTY
        elif "clean" in status_lower:
            return RepoStatusLocal.CLEAN
        return RepoStatusLocal.UNKNOWN

    @staticmethod
    def parse_sync_status(status: str) -> SyncStatus:
        """Parse sync status string into SyncStatus object."""
        status_lower = status.lower()

        # Check for error states first
        if "error" in status_lower:
            return SyncStatus(
                type=SyncStatusType.ERROR, error_message=status.split("Error: ")[-1]
            )

        # Check for disabled states
        if "disabled" in status_lower:
            if "ssh" in status_lower:
                return SyncStatus(type=SyncStatusType.DISABLED_SSH)
            elif "https" in status_lower:
                return SyncStatus(type=SyncStatusType.DISABLED_HTTPS)
            return SyncStatus(type=SyncStatusType.DISABLED_GENERAL)

        # Check for no remote/upstream
        if "no remote" in status_lower:
            return SyncStatus(type=SyncStatusType.NO_REMOTE)
        if "no upstream" in status_lower:
            return SyncStatus(type=SyncStatusType.NO_UPSTREAM)

        # Parse ahead/behind numbers
        ahead_match = re.search(r"↑(\d+)", status)
        behind_match = re.search(r"↓(\d+)", status)
        ahead_count = int(ahead_match.group(1)) if ahead_match else None
        behind_count = int(behind_match.group(1)) if behind_match else None

        # Determine sync status type
        if "synced" in status_lower:
            return SyncStatus(type=SyncStatusType.SYNCED)
        elif "diverged" in status_lower:
            return SyncStatus(
                type=SyncStatusType.DIVERGED,
                ahead_count=ahead_count,
                behind_count=behind_count,
            )
        elif "ahead" in status_lower:
            ahead_count = ahead_count or int(
                re.search(r"ahead by (\d+)", status_lower).group(1)
            )
            return SyncStatus(type=SyncStatusType.AHEAD, ahead_count=ahead_count)
        elif "behind" in status_lower:
            behind_count = behind_count or int(
                re.search(r"behind by (\d+)", status_lower).group(1)
            )
            return SyncStatus(type=SyncStatusType.BEHIND, behind_count=behind_count)

        return SyncStatus(type=SyncStatusType.UNKNOWN)
