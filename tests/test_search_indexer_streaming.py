# ABOUTME: Tests for streaming search indexer
# ABOUTME: Verifies batched generation, JSON validity, and memory-bounded operation

"""Tests for streaming search index generation."""

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.storage.database import ArchiveDatabase
from chronicon.utils.search_indexer import SearchIndexer


@pytest.fixture
def db_with_data(tmp_path):
    """Create a database with multiple topics and posts."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    cat = Category(
        id=1,
        name="General",
        slug="general",
        color="FF0000",
        text_color="FFFFFF",
        description="General",
        parent_category_id=None,
        topic_count=5,
    )
    db.insert_category(cat)

    for i in range(1, 6):
        topic = Topic(
            id=i,
            title=f"Topic {i}",
            slug=f"topic-{i}",
            category_id=1,
            user_id=1,
            created_at=datetime(2024, 1, i, 12, 0, 0),
            updated_at=datetime(2024, 1, i, 12, 0, 0),
            posts_count=3,
            views=10,
        )
        db.insert_topic(topic)

        for j in range(1, 4):
            post = Post(
                id=i * 100 + j,
                topic_id=i,
                user_id=1,
                username=f"user{j}",
                post_number=j,
                cooked=f"<p>Content for topic {i} post {j}</p>",
                raw=f"Content for topic {i} post {j}",
                created_at=datetime(2024, 1, i, 12, j, 0),
                updated_at=datetime(2024, 1, i, 12, j, 0),
            )
            db.insert_post(post)

    yield db
    db.close()


class TestStreamingSearchIndexer:
    """Tests for streaming search index generation."""

    def test_generates_valid_json(self, db_with_data, tmp_path):
        """Generated search index is valid JSON."""
        indexer = SearchIndexer(db_with_data)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        with open(output) as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert "generated_at" in data
        assert isinstance(data["items"], list)

    def test_indexes_topics_and_posts(self, db_with_data, tmp_path):
        """Index contains both topic and post entries."""
        indexer = SearchIndexer(db_with_data)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        with open(output) as f:
            data = json.load(f)

        topics = [item for item in data["items"] if item["type"] == "topic"]
        posts = [item for item in data["items"] if item["type"] == "post"]

        assert len(topics) == 5
        # 3 posts per topic, but first post is indexed as topic, so 2 post entries each
        assert len(posts) == 10

    def test_topic_entry_structure(self, db_with_data, tmp_path):
        """Topic entries have correct structure."""
        indexer = SearchIndexer(db_with_data)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        with open(output) as f:
            data = json.load(f)

        topic_item = next(item for item in data["items"] if item["type"] == "topic")
        assert "id" in topic_item
        assert "title" in topic_item
        assert "url" in topic_item
        assert "excerpt" in topic_item
        assert "category" in topic_item
        assert "author" in topic_item
        assert "created_at" in topic_item

    def test_post_urls_include_page_numbers(self, db_with_data, tmp_path):
        """Post URLs include correct page numbers."""
        indexer = SearchIndexer(db_with_data, posts_per_page=2)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        with open(output) as f:
            data = json.load(f)

        posts = [item for item in data["items"] if item["type"] == "post"]
        # Post 3 (index 2) with posts_per_page=2 should be on page 2
        page2_posts = [p for p in posts if "page-2" in p["url"]]
        assert len(page2_posts) > 0

    def test_compact_json_output(self, db_with_data, tmp_path):
        """Output JSON is compact (no indentation)."""
        indexer = SearchIndexer(db_with_data)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        content = output.read_text()
        # Compact JSON has no newlines within items
        assert "\n  " not in content

    def test_empty_database(self, tmp_path):
        """Handles empty database gracefully."""
        db_path = tmp_path / "empty.db"
        db = ArchiveDatabase(db_path)
        indexer = SearchIndexer(db)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        with open(output) as f:
            data = json.load(f)

        assert data["items"] == []
        db.close()

    def test_category_names_cached(self, db_with_data, tmp_path):
        """Category lookups are cached across topics."""
        indexer = SearchIndexer(db_with_data)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        with open(output) as f:
            data = json.load(f)

        topics = [item for item in data["items"] if item["type"] == "topic"]
        # All topics share category 1 "General"
        assert all(t["category"] == "General" for t in topics)

    def test_uses_iter_topics_batched(self, tmp_path):
        """Indexer uses iter_topics_batched instead of get_all_topics."""
        db_path = tmp_path / "test.db"
        db = ArchiveDatabase(db_path)

        mock_db = MagicMock(wraps=db)
        mock_db.iter_topics_batched.return_value = iter([])

        indexer = SearchIndexer(mock_db)
        output = tmp_path / "search_index.json"
        indexer.generate_index(output)

        mock_db.iter_topics_batched.assert_called_once()
        db.close()


class TestSearchIndexerExcerpt:
    """Tests for excerpt extraction."""

    def test_short_content_unchanged(self):
        """Short content is returned as-is."""
        indexer = SearchIndexer(MagicMock())
        assert indexer.extract_excerpt("Hello world") == "Hello world"

    def test_long_content_truncated(self):
        """Long content is truncated at word boundary."""
        indexer = SearchIndexer(MagicMock())
        long_text = "word " * 100
        result = indexer.extract_excerpt(long_text, max_length=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")
