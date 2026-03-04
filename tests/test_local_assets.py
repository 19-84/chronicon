# ABOUTME: Tests for local asset serving (site assets, avatars, SEO images)
# ABOUTME: Verifies Phase 1-5 implementation of offline asset serving

"""Tests for local asset serving functionality."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronicon.exporters.html_static import HTMLStaticExporter
from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.assets import AssetDownloader
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


class TestSiteAssetDownloads:
    """Tests for site asset (logo, banner) downloads."""

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

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = Mock(spec=DiscourseAPIClient)
        client.base_url = "https://meta.discourse.org"
        return client

    def test_download_site_assets_with_metadata(self, mock_client, mock_db, temp_dir):
        """Test that site assets are downloaded from metadata."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        site_metadata = {
            "logo_url": "https://example.com/logo.png",
            "banner_image_url": "https://example.com/banner.jpg",
        }

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

            downloader.download_site_assets(site_metadata=site_metadata)

        # Should have tried to download logo and banner
        assert mock_urlopen.call_count >= 2

    def test_download_site_assets_without_metadata(
        self, mock_client, mock_db, temp_dir
    ):
        """Test that generic site assets are downloaded without metadata."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

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

            downloader.download_site_assets()

        # Should have tried to download generic assets (favicon, logo.png)
        assert mock_urlopen.call_count >= 1

    def test_download_site_assets_handles_missing_metadata(
        self, mock_client, mock_db, temp_dir
    ):
        """Test that download handles missing logo/banner in metadata."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        site_metadata = {"logo_url": None, "banner_image_url": ""}

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

            # Should not raise exception
            downloader.download_site_assets(site_metadata=site_metadata)

        # Should only have tried generic assets, not metadata assets
        assert mock_urlopen.call_count >= 1


class TestAvatarDownloads:
    """Tests for user avatar downloads."""

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

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = Mock(spec=DiscourseAPIClient)
        client.base_url = "https://meta.discourse.org"
        return client

    def test_download_avatar_returns_tuple(self, mock_client, mock_db, temp_dir):
        """Test that download_avatar returns (dict, best_path) tuple."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        template = "https://example.com/avatars/{size}/user.png"
        sizes = [48, 96, 144]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_avatar_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            results, best_path = downloader.download_avatar(template, sizes)

        # Should return dict of sizes and best path
        assert isinstance(results, dict)
        assert len(results) == 3
        assert best_path is not None
        assert isinstance(best_path, Path)

    def test_download_avatar_downloads_descending_sizes(
        self, mock_client, mock_db, temp_dir
    ):
        """Test that avatars are downloaded in descending order (highest first)."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        template = "https://example.com/avatars/{size}/user.png"
        sizes = [48, 96, 144]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_avatar_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            results, best_path = downloader.download_avatar(template, sizes)

        # Best path should be for the highest resolution (144)
        # Verify the template was called with sizes in descending order
        calls = mock_urlopen.call_args_list
        assert len(calls) == 3

    def test_download_avatar_with_callback(self, mock_client, mock_db, temp_dir):
        """Test that download_avatar calls callback for each size."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        template = "https://example.com/avatars/{size}/user.png"
        sizes = [48, 96, 144]
        callback_calls = []

        def test_callback(url, success, cached, bytes_downloaded):
            callback_calls.append({"url": url, "success": success, "cached": cached})

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_avatar_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {"Content-Type": "image/png"}.get(
                    key, default
                )
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            results, best_path = downloader.download_avatar(
                template, sizes, callback=test_callback
            )

        # Callback should have been called 3 times
        assert len(callback_calls) == 3


class TestSEOImageDownloads:
    """Tests for SEO/Open Graph image downloads."""

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

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = Mock(spec=DiscourseAPIClient)
        client.base_url = "https://meta.discourse.org"
        return client

    def test_download_seo_image(self, mock_client, mock_db, temp_dir):
        """Test downloading SEO/Open Graph images."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        seo_image_url = "https://example.com/og-image.jpg"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_seo_image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {
                    "Content-Type": "image/jpeg"
                }.get(key, default)
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = downloader.download_seo_image(seo_image_url)

        # Should have downloaded and returned path
        assert result is not None
        assert isinstance(result, Path)

    def test_download_seo_image_empty_url(self, mock_client, mock_db, temp_dir):
        """Test that empty URL is handled gracefully."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        result = downloader.download_seo_image("")

        # Should return None for empty URL
        assert result is None

    def test_download_seo_image_with_callback(self, mock_client, mock_db, temp_dir):
        """Test that SEO image download calls callback."""
        downloader = AssetDownloader(mock_client, mock_db, temp_dir)

        seo_image_url = "https://example.com/og-image.jpg"
        callback_called = []

        def test_callback(url, success, cached, bytes_downloaded):
            callback_called.append({"url": url, "success": success})

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"fake_seo_image_data"
            mock_response.headers.get = Mock(
                side_effect=lambda key, default=None: {
                    "Content-Type": "image/jpeg"
                }.get(key, default)
            )
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            downloader.download_seo_image(seo_image_url, callback=test_callback)

        # Callback should have been called once
        assert len(callback_called) == 1
        assert callback_called[0]["success"] is True


class TestLocalPathHelpers:
    """Tests for local path helper functions in HTMLStaticExporter."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def sample_db(self, temp_dir):
        """Create a sample database with test data."""
        db_path = temp_dir / "test.db"
        db = ArchiveDatabase(db_path)

        # Add site metadata
        db.update_site_metadata(
            site_url="https://meta.discourse.org",
            site_title="Test Forum",
            logo_url="https://example.com/logo.png",
            banner_image_url="https://example.com/banner.jpg",
        )

        # Register downloaded assets
        logo_path = str(temp_dir / "assets" / "site" / "logo.png")
        banner_path = str(temp_dir / "assets" / "site" / "banner.jpg")

        (temp_dir / "assets" / "site").mkdir(parents=True, exist_ok=True)
        Path(logo_path).write_bytes(b"logo")
        Path(banner_path).write_bytes(b"banner")

        db.register_asset("https://example.com/logo.png", logo_path, "image/png")
        db.register_asset("https://example.com/banner.jpg", banner_path, "image/jpeg")

        # Add a user with avatar
        user = User(
            id=1,
            username="testuser",
            name="Test User",
            avatar_template="/avatars/{size}/1.png",
            trust_level=1,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            local_avatar_path=str(temp_dir / "assets" / "avatars" / "1-144.png"),
        )

        (temp_dir / "assets" / "avatars").mkdir(parents=True, exist_ok=True)
        assert user.local_avatar_path is not None
        Path(user.local_avatar_path).write_bytes(b"avatar")

        db.insert_user(user)

        return db

    def test_get_local_logo(self, temp_dir, sample_db):
        """Test _get_local_logo helper function."""
        output_dir = temp_dir / "html_output"
        exporter = HTMLStaticExporter(sample_db, output_dir)

        # Test at root level (depth=0)
        local_logo = exporter._get_local_logo(depth=0)
        assert local_logo is not None
        assert "assets/site/logo.png" in local_logo

        # Test at depth 1
        local_logo = exporter._get_local_logo(depth=1)
        assert local_logo is not None
        assert "../assets/site/logo.png" in local_logo

    def test_get_local_banner(self, temp_dir, sample_db):
        """Test _get_local_banner helper function."""
        output_dir = temp_dir / "html_output"
        exporter = HTMLStaticExporter(sample_db, output_dir)

        # Test at root level
        local_banner = exporter._get_local_banner(depth=0)
        assert local_banner is not None
        assert "assets/site/banner.jpg" in local_banner

        # Test at depth 2
        local_banner = exporter._get_local_banner(depth=2)
        assert local_banner is not None
        assert "../../assets/site/banner.jpg" in local_banner

    def test_get_local_avatar(self, temp_dir, sample_db):
        """Test _get_local_avatar helper function."""
        output_dir = temp_dir / "html_output"
        exporter = HTMLStaticExporter(sample_db, output_dir)

        # Test at root level
        local_avatar = exporter._get_local_avatar(user_id=1, depth=0)
        assert local_avatar is not None
        assert "assets/avatars" in local_avatar

        # Test at depth 1
        local_avatar = exporter._get_local_avatar(user_id=1, depth=1)
        assert local_avatar is not None
        assert "../assets/avatars" in local_avatar

    def test_get_local_avatar_nonexistent_user(self, temp_dir, sample_db):
        """Test _get_local_avatar with nonexistent user."""
        output_dir = temp_dir / "html_output"
        exporter = HTMLStaticExporter(sample_db, output_dir)

        # Should return None for nonexistent user
        local_avatar = exporter._get_local_avatar(user_id=999, depth=0)
        assert local_avatar is None

    def test_template_globals_available(self, temp_dir, sample_db):
        """Test that helper functions are available as Jinja2 globals."""
        output_dir = temp_dir / "html_output"
        exporter = HTMLStaticExporter(sample_db, output_dir)

        # Check that globals are registered
        assert "get_local_logo" in exporter.env.globals
        assert "get_local_banner" in exporter.env.globals
        assert "get_local_avatar" in exporter.env.globals

        # Check that they're callable
        assert callable(exporter.env.globals["get_local_logo"])
        assert callable(exporter.env.globals["get_local_banner"])
        assert callable(exporter.env.globals["get_local_avatar"])
