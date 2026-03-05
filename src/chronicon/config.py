# ABOUTME: Configuration management for Chronicon
# ABOUTME: Loads and validates configuration from TOML files

"""Configuration management."""

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SiteConfig:
    """Site-specific configuration."""

    url: str
    nickname: str | None = None
    categories: list[int] | None = None  # None means all categories
    rate_limit: float | None = None  # Override global rate limit


@dataclass
class Config:
    """Application configuration."""

    output_dir: Path
    default_formats: list[str]
    rate_limit: float
    max_workers: int
    retry_max: int
    timeout: int
    exponential_backoff_base: int
    include_users: bool
    text_only: bool
    posts_per_page: int
    pagination_enabled: bool
    canonical_base_url: str | None

    # Continuous mode settings
    continuous_polling_interval: int  # minutes between checks
    continuous_max_consecutive_errors: int
    continuous_error_backoff_multiplier: float

    # Git integration settings
    continuous_git_enabled: bool
    continuous_git_auto_commit: bool
    continuous_git_commit_on_each_update: bool
    continuous_git_push_to_remote: bool
    continuous_git_remote_name: str
    continuous_git_branch: str
    continuous_git_commit_message_template: str

    # Site-specific configurations
    sites: list[SiteConfig] = field(default_factory=list)

    def get_site_config(self, site_url: str) -> SiteConfig | None:
        """
        Get site-specific config for a URL.

        Args:
            site_url: Site URL to look up

        Returns:
            SiteConfig if found, None otherwise
        """
        # Normalize URL for comparison (strip trailing slash)
        normalized = site_url.rstrip("/")
        for site in self.sites:
            if site.url.rstrip("/") == normalized:
                return site
        return None

    def get_category_filter(self, site_url: str) -> list[int] | None:
        """
        Get category filter for a site.

        Args:
            site_url: Site URL

        Returns:
            List of category IDs to include, or None for all categories
        """
        site_config = self.get_site_config(site_url)
        if site_config:
            return site_config.categories
        return None

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Config":
        """
        Load config from file or use defaults.

        Args:
            config_path: Path to TOML config file

        Returns:
            Config instance
        """
        # Start with defaults
        config = cls.defaults()

        # If no config path provided, try default locations
        if config_path is None:
            possible_paths = [
                Path(".chronicon.toml"),
                Path.home() / ".chronicon.toml",
                Path.home() / ".config" / "chronicon" / "config.toml",
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break

        # Load config from file if it exists
        if config_path and config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)

                # Parse general settings
                if "general" in data:
                    general = data["general"]
                    if "output_dir" in general:
                        config.output_dir = Path(general["output_dir"])
                    if "default_formats" in general:
                        config.default_formats = general["default_formats"]

                # Parse fetching settings
                if "fetching" in data:
                    fetching = data["fetching"]
                    if "rate_limit_seconds" in fetching:
                        config.rate_limit = fetching["rate_limit_seconds"]
                    if "max_workers" in fetching:
                        config.max_workers = fetching["max_workers"]
                    if "retry_max" in fetching:
                        config.retry_max = fetching["retry_max"]
                    if "timeout" in fetching:
                        config.timeout = fetching["timeout"]
                    if "exponential_backoff_base" in fetching:
                        config.exponential_backoff_base = fetching[
                            "exponential_backoff_base"
                        ]

                # Parse export settings
                if "export" in data:
                    export = data["export"]
                    if "include_users" in export:
                        config.include_users = export["include_users"]
                    if "text_only" in export:
                        config.text_only = export["text_only"]
                    if "posts_per_page" in export:
                        config.posts_per_page = export["posts_per_page"]
                    if "pagination_enabled" in export:
                        config.pagination_enabled = export["pagination_enabled"]
                    if "canonical_base_url" in export:
                        config.canonical_base_url = export["canonical_base_url"]

                # Parse continuous mode settings
                if "continuous" in data:
                    continuous = data["continuous"]
                    if "polling_interval_minutes" in continuous:
                        config.continuous_polling_interval = continuous[
                            "polling_interval_minutes"
                        ]
                    if "max_consecutive_errors" in continuous:
                        config.continuous_max_consecutive_errors = continuous[
                            "max_consecutive_errors"
                        ]
                    if "error_backoff_multiplier" in continuous:
                        config.continuous_error_backoff_multiplier = continuous[
                            "error_backoff_multiplier"
                        ]

                # Parse git integration settings
                if "continuous" in data and "git" in data["continuous"]:
                    git = data["continuous"]["git"]
                    if "enabled" in git:
                        config.continuous_git_enabled = git["enabled"]
                    if "auto_commit" in git:
                        config.continuous_git_auto_commit = git["auto_commit"]
                    if "commit_on_each_update" in git:
                        config.continuous_git_commit_on_each_update = git[
                            "commit_on_each_update"
                        ]
                    if "push_to_remote" in git:
                        config.continuous_git_push_to_remote = git["push_to_remote"]
                    if "remote_name" in git:
                        config.continuous_git_remote_name = git["remote_name"]
                    if "branch" in git:
                        config.continuous_git_branch = git["branch"]
                    if "commit_message_template" in git:
                        config.continuous_git_commit_message_template = git[
                            "commit_message_template"
                        ]

                # Parse site-specific settings
                if "sites" in data:
                    for site_data in data["sites"]:
                        if "url" not in site_data:
                            log.warning("Site config missing 'url', skipping")
                            continue
                        site_config = SiteConfig(
                            url=site_data["url"],
                            nickname=site_data.get("nickname"),
                            categories=site_data.get("categories"),
                            rate_limit=site_data.get("rate_limit_seconds"),
                        )
                        config.sites.append(site_config)
                    if config.sites:
                        log.info(f"Loaded {len(config.sites)} site configurations")

            except Exception as e:
                # If config file is malformed, fall back to defaults and warn
                log.warning(f"Failed to load config from {config_path}: {e}")
                log.warning("Using default configuration.")

        return config

    @classmethod
    def defaults(cls) -> "Config":
        """
        Return default configuration.

        Returns:
            Config instance with default values
        """
        return cls(
            output_dir=Path("./archives"),
            default_formats=["html", "md"],
            rate_limit=0.5,
            max_workers=8,
            retry_max=5,
            timeout=15,
            exponential_backoff_base=2,
            include_users=True,
            text_only=False,
            posts_per_page=50,
            pagination_enabled=True,
            canonical_base_url=None,
            # Continuous mode defaults
            continuous_polling_interval=10,  # 10 minutes
            continuous_max_consecutive_errors=5,
            continuous_error_backoff_multiplier=2.0,
            # Git integration defaults
            continuous_git_enabled=False,
            continuous_git_auto_commit=True,
            continuous_git_commit_on_each_update=True,
            continuous_git_push_to_remote=False,
            continuous_git_remote_name="origin",
            continuous_git_branch="main",
            continuous_git_commit_message_template=(
                "chore: update archive - {new_posts} new, "
                "{modified_posts} modified, {topics} topics"
            ),
            # No site-specific configs by default
            sites=[],
        )
