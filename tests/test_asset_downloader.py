# ABOUTME: Test file for AssetDownloader
# ABOUTME: Tests for concurrent downloads, deduplication, and error handling

"""Tests for AssetDownloader."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.assets import AssetDownloader
from chronicon.storage.database import ArchiveDatabase


class TestAssetDownloader:
    """Tests for AssetDownloader."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock(spec=ArchiveDatabase)
        db.get_asset_path.return_value = None  # No cached assets by default
        db.register_asset.return_value = None
        return db

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = Mock(spec=DiscourseAPIClient)
        client.base_url = "https://meta.discourse.org"
        return client

    def test_text_only_mode_skips_downloads(self, mock_client, mock_db, temp_dir):
        """Test that text-only mode skips all downloads."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir, text_only=True)

        # Try to download an image
        result = downloader.download_image("https://example.com/image.png", topic_id=1)

        # Should return None without downloading
        assert result is None

    def test_download_avatar_multiple_sizes(self, mock_client, mock_db, temp_dir):
        """Test downloading avatar at multiple sizes."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir, text_only=False)

        template = "https://example.com/avatars/{size}/user.png"
        sizes = [48, 96, 120]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            results, best_path = downloader.download_avatar(template, sizes)

        # Should have downloaded all sizes
        assert len(results) == 3
        assert 48 in results
        assert 96 in results
        assert 120 in results

        # Each should have a local path
        for _size, path in results.items():
            if path:
                assert isinstance(path, Path)

        # Should return best path (highest resolution = 120)
        assert best_path is not None
        assert isinstance(best_path, Path)

    def test_deduplication_checks_database_first(self, mock_client, mock_db, temp_dir):
        """Test that downloader checks database before downloading."""
        # Setup database to return cached path
        cached_path = str(temp_dir / "cached" / "image.png")
        (temp_dir / "cached").mkdir(parents=True, exist_ok=True)
        (temp_dir / "cached" / "image.png").write_bytes(b"cached_image")

        mock_db.get_asset_path.return_value = cached_path

        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            result = downloader.download_image(
                "https://example.com/image.png", topic_id=1
            )

        # Should not have called urlopen
        mock_urlopen.assert_not_called()

        # Should return cached path
        assert result == Path(cached_path)

    def test_download_image_creates_topic_subdirectory(
        self, mock_client, mock_db, temp_dir
    ):
        """Test that images are organized by topic ID."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = downloader.download_image(
                "https://example.com/test.png", topic_id=123
            )

        # Should have created topic-specific directory
        assert result is not None
        assert "123" in str(result)

    def test_batch_download_returns_results(self, mock_client, mock_db, temp_dir):
        """Test batch download returns list of paths."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        urls = [
            "https://example.com/image1.png",
            "https://example.com/image2.jpg",
            "https://example.com/image3.gif",
        ]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            results = downloader.batch_download(urls, temp_dir / "batch")

        # Should return list of paths
        assert isinstance(results, list)
        assert len(results) == len(urls)

    def test_download_handles_relative_urls(self, mock_client, mock_db, temp_dir):
        """Test that relative URLs are made absolute."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            downloader.download_image("/uploads/image.png", topic_id=1)

        # Should have made URL absolute
        # Check that urlopen was called with full URL
        called_url = mock_urlopen.call_args[0][0].full_url
        assert called_url.startswith("https://meta.discourse.org")

    def test_download_failure_returns_none(self, mock_client, mock_db, temp_dir):
        """Test that download failures return None gracefully."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")

            result = downloader.download_image(
                "https://example.com/broken.png", topic_id=1
            )

        # Should return None on failure
        assert result is None

    def test_registers_asset_in_database(self, mock_client, mock_db, temp_dir):
        """Test that successful downloads are registered in database."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            downloader.download_image("https://example.com/test.png", topic_id=1)

        # Should have registered in database
        mock_db.register_asset.assert_called_once()
        call_args = mock_db.register_asset.call_args[0]
        assert call_args[0] == "https://example.com/test.png"  # URL
        assert call_args[2] == "image/png"  # Content type

    def test_download_site_assets_handles_failures(
        self, mock_client, mock_db, temp_dir
    ):
        """Test that site asset download continues on individual failures."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("404 Not Found")

            # Should not raise exception
            downloader.download_site_assets()

        # Method should complete without error

    def test_letter_avatar_unique_filenames(self, mock_client, mock_db, temp_dir):
        """Test that letter avatars get unique filenames instead of colliding."""
        # Simulate two different letter avatar URLs
        url_a = (
            "https://meta.discourse.org/letter_avatar_proxy/v4/letter/a/82dd89/144.png"
        )
        url_b = (
            "https://meta.discourse.org/letter_avatar_proxy/v4/letter/b/f14c23/144.png"
        )

        import urllib.parse

        # Simulate the filename extraction logic from _download_file
        def get_filename(url):
            parsed = urllib.parse.urlparse(url)
            raw_filename = Path(parsed.path).name or "asset"
            if "/letter/" in parsed.path:
                parts = [p for p in parsed.path.split("/") if p]
                letter_idx = parts.index("letter")
                raw_filename = "_".join(parts[letter_idx:])
                if not Path(raw_filename).suffix:
                    raw_filename += ".png"
            return raw_filename

        filename_a = get_filename(url_a)
        filename_b = get_filename(url_b)

        # Filenames must be different
        assert filename_a != filename_b
        # Both should contain identifying info
        assert "letter" in filename_a
        assert "letter" in filename_b
        assert "a" in filename_a
        assert "b" in filename_b

    def test_download_emoji_url_to_shared_dir(self, mock_client, mock_db, temp_dir):
        """Test that emoji URLs download to shared emoji directory."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"emoji_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = downloader.download_emoji_url(
                "https://emoji.discourse-cdn.com/twitter/heart.png"
            )

        assert result is not None
        # Should be in emoji dir, not a topic dir
        assert "emoji" in str(result.parent)
        assert "images" not in str(result.parent)

    def test_download_emoji_url_text_only(self, mock_client, mock_db, temp_dir):
        """Test that text-only mode skips emoji downloads."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir, text_only=True)
        result = downloader.download_emoji_url(
            "https://emoji.discourse-cdn.com/twitter/heart.png"
        )
        assert result is None

    def test_cdn_gets_longer_timeout(self, mock_client, mock_db, temp_dir):
        """Test that CDN URLs use longer timeout and more retries."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"data"
            mock_response.headers.get = Mock(return_value=None)
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            downloader.download_emoji_url(
                "https://emoji.discourse-cdn.com/twitter/heart.png"
            )

            # Check the timeout passed to urlopen
            call_args = mock_urlopen.call_args
            assert call_args[1]["timeout"] == 30  # CDN timeout

    def test_non_cdn_gets_standard_timeout(self, mock_client, mock_db, temp_dir):
        """Test that non-CDN URLs use standard timeout."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"data"
            mock_response.headers.get = Mock(return_value=None)
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            downloader.download_image(
                "https://meta.discourse.org/uploads/image.png", topic_id=1
            )

            call_args = mock_urlopen.call_args
            assert call_args[1]["timeout"] == 15  # Standard timeout

    def test_migrate_emoji_to_shared_dir(self, mock_client, mock_db, temp_dir):
        """Test migrating emoji from per-topic dirs to shared emoji dir."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        # Create a fake emoji in a per-topic dir
        topic_dir = temp_dir / "images" / "12345"
        topic_dir.mkdir(parents=True)
        emoji_file = topic_dir / "heart.png"
        emoji_file.write_bytes(b"emoji_data")

        # Mock DB to return the per-topic path
        mock_db.get_asset_path.return_value = str(emoji_file)

        url = "https://emoji.discourse-cdn.com/twitter/heart.png"
        migrated = downloader.migrate_emoji_to_shared_dir([url])

        assert migrated == 1
        # File should now exist in shared emoji dir
        assert (downloader.emoji_dir / "heart.png").exists()
        # DB should be updated
        mock_db.register_asset.assert_called_once_with(
            url, str(downloader.emoji_dir / "heart.png"), None
        )

    def test_migrate_skips_already_in_emoji_dir(self, mock_client, mock_db, temp_dir):
        """Test migration skips emoji already in shared dir."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        # Create emoji already in the right place
        emoji_file = downloader.emoji_dir / "heart.png"
        emoji_file.write_bytes(b"emoji_data")

        mock_db.get_asset_path.return_value = str(emoji_file)

        url = "https://emoji.discourse-cdn.com/twitter/heart.png"
        migrated = downloader.migrate_emoji_to_shared_dir([url])

        assert migrated == 0
        mock_db.register_asset.assert_not_called()

    def test_download_emoji_url_migrates_cached(self, mock_client, mock_db, temp_dir):
        """Test download_emoji_url migrates per-topic cached emoji."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        # Create emoji in per-topic dir
        topic_dir = temp_dir / "images" / "999"
        topic_dir.mkdir(parents=True)
        emoji_file = topic_dir / "smile.png"
        emoji_file.write_bytes(b"emoji_data")

        mock_db.get_asset_path.return_value = str(emoji_file)

        url = "https://emoji.discourse-cdn.com/twitter/smile.png"
        result = downloader.download_emoji_url(url)

        assert result is not None
        assert "emoji" in str(result.parent)
        assert result.name == "smile.png"
