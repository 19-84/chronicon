# ABOUTME: Asset downloader for Chronicon
# ABOUTME: Downloads and manages forum assets like images, avatars, and uploads

"""Asset downloading and management for archived forums."""

import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..storage.database import ArchiveDatabase
from ..utils.validators import ValidationError, sanitize_filename, validate_file_size
from .api_client import DiscourseAPIClient


class AssetDownloader:
    """Download and manage forum assets."""

    def __init__(
        self,
        client: DiscourseAPIClient,
        db: ArchiveDatabase,
        output_dir: Path,
        text_only: bool = False,
    ):
        """
        Initialize asset downloader.

        Args:
            client: API client instance
            db: Database instance
            output_dir: Base directory for asset storage
            text_only: If True, skip all asset downloads
        """
        self.client = client
        self.db = db
        self.output_dir = Path(output_dir)
        self.text_only = text_only

        # Initialize statistics tracking
        self.stats = {
            "total_queued": 0,
            "downloaded": 0,
            "cached": 0,
            "failed": 0,
            "bytes_downloaded": 0,
            "start_time": time.time(),
        }

        # Create asset directories
        if not self.text_only:
            self.avatars_dir = self.output_dir / "avatars"
            self.images_dir = self.output_dir / "images"
            self.emoji_dir = self.output_dir / "emoji"
            self.site_dir = self.output_dir / "site"

            for directory in [
                self.avatars_dir,
                self.images_dir,
                self.emoji_dir,
                self.site_dir,
            ]:
                directory.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> dict:
        """
        Get current download statistics.

        Returns:
            Dictionary with download statistics including:
            - total_queued: Total assets queued for download
            - downloaded: Successfully downloaded assets
            - cached: Assets found in cache (skipped download)
            - failed: Failed downloads
            - bytes_downloaded: Total bytes downloaded
            - elapsed_time: Seconds since downloader initialization
            - download_rate: Downloads per second
        """
        elapsed = time.time() - self.stats["start_time"]
        download_rate = self.stats["downloaded"] / elapsed if elapsed > 0 else 0

        return {
            "total_queued": self.stats["total_queued"],
            "downloaded": self.stats["downloaded"],
            "cached": self.stats["cached"],
            "failed": self.stats["failed"],
            "bytes_downloaded": self.stats["bytes_downloaded"],
            "elapsed_time": elapsed,
            "download_rate": download_rate,
        }

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        self.stats = {
            "total_queued": 0,
            "downloaded": 0,
            "cached": 0,
            "failed": 0,
            "bytes_downloaded": 0,
            "start_time": time.time(),
        }

    def download_avatar(
        self, template: str, sizes: list[int], callback: Callable | None = None
    ) -> tuple[dict[int, Path | None], Path | None]:
        """
        Download avatar images at specified sizes.

        Args:
            template: Avatar template URL with {size} placeholder
            sizes: List of sizes to download (will be sorted, highest downloaded first)
            callback: Optional callback function(url, success, cached, bytes_downloaded)

        Returns:
            Tuple of (dict mapping size to local path, path to
            best/highest resolution avatar)
        """
        if self.text_only or not template:
            return {}, None

        # Sort sizes in descending order (download highest first)
        sorted_sizes = sorted(sizes, reverse=True)

        results = {}
        best_path = None

        for size in sorted_sizes:
            url = template.replace("{size}", str(size))
            local_path = self._download_file(url, self.avatars_dir, callback=callback)
            results[size] = local_path

            # Store the first successful download (highest resolution) as best_path
            if best_path is None and local_path is not None:
                best_path = local_path

        return results, best_path

    def download_image(
        self, url: str, topic_id: int, callback: Callable | None = None
    ) -> Path | None:
        """
        Download an image from a post.

        Args:
            url: Image URL
            topic_id: Topic ID for organization
            callback: Optional callback function(url, success, cached, bytes_downloaded)

        Returns:
            Local path to downloaded image or None
        """
        if self.text_only:
            return None

        # Create topic-specific subdirectory
        topic_dir = self.images_dir / str(topic_id)
        topic_dir.mkdir(parents=True, exist_ok=True)

        return self._download_file(url, topic_dir, callback=callback)

    def download_emoji(self, name: str) -> Path | None:
        """
        Download an emoji image.

        Args:
            name: Emoji name

        Returns:
            Local path to downloaded emoji or None
        """
        if self.text_only:
            return None

        # Construct emoji URL
        url = f"{self.client.base_url}/images/emoji/twitter/{name}.png"
        return self._download_file(url, self.emoji_dir)

    def download_seo_image(
        self, url: str, callback: Callable | None = None
    ) -> Path | None:
        """
        Download SEO/Open Graph image for a topic.

        These are the images shown in social media previews (topic.image_url).
        Downloaded to site_dir since they're site-wide SEO assets.

        Args:
            url: Image URL from topic.image_url
            callback: Optional callback function(url, success, cached, bytes_downloaded)

        Returns:
            Local path to downloaded image or None
        """
        if self.text_only or not url:
            return None

        return self._download_file(url, self.site_dir, callback=callback)

    def download_site_assets(
        self, site_metadata: dict | None = None, callback: Callable | None = None
    ) -> None:
        """
        Download site-level assets (logo, favicon, banner, etc.).

        Args:
            site_metadata: Optional dictionary with site metadata including
                logo_url, banner_image_url
            callback: Optional callback function(url, success, cached,
                bytes_downloaded)
        """
        if self.text_only:
            return

        # Common site assets (fallback generic paths)
        assets = [
            "/images/favicon.ico",
            "/images/logo.png",
        ]

        from contextlib import suppress

        for asset_path in assets:
            url = f"{self.client.base_url}{asset_path}"
            with suppress(Exception):
                # Don't print, let callback handle it
                self._download_file(url, self.site_dir, callback=callback)

        # Download metadata-specified assets (actual site logo and banner)
        if site_metadata:
            # Download site logo if available
            logo_url = site_metadata.get("logo_url")
            if logo_url and logo_url.strip():
                with suppress(Exception):
                    # Don't print, let callback handle it
                    self._download_file(logo_url, self.site_dir, callback=callback)

            # Download banner image if available
            banner_url = site_metadata.get("banner_image_url")
            if banner_url and banner_url.strip():
                with suppress(Exception):
                    # Don't print, let callback handle it
                    self._download_file(banner_url, self.site_dir, callback=callback)

    def get_local_site_asset_path(self, asset_url: str) -> Path | None:
        """
        Get local path for a downloaded site asset.

        Args:
            asset_url: URL of the site asset (logo_url, banner_image_url, etc.)

        Returns:
            Local Path if asset was downloaded, None otherwise
        """
        if not asset_url:
            return None

        # Query assets table for local path
        local_path_str = self.db.get_asset_path(asset_url)
        if local_path_str and Path(local_path_str).exists():
            return Path(local_path_str)

        return None

    def batch_download(
        self,
        urls: list[str],
        target_dir: Path,
        max_workers: int = 20,
        callback: Callable | None = None,
    ) -> list[Path]:
        """
        Download multiple URLs concurrently.

        Args:
            urls: List of URLs to download
            target_dir: Target directory for downloads
            max_workers: Maximum number of concurrent downloads (default 20)
            callback: Optional callback function(url, success, cached, bytes_downloaded)

        Returns:
            List of local paths (None for failed downloads)
        """
        if self.text_only:
            return []

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        results = []

        # Use ThreadPoolExecutor for concurrent I/O-bound downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(self._download_file, url, target_dir, callback): url
                for url in urls
            }

            # Collect results as they complete
            for future in as_completed(future_to_url):
                _ = future_to_url[future]
                try:
                    path = future.result()
                    results.append(path)
                except Exception:
                    # Don't print, let callback handle it
                    results.append(None)

        return results

    def _download_file(
        self, url: str, target_dir: Path, callback: Callable | None = None
    ) -> Path | None:
        """
        Download a file and save to target directory.

        Args:
            url: URL to download
            target_dir: Target directory
            callback: Optional callback function(url, success, cached, bytes_downloaded)

        Returns:
            Local path or None if download failed
        """
        # Increment total queued
        self.stats["total_queued"] += 1

        # Check if already downloaded
        cached_path = self.db.get_asset_path(url)
        if cached_path and Path(cached_path).exists():
            self.stats["cached"] += 1
            if callback:
                callback(url, success=True, cached=True, bytes_downloaded=0)
            return Path(cached_path)

        try:
            # Make URL absolute if needed
            if url.startswith("/"):
                url = f"{self.client.base_url}{url}"

            # Extract and sanitize filename from URL
            parsed = urllib.parse.urlparse(url)
            raw_filename = Path(parsed.path).name or "asset"
            try:
                filename = sanitize_filename(raw_filename)
            except ValidationError:
                filename = "asset"  # Fallback to generic name

            local_path = target_dir / filename

            # Download file
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Chronicon/1.0.0")

            with urllib.request.urlopen(req, timeout=15) as response:
                # Check file size before downloading
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        validate_file_size(int(content_length))
                    except ValidationError as e:
                        raise ValueError(f"File too large: {e}") from e

                content = response.read()
                content_type = response.headers.get("Content-Type")
                bytes_downloaded = len(content)

                # Validate actual downloaded size
                try:
                    validate_file_size(bytes_downloaded)
                except ValidationError as e:
                    raise ValueError(f"Downloaded file too large: {e}") from e

                with open(local_path, "wb") as f:
                    f.write(content)

                # Register in database
                self.db.register_asset(url, str(local_path), content_type)

                # Update statistics
                self.stats["downloaded"] += 1
                self.stats["bytes_downloaded"] += bytes_downloaded

                # Call callback if provided
                if callback:
                    callback(
                        url,
                        success=True,
                        cached=False,
                        bytes_downloaded=bytes_downloaded,
                    )

                return local_path

        except Exception:
            # Update failure statistics
            self.stats["failed"] += 1

            # Call callback if provided
            if callback:
                callback(url, success=False, cached=False, bytes_downloaded=0)

            return None
