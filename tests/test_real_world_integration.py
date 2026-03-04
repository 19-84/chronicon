# ABOUTME: Real-world integration test against meta.discourse.org
# ABOUTME: Tests API client, fetchers, models, and database operations with live data

"""
Real-world integration test for Chronicon.
Tests against meta.discourse.org to verify all components work together.

NOTE: This test makes real API calls and may take 20-30 seconds to run.
Run with: pytest tests/test_real_world_integration.py -v -s
"""

import tempfile
from pathlib import Path

import pytest

from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.categories import CategoryFetcher
from chronicon.fetchers.posts import PostFetcher
from chronicon.fetchers.topics import TopicFetcher
from chronicon.fetchers.users import UserFetcher
from chronicon.storage.database import ArchiveDatabase

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_client():
    """Fixture providing a real API client for meta.discourse.org."""
    return DiscourseAPIClient("https://meta.discourse.org", rate_limit=1.0)


@pytest.fixture(scope="module")
def real_db():
    """Fixture providing a temporary database for real-world testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    db = ArchiveDatabase(db_path)
    yield db
    db.close()

    # Cleanup
    from contextlib import suppress

    with suppress(Exception):
        db_path.unlink()


def test_api_client_basic(real_client):
    """Test basic API client functionality against real API."""
    # Test fetching latest posts
    response = real_client.get_json("/posts.json")
    assert "latest_posts" in response
    assert isinstance(response["latest_posts"], list)

    # Test fetching categories
    response = real_client.get_json("/categories.json")
    assert "category_list" in response
    assert "categories" in response["category_list"]


def test_category_fetcher_real(real_client, real_db):
    """Test fetching and storing real categories."""
    fetcher = CategoryFetcher(real_client, real_db)

    categories = fetcher.fetch_all_categories()

    assert len(categories) > 0, "Should fetch at least one category"

    # Store first category
    real_db.insert_category(categories[0])

    # Retrieve it back
    retrieved = real_db.get_all_categories()
    assert len(retrieved) > 0
    assert retrieved[0].name == categories[0].name


def test_topic_fetcher_real(real_client, real_db):
    """Test fetching and storing real topics."""
    fetcher = TopicFetcher(real_client, real_db)

    # Get some topic IDs
    topic_ids = fetcher.fetch_all_topic_ids()
    assert len(topic_ids) > 0, "Should fetch at least one topic ID"

    # Fetch first topic
    topic_id = topic_ids[0]
    topic = fetcher.fetch_topic(topic_id)

    assert topic is not None
    assert topic.id == topic_id
    assert len(topic.title) > 0

    # Store it
    real_db.insert_topic(topic)

    # Retrieve it back
    retrieved = real_db.get_topic(topic_id)
    assert retrieved is not None
    assert retrieved.id == topic_id
    assert retrieved.title == topic.title


def test_topic_posts_fetcher_real(real_client, real_db):
    """Test fetching posts for a real topic."""
    fetcher = TopicFetcher(real_client, real_db)

    # Get a topic ID
    topic_ids = fetcher.fetch_all_topic_ids()
    assert len(topic_ids) > 0

    topic_id = topic_ids[0]

    # Fetch topic posts
    posts = fetcher.fetch_topic_posts(topic_id)
    assert len(posts) > 0, "Topic should have at least one post"

    # Store first post
    real_db.insert_post(posts[0])

    # Retrieve it back
    retrieved_post = real_db.get_post(posts[0].id)
    assert retrieved_post is not None
    assert retrieved_post.id == posts[0].id
    assert retrieved_post.username == posts[0].username


def test_user_fetcher_real(real_client, real_db):
    """Test fetching and storing real users."""
    fetcher = UserFetcher(real_client, real_db)

    # Fetch a known user (system user exists on all Discourse instances)
    username = "system"
    user = fetcher.fetch_user(username)

    # Note: system user may not be accessible on all forums
    # So we allow this to fail gracefully
    if user:
        assert user.username == username
        assert user.trust_level >= 0

        # Store it
        real_db.insert_user(user)

        # Retrieve it back
        retrieved = real_db.get_user_by_username(username)
        assert retrieved is not None
        assert retrieved.username == username


def test_post_fetcher_latest_real(real_client, real_db):
    """Test fetching latest posts from real API."""
    fetcher = PostFetcher(real_client, real_db)

    # Fetch latest posts
    posts = fetcher.fetch_latest_posts()

    assert len(posts) > 0, "Should fetch at least one post"
    assert posts[0].id > 0
    assert posts[0].topic_id > 0
    assert len(posts[0].username) > 0


def test_database_queries_real(real_db):
    """Test various database query operations with real data."""
    # Get all topics (from previous tests)
    topics = real_db.get_all_topics()
    assert len(topics) > 0, "Database should contain topics from previous tests"

    # Get all categories
    categories = real_db.get_all_categories()
    assert len(categories) > 0, "Database should contain categories from previous tests"

    # Get posts for first topic
    if topics:
        posts = real_db.get_topic_posts(topics[0].id)
        assert len(posts) > 0, "Topic should have posts"

    # Get topics by category
    if categories:
        topics_in_cat = real_db.get_topics_by_category(categories[0].id)
        # May be 0 if the fetched topic isn't in this category
        assert topics_in_cat is not None


def test_end_to_end_workflow(real_client, real_db):
    """Test complete end-to-end workflow: fetch categories -> topics -> posts."""
    # 1. Fetch categories
    cat_fetcher = CategoryFetcher(real_client, real_db)
    categories = cat_fetcher.fetch_all_categories()
    assert len(categories) > 0

    for cat in categories[:2]:  # Store first 2 categories
        real_db.insert_category(cat)

    # 2. Fetch topic IDs
    topic_fetcher = TopicFetcher(real_client, real_db)
    topic_ids = topic_fetcher.fetch_all_topic_ids()
    assert len(topic_ids) > 0

    # 3. Fetch and store a complete topic with all posts
    topic_id = topic_ids[0]
    topic = topic_fetcher.fetch_topic(topic_id)
    assert topic is not None

    real_db.insert_topic(topic)

    posts = topic_fetcher.fetch_topic_posts(topic_id)
    assert len(posts) > 0

    for post in posts[:5]:  # Store first 5 posts
        real_db.insert_post(post)

    # 4. Verify data integrity
    retrieved_topic = real_db.get_topic(topic_id)
    assert retrieved_topic.title == topic.title

    retrieved_posts = real_db.get_topic_posts(topic_id)
    assert len(retrieved_posts) > 0
    assert retrieved_posts[0].topic_id == topic_id

    # 5. Verify statistics
    stats = real_db.get_statistics()
    assert stats["total_categories"] >= 2
    assert stats["total_topics"] >= 1
    assert stats["total_posts"] >= 1
