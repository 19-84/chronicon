# ABOUTME: End-to-end integration tests for API and MCP
# ABOUTME: Tests complete workflows from database to API/MCP responses

import os

import pytest

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User


@pytest.fixture
def comprehensive_db(tmp_path):
    """Create a comprehensive test database with realistic data."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "comprehensive.db"
    db = ArchiveDatabase(db_path)

    # Create categories
    categories = [
        Category(
            id=1,
            name="General Discussion",
            slug="general",
            color="0088CC",
            text_color="FFFFFF",
            topic_count=2,
            description="General topics",
        ),
        Category(
            id=2,
            name="Python",
            slug="python",
            color="FF0000",
            text_color="FFFFFF",
            topic_count=1,
            description="Python programming",
        ),
    ]
    for cat in categories:
        db.insert_category(cat)

    # Create users
    users = [
        User(
            id=1,
            username="alice",
            name="Alice Smith",
            trust_level=3,
            avatar_template="/avatar/{size}/1.png",
            created_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
        ),
        User(
            id=2,
            username="bob",
            name="Bob Jones",
            trust_level=2,
            avatar_template="/avatar/{size}/2.png",
            created_at="2024-01-02T00:00:00Z",  # type: ignore[arg-type]
        ),
    ]
    for user in users:
        db.insert_user(user)

    # Create topics
    topics = [
        Topic(
            id=1,
            title="Welcome to the forum",
            slug="welcome",
            posts_count=3,
            views=100,
            created_at="2024-01-01T00:00:00Z",  # type: ignore[arg-type]
            last_posted_at="2024-01-03T00:00:00Z",  # type: ignore[arg-type]
            user_id=1,
            category_id=1,
            closed=False,
            archived=False,
            pinned=True,
            visible=True,
            excerpt="Welcome message",
        ),
        Topic(
            id=2,
            title="Python best practices",
            slug="python-best-practices",
            posts_count=5,
            views=250,
            created_at="2024-01-02T00:00:00Z",  # type: ignore[arg-type]
            last_posted_at="2024-01-05T00:00:00Z",  # type: ignore[arg-type]
            user_id=2,
            category_id=2,
            closed=False,
            archived=False,
            pinned=False,
            visible=True,
            excerpt="Discussion about Python coding standards",
        ),
        Topic(
            id=3,
            title="Django vs Flask",
            slug="django-vs-flask",
            posts_count=10,
            views=500,
            created_at="2024-01-03T00:00:00Z",  # type: ignore[arg-type]
            last_posted_at="2024-01-10T00:00:00Z",  # type: ignore[arg-type]
            user_id=1,
            category_id=2,
            closed=False,
            archived=False,
            pinned=False,
            visible=True,
            excerpt="Comparing Django and Flask frameworks",
        ),
    ]
    for topic in topics:
        db.insert_topic(topic)

    # Create posts for topic 1
    for i in range(3):
        post = Post(
            id=i + 1,
            topic_id=1,
            post_number=i + 1,
            user_id=1 if i % 2 == 0 else 2,
            username="alice" if i % 2 == 0 else "bob",
            created_at=f"2024-01-0{i + 1}T00:00:00Z",  # type: ignore[arg-type]
            updated_at=f"2024-01-0{i + 1}T00:00:00Z",  # type: ignore[arg-type]
            raw=f"Welcome post #{i + 1}",
            cooked=f"<p>Welcome post #{i + 1}</p>",
        )
        db.insert_post(post)

    # Create posts for topic 2
    for i in range(5):
        post = Post(
            id=i + 4,
            topic_id=2,
            post_number=i + 1,
            user_id=2,
            username="bob",
            created_at=f"2024-01-0{i + 2}T00:00:00Z",  # type: ignore[arg-type]
            updated_at=f"2024-01-0{i + 2}T00:00:00Z",  # type: ignore[arg-type]
            raw=f"Python discussion post #{i + 1}",
            cooked=f"<p>Python discussion post #{i + 1}</p>",
        )
        db.insert_post(post)

    return db_path


def test_database_statistics(comprehensive_db):
    """Test that database statistics are accurate."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    stats = db.get_statistics()
    assert stats["total_topics"] == 3
    assert stats["total_posts"] == 8  # 3 + 5
    assert stats["total_users"] == 2
    assert stats["total_categories"] == 2
    assert stats["total_views"] == 850  # 100 + 250 + 500


def test_search_integration(comprehensive_db):
    """Test full-text search integration."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    # Search for Python
    results = db.search_topics("python")
    assert len(results) >= 1
    assert any("Python" in r.title for r in results)

    # Search for Django
    results = db.search_topics("django")
    assert len(results) >= 1
    assert "Django" in results[0].title

    # Search posts
    results = db.search_posts("discussion")
    assert len(results) >= 1


def test_category_filtering(comprehensive_db):
    """Test filtering topics by category."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    # Get Python category topics
    topics = db.get_topics_by_category_with_info(2)
    assert len(topics) == 2
    assert all(t["category_id"] == 2 for t in topics)


def test_user_posts_pagination(comprehensive_db):
    """Test paginated user posts."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    # Bob has 6 posts (1 from topic 1, 5 from topic 2)
    page1 = db.get_user_posts_paginated(2, page=1, per_page=3)
    assert len(page1) == 3

    page2 = db.get_user_posts_paginated(2, page=2, per_page=3)
    assert len(page2) == 3

    # Total should be 6
    total = db.get_user_post_count(2)
    assert total == 6


@pytest.mark.skipif(
    not pytest.importorskip("fastapi"),
    reason="FastAPI not installed",
)
def test_api_full_workflow(comprehensive_db):
    """Test complete API workflow."""
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = f"sqlite:///{comprehensive_db}"

    from chronicon.api.app import app

    with TestClient(app) as client:
        # 1. Get statistics
        response = client.get("/api/v1/stats/archive")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_topics"] == 3
        assert stats["total_posts"] == 8

        # 2. List topics
        response = client.get("/api/v1/topics")
        assert response.status_code == 200
        data = response.json()
        assert len(data["topics"]) == 3

        # 3. Filter by category
        response = client.get("/api/v1/topics?category_id=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["topics"]) == 2

        # 4. Get topic details
        response = client.get("/api/v1/topics/1")
        assert response.status_code == 200
        topic = response.json()
        assert topic["title"] == "Welcome to the forum"

        # 5. Get topic posts with pagination
        response = client.get("/api/v1/topics/2/posts?per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["posts"]) == 2
        assert data["pagination"]["total"] == 5  # Topic 2 has 5 posts

        # 6. Search topics
        response = client.get("/api/v1/search/topics?q=python")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "python"
        assert len(data["results"]) >= 1

        # 7. Get user details
        response = client.get("/api/v1/users/2")
        assert response.status_code == 200
        user = response.json()
        assert user["username"] == "bob"
        assert user["post_count"] == 6

        # 8. List categories
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 2

    del os.environ["DATABASE_URL"]


@pytest.mark.skipif(
    not pytest.importorskip("mcp"),
    reason="MCP not installed",
)
@pytest.mark.skipif(
    not pytest.importorskip("pytest_asyncio", reason="pytest-asyncio not installed"),
    reason="pytest-asyncio not installed",
)
@pytest.mark.asyncio
async def test_mcp_full_workflow(comprehensive_db, monkeypatch):
    """Test complete MCP workflow."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{comprehensive_db}")

    from chronicon.mcp.server import mcp_server

    # 1. Get statistics
    result = await mcp_server.call_tool("get_statistics", {})  # type: ignore[call-arg]
    assert "Total Topics: 3" in result
    assert "Total Posts: 8" in result

    # 2. List topics
    result = await mcp_server.call_tool("get_topics", {"page": 1, "per_page": 10})  # type: ignore[call-arg]
    assert "Welcome to the forum" in result
    assert "Python best practices" in result

    # 3. Get topic details
    result = await mcp_server.call_tool("get_topic", {"topic_id": 2})  # type: ignore[call-arg]
    assert "Python best practices" in result
    assert "Posts: 5" in result

    # 4. Search topics
    result = await mcp_server.call_tool("search_topics", {"query": "django"})  # type: ignore[call-arg]
    assert "Django" in result

    # 5. Get users
    result = await mcp_server.call_tool("get_users", {"page": 1, "per_page": 10})  # type: ignore[call-arg]
    assert "alice" in result
    assert "bob" in result

    # 6. Read resources
    result = await mcp_server.read_resource("archive://stats")  # type: ignore[call-arg]
    assert "Total Topics: 3" in result.text

    result = await mcp_server.read_resource("archive://categories")  # type: ignore[call-arg]
    assert "General Discussion" in result.text
    assert "Python" in result.text

    # 7. Get prompts
    result = await mcp_server.get_prompt("token-safety-guide", None)  # type: ignore[call-arg]
    assert "Token Safety Guide" in result


def test_field_selection_reduces_response_size(comprehensive_db):
    """Test that field selection actually reduces response size."""
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = f"sqlite:///{comprehensive_db}"

    from chronicon.api.app import app

    with TestClient(app) as client:
        # Full response
        response_full = client.get("/api/v1/topics")
        full_size = len(response_full.content)

        # Reduced response
        response_reduced = client.get("/api/v1/topics?fields=id,title")
        reduced_size = len(response_reduced.content)

        # Reduced should be smaller
        assert reduced_size < full_size

        # Verify only requested fields are present
        data = response_reduced.json()
        topic = data["topics"][0]
        assert "id" in topic
        assert "title" in topic
        assert "views" not in topic
        assert "created_at" not in topic

    del os.environ["DATABASE_URL"]


def test_body_truncation_reduces_response_size(comprehensive_db):
    """Test that body truncation reduces response size."""
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = f"sqlite:///{comprehensive_db}"

    from chronicon.api.app import app

    with TestClient(app) as client:
        # Full response
        response_full = client.get("/api/v1/topics/2/posts")
        full_size = len(response_full.content)

        # Truncated response
        response_truncated = client.get("/api/v1/topics/2/posts?max_body_length=10")
        truncated_size = len(response_truncated.content)

        # Truncated should be smaller
        assert truncated_size < full_size

    del os.environ["DATABASE_URL"]


def test_activity_timeline(comprehensive_db):
    """Test activity timeline generation."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    timeline = db.get_activity_timeline()
    assert len(timeline) > 0
    assert all("month" in item for item in timeline)
    assert all("topic_count" in item for item in timeline)
    assert all("post_count" in item for item in timeline)


def test_top_contributors(comprehensive_db):
    """Test top contributors statistics."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    stats = db.get_archive_statistics()
    assert "top_contributors" in stats
    contributors = stats["top_contributors"]
    assert len(contributors) == 2

    # Bob should be #1 (6 posts: 1 from topic 1 + 5 from topic 2)
    assert contributors[0]["username"] == "bob"
    assert contributors[0]["post_count"] == 6

    # Alice should be #2 (2 posts from topic 1)
    assert contributors[1]["username"] == "alice"
    assert contributors[1]["post_count"] == 2


def test_popular_categories(comprehensive_db):
    """Test popular categories statistics."""
    from chronicon.storage.database import ArchiveDatabase

    db = ArchiveDatabase(comprehensive_db)

    stats = db.get_archive_statistics()
    assert "popular_categories" in stats
    categories = stats["popular_categories"]
    assert len(categories) == 2

    # Python category was created with topic_count=1
    python_cat = next(c for c in categories if c["slug"] == "python")
    assert python_cat["topic_count"] == 1
