#!/usr/bin/env python3
"""
Git Tracker - A TUI application to monitor multiple Git repositories
"""

from ui.tracker import GitTrackerApp

def main():
    """Run the Git Tracker application."""
    app = GitTrackerApp()
    app.run()

if __name__ == "__main__":
    main()
