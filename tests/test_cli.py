# Test file for CLI commands
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronicon.cli import run_migrate, run_validate
from chronicon.config import Config
from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


def setup_mock_api_client_stats(mock_client):
    """Helper to setup get_stats() method on mock API client."""
    mock_client.get_stats.return_value = {
        "requests_made": 0,
        "requests_successful": 0,
        "requests_failed": 0,
        "retries_attempted": 0,
        "bytes_transferred": 0,
        "elapsed_time": 0,
        "request_rate": 0,
    }
    return mock_client


@pytest.fixture
def sample_archive(tmp_path):
    """Create a sample archive for testing."""
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
        cooked="<p>Test post</p>",
        raw="Test post",
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

    # Record export
    db.record_export("html", 1, 1, str(archive_dir / "html"))

    # Add site metadata for update tests
    db.update_site_metadata(
        site_url="https://meta.discourse.org",
        last_sync_date=datetime(2024, 1, 1).isoformat(),
        site_title="Test Site",
    )

    db.close()

    return archive_dir


def test_validate_missing_directory(tmp_path, capsys):
    """Test validate with missing directory."""
    args = Mock()
    args.output_dir = tmp_path / "nonexistent"
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "does not exist" in captured.out


def test_validate_missing_database(tmp_path, capsys):
    """Test validate with missing database."""
    archive_dir = tmp_path / "empty_archive"
    archive_dir.mkdir()

    args = Mock()
    args.output_dir = archive_dir
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "Database file not found" in captured.out


def test_validate_valid_archive(sample_archive, capsys):
    """Test validate with a valid archive."""
    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    # Create HTML export directory structure
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")
    (html_dir / "assets").mkdir()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "Database file found" in captured.out
    assert "Database is readable" in captured.out
    # Should show statistics
    assert "Categories: 1" in captured.out
    assert "Topics: 1" in captured.out
    assert "Posts: 1" in captured.out
    assert "Users: 1" in captured.out


def test_validate_export_directories(sample_archive, capsys):
    """Test validate checks export directories."""
    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    # Create HTML export directory
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "Checking HTML export" in captured.out
    assert "index.html present" in captured.out


def test_validate_data_integrity(sample_archive, capsys):
    """Test validate checks for data integrity issues."""
    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "Checking Data Integrity" in captured.out
    # Should find no orphaned posts since our sample is clean
    assert "No orphaned posts" in captured.out or "orphaned posts" in captured.out


def test_migrate_missing_source(tmp_path, capsys):
    """Test migrate with missing source directory."""
    args = Mock()
    args.source_dir = tmp_path / "nonexistent"
    args.format = None
    config = Config.defaults()

    run_migrate(args, config)

    captured = capsys.readouterr()
    assert "does not exist" in captured.out


def test_migrate_no_json_files(tmp_path, capsys):
    """Test migrate with directory containing no JSON files."""
    source_dir = tmp_path / "empty"
    source_dir.mkdir()

    args = Mock()
    args.source_dir = source_dir
    args.format = None
    config = Config.defaults()

    run_migrate(args, config)

    captured = capsys.readouterr()
    assert "No JSON files found" in captured.out


def test_migrate_with_json_files(tmp_path, capsys):
    """Test migrate with valid JSON files."""
    source_dir = tmp_path / "legacy_archive"
    source_dir.mkdir()

    # Create sample JSON files
    topic_json = source_dir / "topic_1.json"
    topic_json.write_text(
        json.dumps(
            {
                "topic": {
                    "id": 1,
                    "title": "Migrated Topic",
                    "slug": "migrated-topic",
                    "category_id": 1,
                    "user_id": 1,
                    "created_at": "2024-01-01T12:00:00",
                    "updated_at": "2024-01-01T12:00:00",
                    "posts_count": 1,
                    "views": 5,
                },
                "posts": [
                    {
                        "id": 1,
                        "topic_id": 1,
                        "user_id": 1,
                        "post_number": 1,
                        "created_at": "2024-01-01T12:00:00",
                        "updated_at": "2024-01-01T12:00:00",
                        "cooked": "<p>Migrated post</p>",
                        "raw": "Migrated post",
                        "username": "migrated_user",
                    }
                ],
            }
        )
    )

    args = Mock()
    args.source_dir = source_dir
    args.format = None  # No export after migration
    config = Config.defaults()

    run_migrate(args, config)

    captured = capsys.readouterr()
    assert "Found 1 JSON files" in captured.out
    assert "Migration complete" in captured.out
    assert "Posts imported:" in captured.out
    assert "Topics imported:" in captured.out


def test_migrate_with_export_format(tmp_path, capsys):
    """Test migrate with export to HTML after migration."""
    source_dir = tmp_path / "legacy_archive"
    source_dir.mkdir()

    # Create sample JSON
    topic_json = source_dir / "topic_1.json"
    topic_json.write_text(
        json.dumps(
            {
                "topics": [
                    {
                        "id": 1,
                        "title": "Test",
                        "slug": "test",
                        "category_id": 1,
                        "user_id": 1,
                        "created_at": "2024-01-01T12:00:00",
                        "updated_at": "2024-01-01T12:00:00",
                        "posts_count": 1,
                        "views": 1,
                    }
                ],
                "posts": [],
            }
        )
    )

    args = Mock()
    args.source_dir = source_dir
    args.format = "html"
    config = Config.defaults()

    # Mock the exporter to avoid actual export complexity
    with patch("chronicon.cli.HTMLStaticExporter") as mock_exporter:
        mock_instance = Mock()
        mock_exporter.return_value = mock_instance

        run_migrate(args, config)

        # Verify exporter was called
        assert mock_exporter.called
        assert mock_instance.export.called

    captured = capsys.readouterr()
    assert "Migration complete" in captured.out
    assert "Exporting to html format" in captured.out


def test_migrate_handles_errors_gracefully(tmp_path, capsys):
    """Test that migrate handles malformed JSON gracefully."""
    source_dir = tmp_path / "bad_archive"
    source_dir.mkdir()

    # Create malformed JSON
    bad_json = source_dir / "bad.json"
    bad_json.write_text("{ this is not valid json")

    args = Mock()
    args.source_dir = source_dir
    args.format = None
    config = Config.defaults()

    run_migrate(args, config)

    captured = capsys.readouterr()
    # Should complete but report errors
    assert "Migration complete" in captured.out or "Errors encountered" in captured.out


def test_validate_with_warnings(sample_archive, capsys):
    """Test validate produces warnings for missing optional files."""
    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    # Create HTML export but without assets directory
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")
    # Don't create assets directory

    run_validate(args, config)

    captured = capsys.readouterr()
    # Should warn about missing assets
    assert (
        "assets directory missing" in captured.out or "warning" in captured.out.lower()
    )


# ============================================================================
# Archive Command Tests
# ============================================================================


def test_archive_command_success(tmp_path, capsys):
    """Test successful archive command with mocked dependencies."""
    from unittest.mock import patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://meta.discourse.org"
    args.output_dir = tmp_path / "archive"
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False  # Disable sweep mode for simpler testing
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    # Mock all the heavy dependencies
    with (
        patch("chronicon.cli.DiscourseAPIClient") as mock_client_class,
        patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_class,
        patch("chronicon.cli.TopicFetcher") as mock_topic_fetcher_class,
        patch("chronicon.cli.AssetDownloader") as mock_asset_class,
        patch("chronicon.cli.HTMLProcessor"),
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_exp_class,
        patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_class,
    ):
        # Setup mock category fetcher
        mock_cat_fetcher = mock_cat_fetcher_class.return_value
        test_category = Category(
            id=1,
            name="Test Cat",
            slug="test-cat",
            color="FF0000",
            text_color="FFFFFF",
            description="Test category",
            parent_category_id=None,
            topic_count=1,
        )
        mock_cat_fetcher.fetch_all_categories.return_value = [test_category]

        # Setup mock client
        mock_client = setup_mock_api_client_stats(mock_client_class.return_value)
        mock_client.base_url = (
            "https://meta.discourse.org"  # Fix for SQLite binding error
        )
        mock_client.get_json.return_value = {
            "title": "Test Forum",
            "logo_url": "https://example.com/logo.png",
            "topic_list": {
                "topics": [
                    {
                        "id": 1,
                        "title": "Test Topic",
                        "slug": "test-topic",
                        "category_id": 1,
                        "user_id": 1,
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "posts_count": 1,
                        "views": 10,
                    }
                ]
            },
        }

        # Setup mock asset downloader
        mock_asset_downloader = mock_asset_class.return_value
        mock_asset_downloader.get_stats.return_value = {
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
            "cached": 0,
            "download_rate": 0.0,
            "bytes_downloaded": 0,  # Add bytes_downloaded for stats display
            "total_queued": 0,  # Add total_queued for asset stats tracking
        }

        # Setup mock topic fetcher
        mock_topic_fetcher = mock_topic_fetcher_class.return_value
        mock_post = Mock(
            id=1,
            topic_id=1,
            user_id=1,
            post_number=1,
            username="testuser",
            cooked="<p>Test</p>",
        )
        mock_topic_fetcher.fetch_topic_posts.return_value = [mock_post]

        # Setup mock site config fetcher
        mock_site_config = mock_site_config_class.return_value
        mock_site_config.fetch_and_store_site_metadata.return_value = None

        # Run archive command
        run_archive(args, config)

        captured = capsys.readouterr()
        assert "Archiving forums" in captured.out
        assert "Successfully archived" in captured.out
        assert "Archive complete" in captured.out

        # Verify exporter was called
        assert mock_html_exp_class.called
        mock_html_exporter = mock_html_exp_class.return_value
        mock_html_exporter.export.assert_called_once()


def test_archive_command_multiple_formats(tmp_path, capsys):
    """Test archive command with multiple export formats."""
    from unittest.mock import patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://meta.discourse.org"
    args.output_dir = tmp_path / "archive"
    args.formats = "html,md"  # HTML and Markdown formats
    args.text_only = True
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False  # Disable sweep mode for simpler testing
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient") as mock_client_class,
        patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_class,
        patch("chronicon.cli.TopicFetcher"),
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_exp,
        patch("chronicon.cli.MarkdownGitHubExporter") as mock_md_exp,
        patch("chronicon.cli.HybridExporter"),
        patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_class,
    ):
        # Setup minimal mocks
        mock_client = setup_mock_api_client_stats(mock_client_class.return_value)
        mock_client.base_url = (
            "https://meta.discourse.org"  # Fix for SQLite binding error
        )
        mock_client.get_json.return_value = {
            "title": "Test Forum",
            "logo_url": "https://example.com/logo.png",
        }
        mock_cat_fetcher = mock_cat_fetcher_class.return_value
        mock_cat_fetcher.fetch_all_categories.return_value = []

        # Setup mock site config fetcher
        mock_site_config = mock_site_config_class.return_value
        mock_site_config.fetch_and_store_site_metadata.return_value = None

        run_archive(args, config)

        # Verify both exporters were instantiated and called
        assert mock_html_exp.called
        assert mock_md_exp.called

        mock_html_exp.return_value.export.assert_called_once()
        mock_md_exp.return_value.export.assert_called_once()


def test_archive_command_category_filter(tmp_path, capsys):
    """Test archive command with category filtering."""
    from unittest.mock import patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://meta.discourse.org"
    args.output_dir = tmp_path / "archive"
    args.formats = "html"
    args.text_only = True
    args.include_users = False
    args.categories = "1,2,3"  # Filter specific categories
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False  # Disable sweep mode for simpler testing
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient") as mock_client_class,
        patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_class,
        patch("chronicon.cli.TopicFetcher"),
        patch("chronicon.cli.HTMLStaticExporter"),
    ):
        # Setup API client
        setup_mock_api_client_stats(mock_client_class.return_value)

        # Setup categories - some should be filtered out
        mock_cat_fetcher = mock_cat_fetcher_class.return_value
        all_categories = [
            Category(
                id=1,
                name="Cat 1",
                slug="cat-1",
                color="FF0000",
                text_color="FFFFFF",
                description=None,
                parent_category_id=None,
                topic_count=0,
            ),
            Category(
                id=2,
                name="Cat 2",
                slug="cat-2",
                color="FF0000",
                text_color="FFFFFF",
                description=None,
                parent_category_id=None,
                topic_count=0,
            ),
            Category(
                id=3,
                name="Cat 3",
                slug="cat-3",
                color="FF0000",
                text_color="FFFFFF",
                description=None,
                parent_category_id=None,
                topic_count=0,
            ),
            Category(
                id=4,
                name="Cat 4",
                slug="cat-4",
                color="FF0000",
                text_color="FFFFFF",
                description=None,
                parent_category_id=None,
                topic_count=0,
            ),  # This should be filtered
            Category(
                id=5,
                name="Cat 5",
                slug="cat-5",
                color="FF0000",
                text_color="FFFFFF",
                description=None,
                parent_category_id=None,
                topic_count=0,
            ),  # This should be filtered
        ]
        mock_cat_fetcher.fetch_all_categories.return_value = all_categories

        run_archive(args, config)

        # Check that filtering happened
        captured = capsys.readouterr()
        assert "Fetched" in captured.out


def test_archive_command_invalid_categories(tmp_path, capsys):
    """Test archive command with invalid category IDs."""
    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://meta.discourse.org"
    args.output_dir = tmp_path / "archive"
    args.formats = "html"
    args.text_only = True
    args.include_users = False
    args.categories = "not,valid,numbers"  # Invalid format
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    config = Config.defaults()

    run_archive(args, config)

    captured = capsys.readouterr()
    assert "must be comma-separated integers" in captured.out


def test_archive_command_network_error(tmp_path, capsys):
    """Test archive command handles network errors gracefully."""
    from unittest.mock import patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://meta.discourse.org"
    args.output_dir = tmp_path / "archive"
    args.formats = "html"
    args.text_only = True
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    config = Config.defaults()

    with patch("chronicon.cli.DiscourseAPIClient") as mock_client_class:
        # Simulate network error
        mock_client_class.side_effect = Exception("Network error")

        run_archive(args, config)

        captured = capsys.readouterr()
        assert "Failed to archive" in captured.out
        assert "Network error" in captured.out


def test_archive_command_export_error(tmp_path, capsys):
    """Test archive command handles export errors gracefully."""
    from unittest.mock import patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://meta.discourse.org"
    args.output_dir = tmp_path / "archive"
    args.formats = "html"
    args.text_only = True
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False  # Disable sweep mode for simpler testing
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient") as mock_client_class,
        patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_class,
        patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_class,
        patch("chronicon.cli.TopicFetcher"),
        patch("chronicon.cli.AssetDownloader") as mock_asset_class,
        patch("chronicon.cli.HTMLProcessor"),
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_exp,
    ):
        mock_client = setup_mock_api_client_stats(mock_client_class.return_value)
        mock_client.base_url = (
            "https://meta.discourse.org"  # Set base_url to string for SQLite
        )
        mock_cat_fetcher = mock_cat_fetcher_class.return_value
        mock_cat_fetcher.fetch_all_categories.return_value = []

        # Mock site config fetcher to avoid database operations
        mock_site_config = mock_site_config_class.return_value
        mock_site_config.fetch_and_store_site_metadata.return_value = None

        # Setup mock asset downloader to avoid stats display errors
        mock_asset_downloader = mock_asset_class.return_value
        mock_asset_downloader.get_stats.return_value = {
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
            "cached": 0,
            "download_rate": 0.0,
            "bytes_downloaded": 0,
            "total_queued": 0,
        }

        # Simulate export error
        mock_html_exp.return_value.export.side_effect = Exception("Export failed")

        run_archive(args, config)

        captured = capsys.readouterr()
        assert "HTML export failed" in captured.out


def test_archive_command_multiple_sites(tmp_path, capsys):
    """Test archive command with multiple sites."""
    from unittest.mock import patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://site1.org,https://site2.org"  # Two sites
    args.output_dir = tmp_path / "archive"
    args.formats = "html"
    args.text_only = True
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.CategoryFetcher") as mock_cat_fetcher_class,
        patch("chronicon.cli.TopicFetcher"),
        patch("chronicon.cli.HTMLStaticExporter"),
    ):
        mock_cat_fetcher = mock_cat_fetcher_class.return_value
        mock_cat_fetcher.fetch_all_categories.return_value = []

        run_archive(args, config)

        captured = capsys.readouterr()
        # Should see both sites being archived
        assert "site1.org" in captured.out
        assert "site2.org" in captured.out
        assert "Archive complete" in captured.out


# ============================================================================
# Update Command Tests
# ============================================================================


def test_update_command_success(sample_archive, capsys):
    """Test successful update command."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    # Create HTML export directory
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter"),
    ):
        # Setup mock update manager
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=5,
            modified_posts=2,
            new_topics=1,
            affected_topics=3,
            affected_usernames=2,
            fetch_errors=0,
            duration_seconds=10.5,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [1, 2, 3]
        mock_update_mgr.get_affected_usernames.return_value = {"user1", "user2"}

        run_update(args, config)

        captured = capsys.readouterr()
        assert "Updating archives" in captured.out
        assert "New posts: 5" in captured.out
        assert "Modified posts: 2" in captured.out
        assert "Regenerating exports" in captured.out
        assert "Archive update complete" in captured.out


def test_update_command_no_database(tmp_path, capsys):
    """Test update command with missing database."""
    from chronicon.cli import run_update

    args = Mock()
    args.output_dir = tmp_path / "nonexistent"
    args.formats = "all"
    config = Config.defaults()

    run_update(args, config)

    captured = capsys.readouterr()
    assert "No archive database found" in captured.out
    assert "chronicon archive" in captured.out  # Hint message


def test_update_command_no_updates_needed(sample_archive, capsys):
    """Test update command when archive is already up to date."""
    from unittest.mock import patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "all"
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=0,
            modified_posts=0,
            new_topics=0,
            affected_topics=0,  # No topics to regenerate
            affected_usernames=0,
            fetch_errors=0,
            duration_seconds=1.0,
        )
        mock_update_mgr.update_archive.return_value = mock_stats

        run_update(args, config)

        captured = capsys.readouterr()
        assert "up to date" in captured.out
        assert "No topics need regeneration" in captured.out


def test_update_command_all_formats(sample_archive, capsys):
    """Test update command regenerating all formats."""
    from unittest.mock import patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "all"  # Should regenerate all formats
    config = Config.defaults()

    # Create all export directories
    for format_name in ["html", "md"]:
        format_dir = sample_archive / format_name
        format_dir.mkdir()
        if format_name == "html":
            (format_dir / "index.html").write_text("<html></html>")
        elif format_name == "md":
            (format_dir / "README.md").write_text("# Archive")

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_exp,
        patch("chronicon.cli.MarkdownGitHubExporter") as mock_md_exp,
        patch("chronicon.cli.HybridExporter"),
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=5,
            modified_posts=2,
            new_topics=1,
            affected_topics=3,
            affected_usernames=2,
            fetch_errors=0,
            duration_seconds=10.5,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [1, 2, 3]
        mock_update_mgr.get_affected_usernames.return_value = {"user1", "user2"}

        run_update(args, config)

        # Verify both exporters were called
        mock_html_exp.return_value.export_topics.assert_called_once()
        mock_md_exp.return_value.export_topics.assert_called_once()


def test_update_command_format_missing_directory(sample_archive, capsys):
    """Test update command skips missing export directories."""
    from unittest.mock import patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    # Don't create HTML directory - should be skipped

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_exp,
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=5,
            modified_posts=2,
            new_topics=1,
            affected_topics=3,
            affected_usernames=2,
            fetch_errors=0,
            duration_seconds=10.5,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [1, 2, 3]
        mock_update_mgr.get_affected_usernames.return_value = {"user1", "user2"}

        run_update(args, config)

        captured = capsys.readouterr()
        assert "not found, skipping" in captured.out

        # Exporter should not have been called
        mock_html_exp.return_value.export_topics.assert_not_called()


def test_update_command_update_error(sample_archive, capsys):
    """Test update command handles update errors gracefully."""
    from unittest.mock import patch

    from chronicon.cli import run_update

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    # Create HTML directory
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter"),
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_update_mgr.update_archive.side_effect = Exception("Update failed")

        run_update(args, config)

        captured = capsys.readouterr()
        assert "Error during update" in captured.out or "Update failed" in captured.out


def test_update_command_export_regeneration_error(sample_archive, capsys):
    """Test update command handles export regeneration errors."""
    from unittest.mock import patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    # Create HTML directory
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_exp,
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=5,
            modified_posts=2,
            new_topics=1,
            affected_topics=3,
            affected_usernames=2,
            fetch_errors=0,
            duration_seconds=10.5,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [1, 2, 3]
        mock_update_mgr.get_affected_usernames.return_value = {"user1", "user2"}

        # Simulate export error
        mock_html_exp.return_value.export_topics.side_effect = Exception(
            "Export failed"
        )

        run_update(args, config)

        captured = capsys.readouterr()
        assert "Error during export regeneration" in captured.out


# ========== Phase 1: main() Argument Parsing Tests ==========


def test_main_archive_command_dispatch():
    """Test main() correctly dispatches to archive command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "archive", "--urls", "https://meta.discourse.org"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_archive") as mock_run_archive,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify run_archive was called
        mock_run_archive.assert_called_once()
        args, config = mock_run_archive.call_args[0]
        assert args.urls == "https://meta.discourse.org"
        assert args.command == "archive"


def test_main_update_command_dispatch():
    """Test main() correctly dispatches to update command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "update", "--output-dir", "./archives"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_update") as mock_run_update,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify run_update was called
        mock_run_update.assert_called_once()
        args, config = mock_run_update.call_args[0]
        assert args.command == "update"


def test_main_validate_command_dispatch():
    """Test main() correctly dispatches to validate command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "validate", "--output-dir", "./archives"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_validate") as mock_run_validate,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify run_validate was called
        mock_run_validate.assert_called_once()
        args, config = mock_run_validate.call_args[0]
        assert args.command == "validate"


def test_main_migrate_command_dispatch():
    """Test main() correctly dispatches to migrate command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "migrate", "--from", "./old_archive"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_migrate") as mock_run_migrate,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify run_migrate was called
        mock_run_migrate.assert_called_once()
        args, config = mock_run_migrate.call_args[0]
        assert args.command == "migrate"


def test_main_watch_command_dispatch():
    """Test main() correctly dispatches to watch command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "watch", "start"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_watch") as mock_run_watch,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify run_watch was called
        mock_run_watch.assert_called_once()
        args, config = mock_run_watch.call_args[0]
        assert args.command == "watch"


def test_main_missing_required_argument():
    """Test main() exits when required argument is missing."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "archive"]  # Missing --urls

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.Config.load") as mock_config,
        pytest.raises(SystemExit),
    ):
        mock_config.return_value = Config.defaults()
        main()


def test_main_invalid_command():
    """Test main() exits with invalid command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "invalid_command"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.Config.load") as mock_config,
        pytest.raises(SystemExit),
    ):
        mock_config.return_value = Config.defaults()
        main()


def test_main_debug_flag():
    """Test main() handles --debug flag correctly."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = [
        "chronicon",
        "--debug",
        "archive",
        "--urls",
        "https://meta.discourse.org",
    ]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_archive") as mock_run_archive,
        patch("chronicon.cli.Config.load") as mock_config,
        patch("chronicon.cli.setup_logging") as mock_setup_logging,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify setup_logging was called with debug=True
        mock_setup_logging.assert_called_once_with(True)
        mock_run_archive.assert_called_once()


def test_main_config_flag():
    """Test main() handles --config flag correctly."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    config_path = Path("/tmp/custom.toml")
    test_args = [
        "chronicon",
        "--config",
        str(config_path),
        "archive",
        "--urls",
        "https://meta.discourse.org",
    ]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_archive") as mock_run_archive,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        # Verify Config.load was called with the specified path
        mock_config.assert_called_once_with(config_path)
        mock_run_archive.assert_called_once()


def test_main_archive_default_arguments():
    """Test main() uses correct default values for archive command."""
    import sys
    from unittest.mock import patch

    from chronicon.cli import main

    test_args = ["chronicon", "archive", "--urls", "https://meta.discourse.org"]

    with (
        patch.object(sys, "argv", test_args),
        patch("chronicon.cli.run_archive") as mock_run_archive,
        patch("chronicon.cli.Config.load") as mock_config,
    ):
        mock_config.return_value = Config.defaults()
        main()

        args, config = mock_run_archive.call_args[0]
        # Verify defaults
        assert str(args.output_dir) == "archives"
        assert args.formats == "hybrid"
        assert args.text_only is False
        assert args.include_users is False
        assert args.workers == 8
        assert args.rate_limit == 0.5


# ========== Phase 2: run_watch() Command Tests ==========


def test_watch_start_default_formats(tmp_path):
    """Test watch start with default formats."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "start"
    args.output_dir = tmp_path
    args.formats = None
    args.daemon = False
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon") as mock_daemon_class:
        mock_daemon = mock_daemon_class.return_value

        run_watch(args, config)

        # Verify WatchDaemon was created with correct params
        mock_daemon_class.assert_called_once_with(
            output_dir=tmp_path, config=config, formats=None, daemon_mode=False
        )
        mock_daemon.start.assert_called_once()


def test_watch_start_specific_formats(tmp_path):
    """Test watch start with specific formats."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "start"
    args.output_dir = tmp_path
    args.formats = "html,markdown"
    args.daemon = False
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon") as mock_daemon_class:
        mock_daemon = mock_daemon_class.return_value

        run_watch(args, config)

        # Verify formats were parsed
        mock_daemon_class.assert_called_once_with(
            output_dir=tmp_path,
            config=config,
            formats=["html", "markdown"],
            daemon_mode=False,
        )
        mock_daemon.start.assert_called_once()


def test_watch_start_daemon_mode(tmp_path, capsys):
    """Test watch start in daemon mode shows warning."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "start"
    args.output_dir = tmp_path
    args.formats = None
    args.daemon = True
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon") as mock_daemon_class:
        run_watch(args, config)

        captured = capsys.readouterr()
        assert "Daemon mode not yet implemented" in captured.out
        assert "foreground mode" in captured.out

        # Should still create daemon with daemon_mode=False
        mock_daemon_class.assert_called_once()
        assert mock_daemon_class.call_args[1]["daemon_mode"] is False


def test_watch_start_keyboard_interrupt(tmp_path, capsys):
    """Test watch start handles KeyboardInterrupt."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "start"
    args.output_dir = tmp_path
    args.formats = None
    args.daemon = False
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon") as mock_daemon_class:
        mock_daemon = mock_daemon_class.return_value
        mock_daemon.start.side_effect = KeyboardInterrupt()

        run_watch(args, config)

        captured = capsys.readouterr()
        assert "Interrupted by user" in captured.out


def test_watch_start_exception(tmp_path, capsys):
    """Test watch start handles exceptions."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "start"
    args.output_dir = tmp_path
    args.formats = None
    args.daemon = False
    config = Config.defaults()

    with (
        patch("chronicon.cli.WatchDaemon") as mock_daemon_class,
        pytest.raises(SystemExit) as exc_info,
    ):
        mock_daemon = mock_daemon_class.return_value
        mock_daemon.start.side_effect = Exception("Watch failed")

        run_watch(args, config)

    # Should exit with code 1
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.out or "Watch failed" in captured.out


def test_watch_stop_daemon_running(tmp_path, capsys):
    """Test watch stop when daemon is running."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "stop"
    args.output_dir = tmp_path
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon.stop_daemon") as mock_stop:
        mock_stop.return_value = True

        run_watch(args, config)

        mock_stop.assert_called_once_with(tmp_path)
        captured = capsys.readouterr()
        assert "Daemon stopped" in captured.out or "stopped" in captured.out.lower()


def test_watch_stop_no_daemon(tmp_path, capsys):
    """Test watch stop when no daemon is running."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "stop"
    args.output_dir = tmp_path
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon.stop_daemon") as mock_stop:
        mock_stop.return_value = False

        run_watch(args, config)

        mock_stop.assert_called_once_with(tmp_path)
        captured = capsys.readouterr()
        assert "No daemon running" in captured.out


def test_watch_status_no_status_file(tmp_path, capsys):
    """Test watch status when no status file exists."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    args.watch_action = "status"
    args.output_dir = tmp_path
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon.get_status") as mock_get_status:
        mock_get_status.return_value = None

        run_watch(args, config)

        mock_get_status.assert_called_once_with(tmp_path)
        captured = capsys.readouterr()
        assert "No status file found" in captured.out


def test_watch_status_running_daemon(tmp_path, capsys):
    """Test watch status with running daemon."""
    from unittest.mock import patch

    from chronicon.cli import run_watch
    from chronicon.watch.status import WatchStatus

    args = Mock()
    args.watch_action = "status"
    args.output_dir = tmp_path
    config = Config.defaults()

    # Create mock status
    mock_status = WatchStatus(
        is_running=True,
        pid=12345,
        started_at="2024-01-01T12:00:00",
        uptime_seconds=3600,
        total_cycles=10,
        successful_cycles=9,
        failed_cycles=1,
        consecutive_errors=0,
        total_new_posts=50,
        total_modified_posts=10,
        total_affected_topics=20,
        last_check="2024-01-01T13:00:00",
        next_check="2024-01-01T14:00:00",
        last_error=None,
        recent_cycles=[],
    )

    with patch("chronicon.cli.WatchDaemon.get_status") as mock_get_status:
        mock_get_status.return_value = mock_status

        run_watch(args, config)

        captured = capsys.readouterr()
        assert "Running" in captured.out
        assert "12345" in captured.out  # PID
        assert "Total: 10" in captured.out  # Cycles
        assert "Total new posts: 50" in captured.out


def test_watch_status_stopped_daemon(tmp_path, capsys):
    """Test watch status with stopped daemon."""
    from unittest.mock import patch

    from chronicon.cli import run_watch
    from chronicon.watch.status import WatchStatus

    args = Mock()
    args.watch_action = "status"
    args.output_dir = tmp_path
    config = Config.defaults()

    mock_status = WatchStatus(
        is_running=False,
        pid=None,
        started_at="2024-01-01T12:00:00",
        uptime_seconds=3600,
        total_cycles=5,
        successful_cycles=5,
        failed_cycles=0,
        consecutive_errors=0,
        total_new_posts=10,
        total_modified_posts=5,
        total_affected_topics=3,
        last_check=None,
        next_check=None,
        last_error=None,
        recent_cycles=[],
    )

    with patch("chronicon.cli.WatchDaemon.get_status") as mock_get_status:
        mock_get_status.return_value = mock_status

        run_watch(args, config)

        captured = capsys.readouterr()
        assert "Stopped" in captured.out


def test_watch_status_with_recent_cycles(tmp_path, capsys):
    """Test watch status displays recent cycles."""
    from unittest.mock import patch

    from chronicon.cli import run_watch
    from chronicon.watch.status import WatchCycleResult, WatchStatus

    args = Mock()
    args.watch_action = "status"
    args.output_dir = tmp_path
    config = Config.defaults()

    recent_cycles = [
        WatchCycleResult(
            timestamp="2024-01-01T12:00:00",
            success=True,
            new_posts=5,
            modified_posts=2,
            affected_topics=3,
            duration_seconds=10.5,
            error_message=None,
        ),
        WatchCycleResult(
            timestamp="2024-01-01T13:00:00",
            success=True,
            new_posts=0,
            modified_posts=0,
            affected_topics=0,
            duration_seconds=5.2,
            error_message=None,
        ),
        WatchCycleResult(
            timestamp="2024-01-01T14:00:00",
            success=False,
            new_posts=0,
            modified_posts=0,
            affected_topics=0,
            duration_seconds=2.0,
            error_message="Network error",
        ),
    ]

    mock_status = WatchStatus(
        is_running=True,
        pid=12345,
        started_at="2024-01-01T12:00:00",
        uptime_seconds=7200,
        total_cycles=3,
        successful_cycles=2,
        failed_cycles=1,
        consecutive_errors=1,
        total_new_posts=5,
        total_modified_posts=2,
        total_affected_topics=3,
        last_check="2024-01-01T14:00:00",
        next_check="2024-01-01T15:00:00",
        last_error="Network error",
        recent_cycles=recent_cycles,
    )

    with patch("chronicon.cli.WatchDaemon.get_status") as mock_get_status:
        mock_get_status.return_value = mock_status

        run_watch(args, config)

        captured = capsys.readouterr()
        assert "Recent Cycles:" in captured.out
        assert "5 new, 2 modified" in captured.out
        assert "No changes" in captured.out
        assert "Network error" in captured.out
        assert "Last Error:" in captured.out


def test_watch_status_with_last_error(tmp_path, capsys):
    """Test watch status displays last error."""
    from unittest.mock import patch

    from chronicon.cli import run_watch
    from chronicon.watch.status import WatchStatus

    args = Mock()
    args.watch_action = "status"
    args.output_dir = tmp_path
    config = Config.defaults()

    mock_status = WatchStatus(
        is_running=True,
        pid=12345,
        started_at="2024-01-01T12:00:00",
        uptime_seconds=3600,
        total_cycles=10,
        successful_cycles=8,
        failed_cycles=2,
        consecutive_errors=1,
        total_new_posts=50,
        total_modified_posts=10,
        total_affected_topics=20,
        last_check="2024-01-01T13:00:00",
        next_check="2024-01-01T14:00:00",
        last_error="Connection timeout",
        recent_cycles=[],
    )

    with patch("chronicon.cli.WatchDaemon.get_status") as mock_get_status:
        mock_get_status.return_value = mock_status

        run_watch(args, config)

        captured = capsys.readouterr()
        assert "Last Error:" in captured.out
        assert "Connection timeout" in captured.out


def test_watch_start_no_watch_action(tmp_path):
    """Test watch defaults to start when no action specified."""
    from unittest.mock import patch

    from chronicon.cli import run_watch

    args = Mock()
    # No watch_action attribute (simulates "chronicon watch")
    delattr(args, "watch_action") if hasattr(args, "watch_action") else None
    args.output_dir = tmp_path
    args.formats = None
    args.daemon = False
    config = Config.defaults()

    with patch("chronicon.cli.WatchDaemon") as mock_daemon_class:
        mock_daemon = mock_daemon_class.return_value

        run_watch(args, config)

        # Should default to start action
        mock_daemon_class.assert_called_once()
        mock_daemon.start.assert_called_once()


# ========== Phase 3: run_archive() Edge Cases ==========


def test_archive_http_url_warning(tmp_path, capsys):
    """Test archive shows warning for HTTP URLs (non-localhost)."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "http://example.com"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site"):
        run_archive(args, config)

    captured = capsys.readouterr()
    assert "Warning" in captured.out or "HTTP" in captured.out
    assert "unencrypted" in captured.out.lower() or "security" in captured.out.lower()


def test_archive_https_url_no_warning(tmp_path, capsys):
    """Test archive does not warn for HTTPS URLs."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://example.com"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site"):
        run_archive(args, config)

    captured = capsys.readouterr()
    # Should NOT contain HTTP warning for HTTPS
    assert "unencrypted HTTP" not in captured.out


def test_archive_http_localhost_no_warning(tmp_path, capsys):
    """Test archive does not warn for HTTP localhost."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "http://localhost:3000"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site"):
        run_archive(args, config)

    captured = capsys.readouterr()
    # Should NOT warn for localhost
    assert "unencrypted HTTP" not in captured.out


def test_archive_http_127_no_warning(tmp_path, capsys):
    """Test archive does not warn for HTTP 127.0.0.1."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "http://127.0.0.1:3000"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site"):
        run_archive(args, config)

    captured = capsys.readouterr()
    # Should NOT warn for 127.0.0.1
    assert "unencrypted HTTP" not in captured.out


def test_archive_invalid_url(tmp_path, capsys):
    """Test archive handles invalid URL validation error."""
    from unittest.mock import Mock

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "not-a-valid-url"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    result = run_archive(args, config)

    captured = capsys.readouterr()
    assert "Invalid URL" in captured.out or "Error" in captured.out
    # Should return error code
    assert result == 1


def test_archive_keyboard_interrupt(tmp_path, capsys):
    """Test archive handles KeyboardInterrupt gracefully."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://example.com"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site") as mock_archive:
        mock_archive.side_effect = KeyboardInterrupt()

        run_archive(args, config)

    captured = capsys.readouterr()
    assert "interrupted" in captured.out.lower()


def test_archive_exception_continues_to_next_site(tmp_path, capsys):
    """Test archive continues to next site after exception."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://site1.com,https://site2.com"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site") as mock_archive:
        # First site fails, second succeeds
        mock_archive.side_effect = [Exception("Network error"), None]

        run_archive(args, config)

    # Should have called _archive_site twice
    assert mock_archive.call_count == 2
    captured = capsys.readouterr()
    assert "Failed" in captured.out or "error" in captured.out.lower()


def test_archive_invalid_categories_format(tmp_path, capsys):
    """Test archive handles invalid category format."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://example.com"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = "not-a-number,abc"  # Invalid
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site"):
        run_archive(args, config)

    captured = capsys.readouterr()
    assert "categories" in captured.out.lower() and "integer" in captured.out.lower()


def test_archive_multiple_sites(tmp_path):
    """Test archive processes multiple sites."""
    from unittest.mock import Mock, patch

    from chronicon.cli import run_archive

    args = Mock()
    args.urls = "https://site1.com,https://site2.com,https://site3.com"
    args.output_dir = tmp_path
    args.formats = "html"
    args.text_only = False
    args.include_users = False
    args.categories = None
    args.since = None
    args.workers = 8
    args.rate_limit = 0.5
    args.sweep = False
    args.start_id = None
    args.end_id = 1
    config = Config.defaults()

    with patch("chronicon.cli._archive_site") as mock_archive:
        run_archive(args, config)

    # Should have called _archive_site 3 times
    assert mock_archive.call_count == 3


# ========== Phase 4: run_update() Edge Cases ==========


def test_update_database_open_error(tmp_path, capsys):
    """Test update handles database open error."""
    from unittest.mock import patch

    from chronicon.cli import run_update

    # Create a database file
    db_path = tmp_path / "archive.db"
    db_path.touch()

    args = Mock()
    args.output_dir = tmp_path
    args.formats = "html"
    config = Config.defaults()

    with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
        mock_db_class.side_effect = Exception("Database corrupted")

        run_update(args, config)

    captured = capsys.readouterr()
    assert "Error opening database" in captured.out


def test_update_no_site_metadata(sample_archive, capsys):
    """Test update handles missing site metadata."""
    from chronicon.cli import run_update

    # Remove site metadata from sample_archive
    db = ArchiveDatabase(sample_archive / "archive.db")
    cursor = db.connection.cursor()
    cursor.execute("DELETE FROM site_metadata")
    db.connection.commit()
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    run_update(args, config)

    captured = capsys.readouterr()
    assert "No site metadata found" in captured.out


def test_update_site_metadata_query_error(sample_archive, capsys):
    """Test update handles site metadata query error."""
    from unittest.mock import patch

    from chronicon.cli import run_update

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.connection.cursor.return_value.execute.side_effect = Exception(
            "Query failed"
        )

        run_update(args, config)

    captured = capsys.readouterr()
    assert "Error reading site metadata" in captured.out


def test_update_api_client_init_error(sample_archive, capsys):
    """Test update handles API client initialization error."""
    from unittest.mock import patch

    from chronicon.cli import run_update

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    with patch("chronicon.cli.DiscourseAPIClient") as mock_client_class:
        mock_client_class.side_effect = Exception("Invalid URL")

        run_update(args, config)

    captured = capsys.readouterr()
    assert "Error initializing API client" in captured.out


def test_update_site_metadata_refresh_failure_warning(sample_archive, capsys):
    """Test update shows warning for site metadata refresh failure."""
    from unittest.mock import patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.SiteConfigFetcher") as mock_site_config_class,
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=1,
            modified_posts=0,
            new_topics=1,
            affected_topics=1,
            affected_usernames=1,
            fetch_errors=0,
            duration_seconds=5.0,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [1]
        mock_update_mgr.get_affected_usernames.return_value = {"user1"}

        # Site metadata refresh fails
        mock_site_config = mock_site_config_class.return_value
        mock_site_config.fetch_and_store_site_metadata.side_effect = Exception(
            "Network error"
        )

        # Need to mock exporters too
        with patch("chronicon.cli.HTMLStaticExporter"):
            run_update(args, config)

    captured = capsys.readouterr()
    # Should show warning, not error
    assert "Could not refresh site metadata" in captured.out or "⚠" in captured.out


# ========== Phase 5: run_validate() Edge Cases ==========


def test_validate_database_open_error(tmp_path, capsys):
    """Test validate handles database open error."""
    from unittest.mock import patch

    from chronicon.cli import run_validate

    # Create corrupted database
    db_path = tmp_path / "archive.db"
    db_path.touch()

    args = Mock()
    args.output_dir = tmp_path
    config = Config.defaults()

    with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
        mock_db_class.side_effect = Exception("Database corrupted")

        run_validate(args, config)

    captured = capsys.readouterr()
    assert "Cannot open database" in captured.out


def test_validate_statistics_error(sample_archive, capsys):
    """Test validate handles statistics query error."""
    from unittest.mock import patch

    from chronicon.cli import run_validate

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_statistics.side_effect = Exception("Query failed")

        run_validate(args, config)

    captured = capsys.readouterr()
    assert "Error reading statistics" in captured.out


def test_validate_empty_archive_warnings(sample_archive, capsys):
    """Test validate shows warnings for empty archive."""
    from chronicon.cli import run_validate

    # Delete all topics and posts
    db = ArchiveDatabase(sample_archive / "archive.db")
    cursor = db.connection.cursor()
    cursor.execute("DELETE FROM posts")
    cursor.execute("DELETE FROM topics")
    db.connection.commit()
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "No topics found" in captured.out or "No posts found" in captured.out


def test_validate_markdown_export_missing_topics(sample_archive, capsys):
    """Test validate detects missing topics directory in markdown export."""
    from chronicon.cli import run_validate

    # Record a markdown export but don't create t directory
    db = ArchiveDatabase(sample_archive / "archive.db")
    markdown_dir = sample_archive / "md"
    markdown_dir.mkdir()
    db.record_export("md", 1, 1, str(markdown_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "t directory missing" in captured.out.lower()


def test_validate_markdown_export_missing_metadata(sample_archive, capsys):
    """Test validate detects missing README in markdown export."""
    from chronicon.cli import run_validate

    # Record a markdown export with topics but no README
    db = ArchiveDatabase(sample_archive / "archive.db")
    markdown_dir = sample_archive / "md"
    markdown_dir.mkdir()
    (markdown_dir / "t").mkdir()
    db.record_export("md", 1, 1, str(markdown_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "readme" in captured.out.lower()


def test_validate_github_export_missing_readme(sample_archive, capsys):
    """Test validate detects missing README.md in github export."""
    from chronicon.cli import run_validate

    # Record a github export but don't create README
    db = ArchiveDatabase(sample_archive / "archive.db")
    github_dir = sample_archive / "github"
    github_dir.mkdir()
    (github_dir / "topics").mkdir()
    db.record_export("github", 1, 1, str(github_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "README.md missing" in captured.out


def test_validate_export_check_exception(sample_archive, capsys):
    """Test validate handles export check exception."""
    from unittest.mock import patch

    from chronicon.cli import run_validate

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
        mock_db = mock_db_class.return_value
        mock_db.get_statistics.return_value = {
            "total_categories": 1,
            "total_topics": 1,
            "total_posts": 1,
            "total_users": 1,
        }
        mock_db.get_export_history.side_effect = Exception("Export query failed")

        run_validate(args, config)

    captured = capsys.readouterr()
    assert "Error checking exports" in captured.out


def test_validate_data_integrity_error(sample_archive, capsys):
    """Test validate handles data integrity check error."""
    from unittest.mock import patch

    from chronicon.cli import run_validate

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_statistics.return_value = {
            "total_categories": 1,
            "total_topics": 1,
            "total_posts": 1,
            "total_users": 1,
        }
        mock_db.get_export_history.return_value = []
        # Make connection.cursor().execute() fail for integrity check
        mock_db.connection.cursor.return_value.execute.side_effect = Exception(
            "Integrity query failed"
        )

        run_validate(args, config)

    captured = capsys.readouterr()
    assert (
        "Error checking data integrity" in captured.out
        or "integrity" in captured.out.lower()
    )


def test_validate_html_export_missing_index(sample_archive, capsys):
    """Test validate detects missing index.html in HTML export."""
    from chronicon.cli import run_validate

    # Create HTML export without index.html
    db = ArchiveDatabase(sample_archive / "archive.db")
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "assets").mkdir()
    db.record_export("html", 1, 1, str(html_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "index.html missing" in captured.out.lower()


def test_validate_html_export_missing_assets(sample_archive, capsys):
    """Test validate detects missing assets directory in HTML export."""
    from chronicon.cli import run_validate

    # Create HTML export with index but no assets
    db = ArchiveDatabase(sample_archive / "archive.db")
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")
    db.record_export("html", 1, 1, str(html_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "assets" in captured.out.lower() and "missing" in captured.out.lower()


def test_validate_markdown_export_directory_missing(sample_archive, capsys):
    """Test validate detects missing markdown export directory."""
    from chronicon.cli import run_validate

    # Record export but don't create directory at all
    db = ArchiveDatabase(sample_archive / "archive.db")
    markdown_dir = sample_archive / "markdown_nonexistent"
    db.record_export("markdown", 1, 1, str(markdown_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert (
        "directory not found" in captured.out.lower()
        or "directory missing" in captured.out.lower()
    )


def test_validate_github_export_directory_missing(sample_archive, capsys):
    """Test validate detects missing github export directory."""
    from chronicon.cli import run_validate

    # Record export but don't create directory
    db = ArchiveDatabase(sample_archive / "archive.db")
    github_dir = sample_archive / "github_nonexistent"
    db.record_export("github", 1, 1, str(github_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert (
        "directory not found" in captured.out.lower()
        or "directory missing" in captured.out.lower()
    )


def test_validate_github_export_missing_topics(sample_archive, capsys):
    """Test validate detects missing topics directory in markdown export."""
    from chronicon.cli import run_validate

    # Create markdown export with README but no t directory
    db = ArchiveDatabase(sample_archive / "archive.db")
    md_dir = sample_archive / "md"
    md_dir.mkdir()
    (md_dir / "README.md").write_text("# Archive")
    db.record_export("md", 1, 1, str(md_dir))
    db.close()

    args = Mock()
    args.output_dir = sample_archive
    config = Config.defaults()

    run_validate(args, config)

    captured = capsys.readouterr()
    assert "t directory missing" in captured.out.lower()


# ========== Phase 6: run_migrate() Edge Cases ==========


def test_migrate_migration_error(tmp_path, capsys):
    """Test migrate handles migration error gracefully."""
    from unittest.mock import patch

    from chronicon.cli import run_migrate

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    # Create a JSON file
    (source_dir / "test.json").write_text('{"test": "data"}')

    args = Mock()
    args.source_dir = source_dir
    args.format = None
    config = Config.defaults()

    with (
        patch("chronicon.cli.ArchiveDatabase"),
        patch("chronicon.storage.migrations.JSONMigrator") as mock_migrator_class,
    ):
        mock_migrator = mock_migrator_class.return_value
        mock_migrator.migrate_all.side_effect = Exception("Migration failed")

        run_migrate(args, config)

    captured = capsys.readouterr()
    assert "Migration failed" in captured.out


def test_migrate_with_errors_displays_count(tmp_path, capsys):
    """Test migrate displays error count when errors occurred."""
    from unittest.mock import patch

    from chronicon.cli import run_migrate

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test.json").write_text('{"test": "data"}')

    args = Mock()
    args.source_dir = source_dir
    args.format = None
    config = Config.defaults()

    with (
        patch("chronicon.cli.ArchiveDatabase"),
        patch("chronicon.storage.migrations.JSONMigrator") as mock_migrator_class,
    ):
        mock_migrator = mock_migrator_class.return_value
        mock_migrator.migrate_all.return_value = {
            "posts_imported": 10,
            "topics_imported": 5,
            "errors": 3,  # Has errors
        }

        run_migrate(args, config)

    captured = capsys.readouterr()
    assert "Errors encountered: 3" in captured.out or "errors" in captured.out.lower()


def test_update_command_calls_export_users_by_username(sample_archive, capsys):
    """Test that update command calls export_users_by_username on exporters."""
    from unittest.mock import MagicMock, Mock, patch

    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()
    config.include_users = True

    # Create HTML export directory
    html_dir = sample_archive / "html"
    html_dir.mkdir(exist_ok=True)
    (html_dir / "index.html").write_text("<html></html>")

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter") as mock_html_class,
        patch("chronicon.cli.SiteConfigFetcher"),
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=3,
            modified_posts=1,
            new_topics=1,
            affected_topics=2,
            affected_usernames=2,
            fetch_errors=0,
            duration_seconds=5.0,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [1, 2]
        mock_update_mgr.get_affected_usernames.return_value = {"alice", "bob"}

        mock_html_instance = MagicMock()
        mock_html_class.return_value = mock_html_instance

        run_update(args, config)

        # Verify export_users_by_username was called with affected usernames
        mock_html_instance.export_users_by_username.assert_called_once_with(
            {"alice", "bob"}
        )


def test_update_command_downloads_assets_for_affected_topics(sample_archive, capsys):
    """Test that run_update downloads assets (medium+highest) for affected topics."""
    from chronicon.cli import run_update
    from chronicon.models.post import Post
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    # Create HTML export directory
    html_dir = sample_archive / "html"
    html_dir.mkdir()
    (html_dir / "index.html").write_text("<html></html>")

    # Create a post with image content
    mock_post = Post(
        id=101,
        topic_id=42,
        user_id=1,
        post_number=1,
        username="testuser",
        raw="test",
        cooked='<img src="https://cdn.example.com/img_690w.webp">',
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.HTMLStaticExporter"),
        patch("chronicon.cli.AssetDownloader") as mock_asset_dl_class,
        patch("chronicon.cli.HTMLProcessor") as mock_html_proc_class,
        patch("chronicon.cli.SiteConfigFetcher"),
    ):
        # Setup mock update manager
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=1,
            modified_posts=0,
            new_topics=1,
            affected_topics=1,
            affected_usernames=1,
            fetch_errors=0,
            duration_seconds=2.0,
        )
        mock_update_mgr.update_archive.return_value = mock_stats
        mock_update_mgr.get_topics_to_regenerate.return_value = [42]
        mock_update_mgr.get_affected_usernames.return_value = {"testuser"}

        # Setup mock HTML processor to return image sets
        mock_html_proc = mock_html_proc_class.return_value
        mock_html_proc.extract_image_sets.return_value = {
            "img_base": {
                "all_urls": [
                    "https://cdn.example.com/img_690w.webp",
                    "https://cdn.example.com/img_1380w.webp",
                ],
                "medium": "https://cdn.example.com/img_690w.webp",
                "highest": "https://cdn.example.com/img_1380w.webp",
            }
        }

        # Setup mock asset downloader
        mock_asset_dl = mock_asset_dl_class.return_value

        # Mock db.get_topic_posts to return our test post
        # The actual db is opened from sample_archive/archive.db, so we need
        # to patch the database's get_topic_posts method
        with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db
            mock_db.connection.cursor.return_value.fetchone.return_value = {
                "site_url": "https://example.com"
            }
            mock_db.get_topic_posts.return_value = [mock_post]

            run_update(args, config)

        # Verify asset downloader was called with medium and highest
        download_calls = mock_asset_dl.download_image.call_args_list
        downloaded_urls = [call[0][0] for call in download_calls]
        assert "https://cdn.example.com/img_690w.webp" in downloaded_urls
        assert "https://cdn.example.com/img_1380w.webp" in downloaded_urls


def test_update_command_skips_asset_download_when_no_changes(sample_archive, capsys):
    """Test that run_update skips asset download when there are no affected topics."""
    from chronicon.cli import run_update
    from chronicon.utils.update_manager import UpdateStatistics

    args = Mock()
    args.output_dir = sample_archive
    args.formats = "html"
    config = Config.defaults()

    with (
        patch("chronicon.cli.DiscourseAPIClient"),
        patch("chronicon.cli.UpdateManager") as mock_update_mgr_class,
        patch("chronicon.cli.AssetDownloader") as mock_asset_dl_class,
    ):
        mock_update_mgr = mock_update_mgr_class.return_value
        mock_stats = UpdateStatistics(
            new_posts=0,
            modified_posts=0,
            new_topics=0,
            affected_topics=0,
            affected_usernames=0,
            fetch_errors=0,
            duration_seconds=1.0,
        )
        mock_update_mgr.update_archive.return_value = mock_stats

        with patch("chronicon.cli.ArchiveDatabase") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db
            mock_db.connection.cursor.return_value.fetchone.return_value = {
                "site_url": "https://example.com"
            }

            run_update(args, config)

        # AssetDownloader should not have been used for downloads
        mock_asset_dl = mock_asset_dl_class.return_value
        mock_asset_dl.download_image.assert_not_called()
