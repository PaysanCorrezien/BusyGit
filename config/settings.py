from dataclasses import dataclass
from typing import List


@dataclass
class Settings:
    watched_paths: List[str]
    auto_refresh_interval: int
    max_depth: int
    show_hidden: bool
    theme: str
    use_ssh_agent: bool = True
    fetch_https_status: bool = False
    remote_cache_timeout: int = 120
