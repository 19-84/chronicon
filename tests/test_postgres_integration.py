# ABOUTME: PostgreSQL integration tests for Chronicon
# ABOUTME: Requires TEST_POSTGRES_URL env var and running PostgreSQL instance

"""
PostgreSQL integration tests.

These tests require a running PostgreSQL instance and the TEST_POSTGRES_URL
environment variable to be set.

For CI/CD, use the docker-compose.test-postgres.yml to spin up a test database:
    docker compose -f examples/docker/docker-compose.test-postgres.yml up -d
    export TEST_POSTGRES_URL="postgresql://chronicon:test@localhost:5432/chronicon_test"
    pytest tests/test_postgres_integration.py -v
"""

import os
from datetime import datetime

import pytest

# Skip entire module if no PostgreSQL configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="TEST_POSTGRES_URL environment variable not set",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Get PostgreSQL URL from environment."""
    return os.getenv("TEST_POSTGRES_URL")


@pytest.fixture
def postgres_db(postgres_url):
    """
    Create PostgreSQL database connection for testing.

    Cleans up test data after each test.
    """
    pytest.importorskip("psycopg")
    from chronicon.storage.factory import get_database

    db = get_database(postgres_url)

    yield db

    # Cleanup: Delete all test data
    try:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM posts")
        cursor.execute("DELETE FROM topics")
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM categories")
        cursor.execute("DELETE FROM site_metadata")
        cursor.execute("DELETE FROM assets")
        cursor.execute("DELETE FROM export_history")
        db.connection.commit()
    except Exception:
        pass
    finally:
        db.close()


class TestPostgresFactory:
    """Test database factory with PostgreSQL."""

    def test_factory_returns_postgres_instance(self, postgres_url):
        """Test factory returns PostgresArchiveDatabase for postgresql:// URL."""
        from chronicon.storage.factory import get_database
        from chronicon.storage.postgres_database import PostgresArchiveDatabase

        db = get_database(postgres_url)
        try:
            assert isinstance(db, PostgresArchiveDatabase)
        finally:
            db.close()

    def test_factory_returns_base_interface(self, postgres_url):
        """Test factory returns object implementing ArchiveDatabaseBase."""
        from chronicon.storage.database_base import ArchiveDatabaseBase
        from chronicon.storage.factory import get_database

        db = get_database(postgres_url)
        try:
            assert isinstance(db, ArchiveDatabaseBase)
        finally:
            db.close()


class TestPostgresCRUD:
    """Test CRUD operations with PostgreSQL."""

    def test_insert_and_retrieve_topic(self, postgres_db):
        """Test inserting and retrieving a topic."""
        from chronicon.models.topic import Topic

        topic = Topic(
            id=1,
            title="Test Topic for PostgreSQL",
            slug="test-topic-postgres",
            posts_count=1,
            views=100,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_posted_at=datetime.now(),
            user_id=1,
            closed=False,
            archived=False,
            pinned=False,
            visible=True,
        )

        postgres_db.insert_topic(topic)
        retrieved = postgres_db.get_topic(1)

        assert retrieved is not None
        assert retrieved.title == "Test Topic for PostgreSQL"
        assert retrieved.slug == "test-topic-postgres"

    def test_insert_and_retrieve_post(self, postgres_db):
        """Test inserting and retrieving a post."""
        from chronicon.models.post import Post
        from chronicon.models.topic import Topic

        # First insert a topic
        topic = Topic(
            id=1,
            title="Topic for Post Test",
            slug="topic-post-test",
            posts_count=1,
            views=10,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_posted_at=datetime.now(),
            user_id=1,
            closed=False,
            archived=False,
            pinned=False,
            visible=True,
        )
        postgres_db.insert_topic(topic)

        # Insert a post
        post = Post(
            id=1,
            topic_id=1,
            user_id=1,
            post_number=1,
            raw="Test post content for PostgreSQL",
            cooked="<p>Test post content for PostgreSQL</p>",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            username="testuser",
        )

        postgres_db.insert_post(post)
        retrieved = postgres_db.get_post(1)

        assert retrieved is not None
        assert "PostgreSQL" in retrieved.raw

    def test_get_statistics(self, postgres_db):
        """Test getting archive statistics."""
        stats = postgres_db.get_statistics()

        assert "total_topics" in stats
        assert "total_posts" in stats
        assert "total_users" in stats
        assert isinstance(stats["total_topics"], int)

    def test_get_first_site_url(self, postgres_db):
        """Test getting first site URL from database."""
        # Initially should be None
        url = postgres_db.get_first_site_url()
        assert url is None

        # Add site metadata
        postgres_db.update_site_metadata(
            "https://test.example.com",
            site_title="Test Forum",
        )

        # Now should return the URL
        url = postgres_db.get_first_site_url()
        assert url == "https://test.example.com"


class TestPostgresFTS:
    """Test full-text search with PostgreSQL tsvector."""

    def test_search_is_available(self, postgres_db):
        """Test that FTS is available."""
        assert postgres_db.is_search_available() is True

    def test_search_topics(self, postgres_db):
        """Test searching topics with tsvector."""
        from chronicon.models.topic import Topic

        # Insert test topics
        topics = [
            Topic(
                id=1,
                title="Python Programming Guide",
                slug="python-guide",
                posts_count=5,
                views=100,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_posted_at=datetime.now(),
                user_id=1,
                closed=False,
                archived=False,
                pinned=False,
                visible=True,
            ),
            Topic(
                id=2,
                title="JavaScript Tutorial",
                slug="javascript-tutorial",
                posts_count=3,
                views=50,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_posted_at=datetime.now(),
                user_id=1,
                closed=False,
                archived=False,
                pinned=False,
                visible=True,
            ),
        ]

        for topic in topics:
            postgres_db.insert_topic(topic)

        # Rebuild search index to populate tsvector
        postgres_db.rebuild_search_index()

        # Search for Python
        results = postgres_db.search_topics("Python")

        assert len(results) >= 1
        assert any("Python" in t.title for t in results)

    def test_search_posts(self, postgres_db):
        """Test searching posts with tsvector."""
        from chronicon.models.post import Post
        from chronicon.models.topic import Topic

        # Insert topic first
        topic = Topic(
            id=1,
            title="Search Test Topic",
            slug="search-test",
            posts_count=2,
            views=10,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_posted_at=datetime.now(),
            user_id=1,
            closed=False,
            archived=False,
            pinned=False,
            visible=True,
        )
        postgres_db.insert_topic(topic)

        # Insert posts
        posts = [
            Post(
                id=1,
                topic_id=1,
                user_id=1,
                post_number=1,
                raw="PostgreSQL is a powerful database",
                cooked="<p>PostgreSQL is a powerful database</p>",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                username="user1",
            ),
            Post(
                id=2,
                topic_id=1,
                user_id=1,
                post_number=2,
                raw="SQLite is great for embedded use",
                cooked="<p>SQLite is great for embedded use</p>",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                username="user2",
            ),
        ]

        for post in posts:
            postgres_db.insert_post(post)

        # Rebuild search index
        postgres_db.rebuild_search_index()

        # Search for PostgreSQL
        results = postgres_db.search_posts("PostgreSQL")

        assert len(results) >= 1
        assert any("PostgreSQL" in p.raw for p in results)


class TestPostgresPagination:
    """Test pagination with PostgreSQL."""

    def test_get_topics_paginated(self, postgres_db):
        """Test paginated topic retrieval."""
        from chronicon.models.topic import Topic

        # Insert multiple topics
        for i in range(25):
            topic = Topic(
                id=i + 1,
                title=f"Topic {i + 1}",
                slug=f"topic-{i + 1}",
                posts_count=1,
                views=i * 10,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_posted_at=datetime.now(),
                user_id=1,
                closed=False,
                archived=False,
                pinned=False,
                visible=True,
            )
            postgres_db.insert_topic(topic)

        # Get first page
        topics = postgres_db.get_topics_paginated(page=1, per_page=10)
        assert len(topics) == 10

        # Get second page
        topics = postgres_db.get_topics_paginated(page=2, per_page=10)
        assert len(topics) == 10

        # Get partial last page
        topics = postgres_db.get_topics_paginated(page=3, per_page=10)
        assert len(topics) == 5
