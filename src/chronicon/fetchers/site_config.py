# ABOUTME: Site configuration fetcher for Chronicon
# ABOUTME: Fetches site metadata, banner images, logos from Discourse API

"""Site configuration fetching logic for Discourse API."""

from typing import Any

from bs4 import BeautifulSoup

from ..storage.database import ArchiveDatabase
from ..utils.logger import get_logger
from .api_client import DiscourseAPIClient

log = get_logger(__name__)


class SiteConfigFetcher:
    """Fetches site configuration and metadata from Discourse API."""

    def __init__(self, client: DiscourseAPIClient, db: ArchiveDatabase):
        """
        Initialize site config fetcher.

        Args:
            client: API client instance
            db: Database instance
        """
        self.client = client
        self.db = db

    def fetch_site_config(self) -> dict[str, Any] | None:
        """
        Fetch site configuration from /site.json endpoint.

        Returns:
            Dictionary with site configuration including:
            - categories: List of all categories
            - top_tags: Most popular tags
            - archetypes: Default archetype metadata
            - filters: Available topic filters
        """
        try:
            response = self.client.get_json("/site.json")
            return response
        except Exception as e:
            log.warning(f"Error fetching site config: {e}")
            return None

    def fetch_about_info(self) -> dict[str, Any] | None:
        """
        Fetch about page information from /about.json endpoint.

        Returns:
            Dictionary with about information including:
            - title: Site title
            - description: Site description
            - banner_image: Banner image URL
            - contact_email: Contact email
            - discourse_version: Discourse version
            - stats: Site statistics (user_count, topic_count, etc.)
        """
        try:
            response = self.client.get_json("/about.json")
            return response.get("about", {})
        except Exception as e:
            log.warning(f"Error fetching about info: {e}")
            return None

    def extract_icons_from_html(self) -> tuple[str | None, str | None]:
        """
        Extract favicon and logo URLs from HTML homepage.

        These are not available in JSON APIs and must be scraped from HTML.

        Returns:
            Tuple of (favicon_url, logo_url). Either can be None.
        """
        try:
            html_content = self.client.get("/")
            if not html_content:
                return None, None

            soup = BeautifulSoup(html_content, "html.parser")

            # Favicon: <link rel="icon" href="...">
            favicon_url = None
            icon_link = soup.find("link", {"rel": "icon"})
            if icon_link and icon_link.get("href"):  # type: ignore[union-attr]
                favicon_url = icon_link["href"]  # type: ignore[index]

            # Logo: header img.logo, then apple-touch-icon as fallback
            logo_url = None
            header = soup.find("header")
            if header:
                logo_img = header.find("img", class_="logo")  # type: ignore[call-arg]
                if logo_img and logo_img.get("src"):  # type: ignore[union-attr]
                    logo_url = logo_img["src"]  # type: ignore[index]

            if not logo_url:
                apple_icon = soup.find("link", {"rel": "apple-touch-icon"})
                if apple_icon and apple_icon.get("href"):  # type: ignore[union-attr]
                    logo_url = apple_icon["href"]  # type: ignore[index]

            return str(favicon_url) if favicon_url else None, str(
                logo_url
            ) if logo_url else None

        except Exception as e:
            log.warning(f"Error extracting icons from HTML: {e}")
            return None, None

    def extract_logo_from_html(self) -> str | None:
        """
        Extract site logo URL from HTML homepage.

        Logos are not available in JSON APIs and must be scraped from HTML.

        Returns:
            Logo URL or None if not found
        """
        favicon_url, logo_url = self.extract_icons_from_html()
        # Backward compat: return logo if found, else favicon
        return logo_url or favicon_url

    def fetch_and_store_site_metadata(self) -> None:
        """
        Fetch all site metadata and store in database.

        This includes:
        - Site title and description from /about.json
        - Banner image URL
        - Contact email
        - Discourse version
        - Logo URL extracted from HTML
        - Top tags from /site.json
        """
        log.info("Fetching site metadata...")

        site_url = self.client.base_url

        # Fetch about info
        about_info = self.fetch_about_info()
        if about_info:
            log.info(f"Got site info: {about_info.get('title', 'Unknown')}")

            # Store in database using update_site_metadata
            self.db.update_site_metadata(
                site_url,
                site_title=about_info.get("title"),
                site_description=about_info.get("description"),
                banner_image_url=about_info.get("banner_image"),
                contact_email=about_info.get("contact_email"),
                discourse_version=about_info.get("version"),
            )

        # Fetch site config for additional data
        site_config = self.fetch_site_config()
        if site_config and "top_tags" in site_config:
            # Extract and store top tags
            top_tags = site_config["top_tags"]
            log.info(f"Got {len(top_tags)} top tags")
            self.db.store_top_tags(top_tags)

        # Extract favicon and logo from HTML
        favicon_url, logo_url = self.extract_icons_from_html()
        if favicon_url:
            log.info(f"Found favicon: {favicon_url}")
            self.db.update_site_metadata(site_url, favicon_url=favicon_url)
        if logo_url:
            log.info(f"Found logo: {logo_url}")
            self.db.update_site_metadata(site_url, logo_url=logo_url)

        log.info("Site metadata fetched and stored")
