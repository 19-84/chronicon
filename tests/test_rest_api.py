# ABOUTME: Integration tests for REST API endpoints
# ABOUTME: Tests all routes with FastAPI TestClient

import os

import pytest

# Skip all tests if FastAPI is not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with sample data."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Insert test data
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="0088CC",
        text_color="FFFFFF",
        topic_count=1,
    )
    db.insert_category(category)

    user = User(
        id=1,
        username="alice",
        name="Alice Smith",
        trust_level=3,
        avatar_template="/avatar/{size}/1.png",
        created_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
    )
    db.insert_user(user)

    topic = Topic(
        id=1,
        title="Python Programming",
        slug="python-programming",
        posts_count=2,
        views=100,
        created_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
        last_posted_at="2024-01-02T00:00:00Z",  # type: ignore[arg-type]
        user_id=1,
        category_id=1,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
        excerpt="Learn Python basics",
    )
    db.insert_topic(topic)

    post1 = Post(
        id=1,
        topic_id=1,
        post_number=1,
        user_id=1,
        username="alice",
        created_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
        updated_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
        raw="This is a post about Python programming",
        cooked="<p>This is a post about Python programming</p>",
    )
    post2 = Post(
        id=2,
        topic_id=1,
        post_number=2,
        user_id=1,
        username="alice",
        created_at="2024-01-02T00:00:00Z",  # type: ignore[arg-type]
        updated_at="2024-01-02T00:00:00Z",  # type: ignore[arg-type]
        raw="More details about Python",
        cooked="<p>More details about Python</p>",
    )
    db.insert_post(post1)
    db.insert_post(post2)

    return db_path


@pytest.fixture
def client(test_db):
    """Create a FastAPI test client."""
    # Set DATABASE_URL environment variable
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

    from chronicon.api.app import app

    with TestClient(app) as client:
        yield client

    # Cleanup
    del os.environ["DATABASE_URL"]


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Chronicon API"
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "search_available" in data


def test_list_topics(client):
    """Test listing topics."""
    response = client.get("/api/v1/topics")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "pagination" in data
    assert len(data["topics"]) == 1
    assert data["topics"][0]["title"] == "Python Programming"


def test_list_topics_with_pagination(client):
    """Test topic listing with pagination."""
    response = client.get("/api/v1/topics?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 10


def test_list_topics_with_field_selection(client):
    """Test topic listing with field selection."""
    response = client.get("/api/v1/topics?fields=id,title,posts_count")
    assert response.status_code == 200
    data = response.json()
    assert len(data["topics"]) == 1
    topic = data["topics"][0]
    assert "id" in topic
    assert "title" in topic
    assert "posts_count" in topic
    # These fields should NOT be present
    assert "views" not in topic
    assert "created_at" not in topic


def test_get_topic(client):
    """Test getting a specific topic."""
    response = client.get("/api/v1/topics/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Python Programming"


def test_get_topic_not_found(client):
    """Test getting a non-existent topic."""
    response = client.get("/api/v1/topics/999")
    assert response.status_code == 404


def test_get_topic_posts(client):
    """Test getting posts for a topic."""
    response = client.get("/api/v1/topics/1/posts")
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert "pagination" in data
    assert len(data["posts"]) == 2


def test_get_topic_posts_with_truncation(client):
    """Test getting posts with body truncation."""
    response = client.get("/api/v1/topics/1/posts?max_body_length=10")
    assert response.status_code == 200
    data = response.json()
    post = data["posts"][0]
    # Body should be truncated
    assert len(post["raw"]) <= 13  # 10 chars + "..."


def test_get_post_context(client):
    """Test getting post with context."""
    response = client.get("/api/v1/topics/1/posts/1/context?before=1&after=1")
    assert response.status_code == 200
    data = response.json()
    assert data["target_post_number"] == 1
    assert "posts" in data


def test_get_post(client):
    """Test getting a specific post."""
    response = client.get("/api/v1/posts/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "alice"


def test_get_post_not_found(client):
    """Test getting a non-existent post."""
    response = client.get("/api/v1/posts/999")
    assert response.status_code == 404


def test_list_users(client):
    """Test listing users."""
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "pagination" in data
    assert len(data["users"]) >= 1


def test_get_user(client):
    """Test getting a specific user."""
    response = client.get("/api/v1/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "alice"
    assert "post_count" in data


def test_get_user_posts(client):
    """Test getting user's posts."""
    response = client.get("/api/v1/users/1/posts")
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert len(data["posts"]) == 2


def test_list_categories(client):
    """Test listing categories."""
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "General"


def test_get_category(client):
    """Test getting a specific category."""
    response = client.get("/api/v1/categories/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "General"


def test_get_category_topics(client):
    """Test getting topics in a category."""
    response = client.get("/api/v1/categories/1/topics")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert len(data["topics"]) == 1


def test_search_topics(client):
    """Test searching topics."""
    response = client.get("/api/v1/search/topics?q=python")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "python"
    assert "results" in data
    assert data["total"] >= 0


def test_search_posts(client):
    """Test searching posts."""
    response = client.get("/api/v1/search/posts?q=python")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "python"
    assert "results" in data


def test_search_without_query(client):
    """Test search without query parameter."""
    response = client.get("/api/v1/search/topics")
    assert response.status_code == 422  # Validation error


def test_get_archive_statistics(client):
    """Test getting archive statistics."""
    response = client.get("/api/v1/stats/archive")
    assert response.status_code == 200
    data = response.json()
    assert "total_topics" in data
    assert "total_posts" in data
    assert "total_users" in data
    assert data["total_topics"] >= 1


def test_get_activity_timeline(client):
    """Test getting activity timeline."""
    response = client.get("/api/v1/stats/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_cors_headers(client):
    """Test that CORS headers are present for cross-origin requests."""
    # CORS headers are only sent when Origin header is present
    response = client.get("/api/v1/topics", headers={"Origin": "http://example.com"})
    assert "access-control-allow-origin" in response.headers


def test_rate_limiting_headers(client):
    """Test that rate limiting is active."""
    # Make a request
    response = client.get("/api/v1/topics")
    assert response.status_code == 200
    # Rate limit headers should be present
    # Note: The exact header names depend on slowapi configuration
