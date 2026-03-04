# ABOUTME: Migration utilities for Chronicon
# ABOUTME: Handles importing data from legacy JSON archives and schema migrations

"""Migration utilities for importing legacy data and upgrading schemas."""

import json
from pathlib import Path

from ..models.post import Post
from ..models.topic import Topic
from ..utils.logger import get_logger
from .database import ArchiveDatabase

log = get_logger(__name__)


class JSONMigrator:
    """Migrate data from legacy JSON-based archives."""

    def __init__(self, db: ArchiveDatabase):
        """
        Initialize migrator with database connection.

        Args:
            db: ArchiveDatabase instance
        """
        self.db = db

    def migrate_from_json(self, json_dir: Path) -> dict:
        """
        Import posts and topics from JSON files.

        Args:
            json_dir: Directory containing JSON files from legacy archiver

        Returns:
            dict with migration statistics
        """
        stats = {
            "posts_imported": 0,
            "topics_imported": 0,
            "errors": 0,
        }

        json_files = list(json_dir.glob("*.json"))

        for json_file in json_files:
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Attempt to import as post/topic data
                if "posts" in data:
                    self._import_posts(data["posts"])
                    stats["posts_imported"] += len(data["posts"])

                if "topic" in data or "topics" in data:
                    topic_data = data.get("topic") or data.get("topics")
                    if isinstance(topic_data, list):
                        for t in topic_data:
                            self._import_topic(t)
                            stats["topics_imported"] += 1
                    else:
                        self._import_topic(topic_data)
                        stats["topics_imported"] += 1

            except Exception as e:
                stats["errors"] += 1
                log.warning(f"Error importing {json_file}: {e}")

        return stats

    def _import_posts(self, posts_data: list[dict]) -> None:
        """Import posts from JSON data."""
        for post_data in posts_data:
            try:
                post = Post.from_dict(post_data)
                self.db.insert_post(post)
            except Exception as e:
                log.warning(f"Error importing post {post_data.get('id')}: {e}")

    def _import_topic(self, topic_data: dict) -> None:
        """Import a topic from JSON data."""
        try:
            topic = Topic.from_dict(topic_data)
            self.db.insert_topic(topic)
        except Exception as e:
            log.warning(f"Error importing topic {topic_data.get('id')}: {e}")


def migrate_schema(connection, from_version: int, to_version: int) -> None:
    """
    Migrate database schema from one version to another.

    Args:
        connection: SQLite connection
        from_version: Current schema version
        to_version: Target schema version
    """
    # Placeholder for future schema migrations
    # Example: Add new columns, create new tables, etc.
    pass
