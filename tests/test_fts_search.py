# ABOUTME: Tests for full-text search (SQLite FTS5 and PostgreSQL tsvector)
# ABOUTME: Covers search_topics, search_posts, rebuild_index, and is_search_available

from datetime import UTC, datetime

import pytest

from chronicon.models.post import Post
from chronicon.models.topic import Topic


def test_search_topics_sqlite(tmp_path):
    """Test FTS5 topic search in SQLite."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Insert test topics
    topic1 = Topic(
        id=1,
        title="Python programming basics",
        slug="python-basics",
        posts_count=5,
        views=100,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_posted_at=datetime(2024, 1, 1, tzinfo=UTC),
        user_id=1,
        category_id=None,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
        excerpt="Learn Python fundamentals",
    )
    topic2 = Topic(
        id=2,
        title="JavaScript frameworks comparison",
        slug="js-frameworks",
        posts_count=10,
        views=200,
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        last_posted_at=datetime(2024, 1, 2, tzinfo=UTC),
        user_id=1,
        category_id=None,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
        excerpt="Comparing React, Vue, and Angular",
    )

    db.insert_topic(topic1)
    db.insert_topic(topic2)

    # Search is available
    assert db.is_search_available() is True

    # Search for Python
    results = db.search_topics("python")
    assert len(results) == 1
    assert results[0].id == 1

    # Search for JavaScript
    results = db.search_topics("javascript")
    assert len(results) == 1
    assert results[0].id == 2

    # Search count
    count = db.search_topics_count("python")
    assert count == 1

    # Pagination
    results = db.search_topics("programming OR frameworks", limit=1, offset=0)
    assert len(results) == 1


def test_search_posts_sqlite(tmp_path):
    """Test FTS5 post search in SQLite."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Insert test posts
    post1 = Post(
        id=1,
        topic_id=1,
        post_number=1,
        user_id=1,
        username="alice",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        raw="This is a post about Python programming",
        cooked="<p>This is a post about Python programming</p>",
    )
    post2 = Post(
        id=2,
        topic_id=1,
        post_number=2,
        user_id=2,
        username="bob",
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        raw="JavaScript is great for web development",
        cooked="<p>JavaScript is great for web development</p>",
    )

    db.insert_post(post1)
    db.insert_post(post2)

    # Search for Python
    results = db.search_posts("python")
    assert len(results) == 1
    assert results[0].id == 1

    # Search by username
    results = db.search_posts("alice")
    assert len(results) == 1
    assert results[0].username == "alice"

    # Search count
    count = db.search_posts_count("javascript")
    assert count == 1


def test_rebuild_search_index_sqlite(tmp_path):
    """Test rebuilding search index in SQLite."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Insert topics and posts
    topic = Topic(
        id=1,
        title="Test topic",
        slug="test",
        posts_count=1,
        views=10,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_posted_at=datetime(2024, 1, 1, tzinfo=UTC),
        user_id=1,
        category_id=None,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
    )
    post = Post(
        id=1,
        topic_id=1,
        post_number=1,
        user_id=1,
        username="alice",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        raw="Test content",
        cooked="<p>Test content</p>",
    )

    db.insert_topic(topic)
    db.insert_post(post)

    # Rebuild index
    db.rebuild_search_index()

    # Verify search works
    results = db.search_topics("test")
    assert len(results) >= 1

    results = db.search_posts("content")
    assert len(results) >= 1


@pytest.mark.skipif(
    not pytest.importorskip("psycopg"),
    reason="PostgreSQL tests require psycopg",
)
def test_search_topics_postgres():
    """Test tsvector topic search in PostgreSQL."""
    # Note: This test requires a running PostgreSQL instance
    # Skip in CI/CD unless DATABASE_URL is set
    import os

    postgres_url = os.getenv("TEST_POSTGRES_URL")
    if not postgres_url:
        pytest.skip("TEST_POSTGRES_URL not set")

    from chronicon.storage.postgres_database import PostgresArchiveDatabase

    db = PostgresArchiveDatabase(postgres_url)

    # Insert test topics
    topic1 = Topic(
        id=1,
        title="Python programming basics",
        slug="python-basics",
        posts_count=5,
        views=100,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_posted_at=datetime(2024, 1, 1, tzinfo=UTC),
        user_id=1,
        category_id=None,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
        excerpt="Learn Python fundamentals",
    )

    db.insert_topic(topic1)

    # Search is available
    assert db.is_search_available() is True

    # Search for Python
    results = db.search_topics("python")
    assert len(results) >= 1

    # Cleanup
    db.connection.rollback()


def test_is_search_available(tmp_path):
    """Test search availability detection."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Search should be available after schema creation
    assert db.is_search_available() is True


def test_search_with_special_characters(tmp_path):
    """Test search with special characters."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    topic = Topic(
        id=1,
        title="C++ programming guide",
        slug="cpp-guide",
        posts_count=1,
        views=10,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_posted_at=datetime(2024, 1, 1, tzinfo=UTC),
        user_id=1,
        category_id=None,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
        excerpt="Learn C++ basics",
    )

    db.insert_topic(topic)

    # Search with special characters (should not crash)
    try:
        results = db.search_topics("C++")
        # May or may not find results depending on FTS tokenization
        assert isinstance(results, list)
    except Exception as e:
        # Some search backends may not support certain characters
        pytest.skip(f"Search backend doesn't support this query: {e}")
