"""Configuration constants for the testing suite."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Immutable configuration for a test run."""

    # Repository
    repo_url: str = "https://github.com/yuzono/anime-extensions.git"
    repo_branch: str = "master"
    clone_dir: str = "repo"

    # HTTP
    http_timeout: float = 30.0
    http_connect_timeout: float = 15.0
    http_total_timeout: float = 120.0  # per-extension total

    # Concurrency
    max_concurrent: int = 20

    # Retry
    max_retries: int = 2
    retry_backoff: float = 5.0

    # User-Agent (matches Android Chrome used by extensions)
    user_agent: str = (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36"
    )

    # Filtering
    languages: list[str] = field(default_factory=list)  # empty = all
    extensions: list[str] = field(default_factory=list)  # empty = all
    test_categories: list[str] = field(default_factory=lambda: [
        "structural", "connectivity", "popular", "search", "details",
        "episodes", "latest", "filters", "series_details",
        "episode_list", "video_streams", "pagination", "post_search",
    ])

    # API key handling
    skip_api_key_extensions: bool = True
    api_key_build_configs: set[str] = field(default_factory=lambda: {"TMDB_API"})

    # Output
    output_dir: str = "./reports"
    report_format: str = "both"  # "json", "markdown", "html", "both" (json+markdown), "all" (json+markdown+html)

    # Paths
    no_clone: bool = False
    repo_dir: str = ""
