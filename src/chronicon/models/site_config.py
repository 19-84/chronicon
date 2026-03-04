# ABOUTME: Site configuration data model for Chronicon
# ABOUTME: Represents site-level metadata and archiving configuration

"""Site configuration model for archived Discourse sites."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SiteConfig:
    """Represents site-level metadata for an archived forum."""

    site_url: str
    last_sync_date: datetime | None
    theme_version: str | None
    site_title: str
    site_description: str | None

    @classmethod
    def from_dict(cls, data: dict) -> "SiteConfig":
        """Create a SiteConfig instance from a dictionary."""
        last_sync = data.get("last_sync_date")
        return cls(
            site_url=data["site_url"],
            last_sync_date=datetime.fromisoformat(last_sync) if last_sync else None,
            theme_version=data.get("theme_version"),
            site_title=data.get("site_title", ""),
            site_description=data.get("site_description"),
        )

    def to_dict(self) -> dict:
        """Convert SiteConfig to dictionary."""
        return {
            "site_url": self.site_url,
            "last_sync_date": self.last_sync_date.isoformat()
            if self.last_sync_date
            else None,
            "theme_version": self.theme_version,
            "site_title": self.site_title,
            "site_description": self.site_description,
        }
