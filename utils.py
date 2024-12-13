import os

def is_git_repo(path: str) -> bool:
    """Check if the given path is a git repository."""
    git_dir = os.path.join(path, '.git')
    return os.path.exists(git_dir) and os.path.isdir(git_dir) 