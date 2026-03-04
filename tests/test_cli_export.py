# ABOUTME: Tests for --formats none and standalone export command
# ABOUTME: Verifies decoupled fetch/export workflow in the CLI

"""Tests for --formats none and standalone export command."""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronicon.cli import run_export
from chronicon.config import Config
from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


@pytest.fixture
def sample_archive(tmp_path):
    """Create a sample archive with pre-populated database for testing."""
    archive_dir = tmp_path / "test_archive"
    archive_dir.mkdir()

    # Create database with sample data
    db = ArchiveDatabase(archive_dir / "archive.db")

    # Add sample category
    category = Category(
        id=1,
        name="Test Category",
        slug="test",
        color="FF0000",
        text_color="FFFFFF",
        description="Test category",
        parent_category_id=None,
        topic_count=1,
    )
    db.insert_category(category)

    # Add sample topic
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        posts_count=1,
        views=10,
    )
    db.insert_topic(topic)

    # Add sample post
    post = Post(
        id=1,
        topic_id=1,
        user_id=1,
        post_number=1,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        cooked="<p>Test post content</p>",
        raw="Test post content",
        username="testuser",
    )
    db.insert_post(post)

    # Add sample user
    user = User(
        id=1,
        username="testuser",
        name="Test User",
        avatar_template="",
        trust_level=1,
        created_at=datetime(2024, 1, 1),
    )
    db.insert_user(user)

    # Add site metadata
    db.update_site_metadata(
        site_url="https://meta.discourse.org",
        last_sync_date=datetime(2024, 1, 1).isoformat(),
        site_title="Test Site",
    )

    db.close()

    return archive_dir


# ============================================================
# Tests for --formats none
# ============================================================


class TestFormatsNone:
    """Tests for --formats none skipping export."""

    def test_formats_none_skips_export(self, sample_archive, capsys):
        """Verify no exporter is called when formats is 'none'."""
        with (
            patch("chronicon.cli.HTMLStaticExporter") as mock_html,
            patch("chronicon.cli.HybridExporter") as mock_hybrid,
            patch("chronicon.cli.MarkdownGitHubExporter") as mock_md,
            patch("chronicon.cli.DiscourseAPIClient") as mock_client_cls,
            patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_cls,
            patch("chronicon.cli.TopicFetcher") as mock_topic_fetcher_cls,
            patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_cls,
        ):
            # Setup mock API client
            mock_client = MagicMock()
            mock_client.get_stats.return_value = {
                "requests_made": 0,
                "requests_successful": 0,
                "requests_failed": 0,
                "retries_attempted": 0,
                "bytes_transferred": 0,
                "elapsed_time": 0,
                "request_rate": 0,
            }
            mock_client_cls.return_value = mock_client

            # Setup mock fetchers
            mock_cat_fetcher = MagicMock()
            mock_cat_fetcher.fetch_all_categories.return_value = []
            mock_cat_fetcher_cls.return_value = mock_cat_fetcher

            mock_topic_fetcher = MagicMock()
            mock_topic_fetcher_cls.return_value = mock_topic_fetcher

            mock_site_config = MagicMock()
            mock_site_config_cls.return_value = mock_site_config

            from chronicon.cli import _archive_site

            _archive_site(
                site_url="https://meta.discourse.org",
                output_dir=sample_archive,
                formats=["none"],
                text_only=True,
                include_users=False,
                category_ids=None,
                since_date=None,
                workers=1,
                rate_limit=0.0,
                config=Config.defaults(),
            )

            # No exporters should have been instantiated
            mock_html.assert_not_called()
            mock_hybrid.assert_not_called()
            mock_md.assert_not_called()

            # Should print skip message
            captured = capsys.readouterr()
            assert "Skipping export" in captured.out

    def test_formats_none_creates_database(self, tmp_path, capsys):
        """Verify database is still created when formats is 'none'."""
        archive_dir = tmp_path / "new_archive"
        archive_dir.mkdir()

        with (
            patch("chronicon.cli.DiscourseAPIClient") as mock_client_cls,
            patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_cls,
            patch("chronicon.cli.TopicFetcher") as mock_topic_fetcher_cls,
            patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_cls,
        ):
            mock_client = MagicMock()
            mock_client.get_stats.return_value = {
                "requests_made": 0,
                "requests_successful": 0,
                "requests_failed": 0,
                "retries_attempted": 0,
                "bytes_transferred": 0,
                "elapsed_time": 0,
                "request_rate": 0,
            }
            mock_client_cls.return_value = mock_client

            mock_cat_fetcher = MagicMock()
            mock_cat_fetcher.fetch_all_categories.return_value = []
            mock_cat_fetcher_cls.return_value = mock_cat_fetcher

            mock_topic_fetcher = MagicMock()
            mock_topic_fetcher_cls.return_value = mock_topic_fetcher

            mock_site_config = MagicMock()
            mock_site_config_cls.return_value = mock_site_config

            from chronicon.cli import _archive_site

            _archive_site(
                site_url="https://meta.discourse.org",
                output_dir=archive_dir,
                formats=["none"],
                text_only=True,
                include_users=False,
                category_ids=None,
                since_date=None,
                workers=1,
                rate_limit=0.0,
                config=Config.defaults(),
            )

        # Database should still exist
        db_path = archive_dir / "archive.db"
        assert db_path.exists(), "Database should be created even with --formats none"


# ============================================================
# Tests for standalone export command
# ============================================================


class TestExportCommand:
    """Tests for the standalone export command."""

    def test_export_html(self, sample_archive, capsys):
        """Test export command generates HTML output."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "html"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        with patch("chronicon.cli.HTMLStaticExporter") as mock_html_cls:
            mock_exporter = MagicMock()
            mock_html_cls.return_value = mock_exporter

            run_export(args, config)

            mock_html_cls.assert_called_once()
            mock_exporter.export.assert_called_once()

    def test_export_md(self, sample_archive, capsys):
        """Test export command generates Markdown output."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "md"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        with patch("chronicon.cli.MarkdownGitHubExporter") as mock_md_cls:
            mock_exporter = MagicMock()
            mock_md_cls.return_value = mock_exporter

            run_export(args, config)

            mock_md_cls.assert_called_once()
            mock_exporter.export.assert_called_once()

    def test_export_hybrid(self, sample_archive, capsys):
        """Test export command generates Hybrid output."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "hybrid"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        with patch("chronicon.cli.HybridExporter") as mock_hybrid_cls:
            mock_exporter = MagicMock()
            mock_hybrid_cls.return_value = mock_exporter

            run_export(args, config)

            mock_hybrid_cls.assert_called_once()
            mock_exporter.export.assert_called_once()

    def test_export_json(self, sample_archive, capsys):
        """Test export command generates valid JSON output."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "json"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        run_export(args, config)

        # JSON file should exist
        json_path = sample_archive / "json" / "archive.json"
        assert json_path.exists(), "archive.json should be created"

        # Validate JSON structure
        with open(json_path) as f:
            data = json.load(f)

        assert "topics" in data
        assert "categories" in data
        assert "users" in data
        assert "statistics" in data

        # Verify data content
        assert len(data["topics"]) == 1
        assert data["topics"][0]["id"] == 1
        assert data["topics"][0]["title"] == "Test Topic"
        assert len(data["topics"][0]["posts"]) == 1
        assert len(data["categories"]) == 1
        assert len(data["users"]) == 1

    def test_export_missing_db(self, tmp_path, capsys):
        """Test export command errors gracefully when DB doesn't exist."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        args = Mock()
        args.output_dir = empty_dir
        args.formats = "html"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        run_export(args, config)

        captured = capsys.readouterr()
        assert "No archive database found" in captured.out

    def test_export_empty_db(self, tmp_path, capsys):
        """Test export command warns about empty database."""
        archive_dir = tmp_path / "empty_archive"
        archive_dir.mkdir()

        # Create empty database
        db = ArchiveDatabase(archive_dir / "archive.db")
        db.close()

        args = Mock()
        args.output_dir = archive_dir
        args.formats = "json"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        run_export(args, config)

        captured = capsys.readouterr()
        assert "empty" in captured.out.lower() or "no topics" in captured.out.lower()

    def test_export_with_database_url(self, sample_archive, capsys):
        """Test export command uses factory when DATABASE_URL is set."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "json"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        db_url = f"sqlite:///{sample_archive / 'archive.db'}"

        with (
            patch.dict("os.environ", {"DATABASE_URL": db_url}),
            patch("chronicon.storage.factory.get_database") as mock_factory,
        ):
            # Return a real database from the factory
            mock_factory.return_value = ArchiveDatabase(sample_archive / "archive.db")

            run_export(args, config)

            mock_factory.assert_called_once_with(db_url)

    def test_export_records_history(self, sample_archive, capsys):
        """Test export command records export history in the database."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "json"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        run_export(args, config)

        # Open database and check export history
        db = ArchiveDatabase(sample_archive / "archive.db")
        history = db.get_export_history(limit=10)
        db.close()

        # Should have at least one json export recorded
        json_exports = [h for h in history if h["format"] == "json"]
        assert len(json_exports) >= 1, "JSON export should be recorded in history"


# ============================================================
# Integration tests
# ============================================================


class TestArchiveExportRoundtrip:
    """Integration tests for archive -> export roundtrip."""

    def test_archive_none_then_export_roundtrip(self, tmp_path, capsys):
        """Archive with --formats none, then export separately."""
        archive_dir = tmp_path / "roundtrip_archive"
        archive_dir.mkdir()

        # Step 1: Archive with --formats none (creates DB but no exports)
        with (
            patch("chronicon.cli.DiscourseAPIClient") as mock_client_cls,
            patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_cls,
            patch("chronicon.cli.TopicFetcher") as mock_topic_fetcher_cls,
            patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_cls,
        ):
            mock_client = MagicMock()
            mock_client.get_stats.return_value = {
                "requests_made": 5,
                "requests_successful": 5,
                "requests_failed": 0,
                "retries_attempted": 0,
                "bytes_transferred": 1024,
                "elapsed_time": 1.0,
                "request_rate": 5.0,
            }
            mock_client_cls.return_value = mock_client

            # Setup category fetcher to return a category
            cat = Category(
                id=1,
                name="General",
                slug="general",
                color="0088CC",
                text_color="FFFFFF",
                description="General discussion",
                parent_category_id=None,
                topic_count=1,
            )
            mock_cat_fetcher = MagicMock()
            mock_cat_fetcher.fetch_all_categories.return_value = [cat]
            mock_cat_fetcher_cls.return_value = mock_cat_fetcher

            # Setup topic fetcher
            topic = Topic(
                id=1,
                title="Welcome Topic",
                slug="welcome-topic",
                category_id=1,
                user_id=1,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
                posts_count=1,
                views=100,
            )
            mock_topic_fetcher = MagicMock()
            mock_topic_fetcher.fetch_category_topics.return_value = [topic]
            mock_topic_fetcher.fetch_topic_posts.return_value = [
                Post(
                    id=1,
                    topic_id=1,
                    user_id=1,
                    post_number=1,
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 1),
                    cooked="<p>Welcome!</p>",
                    raw="Welcome!",
                    username="admin",
                )
            ]
            mock_topic_fetcher_cls.return_value = mock_topic_fetcher

            mock_site_config = MagicMock()
            mock_site_config_cls.return_value = mock_site_config

            from chronicon.cli import _archive_site

            _archive_site(
                site_url="https://meta.discourse.org",
                output_dir=archive_dir,
                formats=["none"],
                text_only=True,
                include_users=False,
                category_ids=None,
                since_date=None,
                workers=1,
                rate_limit=0.0,
                config=Config.defaults(),
            )

        # Verify: DB exists but no export directories
        assert (archive_dir / "archive.db").exists()
        assert not (archive_dir / "json").exists()

        # Step 2: Export from existing DB
        args = Mock()
        args.output_dir = archive_dir
        args.formats = "json"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        run_export(args, config)

        # Verify: JSON export now exists with data from step 1
        json_path = archive_dir / "json" / "archive.json"
        assert json_path.exists()

        with open(json_path) as f:
            data = json.load(f)

        assert len(data["topics"]) == 1
        assert data["topics"][0]["title"] == "Welcome Topic"


# ============================================================
# E2E tests
# ============================================================


class TestExportE2E:
    """End-to-end tests for the export command."""

    def test_export_e2e_html_output(self, sample_archive, capsys):
        """Real export produces valid HTML files."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "html"
        args.include_users = False
        args.search_backend = "static"
        config = Config.defaults()

        run_export(args, config)

        # HTML index should exist
        html_dir = sample_archive / "html"
        assert html_dir.exists(), "HTML directory should be created"
        assert (html_dir / "index.html").exists(), "index.html should be created"

        # Verify HTML content is valid
        index_html = (html_dir / "index.html").read_text()
        assert "<html" in index_html
        assert "Test Category" in index_html or "Test Topic" in index_html

    def test_export_e2e_json_output(self, sample_archive, capsys):
        """Real export produces parseable JSON."""
        args = Mock()
        args.output_dir = sample_archive
        args.formats = "json"
        args.include_users = False
        args.search_backend = "fts"
        config = Config.defaults()

        run_export(args, config)

        # JSON should be valid and parseable
        json_path = sample_archive / "json" / "archive.json"
        assert json_path.exists()

        with open(json_path) as f:
            data = json.load(f)

        # Verify structure
        assert isinstance(data["topics"], list)
        assert isinstance(data["categories"], list)
        assert isinstance(data["users"], list)
        assert isinstance(data["statistics"], dict)

        # Verify topic has embedded posts
        topic = data["topics"][0]
        assert "posts" in topic
        assert len(topic["posts"]) >= 1
        assert topic["posts"][0]["cooked"] == "<p>Test post content</p>"
