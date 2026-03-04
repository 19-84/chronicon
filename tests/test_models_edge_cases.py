# ABOUTME: Edge case tests for model dataclasses
# ABOUTME: Tests serialization, deserialization, missing fields, and date parsing

"""Tests for model edge cases."""

from datetime import datetime

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User

# ============================================================================
# Post Model Edge Cases
# ============================================================================


def test_post_from_dict_minimal_fields():
    """Test Post creation with minimal required fields."""
    data = {
        "id": 1,
        "topic_id": 10,
        "post_number": 1,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "cooked": "<p>Test</p>",
        "raw": "Test",
        "username": "testuser",
    }

    post = Post.from_dict(data)

    assert post.id == 1
    assert post.user_id is None  # Optional field


def test_post_from_dict_missing_optional_fields():
    """Test Post with various optional fields missing."""
    data = {
        "id": 1,
        "topic_id": 10,
        "post_number": 1,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "cooked": None,  # Can be None
        "raw": "Test",
        "username": "testuser",
    }

    post = Post.from_dict(data)

    assert post.cooked is None


def test_post_to_dict():
    """Test Post serialization to dict."""
    post = Post(
        id=1,
        topic_id=10,
        user_id=5,
        post_number=1,
        created_at=datetime(2024, 1, 1, 12, 0),
        updated_at=datetime(2024, 1, 1, 12, 0),
        cooked="<p>Test</p>",
        raw="Test",
        username="testuser",
    )

    data = post.to_dict()

    assert data["id"] == 1
    assert data["topic_id"] == 10
    assert isinstance(data["created_at"], str)


def test_post_to_db_row():
    """Test Post conversion to database row."""
    post = Post(
        id=1,
        topic_id=10,
        user_id=5,
        post_number=1,
        created_at=datetime(2024, 1, 1, 12, 0),
        updated_at=datetime(2024, 1, 1, 12, 0),
        cooked="<p>Test</p>",
        raw="Test",
        username="testuser",
    )

    row = post.to_db_row()

    assert row[0] == 1  # id
    assert row[1] == 10  # topic_id
    assert isinstance(row[4], str)  # created_at as ISO string


# ============================================================================
# Topic Model Edge Cases
# ============================================================================


def test_topic_from_dict_minimal_fields():
    """Test Topic creation with minimal fields."""
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "created_at": "2024-01-01T12:00:00Z",
        "posts_count": 5,
        "views": 100,
    }

    topic = Topic.from_dict(data)

    assert topic.id == 1
    assert topic.category_id is None
    assert topic.updated_at is None


def test_topic_from_dict_null_category():
    """Test Topic with null category_id."""
    data = {
        "id": 1,
        "title": "Test Topic",
        "slug": "test-topic",
        "category_id": None,
        "created_at": "2024-01-01T12:00:00Z",
        "posts_count": 5,
        "views": 100,
    }

    topic = Topic.from_dict(data)

    assert topic.category_id is None


def test_topic_to_dict():
    """Test Topic serialization."""
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=5,
        user_id=10,
        created_at=datetime(2024, 1, 1, 12, 0),
        updated_at=datetime(2024, 1, 2, 12, 0),
        posts_count=5,
        views=100,
    )

    data = topic.to_dict()

    assert data["id"] == 1
    assert data["title"] == "Test Topic"
    assert isinstance(data["created_at"], str)


def test_topic_to_db_row():
    """Test Topic conversion to database row."""
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=5,
        user_id=10,
        created_at=datetime(2024, 1, 1, 12, 0),
        updated_at=datetime(2024, 1, 2, 12, 0),
        posts_count=5,
        views=100,
    )

    row = topic.to_db_row()

    assert row[0] == 1
    assert row[1] == "Test Topic"


# ============================================================================
# User Model Edge Cases
# ============================================================================


def test_user_from_dict_minimal_fields():
    """Test User creation with minimal fields."""
    data = {
        "id": 1,
        "username": "testuser",
        "avatar_template": "/avatars/{size}/1.png",
        "trust_level": 1,
    }

    user = User.from_dict(data)

    assert user.id == 1
    assert user.name is None
    assert user.created_at is None


def test_user_from_dict_with_name():
    """Test User with name field."""
    data = {
        "id": 1,
        "username": "testuser",
        "name": "Test User",
        "avatar_template": "/avatars/{size}/1.png",
        "trust_level": 1,
        "created_at": "2023-01-01T00:00:00Z",
    }

    user = User.from_dict(data)

    assert user.name == "Test User"
    assert user.created_at is not None


def test_user_to_dict():
    """Test User serialization."""
    user = User(
        id=1,
        username="testuser",
        name="Test User",
        avatar_template="/avatars/{size}/1.png",
        trust_level=2,
        created_at=datetime(2023, 1, 1),
    )

    data = user.to_dict()

    assert data["id"] == 1
    assert data["username"] == "testuser"


def test_user_get_avatar_url():
    """Test user avatar URL generation."""
    user = User(
        id=1,
        username="testuser",
        name="Test User",
        avatar_template="/user_avatar/site/{size}/1_2.png",
        trust_level=1,
        created_at=None,
    )

    url = user.get_avatar_url(size=48)

    assert "48" in url
    assert "/user_avatar/" in url


# ============================================================================
# Category Model Edge Cases
# ============================================================================


def test_category_from_dict_minimal_fields():
    """Test Category with minimal required fields."""
    data = {
        "id": 1,
        "name": "General",
        "slug": "general",
        "color": "0088CC",
        "text_color": "FFFFFF",
        "topic_count": 50,
    }

    category = Category.from_dict(data)

    assert category.id == 1
    assert category.description is None
    assert category.parent_category_id is None


def test_category_from_dict_with_parent():
    """Test Category with parent category."""
    data = {
        "id": 2,
        "name": "Support",
        "slug": "support",
        "color": "FF0000",
        "text_color": "FFFFFF",
        "description": "Get help here",
        "parent_category_id": 1,
        "topic_count": 25,
    }

    category = Category.from_dict(data)

    assert category.parent_category_id == 1
    assert category.description == "Get help here"


def test_category_to_dict():
    """Test Category serialization."""
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="0088CC",
        text_color="FFFFFF",
        description="General discussion",
        parent_category_id=None,
        topic_count=50,
    )

    data = category.to_dict()

    assert data["id"] == 1
    assert data["name"] == "General"


def test_category_to_db_row():
    """Test Category conversion to database row."""
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="0088CC",
        text_color="FFFFFF",
        description="General discussion",
        parent_category_id=None,
        topic_count=50,
    )

    row = category.to_db_row()

    assert row[0] == 1
    assert row[1] == "General"
    assert row[2] == "general"


# ============================================================================
# Date Parsing Edge Cases
# ============================================================================


def test_post_date_parsing_with_z():
    """Test date parsing with Z timezone indicator."""
    data = {
        "id": 1,
        "topic_id": 10,
        "post_number": 1,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "cooked": "<p>Test</p>",
        "raw": "Test",
        "username": "testuser",
    }

    post = Post.from_dict(data)

    assert post.created_at.year == 2024
    assert post.created_at.month == 1


def test_post_date_parsing_with_milliseconds():
    """Test date parsing with milliseconds."""
    data = {
        "id": 1,
        "topic_id": 10,
        "post_number": 1,
        "created_at": "2024-01-01T12:00:00.123Z",
        "updated_at": "2024-01-01T12:00:00.456Z",
        "cooked": "<p>Test</p>",
        "raw": "Test",
        "username": "testuser",
    }

    post = Post.from_dict(data)

    assert post.created_at.year == 2024
