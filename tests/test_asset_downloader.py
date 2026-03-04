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
