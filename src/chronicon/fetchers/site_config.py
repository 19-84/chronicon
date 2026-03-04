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

    def extract_logo_from_html(self) -> str | None:
        """
        Extract site logo URL from HTML homepage.

        Logos are not available in JSON APIs and must be scraped from HTML.
        Looks for <link rel="icon"> tags and logo images in header.

        Returns:
            Logo URL or None if not found
        """
        try:
            # Fetch HTML homepage
            html_content = self.client.get("/")

            if not html_content:
                return None

            soup = BeautifulSoup(html_content, "html.parser")

            # Try multiple strategies to find logo

            # 1. Look for <link rel="icon" href="...">
            icon_link = soup.find("link", {"rel": "icon"})
            if icon_link and icon_link.get("href"):
                return icon_link["href"]

            # 2. Look for apple-touch-icon (often higher quality)
            apple_icon = soup.find("link", {"rel": "apple-touch-icon"})
            if apple_icon and apple_icon.get("href"):
                return apple_icon["href"]

            # 3. Look for logo in header
            header = soup.find("header")
            if header:
                logo_img = header.find("img", class_="logo")
                if logo_img and logo_img.get("src"):
                    return logo_img["src"]

            return None

        except Exception as e:
            log.warning(f"Error extracting logo from HTML: {e}")
            return None

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

        # Extract logo from HTML
        logo_url = self.extract_logo_from_html()
        if logo_url:
            log.info(f"Found logo: {logo_url}")
            self.db.update_site_metadata(site_url, logo_url=logo_url)

        log.info("Site metadata fetched and stored")
