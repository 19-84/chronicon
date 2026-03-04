# Test suite for UpdateManager incremental update functionality

"""Tests for UpdateManager class."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.utils.update_manager import UpdateManager


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock()
    db.get_site_metadata.return_value = {
        "last_sync_date": (datetime.now() - timedelta(days=1)).isoformat()
    }
    db.get_post.return_value = None  # Default: no existing post
    db.insert_post = Mock()
    db.update_post = Mock()
    db.get_topic.return_value = None
    db.insert_topic = Mock()
    db.update_site_metadata = Mock()
    return db


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = Mock()
    return client


@pytest.fixture
def update_manager(mock_db, mock_client):
    """Create UpdateManager with mocked dependencies."""
    with (
        patch("chronicon.utils.update_manager.PostFetcher") as mock_post_fetcher,
        patch("chronicon.utils.update_manager.TopicFetcher") as mock_topic_fetcher,
    ):
        post_fetcher = Mock()
        topic_fetcher = Mock()

        mock_post_fetcher.return_value = post_fetcher
        mock_topic_fetcher.return_value = topic_fetcher

        manager = UpdateManager(mock_db, mock_client)
        manager.post_fetcher = post_fetcher
        manager.topic_fetcher = topic_fetcher

        return manager


def create_post(
    post_id, topic_id, created_at=None, updated_at=None, username="testuser"
):
    """Helper to create a Post instance."""
    if created_at is None:
        created_at = datetime.now()
    if updated_at is None:
        updated_at = created_at

    return Post(
        id=post_id,
        topic_id=topic_id,
        user_id=1,
        post_number=1,
        created_at=created_at,
        updated_at=updated_at,
        cooked="<p>Test</p>",
        raw="Test",
        username=username,
    )


def test_update_archive_no_previous_sync(mock_db, update_manager):
    """Test update when there's no previous sync date."""
    mock_db.get_site_metadata.return_value = {}

    stats = update_manager.update_archive("https://example.com")

    assert stats.new_posts == 0
    assert stats.modified_posts == 0
    assert stats.affected_topics == 0


def test_update_archive_with_new_posts(mock_db, update_manager):
    """Test update correctly identifies new posts."""
    # Setup: post fetcher returns new posts
    new_post1 = create_post(1, 100)
    new_post2 = create_post(2, 101)

    update_manager.post_fetcher.fetch_latest_posts.return_value = [
        new_post1,
        new_post2,
    ]

    # DB says these posts don't exist
    mock_db.get_post.return_value = None

    # DB has topics
    mock_db.get_topic.return_value = Topic(
        id=100,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )

    stats = update_manager.update_archive("https://example.com")

    assert stats.new_posts == 2
    assert stats.modified_posts == 0
    assert stats.affected_topics == 2
    assert mock_db.insert_post.call_count == 2


def test_update_archive_with_modified_posts(mock_db, update_manager):
    """Test update correctly identifies modified posts."""
    # Setup: post fetcher returns modified post
    old_time = datetime.now() - timedelta(hours=2)
    new_time = datetime.now()

    # Existing post in DB
    existing_post = create_post(1, 100, created_at=old_time, updated_at=old_time)

    # Updated post from API
    updated_post = create_post(1, 100, created_at=old_time, updated_at=new_time)

    update_manager.post_fetcher.fetch_latest_posts.return_value = [updated_post]

    # Mock DB to return existing post
    mock_db.get_post.return_value = existing_post

    # DB has topic
    mock_db.get_topic.return_value = Topic(
        id=100,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )

    stats = update_manager.update_archive("https://example.com")

    assert stats.new_posts == 0
    assert stats.modified_posts == 1
    assert stats.affected_topics == 1
    assert mock_db.update_post.call_count == 1


def test_update_archive_fetches_missing_topics(mock_db, update_manager):
    """Test that missing topics are fetched when new posts are found."""
    # Setup: new post in a topic not in DB
    new_post = create_post(1, 999)

    update_manager.post_fetcher.fetch_latest_posts.return_value = [new_post]

    # DB says post doesn't exist
    mock_db.get_post.return_value = None

    # DB says topic doesn't exist initially
    mock_db.get_topic.return_value = None

    # Topic fetcher returns the topic
    topic = Topic(
        id=999,
        title="New Topic",
        slug="new-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )
    update_manager.topic_fetcher.fetch_topic.return_value = topic

    stats = update_manager.update_archive("https://example.com")

    assert stats.new_posts == 1
    assert stats.new_topics == 1
    update_manager.topic_fetcher.fetch_topic.assert_called_once_with(999)
    mock_db.insert_topic.assert_called_once()


def test_get_topics_to_regenerate(update_manager):
    """Test that get_topics_to_regenerate returns the tracked topics."""
    # Manually mark some topics
    update_manager._mark_topic_for_regeneration(100)
    update_manager._mark_topic_for_regeneration(200)
    update_manager._mark_topic_for_regeneration(300)

    topics = update_manager.get_topics_to_regenerate()

    assert topics == {100, 200, 300}
    # Should return a copy, not the original set
    assert topics is not update_manager._topics_to_regenerate


def test_update_archive_with_fetch_errors(mock_db, update_manager):
    """Test that fetch errors are tracked."""
    # Setup: fetcher raises exception
    update_manager.post_fetcher.fetch_latest_posts.side_effect = Exception("API Error")

    stats = update_manager.update_archive("https://example.com")

    assert stats.fetch_errors == 1
    assert stats.new_posts == 0
    assert stats.modified_posts == 0


def test_update_manager_date_buffer(mock_db, update_manager):
    """Test that update uses 1-day buffer when fetching."""
    # Setup - use timezone-aware datetime
    last_sync = datetime.now(UTC) - timedelta(days=2)
    mock_db.get_site_metadata.return_value = {"last_sync_date": last_sync.isoformat()}

    update_manager.post_fetcher.fetch_latest_posts.return_value = []

    update_manager.update_archive("https://example.com")

    # Verify fetch_latest_posts was called with date minus 1 day
    call_args = update_manager.post_fetcher.fetch_latest_posts.call_args
    since_arg = call_args.kwargs["since"]

    # Should be approximately 1 day earlier than last_sync
    expected_since = last_sync - timedelta(days=1)
    time_diff = abs((since_arg - expected_since).total_seconds())
    assert time_diff < 1  # Within 1 second


def test_update_archive_updates_site_metadata(mock_db, update_manager):
    """Test that site metadata is updated after successful update."""
    # Setup: return a new post so there's something to update
    new_post = create_post(1, 100)
    update_manager.post_fetcher.fetch_latest_posts.return_value = [new_post]
    mock_db.get_post.return_value = None

    # Mock topic exists
    mock_db.get_topic.return_value = Topic(
        id=100,
        title="Test",
        slug="test",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )

    update_manager.update_archive("https://example.com")

    # Verify metadata was updated
    mock_db.update_site_metadata.assert_called_once()
    call_args = mock_db.update_site_metadata.call_args
    assert call_args[0][0] == "https://example.com"
    assert "last_sync_date" in call_args[1]


def test_update_archive_no_changes(mock_db, update_manager):
    """Test update when no changes are detected."""
    # Setup: no posts returned
    update_manager.post_fetcher.fetch_latest_posts.return_value = []

    stats = update_manager.update_archive("https://example.com")

    assert stats.new_posts == 0
    assert stats.modified_posts == 0
    assert stats.affected_topics == 0
    # Metadata should not be updated when there are no changes
    mock_db.update_site_metadata.assert_not_called()


def test_update_manager_with_category_filter(mock_db, mock_client):
    """Test that category filter is applied when processing posts."""
    with (
        patch("chronicon.utils.update_manager.PostFetcher") as mock_post_fetcher,
        patch("chronicon.utils.update_manager.TopicFetcher") as mock_topic_fetcher,
    ):
        post_fetcher = Mock()
        topic_fetcher = Mock()

        mock_post_fetcher.return_value = post_fetcher
        mock_topic_fetcher.return_value = topic_fetcher

        # Create manager with category filter
        manager = UpdateManager(mock_db, mock_client, category_ids=[1, 2])
        manager.post_fetcher = post_fetcher
        manager.topic_fetcher = topic_fetcher

        # Setup: two posts, one in allowed category, one not
        post_in_category = create_post(1, 100)
        post_not_in_category = create_post(2, 200)

        post_fetcher.fetch_latest_posts.return_value = [
            post_in_category,
            post_not_in_category,
        ]

        # DB says posts don't exist
        mock_db.get_post.return_value = None

        # Topic 100: category 1 (allowed), topic 200: category 99 (not allowed)
        def mock_get_topic(topic_id):
            if topic_id == 100:
                return Topic(
                    id=100,
                    title="Test Topic 1",
                    slug="test-topic-1",
                    category_id=1,  # Allowed
                    user_id=1,
                    created_at=datetime.now(),
                    updated_at=None,
                    posts_count=1,
                    views=0,
                )
            elif topic_id == 200:
                return Topic(
                    id=200,
                    title="Test Topic 2",
                    slug="test-topic-2",
                    category_id=99,  # Not allowed
                    user_id=1,
                    created_at=datetime.now(),
                    updated_at=None,
                    posts_count=1,
                    views=0,
                )
            return None

        mock_db.get_topic.side_effect = mock_get_topic

        stats = manager.update_archive("https://example.com")

        # Only post in category 1 should be processed
        assert stats.new_posts == 1
        assert stats.affected_topics == 1
        assert mock_db.insert_post.call_count == 1


def test_update_manager_no_category_filter_includes_all(mock_db, mock_client):
    """Test that without category filter, all posts are included."""
    with (
        patch("chronicon.utils.update_manager.PostFetcher") as mock_post_fetcher,
        patch("chronicon.utils.update_manager.TopicFetcher") as mock_topic_fetcher,
    ):
        post_fetcher = Mock()
        topic_fetcher = Mock()

        mock_post_fetcher.return_value = post_fetcher
        mock_topic_fetcher.return_value = topic_fetcher

        # Create manager WITHOUT category filter
        manager = UpdateManager(mock_db, mock_client, category_ids=None)
        manager.post_fetcher = post_fetcher
        manager.topic_fetcher = topic_fetcher

        # Setup: two posts in different categories
        post1 = create_post(1, 100)
        post2 = create_post(2, 200)

        post_fetcher.fetch_latest_posts.return_value = [post1, post2]

        # DB says posts don't exist
        mock_db.get_post.return_value = None

        # Topics in different categories
        def mock_get_topic(topic_id):
            return Topic(
                id=topic_id,
                title=f"Test Topic {topic_id}",
                slug=f"test-topic-{topic_id}",
                category_id=topic_id,  # Different category for each
                user_id=1,
                created_at=datetime.now(),
                updated_at=None,
                posts_count=1,
                views=0,
            )

        mock_db.get_topic.side_effect = mock_get_topic

        stats = manager.update_archive("https://example.com")

        # Both posts should be processed
        assert stats.new_posts == 2
        assert stats.affected_topics == 2
        assert mock_db.insert_post.call_count == 2


def test_update_manager_category_filter_fetches_topic_for_check(mock_db, mock_client):
    """Test that topic is fetched from API if not in DB for category check."""
    with (
        patch("chronicon.utils.update_manager.PostFetcher") as mock_post_fetcher,
        patch("chronicon.utils.update_manager.TopicFetcher") as mock_topic_fetcher,
    ):
        post_fetcher = Mock()
        topic_fetcher = Mock()

        mock_post_fetcher.return_value = post_fetcher
        mock_topic_fetcher.return_value = topic_fetcher

        # Create manager with category filter
        manager = UpdateManager(mock_db, mock_client, category_ids=[5])
        manager.post_fetcher = post_fetcher
        manager.topic_fetcher = topic_fetcher

        # Setup: post in topic not in DB
        new_post = create_post(1, 999)
        post_fetcher.fetch_latest_posts.return_value = [new_post]

        # DB says post doesn't exist
        mock_db.get_post.return_value = None

        # DB says topic doesn't exist (will need to fetch from API)
        mock_db.get_topic.return_value = None

        # Topic fetcher returns topic in category 5 (allowed)
        topic_fetcher.fetch_topic.return_value = Topic(
            id=999,
            title="New Topic",
            slug="new-topic",
            category_id=5,  # Allowed
            user_id=1,
            created_at=datetime.now(),
            updated_at=None,
            posts_count=1,
            views=0,
        )

        stats = manager.update_archive("https://example.com")

        # Post should be included (topic was fetched and verified)
        assert stats.new_posts == 1
        assert topic_fetcher.fetch_topic.called


def test_get_affected_usernames_from_new_posts(mock_db, update_manager):
    """Test that affected usernames are collected from new posts."""
    post1 = create_post(1, 100, username="alice")
    post2 = create_post(2, 101, username="bob")
    post3 = create_post(3, 100, username="alice")  # Same user, different post

    update_manager.post_fetcher.fetch_latest_posts.return_value = [post1, post2, post3]
    mock_db.get_post.return_value = None

    # DB has topics
    mock_db.get_topic.return_value = Topic(
        id=100,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )

    update_manager.update_archive("https://example.com")

    usernames = update_manager.get_affected_usernames()
    assert usernames == {"alice", "bob"}


def test_get_affected_usernames_from_modified_posts(mock_db, update_manager):
    """Test that affected usernames are collected from modified posts."""
    old_time = datetime.now() - timedelta(hours=2)
    new_time = datetime.now()

    existing_post = create_post(
        1, 100, created_at=old_time, updated_at=old_time, username="charlie"
    )
    updated_post = create_post(
        1, 100, created_at=old_time, updated_at=new_time, username="charlie"
    )

    update_manager.post_fetcher.fetch_latest_posts.return_value = [updated_post]
    mock_db.get_post.return_value = existing_post

    mock_db.get_topic.return_value = Topic(
        id=100,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )

    update_manager.update_archive("https://example.com")

    usernames = update_manager.get_affected_usernames()
    assert usernames == {"charlie"}


def test_get_affected_usernames_from_missing_topic_posts(mock_db, update_manager):
    """Test that usernames from newly-fetched missing topic posts are collected."""
    new_post = create_post(1, 999, username="dave")

    update_manager.post_fetcher.fetch_latest_posts.return_value = [new_post]
    mock_db.get_post.return_value = None
    mock_db.get_topic.return_value = None

    topic = Topic(
        id=999,
        title="New Topic",
        slug="new-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=2,
        views=0,
    )
    update_manager.topic_fetcher.fetch_topic.return_value = topic

    # When missing topic is fetched, its posts are also fetched
    topic_post1 = create_post(10, 999, username="dave")
    topic_post2 = create_post(11, 999, username="eve")
    update_manager.topic_fetcher.fetch_topic_posts.return_value = [
        topic_post1,
        topic_post2,
    ]

    update_manager.update_archive("https://example.com")

    usernames = update_manager.get_affected_usernames()
    assert "dave" in usernames
    assert "eve" in usernames


def test_get_affected_usernames_empty_when_no_changes(mock_db, update_manager):
    """Test that affected usernames is empty when no posts changed."""
    update_manager.post_fetcher.fetch_latest_posts.return_value = []

    update_manager.update_archive("https://example.com")

    usernames = update_manager.get_affected_usernames()
    assert usernames == set()


def test_get_affected_usernames_returns_copy(update_manager):
    """Test that get_affected_usernames returns a copy, not the original set."""
    update_manager._affected_usernames.add("testuser")

    usernames = update_manager.get_affected_usernames()
    assert usernames == {"testuser"}
    assert usernames is not update_manager._affected_usernames


def test_update_statistics_has_affected_usernames(mock_db, update_manager):
    """Test that UpdateStatistics includes affected_usernames count."""
    post1 = create_post(1, 100, username="alice")
    post2 = create_post(2, 101, username="bob")

    update_manager.post_fetcher.fetch_latest_posts.return_value = [post1, post2]
    mock_db.get_post.return_value = None

    mock_db.get_topic.return_value = Topic(
        id=100,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=None,
        posts_count=1,
        views=0,
    )

    stats = update_manager.update_archive("https://example.com")

    assert stats.affected_usernames == 2
