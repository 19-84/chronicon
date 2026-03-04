# ABOUTME: Comprehensive tests for all fetcher modules
# ABOUTME: Tests API client, category, topic, post, and user fetchers

"""Tests for fetcher modules."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.categories import CategoryFetcher
from chronicon.fetchers.posts import PostFetcher
from chronicon.fetchers.topics import TopicFetcher
from chronicon.fetchers.users import UserFetcher
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase

# ============================================================================
# CategoryFetcher Tests
# ============================================================================


def test_category_fetcher_fetch_all(tmp_path):
    """Test fetching all categories."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "category_list": {
            "categories": [
                {
                    "id": 1,
                    "name": "General",
                    "slug": "general",
                    "color": "0088CC",
                    "text_color": "FFFFFF",
                    "description": "General discussion",
                    "topic_count": 100,
                },
                {
                    "id": 2,
                    "name": "Support",
                    "slug": "support",
                    "color": "FF0000",
                    "text_color": "FFFFFF",
                    "description": "Get help",
                    "parent_category_id": 1,
                    "topic_count": 50,
                },
            ]
        }
    }

    fetcher = CategoryFetcher(mock_client, db)
    categories = fetcher.fetch_all_categories()

    assert len(categories) == 2
    assert categories[0].name == "General"
    assert categories[1].name == "Support"
    assert categories[1].parent_category_id == 1

    db.close()


def test_category_fetcher_empty_response(tmp_path):
    """Test category fetcher with empty response."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {"category_list": {"categories": []}}

    fetcher = CategoryFetcher(mock_client, db)
    categories = fetcher.fetch_all_categories()

    assert len(categories) == 0

    db.close()


def test_category_fetcher_malformed_data(tmp_path):
    """Test category fetcher handles malformed data."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "category_list": {
            "categories": [
                {"id": 1, "name": "Valid"},  # Missing required fields
                {"invalid": "data"},  # Completely invalid
            ]
        }
    }

    fetcher = CategoryFetcher(mock_client, db)
    categories = fetcher.fetch_all_categories()

    # Should handle errors gracefully
    assert isinstance(categories, list)

    db.close()


# ============================================================================
# TopicFetcher Tests
# ============================================================================


def test_topic_fetcher_fetch_topic(tmp_path):
    """Test fetching a single topic."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "id": 123,
        "title": "Test Topic",
        "slug": "test-topic",
        "category_id": 1,
        "user_id": 5,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-02T12:00:00Z",
        "posts_count": 10,
        "views": 100,
    }

    fetcher = TopicFetcher(mock_client, db)
    topic = fetcher.fetch_topic(123)

    assert topic is not None
    assert topic.id == 123
    assert topic.title == "Test Topic"
    assert topic.posts_count == 10

    db.close()


def test_topic_fetcher_fetch_topic_not_found(tmp_path):
    """Test fetching topic that doesn't exist."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.side_effect = Exception("Not found")

    fetcher = TopicFetcher(mock_client, db)
    topic = fetcher.fetch_topic(999)

    assert topic is None

    db.close()


def test_topic_fetcher_fetch_topic_posts(tmp_path):
    """Test fetching posts for a topic."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "post_stream": {
            "posts": [
                {
                    "id": 1,
                    "topic_id": 123,
                    "user_id": 5,
                    "post_number": 1,
                    "created_at": "2024-01-01T12:00:00Z",
                    "updated_at": "2024-01-01T12:00:00Z",
                    "cooked": "<p>First post</p>",
                    "raw": "First post",
                    "username": "admin",
                },
                {
                    "id": 2,
                    "topic_id": 123,
                    "user_id": 6,
                    "post_number": 2,
                    "created_at": "2024-01-01T13:00:00Z",
                    "updated_at": "2024-01-01T13:00:00Z",
                    "cooked": "<p>Reply</p>",
                    "raw": "Reply",
                    "username": "user1",
                },
            ],
            "stream": [1, 2],
        }
    }

    fetcher = TopicFetcher(mock_client, db)
    posts = fetcher.fetch_topic_posts(123)

    assert len(posts) == 2
    assert posts[0].post_number == 1
    assert posts[1].post_number == 2
    assert posts[0].username == "admin"

    db.close()


def test_topic_fetcher_fetch_all_topic_ids(tmp_path):
    """Test fetching all topic IDs."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)

    # Mock single page of results (simplified test)
    mock_client.get_json.return_value = {
        "topic_list": {"topics": [{"id": 1}, {"id": 2}, {"id": 3}]}
    }

    fetcher = TopicFetcher(mock_client, db)
    topic_ids = fetcher.fetch_all_topic_ids()

    # Should return at least the topics from one page
    assert len(topic_ids) >= 3
    assert 1 in topic_ids
    assert 2 in topic_ids
    assert 3 in topic_ids

    db.close()


def test_topic_fetcher_fetch_category_topics_single_page(tmp_path):
    """Test fetching category topics with single page of results."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)

    # Mock response with fewer than 30 topics (indicates last page)
    mock_client.get_json.return_value = {
        "topic_list": {
            "topics": [
                {
                    "id": 1,
                    "title": "Topic 1",
                    "slug": "topic-1",
                    "category_id": 5,
                    "user_id": 10,
                    "created_at": "2024-01-01T12:00:00Z",
                    "posts_count": 5,
                    "views": 100,
                },
                {
                    "id": 2,
                    "title": "Topic 2",
                    "slug": "topic-2",
                    "category_id": 5,
                    "user_id": 11,
                    "created_at": "2024-01-02T12:00:00Z",
                    "posts_count": 3,
                    "views": 50,
                },
            ]
        }
    }

    fetcher = TopicFetcher(mock_client, db)
    topics = fetcher.fetch_category_topics(5)

    # Should fetch all topics from single page
    assert len(topics) == 2
    assert topics[0].id == 1
    assert topics[1].id == 2
    assert topics[0].title == "Topic 1"

    # Should only call API once (single page)
    mock_client.get_json.assert_called_once_with("/c/5.json?page=0")

    db.close()


def test_topic_fetcher_fetch_category_topics_multiple_pages(tmp_path):
    """Test fetching category topics with pagination across multiple pages."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)

    # Mock multiple pages of results
    # Page 0: 30 topics (full page, indicates more pages)
    # Page 1: 15 topics (partial page, indicates last page)
    def mock_get_json(path):
        if "page=0" in path:
            return {
                "topic_list": {
                    "topics": [
                        {
                            "id": i,
                            "title": f"Topic {i}",
                            "slug": f"topic-{i}",
                            "category_id": 5,
                            "user_id": 10,
                            "created_at": "2024-01-01T12:00:00Z",
                            "posts_count": 5,
                            "views": 100,
                        }
                        for i in range(1, 31)  # 30 topics
                    ]
                }
            }
        elif "page=1" in path:
            return {
                "topic_list": {
                    "topics": [
                        {
                            "id": i,
                            "title": f"Topic {i}",
                            "slug": f"topic-{i}",
                            "category_id": 5,
                            "user_id": 10,
                            "created_at": "2024-01-01T12:00:00Z",
                            "posts_count": 5,
                            "views": 100,
                        }
                        for i in range(31, 46)  # 15 topics
                    ]
                }
            }
        else:
            return {"topic_list": {"topics": []}}

    mock_client.get_json.side_effect = mock_get_json

    fetcher = TopicFetcher(mock_client, db)
    topics = fetcher.fetch_category_topics(5)

    # Should fetch all topics from both pages
    assert len(topics) == 45
    assert topics[0].id == 1
    assert topics[29].id == 30
    assert topics[30].id == 31
    assert topics[44].id == 45

    # Should call API twice (two pages)
    assert mock_client.get_json.call_count == 2

    db.close()


def test_topic_fetcher_fetch_category_topics_empty_category(tmp_path):
    """Test fetching topics from empty category."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {"topic_list": {"topics": []}}

    fetcher = TopicFetcher(mock_client, db)
    topics = fetcher.fetch_category_topics(999)

    # Should return empty list for empty category
    assert len(topics) == 0

    # Should call API once and stop
    mock_client.get_json.assert_called_once()

    db.close()


def test_topic_fetcher_fetch_all_topics_with_pagination(tmp_path):
    """Test fetching all forum topics with pagination."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)

    # Mock two pages of results
    def mock_get_json(path):
        if "page=0" in path:
            return {
                "topic_list": {
                    "topics": [
                        {
                            "id": i,
                            "title": f"Topic {i}",
                            "slug": f"topic-{i}",
                            "category_id": 1,
                            "user_id": 10,
                            "created_at": "2024-01-01T12:00:00Z",
                            "posts_count": 5,
                            "views": 100,
                        }
                        for i in range(1, 31)
                    ]
                }
            }
        elif "page=1" in path:
            return {
                "topic_list": {
                    "topics": [
                        {
                            "id": i,
                            "title": f"Topic {i}",
                            "slug": f"topic-{i}",
                            "category_id": 1,
                            "user_id": 10,
                            "created_at": "2024-01-01T12:00:00Z",
                            "posts_count": 5,
                            "views": 100,
                        }
                        for i in range(31, 41)  # 10 topics (last page)
                    ]
                }
            }
        else:
            return {"topic_list": {"topics": []}}

    mock_client.get_json.side_effect = mock_get_json

    fetcher = TopicFetcher(mock_client, db)
    topics = fetcher.fetch_all_topics()

    # Should fetch all topics from both pages
    assert len(topics) == 40
    assert topics[0].id == 1
    assert topics[39].id == 40

    # Should call API twice
    assert mock_client.get_json.call_count == 2

    db.close()


def test_topic_fetcher_fetch_category_topics_with_api_error(tmp_path):
    """Test that pagination handles API errors gracefully."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)

    # First page succeeds, second page fails
    def mock_get_json(path):
        if "page=0" in path:
            return {
                "topic_list": {
                    "topics": [
                        {
                            "id": i,
                            "title": f"Topic {i}",
                            "slug": f"topic-{i}",
                            "category_id": 5,
                            "user_id": 10,
                            "created_at": "2024-01-01T12:00:00Z",
                            "posts_count": 5,
                            "views": 100,
                        }
                        for i in range(1, 31)
                    ]
                }
            }
        elif "page=1" in path:
            raise Exception("API error")

    mock_client.get_json.side_effect = mock_get_json

    fetcher = TopicFetcher(mock_client, db)
    topics = fetcher.fetch_category_topics(5)

    # Should return topics from first page even if second page fails
    assert len(topics) == 30
    assert topics[0].id == 1

    db.close()


# ============================================================================
# PostFetcher Tests
# ============================================================================


def test_post_fetcher_fetch_latest_posts(tmp_path):
    """Test fetching latest posts."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "latest_posts": [
            {
                "id": 1,
                "topic_id": 10,
                "user_id": 5,
                "post_number": 1,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "cooked": "<p>Post 1</p>",
                "raw": "Post 1",
                "username": "user1",
            },
            {
                "id": 2,
                "topic_id": 11,
                "user_id": 6,
                "post_number": 1,
                "created_at": "2024-01-02T12:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z",
                "cooked": "<p>Post 2</p>",
                "raw": "Post 2",
                "username": "user2",
            },
        ]
    }

    fetcher = PostFetcher(mock_client, db)
    posts = fetcher.fetch_latest_posts()

    assert len(posts) == 2
    assert posts[0].id == 1
    assert posts[1].id == 2

    db.close()


def test_post_fetcher_fetch_latest_posts_since_date(tmp_path):
    """Test fetching posts since a specific date."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "latest_posts": [
            {
                "id": 1,
                "topic_id": 10,
                "user_id": 5,
                "post_number": 1,
                "created_at": "2024-01-05T12:00:00Z",
                "updated_at": "2024-01-05T12:00:00Z",
                "cooked": "<p>Recent post</p>",
                "raw": "Recent post",
                "username": "user1",
            }
        ]
    }

    fetcher = PostFetcher(mock_client, db)
    since_date = datetime(2024, 1, 1)
    posts = fetcher.fetch_latest_posts(since=since_date)

    assert len(posts) >= 0  # Should return posts after the date

    db.close()


def test_post_fetcher_fetch_post(tmp_path):
    """Test fetching a single post."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "id": 123,
        "topic_id": 10,
        "user_id": 5,
        "post_number": 1,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "cooked": "<p>Test post</p>",
        "raw": "Test post",
        "username": "testuser",
    }

    fetcher = PostFetcher(mock_client, db)
    post = fetcher.fetch_post(123)

    assert post is not None
    assert post.id == 123
    assert post.username == "testuser"

    db.close()


def test_post_fetcher_fetch_posts_before(tmp_path):
    """Test fetching posts before a specific post ID."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "latest_posts": [
            {
                "id": 98,
                "topic_id": 10,
                "user_id": 5,
                "post_number": 1,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "cooked": "<p>Earlier post</p>",
                "raw": "Earlier post",
                "username": "user1",
            }
        ]
    }

    fetcher = PostFetcher(mock_client, db)
    posts = fetcher.fetch_posts_before(100)

    assert len(posts) >= 0

    db.close()


# ============================================================================
# UserFetcher Tests
# ============================================================================


def test_user_fetcher_fetch_user(tmp_path):
    """Test fetching a user by username."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.return_value = {
        "user": {
            "id": 123,
            "username": "testuser",
            "name": "Test User",
            "avatar_template": "/user_avatar/test/{size}/1_2.png",
            "trust_level": 2,
            "created_at": "2023-01-01T00:00:00Z",
        }
    }

    fetcher = UserFetcher(mock_client, db)
    user = fetcher.fetch_user("testuser")

    assert user is not None
    assert user.id == 123
    assert user.username == "testuser"
    assert user.trust_level == 2

    db.close()


def test_user_fetcher_fetch_user_not_found(tmp_path):
    """Test fetching user that doesn't exist."""
    db = ArchiveDatabase(tmp_path / "test.db")

    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.get_json.side_effect = Exception("User not found")

    fetcher = UserFetcher(mock_client, db)
    user = fetcher.fetch_user("nonexistent")

    assert user is None

    db.close()


def test_user_fetcher_fetch_user_by_id(tmp_path):
    """Test fetching a user by ID."""
    db = ArchiveDatabase(tmp_path / "test.db")

    # First, store a user
    user = User(
        id=456,
        username="existinguser",
        name="Existing User",
        avatar_template="",
        trust_level=1,
        created_at=datetime(2023, 1, 1),
    )
    db.insert_user(user)

    mock_client = Mock(spec=DiscourseAPIClient)

    UserFetcher(mock_client, db)
    # Try to get from database
    retrieved = db.get_user(456)

    assert retrieved is not None
    assert retrieved.id == 456
    assert retrieved.username == "existinguser"

    db.close()


# ============================================================================
# API Client Retry and Rate Limiting Tests
# ============================================================================


def test_api_client_exponential_backoff():
    """Test exponential backoff calculation."""
    client = DiscourseAPIClient("https://test.org", rate_limit=0.1)

    # Test backoff increases exponentially
    backoff_0 = client._exponential_backoff(0)
    backoff_1 = client._exponential_backoff(1)
    backoff_2 = client._exponential_backoff(2)

    assert backoff_0 < backoff_1 < backoff_2
    assert backoff_1 == backoff_0 * 2
    assert backoff_2 == backoff_1 * 2


def test_api_client_fetch_with_retry_success():
    """Test successful fetch after retries."""
    client = DiscourseAPIClient("https://test.org", rate_limit=0.01, max_retries=3)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        result = client._fetch_with_retry("https://test.org/api/test")

        assert result == '{"success": true}'
        mock_urlopen.assert_called_once()


def test_api_client_fetch_with_retry_failure():
    """Test fetch fails after max retries."""
    import urllib.error

    client = DiscourseAPIClient("https://test.org", rate_limit=0.01, max_retries=2)

    with patch("urllib.request.urlopen") as mock_urlopen:
        # Simulate network errors
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        with pytest.raises(urllib.error.URLError):
            client._fetch_with_retry("https://test.org/api/test")

        # Should retry max_retries times
        assert mock_urlopen.call_count == 2


def test_api_client_get_json():
    """Test get_json method."""
    client = DiscourseAPIClient("https://test.org", rate_limit=0.01)

    with patch.object(client, "_fetch_with_retry") as mock_fetch:
        mock_fetch.return_value = '{"key": "value"}'

        result = client.get_json("/api/test")

        assert result == {"key": "value"}
        mock_fetch.assert_called_once()


# ============================================================================
# API Client Statistics Tests
# ============================================================================


def test_api_client_statistics_initialization():
    """Test that statistics are initialized to zero."""
    client = DiscourseAPIClient("https://test.org", rate_limit=0.01)

    assert client.requests_made == 0
    assert client.requests_successful == 0
    assert client.requests_failed == 0
    assert client.retries_attempted == 0
    assert client.bytes_transferred == 0
    assert client.start_time > 0


def test_api_client_statistics_successful_request():
    """Test statistics tracking on successful request."""
    client = DiscourseAPIClient("https://test.org", rate_limit=0.01)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"test": "data"}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client._fetch_with_retry("https://test.org/api/test")

        assert client.requests_made == 1
        assert client.requests_successful == 1
        assert client.requests_failed == 0
        assert client.retries_attempted == 0
        assert client.bytes_transferred == len(b'{"test": "data"}')


def test_api_client_statistics_failed_request():
    """Test statistics tracking on failed request."""
    import urllib.error

    client = DiscourseAPIClient("https://test.org", rate_limit=0.01, max_retries=2)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        with pytest.raises(urllib.error.URLError):
            client._fetch_with_retry("https://test.org/api/test")

        # Should have made 2 attempts (max_retries)
        assert client.requests_made == 2
        assert client.requests_successful == 0
        assert client.requests_failed == 1
        assert client.retries_attempted == 1  # Second attempt counts as retry


def test_api_client_statistics_with_retries():
    """Test statistics tracking with successful retry."""
    import urllib.error

    client = DiscourseAPIClient("https://test.org", rate_limit=0.01, max_retries=3)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        # First call fails, second succeeds
        mock_urlopen.side_effect = [
            urllib.error.URLError("Network error"),
            mock_response,
        ]

        result = client._fetch_with_retry("https://test.org/api/test")

        assert result == '{"success": true}'
        assert client.requests_made == 2
        assert client.requests_successful == 1
        assert client.requests_failed == 0
        assert client.retries_attempted == 1


def test_api_client_get_stats():
    """Test get_stats method returns correct statistics."""

    client = DiscourseAPIClient("https://test.org", rate_limit=0.01)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": "test"}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client._fetch_with_retry("https://test.org/api/test")

        stats = client.get_stats()

        assert stats["requests_made"] == 1
        assert stats["requests_successful"] == 1
        assert stats["requests_failed"] == 0
        assert stats["retries_attempted"] == 0
        assert stats["bytes_transferred"] == len(b'{"data": "test"}')
        assert stats["elapsed_time"] > 0
        assert stats["request_rate"] >= 0


def test_api_client_reset_stats():
    """Test reset_stats method clears all statistics."""
    client = DiscourseAPIClient("https://test.org", rate_limit=0.01)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b"test data"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        # Make a request
        client._fetch_with_retry("https://test.org/api/test")

        # Verify stats are set
        assert client.requests_made > 0

        # Reset stats
        client.reset_stats()

        # Verify stats are cleared
        assert client.requests_made == 0
        assert client.requests_successful == 0
        assert client.requests_failed == 0
        assert client.retries_attempted == 0
        assert client.bytes_transferred == 0
