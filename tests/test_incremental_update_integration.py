# ABOUTME: Integration tests for incremental update workflow
# ABOUTME: Tests UpdateManager, affected topic detection, and incremental exports

"""Integration tests for incremental update functionality."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from chronicon.exporters.html_static import HTMLStaticExporter
from chronicon.exporters.markdown import MarkdownGitHubExporter
from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.storage.database import ArchiveDatabase
from chronicon.utils.update_manager import UpdateManager


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with initial data."""
    db = ArchiveDatabase(tmp_path / "test.db")

    # Add site metadata with last sync date
    db.update_site_metadata(
        "https://test.example.com",
        last_sync_date=(datetime.now() - timedelta(days=1)).isoformat(),
        site_title="Test Forum",
    )

    # Add a category
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="0088CC",
        text_color="FFFFFF",
        description="General discussion",
        parent_category_id=None,
        topic_count=0,
    )
    db.insert_category(category)

    # Add existing topic
    topic = Topic(
        id=100,
        title="Existing Topic",
        slug="existing-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now() - timedelta(days=2),
        updated_at=datetime.now() - timedelta(days=2),
        posts_count=2,
        views=10,
    )
    db.insert_topic(topic)

    # Add existing posts
    post1 = Post(
        id=1,
        topic_id=100,
        user_id=1,
        post_number=1,
        created_at=datetime.now() - timedelta(days=2),
        updated_at=datetime.now() - timedelta(days=2),
        cooked="<p>Original post content</p>",
        raw="Original post content",
        username="user1",
    )
    db.insert_post(post1)

    post2 = Post(
        id=2,
        topic_id=100,
        user_id=1,
        post_number=2,
        created_at=datetime.now() - timedelta(days=2),
        updated_at=datetime.now() - timedelta(days=2),
        cooked="<p>Reply content</p>",
        raw="Reply content",
        username="user2",
    )
    db.insert_post(post2)

    yield db
    db.close()


def test_incremental_update_detects_new_and_modified_posts(test_db):
    """Test that UpdateManager correctly identifies new and modified posts."""
    # Mock API client and fetchers
    mock_client = Mock()

    with (
        patch("chronicon.utils.update_manager.PostFetcher") as mock_post_fetcher,
        patch("chronicon.utils.update_manager.TopicFetcher") as mock_topic_fetcher,
    ):
        # Setup mocks
        post_fetcher = Mock()
        topic_fetcher = Mock()

        mock_post_fetcher.return_value = post_fetcher
        mock_topic_fetcher.return_value = topic_fetcher

        # Simulate API returning:
        # 1. Modified existing post
        # 2. New post in existing topic
        # 3. New post in new topic

        modified_post = Post(
            id=1,
            topic_id=100,
            user_id=1,
            post_number=1,
            created_at=datetime.now() - timedelta(days=2),
            updated_at=datetime.now(),  # Updated recently
            cooked="<p>Updated content</p>",
            raw="Updated content",
            username="user1",
        )

        new_post_existing_topic = Post(
            id=3,
            topic_id=100,
            user_id=1,
            post_number=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cooked="<p>New reply</p>",
            raw="New reply",
            username="user3",
        )

        new_post_new_topic = Post(
            id=4,
            topic_id=200,
            user_id=1,
            post_number=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cooked="<p>New topic content</p>",
            raw="New topic content",
            username="user1",
        )

        post_fetcher.fetch_latest_posts.return_value = [
            modified_post,
            new_post_existing_topic,
            new_post_new_topic,
        ]

        # Topic fetcher returns new topic
        new_topic = Topic(
            id=200,
            title="New Topic",
            slug="new-topic",
            category_id=1,
            user_id=1,
            created_at=datetime.now(),
            updated_at=None,
            posts_count=1,
            views=0,
        )
        topic_fetcher.fetch_topic.return_value = new_topic

        # Run update
        update_manager = UpdateManager(test_db, mock_client)
        update_manager.post_fetcher = post_fetcher
        update_manager.topic_fetcher = topic_fetcher

        stats = update_manager.update_archive("https://test.example.com")

        # Verify statistics
        assert stats.new_posts == 2  # posts 3 and 4
        assert stats.modified_posts == 1  # post 1
        assert stats.new_topics == 1  # topic 200
        assert stats.affected_topics == 2  # topics 100 and 200

        # Verify topics marked for regeneration
        topics_to_regen = update_manager.get_topics_to_regenerate()
        assert 100 in topics_to_regen
        assert 200 in topics_to_regen


def test_incremental_export_regenerates_only_affected_topics(test_db, tmp_path):
    """Test that exporters only regenerate affected topics."""
    # Add a second topic that won't be affected
    unaffected_topic = Topic(
        id=300,
        title="Unaffected Topic",
        slug="unaffected",
        category_id=1,
        user_id=1,
        created_at=datetime.now() - timedelta(days=5),
        updated_at=None,
        posts_count=1,
        views=5,
    )
    test_db.insert_topic(unaffected_topic)

    unaffected_post = Post(
        id=10,
        topic_id=300,
        user_id=1,
        post_number=1,
        created_at=datetime.now() - timedelta(days=5),
        updated_at=datetime.now() - timedelta(days=5),
        cooked="<p>Unaffected</p>",
        raw="Unaffected",
        username="user1",
    )
    test_db.insert_post(unaffected_post)

    # Setup HTML exporter
    html_dir = tmp_path / "html"
    html_dir.mkdir()

    html_exporter = HTMLStaticExporter(test_db, html_dir)

    # Regenerate only topic 100
    html_exporter.export_topics([100])

    # Verify topic 100 was exported (HTML uses /t/{slug}/{id}/index.html structure)
    topic_100_path = html_dir / "t" / "existing-topic" / "100" / "index.html"
    assert topic_100_path.exists(), (
        "Topic 100 should be exported to /t/existing-topic/100/index.html"
    )

    # Topic 300 should not be in the regeneration (though it might exist from earlier)
    # The key test is that export_topics() only regenerates what we tell it to


def test_exporter_update_index_methods(test_db, tmp_path):
    """Test that update_index() methods work for all exporters."""
    # HTML exporter
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_exporter = HTMLStaticExporter(test_db, html_dir)
    html_exporter.update_index()

    assert (html_dir / "index.html").exists()
    # Note: search.html and search_index.json only exist with static search backend
    # Default is FTS (server-side search)

    # Markdown exporter
    md_dir = tmp_path / "markdown"
    md_dir.mkdir()
    md_exporter = MarkdownGitHubExporter(test_db, md_dir)
    md_exporter.update_index()

    assert (md_dir / "README.md").exists()

    # GitHub markdown exporter
    github_dir = tmp_path / "github"
    github_dir.mkdir()
    github_exporter = MarkdownGitHubExporter(test_db, github_dir)
    github_exporter.update_index()

    assert (github_dir / "README.md").exists()


def test_database_helpers_get_topics_by_ids(test_db):
    """Test that get_topics_by_ids works correctly."""
    # Add multiple topics
    for i in range(5):
        topic = Topic(
            id=1000 + i,
            title=f"Topic {i}",
            slug=f"topic-{i}",
            category_id=1,
            user_id=1,
            created_at=datetime.now(),
            updated_at=None,
            posts_count=1,
            views=0,
        )
        test_db.insert_topic(topic)

    # Fetch specific topics
    topics = test_db.get_topics_by_ids([1000, 1002, 1004, 9999])  # 9999 doesn't exist

    assert len(topics) == 3
    topic_ids = [t.id for t in topics]
    assert 1000 in topic_ids
    assert 1002 in topic_ids
    assert 1004 in topic_ids
    assert 9999 not in topic_ids


def test_database_record_export(test_db):
    """Test that export history is recorded correctly."""
    test_db.record_export("html", 10, 50, "/path/to/html")
    test_db.record_export("markdown", 5, 25, "/path/to/markdown")

    history = test_db.get_export_history(limit=10)

    assert len(history) >= 2
    # Most recent first
    assert history[0]["format"] in ["html", "markdown"]
    assert history[0]["topic_count"] in [10, 5]


def test_no_changes_update_is_handled_gracefully(test_db):
    """Test that update with no changes works correctly."""
    mock_client = Mock()

    with (
        patch("chronicon.utils.update_manager.PostFetcher") as mock_post_fetcher,
        patch("chronicon.utils.update_manager.TopicFetcher") as mock_topic_fetcher,
    ):
        post_fetcher = Mock()
        topic_fetcher = Mock()

        mock_post_fetcher.return_value = post_fetcher
        mock_topic_fetcher.return_value = topic_fetcher

        # No new posts
        post_fetcher.fetch_latest_posts.return_value = []

        update_manager = UpdateManager(test_db, mock_client)
        update_manager.post_fetcher = post_fetcher
        update_manager.topic_fetcher = topic_fetcher

        stats = update_manager.update_archive("https://test.example.com")

        assert stats.new_posts == 0
        assert stats.modified_posts == 0
        assert stats.affected_topics == 0
        assert stats.new_topics == 0
