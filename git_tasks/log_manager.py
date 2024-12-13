from enum import Enum
import logging
import os
import re
from typing import Optional
from textual.worker import get_current_worker


class LogLevel(Enum):
    """Enum for log levels with their Rich styling."""

    DEBUG = ("[blue bold]DEBUG[/blue bold]", logging.DEBUG)
    INFO = ("[green bold]INFO[/green bold]", logging.INFO)
    WARNING = ("[yellow bold]WARNING[/yellow bold]", logging.WARNING)
    ERROR = ("[red bold]ERROR[/red bold]", logging.ERROR)
    CRITICAL = ("[red bold reverse]CRITICAL[/red bold reverse]", logging.CRITICAL)


class LogManager:
    """Enhanced log manager with styling and buffer management."""

    def __init__(self, config_dir: str = "~/.config/git-tracker"):
        self.LOG_FILE = os.path.expanduser(os.path.join(config_dir, "app.log"))

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)

        # Configure logging
        self._configure_logger()

        # Store latest logs in memory for quick access
        self._log_buffer = []
        self._max_buffer_size = 1000  # Keep last 1000 log entries in memory

    def _configure_logger(self):
        """Configure the logger with proper formatting."""
        # Create a logger
        self.logger = logging.getLogger("GitTracker")
        self.logger.setLevel(logging.DEBUG)

        # Remove any existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Create formatters
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Add file handler
        file_handler = logging.FileHandler(self.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _add_to_buffer(self, message: str):
        """Add a log message to the in-memory buffer."""
        self._log_buffer.append(message)
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer.pop(0)

    def debug(self, message: str, *args):
        """Log a debug message."""
        self.log(message, LogLevel.DEBUG, *args)

    def info(self, message: str, *args):
        """Log an info message."""
        self.log(message, LogLevel.INFO, *args)

    def warning(self, message: str, *args):
        """Log a warning message."""
        self.log(message, LogLevel.WARNING, *args)

    def error(self, message: str, *args):
        """Log an error message."""
        self.log(message, LogLevel.ERROR, *args)

    def critical(self, message: str, *args):
        """Log a critical message."""
        self.log(message, LogLevel.CRITICAL, *args)

    def log(self, message: str, level: LogLevel = LogLevel.DEBUG, *args):
        """Log a message with the specified level."""
        if args:
            message = message % args
        getattr(self.logger, level.name.lower())(message)
        self._add_to_buffer(message)

    def read_logs(self) -> str:
        """Read logs from the log file and add Rich markup."""
        if not os.path.exists(self.LOG_FILE):
            return "No logs available."

        with open(self.LOG_FILE, "r") as f:
            logs = f.read()

        # Add markup to log levels
        for level in LogLevel:
            logs = re.sub(f" {level.name} ", f" {level.value[0]} ", logs)

        return logs

    def clear_logs(self):
        """Clear the log file and buffer."""
        self._log_buffer.clear()
        with open(self.LOG_FILE, "w") as f:
            f.write("")

    def get_log_size(self) -> int:
        """Get the size of the log file in bytes."""
        if os.path.exists(self.LOG_FILE):
            return os.path.getsize(self.LOG_FILE)
        return 0
