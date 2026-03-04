# ABOUTME: Tests for Pydantic API schemas and field selection
# ABOUTME: Covers all response models and FieldSelectionMixin functionality

from datetime import datetime

from chronicon.api.schemas import (
    CategoryDetail,
    PostDetail,
    TopicDetail,
    UserWithStats,
)


def test_topic_schema_basic():
    """Test basic topic schema validation."""
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "posts_count": 10,
        "views": 100,
        "created_at": "2024-01-01T00:00:00Z",
        "last_posted_at": "2024-01-02T00:00:00Z",
        "closed": False,
        "archived": False,
        "pinned": False,
        "visible": True,
        "category_id": 1,
        "user_id": 1,
    }

    topic = TopicDetail.model_validate(data)
    assert topic.id == 1
    assert topic.title == "Test Topic"
    assert topic.posts_count == 10


def test_field_selection():
    """Test field selection functionality."""
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "posts_count": 10,
        "views": 100,
        "created_at": "2024-01-01T00:00:00Z",
        "last_posted_at": "2024-01-02T00:00:00Z",
        "closed": False,
        "archived": False,
        "pinned": False,
        "visible": True,
        "category_id": 1,
        "user_id": 1,
    }

    topic = TopicDetail.model_validate(data)

    # Select only specific fields
    selected = topic.model_dump_selected(["id", "title", "posts_count"])
    assert "id" in selected
    assert "title" in selected
    assert "posts_count" in selected
    assert "views" not in selected
    assert "slug" not in selected


def test_field_selection_all_fields():
    """Test field selection with None (all fields)."""
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "posts_count": 10,
        "views": 100,
        "created_at": "2024-01-01T00:00:00Z",
        "last_posted_at": "2024-01-02T00:00:00Z",
        "closed": False,
        "archived": False,
        "pinned": False,
        "visible": True,
        "category_id": 1,
        "user_id": 1,
    }

    topic = TopicDetail.model_validate(data)

    # None should return all fields
    all_fields = topic.model_dump_selected(None)
    assert "id" in all_fields
    assert "title" in all_fields
    assert "posts_count" in all_fields
    assert "views" in all_fields


def test_post_schema_with_content():
    """Test post schema with content fields."""
    data = {
        "id": 1,
        "topic_id": 1,
        "post_number": 1,
        "username": "alice",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "reply_count": 0,
        "quote_count": 0,
        "reads": 10,
        "raw": "This is the raw content",
        "cooked": "<p>This is the cooked content</p>",
        "user_id": 1,
    }

    post = PostDetail.model_validate(data)
    assert post.id == 1
    assert post.raw == "This is the raw content"
    assert post.cooked == "<p>This is the cooked content</p>"


def test_user_with_stats_schema():
    """Test user schema with statistics."""
    data = {
        "id": 1,
        "username": "alice",
        "name": "Alice Smith",
        "trust_level": 3,
        "created_at": "2024-01-01T00:00:00Z",
        "avatar_template": "/user_avatar/example.com/alice/{size}/1.png",
        "post_count": 42,
    }

    user = UserWithStats.model_validate(data)
    assert user.id == 1
    assert user.username == "alice"
    assert user.post_count == 42


def test_category_schema():
    """Test category schema."""
    data = {
        "id": 1,
        "name": "General",
        "slug": "general",
        "color": "0088CC",
        "text_color": "FFFFFF",
        "topic_count": 100,
        "description": "General discussion",
        "parent_category_id": None,
    }

    category = CategoryDetail.model_validate(data)
    assert category.id == 1
    assert category.name == "General"
    assert category.topic_count == 100


def test_schema_datetime_parsing():
    """Test that datetime fields are properly parsed."""
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "posts_count": 10,
        "views": 100,
        "created_at": "2024-01-01T12:34:56Z",
        "last_posted_at": "2024-01-02T12:34:56Z",
        "closed": False,
        "archived": False,
        "pinned": False,
        "visible": True,
        "category_id": 1,
        "user_id": 1,
    }

    topic = TopicDetail.model_validate(data)
    assert isinstance(topic.created_at, datetime)
    assert topic.created_at.year == 2024
    assert topic.created_at.month == 1
    assert topic.created_at.day == 1


def test_optional_fields():
    """Test that optional fields work correctly."""
    # Minimal topic data
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "posts_count": 10,
        "views": 100,
        "created_at": "2024-01-01T00:00:00Z",
        "closed": False,
        "archived": False,
        "pinned": False,
        "visible": True,
        "user_id": 1,
        # last_posted_at is optional
        # category_id is optional
        # excerpt is optional
    }

    topic = TopicDetail.model_validate(data)
    assert topic.id == 1
    assert topic.last_posted_at is None
    assert topic.category_id is None
    assert topic.excerpt is None


def test_field_selection_with_nested_data():
    """Test field selection doesn't break with complex data."""
    data = {
        "id": 1,
        "username": "alice",
        "name": "Alice Smith",
        "trust_level": 3,
        "created_at": "2024-01-01T00:00:00Z",
        "avatar_template": "/avatar/{size}/1.png",
        "post_count": 42,
    }

    user = UserWithStats.model_validate(data)

    # Select only a few fields
    selected = user.model_dump_selected(["username", "post_count"])
    assert selected == {"username": "alice", "post_count": 42}
