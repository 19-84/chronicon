# ABOUTME: Asset downloader for Chronicon
# ABOUTME: Downloads and manages forum assets like images, avatars, and uploads

"""Asset downloading and management for archived forums."""

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..storage.database import ArchiveDatabase
from ..utils.validators import ValidationError, sanitize_filename, validate_file_size
from .api_client import DiscourseAPIClient

log = logging.getLogger(__name__)


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

    def download_emoji_url(
        self, url: str, callback: Callable | None = None
    ) -> Path | None:
        """
        Download an emoji image to the shared emoji directory.

        If the emoji was previously downloaded to a per-topic directory,
        copies it to the shared emoji directory and updates the DB.

        Args:
            url: Full emoji URL (e.g., CDN or forum-hosted)
            callback: Optional callback function(url, success, cached, bytes_downloaded)

        Returns:
            Local path to downloaded emoji or None
        """
        if self.text_only or not url:
            return None

        # Check if cached in a per-topic dir — migrate to shared emoji dir
        import shutil

        cached_path = self.db.get_asset_path(url)
        if cached_path:
            cached = Path(cached_path)
            emoji_dir_str = str(self.emoji_dir)
            if cached.exists() and emoji_dir_str not in cached_path:
                # Cached in wrong dir — copy to emoji dir and re-register
                dest = self.emoji_dir / cached.name
                if not dest.exists():
                    shutil.copy2(cached, dest)
                self.db.register_asset(url, str(dest), None)
                if callback:
                    callback(url, success=True, cached=True, bytes_downloaded=0)
                return dest

        return self._download_file(url, self.emoji_dir, callback=callback)

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

        # Download metadata-specified assets (actual site logo, favicon, and banner)
        if site_metadata:
            # Download site logo if available
            logo_url = site_metadata.get("logo_url")
            if logo_url and logo_url.strip():
                with suppress(Exception):
                    self._download_file(logo_url, self.site_dir, callback=callback)

            # Download favicon if available
            favicon_url = site_metadata.get("favicon_url")
            if favicon_url and favicon_url.strip():
                with suppress(Exception):
                    self._download_file(favicon_url, self.site_dir, callback=callback)

            # Download banner image if available
            banner_url = site_metadata.get("banner_image_url")
            if banner_url and banner_url.strip():
                with suppress(Exception):
                    self._download_file(banner_url, self.site_dir, callback=callback)

    def migrate_emoji_to_shared_dir(self, emoji_urls: list[str]) -> int:
        """
        Migrate emoji cached in per-topic dirs to the shared emoji directory.

        Call before batch-downloading emoji to ensure DB paths point to
        the shared dir, not scattered per-topic dirs.

        Args:
            emoji_urls: List of emoji URLs to check and migrate

        Returns:
            Number of emoji migrated
        """
        import shutil

        migrated = 0
        emoji_dir_str = str(self.emoji_dir)
        for url in emoji_urls:
            cached_path = self.db.get_asset_path(url)
            if not cached_path or emoji_dir_str in cached_path:
                continue
            cached = Path(cached_path)
            if not cached.exists():
                continue
            dest = self.emoji_dir / cached.name
            if not dest.exists():
                shutil.copy2(cached, dest)
            self.db.register_asset(url, str(dest), None)
            migrated += 1
        return migrated

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
        retry_failures: bool = True,
    ) -> list[Path | None]:
        """
        Download multiple URLs concurrently with automatic retry of failures.

        Args:
            urls: List of URLs to download
            target_dir: Target directory for downloads
            max_workers: Maximum number of concurrent downloads (default 20)
            callback: Optional callback function(url, success, cached, bytes_downloaded)
            retry_failures: If True, retry failed downloads at lower concurrency

        Returns:
            List of local paths (None for failed downloads)
        """
        if self.text_only:
            return []

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        results: list[Path | None] = []
        failed_urls: list[str] = []

        # Use ThreadPoolExecutor for concurrent I/O-bound downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(self._download_file, url, target_dir, callback): url
                for url in urls
            }

            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    path = future.result()
                    results.append(path)
                    if path is None:
                        failed_urls.append(url)
                except Exception:
                    results.append(None)
                    failed_urls.append(url)

        # Retry failed downloads at lower concurrency
        if retry_failures and failed_urls:
            log.info(f"Retrying {len(failed_urls)} failed downloads (concurrency: 5)")
            retry_workers = min(5, len(failed_urls))
            recovered = 0
            with ThreadPoolExecutor(max_workers=retry_workers) as executor:
                future_to_url = {
                    executor.submit(self._download_file, url, target_dir, callback): url
                    for url in failed_urls
                }
                for future in as_completed(future_to_url):
                    try:
                        path = future.result()
                        if path is not None:
                            results.append(path)
                            recovered += 1
                            # Correct double-counted failure from first pass
                            self.stats["failed"] = max(0, self.stats["failed"] - 1)
                    except Exception:
                        pass
            if recovered:
                log.info(f"Recovered {recovered}/{len(failed_urls)} on retry")

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

            # Letter avatars have path like /v4/letter/a/82dd89/144.png
            # All resolve to "144.png" causing collisions — use full path
            if "/letter/" in parsed.path:
                parts = [p for p in parsed.path.split("/") if p]
                try:
                    letter_idx = parts.index("letter")
                    raw_filename = "_".join(parts[letter_idx:])
                    # Ensure extension
                    if not Path(raw_filename).suffix:
                        raw_filename += ".png"
                except ValueError:
                    pass  # Fall through to default filename

            # Regular avatars: /user_avatar/site/username/{size}/id.png
            # All sizes resolve to same filename — include size for uniqueness
            elif "/user_avatar/" in parsed.path:
                parts = [p for p in parsed.path.split("/") if p]
                # Pattern: user_avatar / site / username / size / filename
                if len(parts) >= 5:
                    size = parts[-2]  # e.g., "48", "96", "144"
                    raw_filename = f"{size}_{raw_filename}"
            try:
                filename = sanitize_filename(raw_filename)
            except ValidationError:
                filename = "asset"  # Fallback to generic name

            local_path = target_dir / filename

            # CDN requests get longer timeout and more retries
            is_cdn = "cdn" in url or "cloudfront" in url
            max_retries = 6 if is_cdn else 4
            timeout = 30 if is_cdn else 15

            # Download file with exponential backoff on rate limiting
            for attempt in range(max_retries + 1):
                try:
                    req = urllib.request.Request(url)
                    req.add_header("User-Agent", "Chronicon/1.0.0")
                    # Add Referer for CDN requests that check origin
                    if is_cdn:
                        req.add_header("Referer", self.client.base_url + "/")

                    with urllib.request.urlopen(req, timeout=timeout) as response:
                        content_length = response.headers.get("Content-Length")
                        if content_length:
                            try:
                                validate_file_size(int(content_length))
                            except ValidationError as e:
                                raise ValueError(f"File too large: {e}") from e

                        content = response.read()
                        content_type = response.headers.get("Content-Type")
                        bytes_downloaded = len(content)

                        try:
                            validate_file_size(bytes_downloaded)
                        except ValidationError as e:
                            raise ValueError(f"Downloaded file too large: {e}") from e

                        with open(local_path, "wb") as f:
                            f.write(content)

                        self.db.register_asset(url, str(local_path), content_type)

                        self.stats["downloaded"] += 1
                        self.stats["bytes_downloaded"] += bytes_downloaded

                        if callback:
                            callback(
                                url,
                                success=True,
                                cached=False,
                                bytes_downloaded=bytes_downloaded,
                            )

                        return local_path

                except urllib.error.HTTPError as e:
                    # Retry on 429 (rate limit) and 5xx (server errors)
                    if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                        backoff = 2**attempt  # 1s, 2s, 4s, 8s
                        time.sleep(backoff)
                        continue
                    raise
                except (urllib.error.URLError, TimeoutError, OSError):
                    if attempt < max_retries:
                        backoff = 2**attempt
                        time.sleep(backoff)
                        continue
                    raise

        except Exception:
            self.stats["failed"] += 1

            if callback:
                callback(url, success=False, cached=False, bytes_downloaded=0)

            return None
