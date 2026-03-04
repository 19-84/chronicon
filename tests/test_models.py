# ABOUTME: Test file for data models
# ABOUTME: Comprehensive tests for Post, Topic, User, and Category models

"""Tests for data models and validation."""

from datetime import datetime, timedelta

import pytest

from chronicon.models.category import (
    Category,
)
from chronicon.models.category import (
    ValidationError as CategoryValidationError,
)
from chronicon.models.post import Post
from chronicon.models.post import ValidationError as PostValidationError
from chronicon.models.topic import Topic
from chronicon.models.topic import ValidationError as TopicValidationError
from chronicon.models.user import User
from chronicon.models.user import ValidationError as UserValidationError


class TestPostModel:
    """Tests for Post model."""

    def test_post_valid_creation(self):
        """Test creating a valid Post."""
        now = datetime.now()
        post = Post(
            id=1,
            topic_id=10,
            user_id=100,
            post_number=1,
            created_at=now,
            updated_at=now,
            cooked="<p>Hello</p>",
            raw="Hello",
            username="testuser",
        )
        assert post.id == 1
        assert post.topic_id == 10
        assert post.username == "testuser"

    def test_post_from_dict_valid(self):
        """Test Post.from_dict() with valid data."""
        data = {
            "id": 1,
            "topic_id": 10,
            "user_id": 100,
            "post_number": 1,
            "created_at": "2024-10-14T12:00:00Z",
            "updated_at": "2024-10-14T12:00:00Z",
            "cooked": "<p>Hello</p>",
            "raw": "Hello",
            "username": "testuser",
        }
        post = Post.from_dict(data)
        assert post.id == 1
        assert post.topic_id == 10
        assert post.username == "testuser"

    def test_post_from_dict_missing_required_field(self):
        """Test Post.from_dict() with missing required field."""
        data = {
            "id": 1,
            "topic_id": 10,
            # Missing post_number
            "created_at": "2024-10-14T12:00:00Z",
            "updated_at": "2024-10-14T12:00:00Z",
        }
        with pytest.raises(PostValidationError):
            Post.from_dict(data)

    def test_post_validation_negative_id(self):
        """Test Post validation with negative ID."""
        now = datetime.now()
        with pytest.raises(PostValidationError, match="id must be positive"):
            Post(
                id=-1,
                topic_id=10,
                user_id=100,
                post_number=1,
                created_at=now,
                updated_at=now,
                cooked="<p>Hello</p>",
                raw="Hello",
                username="testuser",
            )

    def test_post_validation_updated_before_created(self):
        """Test Post validation with updated_at before created_at."""
        now = datetime.now()
        past = now - timedelta(days=1)
        with pytest.raises(
            PostValidationError, match="updated_at.*cannot be before created_at"
        ):
            Post(
                id=1,
                topic_id=10,
                user_id=100,
                post_number=1,
                created_at=now,
                updated_at=past,
                cooked="<p>Hello</p>",
                raw="Hello",
                username="testuser",
            )

    def test_post_to_dict(self):
        """Test Post.to_dict() method."""
        now = datetime.now()
        post = Post(
            id=1,
            topic_id=10,
            user_id=100,
            post_number=1,
            created_at=now,
            updated_at=now,
            cooked="<p>Hello</p>",
            raw="Hello",
            username="testuser",
        )
        data = post.to_dict()
        assert data["id"] == 1
        assert data["topic_id"] == 10
        assert data["username"] == "testuser"

    def test_post_to_db_row(self):
        """Test Post.to_db_row() method."""
        now = datetime.now()
        post = Post(
            id=1,
            topic_id=10,
            user_id=100,
            post_number=1,
            created_at=now,
            updated_at=now,
            cooked="<p>Hello</p>",
            raw="Hello",
            username="testuser",
        )
        row = post.to_db_row()
        assert row[0] == 1
        assert row[1] == 10
        assert row[8] == "testuser"


class TestTopicModel:
    """Tests for Topic model."""

    def test_topic_valid_creation(self):
        """Test creating a valid Topic."""
        now = datetime.now()
        topic = Topic(
            id=1,
            title="Test Topic",
            slug="test-topic",
            category_id=5,
            user_id=100,
            created_at=now,
            updated_at=now,
            posts_count=10,
            views=50,
        )
        assert topic.id == 1
        assert topic.title == "Test Topic"
        assert topic.posts_count == 10

    def test_topic_from_dict_valid(self):
        """Test Topic.from_dict() with valid data."""
        data = {
            "id": 1,
            "title": "Test Topic",
            "slug": "test-topic",
            "category_id": 5,
            "user_id": 100,
            "created_at": "2024-10-14T12:00:00Z",
            "updated_at": "2024-10-14T13:00:00Z",
            "posts_count": 10,
            "views": 50,
        }
        topic = Topic.from_dict(data)
        assert topic.id == 1
        assert topic.title == "Test Topic"

    def test_topic_validation_empty_title(self):
        """Test Topic validation with empty title."""
        now = datetime.now()
        with pytest.raises(TopicValidationError, match="title cannot be empty"):
            Topic(
                id=1,
                title="   ",
                slug="test-topic",
                category_id=5,
                user_id=100,
                created_at=now,
                updated_at=now,
                posts_count=10,
                views=50,
            )

    def test_topic_validation_negative_posts_count(self):
        """Test Topic validation with negative posts_count."""
        now = datetime.now()
        with pytest.raises(
            TopicValidationError,
            match="posts_count must be non-negative",
        ):
            Topic(
                id=1,
                title="Test Topic",
                slug="test-topic",
                category_id=5,
                user_id=100,
                created_at=now,
                updated_at=now,
                posts_count=-5,
                views=50,
            )


class TestUserModel:
    """Tests for User model."""

    def test_user_valid_creation(self):
        """Test creating a valid User."""
        now = datetime.now()
        user = User(
            id=1,
            username="testuser",
            name="Test User",
            avatar_template="/avatars/{size}/1.png",
            trust_level=2,
            created_at=now,
        )
        assert user.id == 1
        assert user.username == "testuser"
        assert user.trust_level == 2

    def test_user_from_dict_valid(self):
        """Test User.from_dict() with valid data."""
        data = {
            "id": 1,
            "username": "testuser",
            "name": "Test User",
            "avatar_template": "/avatars/{size}/1.png",
            "trust_level": 2,
            "created_at": "2024-10-14T12:00:00Z",
        }
        user = User.from_dict(data)
        assert user.id == 1
        assert user.username == "testuser"

    def test_user_validation_empty_username(self):
        """Test User validation with empty username."""
        now = datetime.now()
        with pytest.raises(UserValidationError, match="username cannot be empty"):
            User(
                id=1,
                username="   ",
                name="Test User",
                avatar_template="/avatars/{size}/1.png",
                trust_level=2,
                created_at=now,
            )

    def test_user_validation_invalid_trust_level(self):
        """Test User validation with invalid trust_level."""
        now = datetime.now()
        with pytest.raises(
            UserValidationError, match="trust_level must be between 0 and 4"
        ):
            User(
                id=1,
                username="testuser",
                name="Test User",
                avatar_template="/avatars/{size}/1.png",
                trust_level=10,
                created_at=now,
            )

    def test_user_get_avatar_url(self):
        """Test User.get_avatar_url() method."""
        user = User(
            id=1,
            username="testuser",
            name="Test User",
            avatar_template="/avatars/{size}/1.png",
            trust_level=2,
            created_at=None,
        )
        url = user.get_avatar_url(48)
        assert url == "/avatars/48/1.png"


class TestCategoryModel:
    """Tests for Category model."""

    def test_category_valid_creation(self):
        """Test creating a valid Category."""
        category = Category(
            id=1,
            name="General",
            slug="general",
            color="0088CC",
            text_color="FFFFFF",
            description="General discussion",
            parent_category_id=None,
            topic_count=100,
        )
        assert category.id == 1
        assert category.name == "General"
        assert category.topic_count == 100

    def test_category_from_dict_valid(self):
        """Test Category.from_dict() with valid data."""
        data = {
            "id": 1,
            "name": "General",
            "slug": "general",
            "color": "0088CC",
            "text_color": "FFFFFF",
            "description": "General discussion",
            "topic_count": 100,
        }
        category = Category.from_dict(data)
        assert category.id == 1
        assert category.name == "General"

    def test_category_validation_invalid_color(self):
        """Test Category validation with invalid color format."""
        with pytest.raises(
            CategoryValidationError, match="color must be 3 or 6-digit hex color"
        ):
            Category(
                id=1,
                name="General",
                slug="general",
                color="INVALID",
                text_color="FFFFFF",
                description="General discussion",
                parent_category_id=None,
                topic_count=100,
            )

    def test_category_validation_empty_name(self):
        """Test Category validation with empty name."""
        with pytest.raises(CategoryValidationError, match="name cannot be empty"):
            Category(
                id=1,
                name="   ",
                slug="general",
                color="0088CC",
                text_color="FFFFFF",
                description="General discussion",
                parent_category_id=None,
                topic_count=100,
            )

    def test_category_validation_negative_topic_count(self):
        """Test Category validation with negative topic_count."""
        with pytest.raises(
            CategoryValidationError, match="topic_count must be non-negative"
        ):
            Category(
                id=1,
                name="General",
                slug="general",
                color="0088CC",
                text_color="FFFFFF",
                description="General discussion",
                parent_category_id=None,
                topic_count=-10,
            )
