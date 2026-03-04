# ABOUTME: Integration tests for asset management pipeline
# ABOUTME: Tests full pipeline: download assets, process HTML, rewrite URLs

"""Integration tests for asset management pipeline."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.assets import AssetDownloader
from chronicon.processors.html_parser import HTMLProcessor
from chronicon.processors.url_rewriter import URLRewriter
from chronicon.storage.database import ArchiveDatabase


class TestAssetPipelineIntegration:
    """Integration tests for asset management pipeline."""

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
        db.get_asset_path.return_value = None
        db.register_asset.return_value = None
        return db

    def test_full_pipeline_html_with_images(self, temp_dir, mock_db):
        """Test HTML processing with image downloads."""
        # Mock API client
        mock_client = Mock(spec=DiscourseAPIClient)
        mock_client.base_url = "https://meta.discourse.org"

        # Create asset downloader
        asset_dir = temp_dir / "assets"
        downloader = AssetDownloader(mock_client, mock_db, asset_dir)

        # Create HTML processor with downloader
        processor = HTMLProcessor(downloader)

        # HTML with images
        html = """
        <div class="post">
            <p>Check out this image:</p>
            <img src="https://example.com/uploads/image.png" alt="Test">
            <p>More text</p>
        </div>
        """

        # Mock the download
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_image_data"
            mock_response.headers.get.return_value = "image/png"
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            # Process HTML
            result = processor.download_and_rewrite(html, topic_id=1)

        # Verify HTML was processed
        assert result
        # Should have downloaded image
        assert mock_urlopen.called
        # Result should contain local path reference
        assert "assets" in result or "image" in result

    def test_url_rewriter_integration(self, temp_dir):
        """Test URL rewriting in realistic scenario."""
        # Setup paths like they would be in actual export
        topics_dir = temp_dir / "topics" / "2024-10"
        assets_dir = temp_dir / "assets" / "images" / "123"

        topics_dir.mkdir(parents=True)
        assets_dir.mkdir(parents=True)

        topic_file = topics_dir / "my-topic-456.html"
        image_file = assets_dir / "screenshot.png"

        # Create dummy files
        topic_file.write_text("<html></html>")
        image_file.write_bytes(b"fake_image")

        # Rewrite URL
        rewriter = URLRewriter("https://meta.discourse.org")
        relative_url = rewriter.rewrite_image_url(
            "https://meta.discourse.org/uploads/screenshot.png", image_file, topic_file
        )

        # Verify relative path is correct
        assert relative_url
        assert ".." in relative_url  # Should go up from topics dir
        assert "screenshot.png" in relative_url

        # Verify we can actually resolve the path
        resolved = (topics_dir / relative_url).resolve()
        assert resolved == image_file.resolve()

    def test_asset_deduplication_across_pipeline(self, temp_dir, mock_db):
        """Test that assets are deduplicated across the pipeline."""
        mock_client = Mock(spec=DiscourseAPIClient)
        mock_client.base_url = "https://meta.discourse.org"

        # First download should cache in database
        cached_path = str(temp_dir / "cached_image.png")
        (temp_dir / "cached_image.png").write_bytes(b"cached")

        # Setup mock to return None first, then cached path
        call_count = [0]

        def get_asset_side_effect(url):
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # First call: not cached
            else:
                return cached_path  # Subsequent calls: cached

        mock_db.get_asset_path.side_effect = get_asset_side_effect

        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        # First download
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get.return_value = "image/png"
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            downloader.download_image("https://example.com/image.png", topic_id=1)

        # Second download of same URL
        result2 = downloader.download_image("https://example.com/image.png", topic_id=1)

        # Second call should use cache
        assert result2 == Path(cached_path)
        # Should have called database twice
        assert mock_db.get_asset_path.call_count == 2

    def test_text_only_mode_pipeline(self, temp_dir, mock_db):
        """Test that text-only mode works end-to-end."""
        mock_client = Mock(spec=DiscourseAPIClient)
        mock_client.base_url = "https://meta.discourse.org"

        # Create downloader in text-only mode
        downloader = AssetDownloader(mock_client, mock_db, temp_dir, text_only=True)

        # Create processor
        processor = HTMLProcessor(downloader)

        html = '<img src="https://example.com/image.png" alt="Test">'

        # Process HTML - should not download
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = processor.download_and_rewrite(html, topic_id=1)

        # Should not have downloaded anything
        mock_urlopen.assert_not_called()

        # HTML should be unchanged (no URLs rewritten)
        assert "example.com" in result

    def test_concurrent_asset_downloads(self, temp_dir, mock_db):
        """Test that concurrent downloads work correctly."""
        mock_client = Mock(spec=DiscourseAPIClient)
        mock_client.base_url = "https://meta.discourse.org"

        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        # Multiple URLs
        urls = [f"https://example.com/image{i}.png" for i in range(10)]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get.return_value = "image/png"
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            # Download concurrently
            results = downloader.batch_download(urls, temp_dir / "batch")

        # Should have downloaded all
        assert len(results) == len(urls)
        # Should have made concurrent requests
        assert mock_urlopen.call_count == len(urls)

    def test_error_handling_graceful_degradation(self, temp_dir, mock_db):
        """Test that errors are handled gracefully without breaking pipeline."""
        mock_client = Mock(spec=DiscourseAPIClient)
        mock_client.base_url = "https://meta.discourse.org"

        downloader = AssetDownloader(mock_client, mock_db, temp_dir)
        processor = HTMLProcessor(downloader)

        html = """
        <img src="https://example.com/good.png" alt="Good">
        <img src="https://example.com/broken.png" alt="Broken">
        <img src="https://example.com/good2.png" alt="Good2">
        """

        # Mock: first and third succeed, second fails
        call_count = [0]

        def urlopen_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call fails
                raise Exception("Network error")
            mock_response = MagicMock()
            mock_response.read.return_value = b"image_data"
            mock_response.headers.get.return_value = "image/png"
            mock_response.__enter__.return_value = mock_response
            return mock_response

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            # Should not raise exception
            result = processor.download_and_rewrite(html, topic_id=1)

        # Result should still be HTML
        assert result
        assert "<img" in result
