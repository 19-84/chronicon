# ABOUTME: Main database interface for Chronicon
# ABOUTME: Provides CRUD operations for all entities and query methods

"""Archive database interface using SQLite."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ..models.category import Category
from ..models.post import Post
from ..models.topic import Topic
from ..models.user import User
from .database_base import ArchiveDatabaseBase
from .schema import create_schema


class ArchiveDatabase(ArchiveDatabaseBase):
    """Main database interface for the archive."""

    def __init__(
        self, db_path: Path | None = None, connection_string: str | None = None
    ):
        """
        Initialize database connection and create schema if needed.

        Args:
            db_path: Path to SQLite database file (for backward compatibility)
            connection_string: Database connection string
                              (overrides db_path if provided)
        """
        # Support both old (db_path) and new (connection_string) interfaces
        if connection_string:
            db_path = Path(connection_string)
        elif db_path is None:
            raise ValueError("Either db_path or connection_string must be provided")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()
        self._run_migrations()

    def _create_schema(self):
        """Create database schema if it doesn't exist."""
        create_schema(self.connection)

    def _run_migrations(self):
        """
        Apply any necessary schema migrations for old databases.

        This method checks for missing columns and adds them to maintain
        backward compatibility with older archive databases.
        """
        cursor = self.connection.cursor()

        # Get current columns in site_metadata table
        cursor.execute("PRAGMA table_info(site_metadata)")
        columns = [row[1] for row in cursor.fetchall()]

        # Track if we need to commit changes
        needs_commit = False

        # Check and add missing site_metadata columns
        if "logo_url" not in columns:
            cursor.execute("ALTER TABLE site_metadata ADD COLUMN logo_url TEXT")
            needs_commit = True

        if "banner_image_url" not in columns:
            cursor.execute("ALTER TABLE site_metadata ADD COLUMN banner_image_url TEXT")
            needs_commit = True

        if "contact_email" not in columns:
            cursor.execute("ALTER TABLE site_metadata ADD COLUMN contact_email TEXT")
            needs_commit = True

        if "discourse_version" not in columns:
            cursor.execute(
                "ALTER TABLE site_metadata ADD COLUMN discourse_version TEXT"
            )
            needs_commit = True

        if "favicon_url" not in columns:
            cursor.execute("ALTER TABLE site_metadata ADD COLUMN favicon_url TEXT")
            needs_commit = True

        # Check and add missing users table columns
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [row[1] for row in cursor.fetchall()]

        if "local_avatar_path" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN local_avatar_path TEXT")
            needs_commit = True

        # Commit if any migrations were applied
        if needs_commit:
            self.connection.commit()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    # Post operations
    def insert_post(self, post: Post) -> None:
        """Insert a post into the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO posts
            (id, topic_id, user_id, post_number, created_at, updated_at,
             cooked, raw, username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            post.to_db_row(),
        )
        self.connection.commit()

    def update_post(self, post: Post) -> None:
        """Update an existing post."""
        self.insert_post(post)  # INSERT OR REPLACE handles updates

    def get_post(self, post_id: int) -> Post | None:
        """Retrieve a post by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        if row:
            return Post(
                id=row["id"],
                topic_id=row["topic_id"],
                user_id=row["user_id"],
                post_number=row["post_number"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                cooked=row["cooked"],
                raw=row["raw"],
                username=row["username"],
            )
        return None

    def get_posts_since(self, date: datetime) -> list[Post]:
        """Get all posts created or updated since a specific date."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM posts WHERE updated_at >= ? ORDER BY updated_at",
            (date.isoformat(),),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_topic_posts(self, topic_id: int) -> list[Post]:
        """Get all posts for a specific topic."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM posts WHERE topic_id = ? ORDER BY post_number",
            (topic_id,),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_topic_posts_paginated(
        self, topic_id: int, page: int, per_page: int
    ) -> list[Post]:
        """
        Get a specific page of posts for a topic.

        Args:
            topic_id: Topic ID
            page: Page number (1-indexed)
            per_page: Number of posts per page

        Returns:
            List of Post objects for the requested page
        """
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT * FROM posts
            WHERE topic_id = ?
            ORDER BY post_number
            LIMIT ? OFFSET ?
            """,
            (topic_id, per_page, offset),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_topic_posts_count(self, topic_id: int) -> int:
        """
        Get the total number of posts for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            Total count of posts
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM posts WHERE topic_id = ?",
            (topic_id,),
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def post_exists(self, post_id: int) -> bool:
        """Check if a post exists in the database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,))
        return cursor.fetchone() is not None

    # Topic operations
    def insert_topic(self, topic: Topic) -> None:
        """Insert a topic into the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO topics
            (id, title, slug, category_id, user_id, created_at, updated_at,
             posts_count, views, tags, excerpt, image_url, fancy_title,
             like_count, reply_count, highest_post_number, participant_count,
             word_count, pinned, pinned_globally, closed, archived,
             featured_link, has_accepted_answer, has_summary, visible,
             last_posted_at, thumbnails, bookmarked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                # Core fields
                topic.id,
                topic.title,
                topic.slug,
                topic.category_id,
                topic.user_id,
                topic.created_at.isoformat(),
                topic.updated_at.isoformat() if topic.updated_at else None,
                topic.posts_count,
                topic.views,
                # Content & Discovery
                json.dumps(topic.tags) if topic.tags else None,
                topic.excerpt,
                topic.image_url,
                topic.fancy_title,
                # Engagement Metrics
                topic.like_count,
                topic.reply_count,
                topic.highest_post_number,
                topic.participant_count,
                topic.word_count,
                # Status & Classification (bool -> int for SQLite)
                1 if topic.pinned else 0,
                1 if topic.pinned_globally else 0,
                1 if topic.closed else 0,
                1 if topic.archived else 0,
                # Context & Metadata
                topic.featured_link,
                1 if topic.has_accepted_answer else 0,
                1 if topic.has_summary else 0,
                1 if topic.visible else 0,
                topic.last_posted_at.isoformat() if topic.last_posted_at else None,
                json.dumps(topic.thumbnails) if topic.thumbnails else None,
                1 if topic.bookmarked else 0,
            ),
        )
        self.connection.commit()

    def get_topic(self, topic_id: int) -> Topic | None:
        """Retrieve a topic by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_topic(row)
        return None

    def get_topics_by_category(self, category_id: int) -> list[Topic]:
        """Get all topics in a specific category."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM topics WHERE category_id = ? ORDER BY created_at DESC",
            (category_id,),
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_all_topics(self) -> list[Topic]:
        """Get all topics in the database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM topics ORDER BY created_at DESC")
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_topics_by_ids(self, topic_ids: list[int]) -> list[Topic]:
        """
        Get multiple topics by their IDs.

        Args:
            topic_ids: List of topic IDs to fetch

        Returns:
            List of Topic objects (may be fewer than requested if some don't exist)
        """
        if not topic_ids:
            return []

        cursor = self.connection.cursor()
        placeholders = ",".join(["?" for _ in topic_ids])
        cursor.execute(
            f"""
            SELECT * FROM topics
            WHERE id IN ({placeholders})
            ORDER BY created_at DESC
            """,
            topic_ids,
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_topics_by_tag(self, tag: str) -> list[Topic]:
        """
        Get all topics with a specific tag.

        Args:
            tag: Tag to search for (case-sensitive)

        Returns:
            List of Topic objects that have the specified tag
        """
        cursor = self.connection.cursor()
        # Use LIKE to match the tag in the JSON array
        # This searches for the tag as a JSON string value
        cursor.execute(
            """SELECT * FROM topics
               WHERE tags IS NOT NULL
               AND tags LIKE ?
               ORDER BY created_at DESC""",
            (f'%"{tag}"%',),
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_pinned_topics(self, globally_pinned_only: bool = False) -> list[Topic]:
        """
        Get all pinned topics.

        Args:
            globally_pinned_only: If True, only return globally pinned topics

        Returns:
            List of pinned Topic objects sorted by created_at descending
        """
        cursor = self.connection.cursor()
        if globally_pinned_only:
            cursor.execute(
                """
                SELECT * FROM topics
                WHERE pinned_globally = 1
                ORDER BY created_at DESC
                """
            )
        else:
            cursor.execute(
                """
                SELECT * FROM topics
                WHERE pinned = 1 OR pinned_globally = 1
                ORDER BY created_at DESC
                """
            )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_closed_topics(self) -> list[Topic]:
        """
        Get all closed topics.

        Returns:
            List of closed Topic objects sorted by created_at descending
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM topics WHERE closed = 1 ORDER BY created_at DESC")
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_archived_topics(self) -> list[Topic]:
        """
        Get all archived topics.

        Returns:
            List of archived Topic objects sorted by created_at descending
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM topics WHERE archived = 1 ORDER BY created_at DESC"
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_all_topics_with_category(self) -> list[dict]:
        """
        Get all topics with category information included.

        Returns:
            List of dicts with topic data and category fields
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT t.*, c.name as category_name, c.slug as category_slug,
                   c.color as category_color
            FROM topics t
            LEFT JOIN categories c ON t.category_id = c.id
            ORDER BY t.created_at DESC
            """
        )
        results = []
        for row in cursor.fetchall():
            topic_dict = dict(row)
            results.append(topic_dict)
        return results

    def get_topics_by_category_with_info(self, category_id: int) -> list[dict]:
        """
        Get topics in a category with category information included.

        Args:
            category_id: Category ID to filter by

        Returns:
            List of dicts with topic data and category fields
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT t.*, c.name as category_name, c.slug as category_slug,
                   c.color as category_color
            FROM topics t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.category_id = ?
            ORDER BY t.created_at DESC
            """,
            (category_id,),
        )
        results = []
        for row in cursor.fetchall():
            topic_dict = dict(row)
            results.append(topic_dict)
        return results

    # User operations
    def insert_user(self, user: User) -> None:
        """Insert a user into the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO users
            (id, username, name, avatar_template, trust_level, created_at,
             local_avatar_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.name,
                user.avatar_template,
                user.trust_level,
                user.created_at.isoformat() if user.created_at else None,
                user.local_avatar_path,
            ),
        )
        self.connection.commit()

    def get_user(self, user_id: int) -> User | None:
        """Retrieve a user by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_user(row)
        return None

    def get_user_by_username(self, username: str) -> User | None:
        """Retrieve a user by username."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return self._row_to_user(row)
        return None

    # Category operations
    def insert_category(self, category: Category) -> None:
        """Insert a category into the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO categories
            (id, name, slug, color, text_color, description,
             parent_category_id, topic_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category.id,
                category.name,
                category.slug,
                category.color,
                category.text_color,
                category.description,
                category.parent_category_id,
                category.topic_count,
            ),
        )
        self.connection.commit()

    def get_all_categories(self) -> list[Category]:
        """Get all categories in the database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        return [self._row_to_category(row) for row in cursor.fetchall()]

    def get_category(self, category_id: int) -> Category | None:
        """Get a single category by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_category(row)
        return None

    # Query operations for exporters
    def get_recent_topics(self, limit: int = 20) -> list[Topic]:
        """
        Get recent topics for homepage.

        Args:
            limit: Maximum number of topics to return

        Returns:
            List of recent topics sorted by created_at descending
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM topics ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_topics_count(self) -> int:
        """
        Get the total number of topics in the database.

        Returns:
            Total count of topics
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM topics")
        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_topics_paginated(
        self,
        page: int,
        per_page: int,
        order_by: str = "created_at",
        order_dir: str = "DESC",
    ) -> list[Topic]:
        """
        Get a paginated list of topics with flexible sorting.

        Args:
            page: Page number (1-indexed)
            per_page: Number of topics per page
            order_by: Column to sort by (created_at, posts_count, views)
            order_dir: Sort direction (ASC or DESC)

        Returns:
            List of Topic objects for the requested page
        """
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page

        # Validate order_by to prevent SQL injection
        valid_columns = ["created_at", "posts_count", "views", "updated_at"]
        if order_by not in valid_columns:
            order_by = "created_at"

        # Validate order_dir
        if order_dir.upper() not in ["ASC", "DESC"]:
            order_dir = "DESC"

        query = f"SELECT * FROM topics ORDER BY {order_by} {order_dir} LIMIT ? OFFSET ?"
        cursor.execute(query, (per_page, offset))
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_category_topics_paginated(
        self, category_id: int, page: int, per_page: int
    ) -> list[Topic]:
        """
        Get a paginated list of topics for a specific category.

        Args:
            category_id: Category ID
            page: Page number (1-indexed)
            per_page: Number of topics per page

        Returns:
            List of Topic objects for the requested page
        """
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT * FROM topics
            WHERE category_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (category_id, per_page, offset),
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_all_users(self) -> list[User]:
        """Get all users in the database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users ORDER BY username")
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def get_unique_usernames(self) -> set[str]:
        """
        Get all unique usernames from posts in the database.

        Returns:
            Set of unique usernames (excluding None and empty strings)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT DISTINCT username
            FROM posts
            WHERE username IS NOT NULL AND username != ''
            """
        )
        return {row[0] for row in cursor.fetchall()}

    def get_users_count(self) -> int:
        """
        Get the total number of users in the database.

        Returns:
            Total count of users
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_users_with_post_counts(
        self,
        page: int,
        per_page: int,
        order_by: str = "post_count",
        order_dir: str = "DESC",
    ) -> list[dict]:
        """
        Get paginated list of users with their post counts.

        Args:
            page: Page number (1-indexed)
            per_page: Number of users per page
            order_by: Column to sort by (post_count, username)
            order_dir: Sort direction (ASC or DESC)

        Returns:
            List of dictionaries with user data and post_count
        """
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page

        # Validate order_by to prevent SQL injection
        valid_columns = ["post_count", "username"]
        if order_by not in valid_columns:
            order_by = "post_count"

        # Validate order_dir
        if order_dir.upper() not in ["ASC", "DESC"]:
            order_dir = "DESC"

        query = f"""
            SELECT
                u.*,
                COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.username = p.username
            GROUP BY u.id
            ORDER BY {order_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, (per_page, offset))

        results = []
        for row in cursor.fetchall():
            user = self._row_to_user(row)
            # Create dict with user attributes and post_count
            user_dict = {"user": user, "post_count": row["post_count"]}
            results.append(user_dict)

        return results

    def get_user_posts(self, user_id: int, limit: int = 50) -> list[dict]:
        """
        Get posts by a specific user with topic information.

        Args:
            user_id: User ID
            limit: Maximum number of posts to return

        Returns:
            List of dictionaries with post data and associated topic info
        """
        # First get the username
        user = self.get_user(user_id)
        if not user:
            return []

        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT
                p.*,
                t.title as topic_title,
                t.slug as topic_slug,
                t.id as topic_id,
                c.name as category_name,
                c.slug as category_slug,
                c.color as category_color
            FROM posts p
            JOIN topics t ON p.topic_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE p.username = ?
            ORDER BY p.created_at DESC
            LIMIT ?
            """,
            (user.username, limit),
        )

        results = []
        for row in cursor.fetchall():
            post_dict = {
                "post": self._row_to_post(row),
                "topic_title": row["topic_title"],
                "topic_slug": row["topic_slug"],
                "topic_id": row["topic_id"],
                "category_name": row["category_name"],
                "category_slug": row["category_slug"],
                "category_color": row["category_color"],
            }
            results.append(post_dict)

        return results

    def get_user_posts_paginated(
        self, user_id: int, page: int, per_page: int
    ) -> list[dict]:
        """
        Get a paginated list of posts by a specific user with topic information.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            per_page: Number of posts per page

        Returns:
            List of dictionaries with post data and associated topic info
        """
        # First get the username
        user = self.get_user(user_id)
        if not user:
            return []

        cursor = self.connection.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT
                p.*,
                t.title as topic_title,
                t.slug as topic_slug,
                t.id as topic_id,
                c.name as category_name,
                c.slug as category_slug,
                c.color as category_color
            FROM posts p
            JOIN topics t ON p.topic_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE p.username = ?
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user.username, per_page, offset),
        )

        results = []
        for row in cursor.fetchall():
            post_dict = {
                "post": self._row_to_post(row),
                "topic_title": row["topic_title"],
                "topic_slug": row["topic_slug"],
                "topic_id": row["topic_id"],
                "category_name": row["category_name"],
                "category_slug": row["category_slug"],
                "category_color": row["category_color"],
            }
            results.append(post_dict)

        return results

    def get_user_post_count(self, user_id: int) -> int:
        """
        Get the total number of posts by a user.

        Args:
            user_id: User ID

        Returns:
            Total count of posts
        """
        user = self.get_user(user_id)
        if not user:
            return 0

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM posts WHERE username = ?", (user.username,)
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_statistics(self) -> dict:
        """
        Get overall statistics for the archive.

        Returns:
            Dictionary with total_topics, total_posts, total_users,
            total_categories, total_views counts
        """
        cursor = self.connection.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM topics")
        total_topics = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM posts")
        total_posts = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM categories")
        total_categories = cursor.fetchone()["count"]

        cursor.execute("SELECT COALESCE(SUM(views), 0) as count FROM topics")
        total_views = cursor.fetchone()["count"]

        return {
            "total_topics": total_topics,
            "total_posts": total_posts,
            "total_users": total_users,
            "total_categories": total_categories,
            "total_views": total_views,
        }

    def get_archive_statistics(self) -> dict:
        """
        Get extended statistics for About page.

        Returns:
            Dictionary with comprehensive archive statistics including:
            - Basic counts (topics, posts, users, categories)
            - Date range (earliest and latest content dates)
            - Top contributors (users with most posts)
            - Popular categories (by topic count)
            - Export history (last export info)
        """
        cursor = self.connection.cursor()

        # Start with basic statistics
        stats = self.get_statistics()

        # Get date range of archived content
        cursor.execute("""
            SELECT MIN(created_at) as earliest, MAX(created_at) as latest
            FROM topics
        """)
        date_row = cursor.fetchone()
        if date_row and date_row["earliest"]:
            stats["earliest_topic"] = date_row["earliest"]
            stats["latest_topic"] = date_row["latest"]
        else:
            stats["earliest_topic"] = None
            stats["latest_topic"] = None

        # Get top 10 contributors by post count
        cursor.execute("""
            SELECT username, COUNT(*) as post_count
            FROM posts
            WHERE username IS NOT NULL
            GROUP BY username
            ORDER BY post_count DESC
            LIMIT 10
        """)
        stats["top_contributors"] = [
            {"username": row["username"], "post_count": row["post_count"]}
            for row in cursor.fetchall()
        ]

        # Get popular categories (top 5 by topic count)
        cursor.execute("""
            SELECT id, name, slug, color, topic_count
            FROM categories
            ORDER BY topic_count DESC
            LIMIT 5
        """)
        stats["popular_categories"] = [dict(row) for row in cursor.fetchall()]

        # Get last HTML export information
        cursor.execute("""
            SELECT format, exported_at, topic_count, post_count
            FROM export_history
            WHERE format = 'html'
            ORDER BY exported_at DESC
            LIMIT 1
        """)
        export_row = cursor.fetchone()
        if export_row:
            stats["last_export"] = dict(export_row)
        else:
            stats["last_export"] = None

        return stats

    def get_activity_timeline(self) -> list[dict]:
        """
        Get monthly activity timeline for visualization.

        Returns:
            List of dictionaries with month, topic_count, and post_count
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as topic_count,
                SUM(posts_count) as post_count
            FROM topics
            GROUP BY month
            ORDER BY month
        """)
        return [dict(row) for row in cursor.fetchall()]

    # Full-text search operations (FTS5)
    def search_topics(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> list[Topic]:
        """
        Full-text search across topics using SQLite FTS5.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching Topic objects, ranked by relevance (BM25)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT t.* FROM topics t
            JOIN topics_fts ON t.id = topics_fts.rowid
            WHERE topics_fts MATCH ?
            ORDER BY bm25(topics_fts)
            LIMIT ? OFFSET ?
            """,
            (query, limit, offset),
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def search_posts(self, query: str, limit: int = 50, offset: int = 0) -> list[Post]:
        """
        Full-text search across posts using SQLite FTS5.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching Post objects, ranked by relevance (BM25)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT p.* FROM posts p
            JOIN posts_fts ON p.id = posts_fts.rowid
            WHERE posts_fts MATCH ?
            ORDER BY bm25(posts_fts)
            LIMIT ? OFFSET ?
            """,
            (query, limit, offset),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def search_topics_count(self, query: str) -> int:
        """
        Get the total number of topics matching a search query.

        Args:
            query: Search query string

        Returns:
            Total count of matching topics
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM topics t
            JOIN topics_fts ON t.id = topics_fts.rowid
            WHERE topics_fts MATCH ?
            """,
            (query,),
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def search_posts_count(self, query: str) -> int:
        """
        Get the total number of posts matching a search query.

        Args:
            query: Search query string

        Returns:
            Total count of matching posts
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM posts p
            JOIN posts_fts ON p.id = posts_fts.rowid
            WHERE posts_fts MATCH ?
            """,
            (query,),
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def rebuild_search_index(self) -> None:
        """
        Rebuild the full-text search index.

        This populates the FTS5 tables with data from existing topics and posts.
        Should be called after migrating an existing database or if the search
        index becomes corrupted.
        """
        cursor = self.connection.cursor()

        # Rebuild topics_fts
        cursor.execute("INSERT INTO topics_fts(topics_fts) VALUES('rebuild')")

        # Rebuild posts_fts
        cursor.execute("INSERT INTO posts_fts(posts_fts) VALUES('rebuild')")

        self.connection.commit()

    def is_search_available(self) -> bool:
        """
        Check if full-text search is available and properly configured.

        Returns:
            True if FTS5 tables exist and are accessible, False otherwise
        """
        cursor = self.connection.cursor()
        try:
            # Check if topics_fts table exists
            cursor.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type='table' AND name='topics_fts'"
            )
            if not cursor.fetchone():
                return False

            # Check if posts_fts table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
            )
            if not cursor.fetchone():
                return False

            # Try a simple query to ensure FTS is working
            cursor.execute("SELECT * FROM topics_fts LIMIT 1")
            return True
        except Exception:
            return False

    # Asset operations
    def register_asset(
        self, url: str, local_path: str, content_type: str | None = None
    ) -> None:
        """Register a downloaded asset."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO assets (url, local_path, content_type, downloaded_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (url, local_path, content_type),
        )
        self.connection.commit()

    def get_asset_path(self, url: str) -> str | None:
        """Get local path for a previously downloaded asset."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT local_path FROM assets WHERE url = ?", (url,))
        row = cursor.fetchone()
        return row["local_path"] if row else None

    def find_asset_by_url_prefix(self, url_prefix: str) -> str | None:
        """Find asset path by URL prefix match (ignoring query params)."""
        # Escape LIKE wildcards to prevent false matches
        escaped = (
            url_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT local_path FROM assets WHERE url LIKE ? ESCAPE '\\' LIMIT 1",
            (escaped + "%",),
        )
        row = cursor.fetchone()
        return row["local_path"] if row else None

    def get_asset(self, url: str) -> dict | None:
        """
        Get full asset information for a URL.

        Args:
            url: Asset URL

        Returns:
            Dictionary with url, local_path, content_type, downloaded_at or None
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM assets WHERE url = ?", (url,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_assets_by_pattern(self, url_pattern: str) -> list[dict]:
        """
        Find assets matching a URL pattern.

        Useful for finding different resolutions of the same image.

        Args:
            url_pattern: SQL LIKE pattern for matching URLs

        Returns:
            List of asset dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM assets WHERE url LIKE ? ORDER BY url", (url_pattern,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_assets_for_topic(self, topic_id: int) -> list[dict]:
        """
        Get all assets downloaded for a specific topic.

        Assets are organized in directories by topic_id, so this matches
        any asset whose local_path contains /images/{topic_id}/.

        Args:
            topic_id: Topic ID

        Returns:
            List of asset dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM assets WHERE local_path LIKE ? ORDER BY url",
            (f"%/images/{topic_id}/%",),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_assets(self) -> list[dict]:
        """
        Get all registered assets.

        Returns:
            List of all asset dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM assets ORDER BY downloaded_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    # Metadata operations
    def update_site_metadata(self, site_url: str, **kwargs) -> None:
        """Update site metadata."""
        cursor = self.connection.cursor()
        # Check if record exists
        cursor.execute("SELECT 1 FROM site_metadata WHERE site_url = ?", (site_url,))
        exists = cursor.fetchone() is not None

        if exists:
            # Build UPDATE statement dynamically
            fields = ", ".join([f"{k} = ?" for k in kwargs])
            values = list(kwargs.values()) + [site_url]
            cursor.execute(
                f"UPDATE site_metadata SET {fields} WHERE site_url = ?", values
            )
        else:
            # INSERT with provided kwargs
            kwargs["site_url"] = site_url
            fields = ", ".join(kwargs.keys())
            placeholders = ", ".join(["?" for _ in kwargs])
            cursor.execute(
                f"INSERT INTO site_metadata ({fields}) VALUES ({placeholders})",
                list(kwargs.values()),
            )
        self.connection.commit()

    def get_site_metadata(self, site_url: str) -> dict:
        """Get site metadata."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM site_metadata WHERE site_url = ?", (site_url,))
        row = cursor.fetchone()
        return dict(row) if row else {}

    def get_first_site_url(self) -> str | None:
        """
        Get the first site URL from the database.

        Used by watch daemon to discover which site to monitor.

        Returns:
            Site URL string or None if no sites in database
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT site_url FROM site_metadata LIMIT 1")
        row = cursor.fetchone()
        return row["site_url"] if row else None

    def get_site_asset_local_path(self, site_url: str, asset_type: str) -> str | None:
        """
        Get local path for a site asset (logo, banner, etc.).

        Args:
            site_url: Site URL
            asset_type: Type of asset ('logo_url' or 'banner_image_url')

        Returns:
            Local path string if asset was downloaded, None otherwise
        """
        # Get site metadata to find the remote URL
        metadata = self.get_site_metadata(site_url)
        if not metadata or asset_type not in metadata:
            return None

        asset_url = metadata.get(asset_type)
        if not asset_url:
            return None

        # Look up local path in assets table
        return self.get_asset_path(asset_url)

    # Top tags operations
    def store_top_tags(self, tags: list) -> None:
        """
        Store top tags from site configuration.

        Args:
            tags: List of tag names (strings) or tag dicts with 'name' key
        """
        cursor = self.connection.cursor()
        for tag in tags:
            # Handle both string tags and dict tags with 'name' key
            tag_name = tag["name"] if isinstance(tag, dict) else tag
            cursor.execute(
                """
                INSERT OR REPLACE INTO top_tags (tag, topic_count)
                VALUES (?, COALESCE(
                    (SELECT topic_count FROM top_tags WHERE tag = ?), 0))
                """,
                (tag_name, tag_name),
            )
        self.connection.commit()

    def get_all_tags(self, limit: int | None = None) -> list[dict]:
        """
        Get all tags sorted by topic count.

        Args:
            limit: Optional limit on number of tags to return

        Returns:
            List of dicts with 'tag' and 'topic_count' keys
        """
        cursor = self.connection.cursor()
        if limit:
            cursor.execute(
                """
                SELECT tag, topic_count FROM top_tags
                ORDER BY topic_count DESC, tag
                LIMIT ?
                """,
                (limit,),
            )
        else:
            cursor.execute(
                "SELECT tag, topic_count FROM top_tags ORDER BY topic_count DESC, tag"
            )
        return [dict(row) for row in cursor.fetchall()]

    # Export tracking operations
    def record_export(
        self,
        format: str,
        topic_count: int,
        post_count: int,
        output_path: str,
    ) -> None:
        """
        Record an export operation in the export history.

        Args:
            format: Export format ('html', 'markdown', 'github')
            topic_count: Number of topics exported
            post_count: Number of posts exported
            output_path: Path where export was written
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO export_history
            (format, exported_at, topic_count, post_count, output_path)
            VALUES (?, datetime('now'), ?, ?, ?)
            """,
            (format, topic_count, post_count, output_path),
        )
        self.connection.commit()

    def get_export_history(self, limit: int = 10) -> list[dict]:
        """
        Get recent export history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of export history records as dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM export_history ORDER BY exported_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def set_category_filter(
        self, site_url: str, category_ids: list[int] | None
    ) -> None:
        """
        Set the category filter for a site.

        Args:
            site_url: Site URL
            category_ids: List of category IDs to archive, or None for all categories
        """
        import json

        cursor = self.connection.cursor()
        filter_json = json.dumps(category_ids) if category_ids else None

        # Try to update existing row
        cursor.execute(
            "UPDATE site_metadata SET category_filter = ? WHERE site_url = ?",
            (filter_json, site_url),
        )

        # If no row exists, insert one
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO site_metadata (site_url, category_filter) VALUES (?, ?)",
                (site_url, filter_json),
            )

        self.connection.commit()

    def get_category_filter(self, site_url: str) -> list[int] | None:
        """
        Get the category filter for a site.

        Args:
            site_url: Site URL

        Returns:
            List of category IDs, or None if archiving all categories
        """
        import json

        cursor = self.connection.cursor()

        # First check if column exists (for migration from older schema)
        cursor.execute("PRAGMA table_info(site_metadata)")
        columns = [row[1] for row in cursor.fetchall()]
        if "category_filter" not in columns:
            # Add column if it doesn't exist
            cursor.execute("ALTER TABLE site_metadata ADD COLUMN category_filter TEXT")
            self.connection.commit()
            return None

        cursor.execute(
            "SELECT category_filter FROM site_metadata WHERE site_url = ?",
            (site_url,),
        )
        row = cursor.fetchone()

        if row and row["category_filter"]:
            return json.loads(row["category_filter"])
        return None

    # Helper methods
    def _row_to_post(self, row) -> Post:
        """Convert database row to Post object."""
        return Post(
            id=row["id"],
            topic_id=row["topic_id"],
            user_id=row["user_id"],
            post_number=row["post_number"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            cooked=row["cooked"],
            raw=row["raw"],
            username=row["username"],
        )

    def _row_to_topic(self, row) -> Topic:
        """Convert database row to Topic object."""
        updated_at = row["updated_at"]
        last_posted_at = row["last_posted_at"]
        tags_json = row["tags"]
        thumbnails_json = row["thumbnails"]

        return Topic(
            # Core fields
            id=row["id"],
            title=row["title"],
            slug=row["slug"],
            category_id=row["category_id"],
            user_id=row["user_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
            posts_count=row["posts_count"],
            views=row["views"],
            # Content & Discovery - extract tag names if stored as dicts
            tags=[
                t["name"] if isinstance(t, dict) else t
                for t in (json.loads(tags_json) if tags_json else [])
            ],
            excerpt=row["excerpt"],
            image_url=row["image_url"],
            fancy_title=row["fancy_title"],
            # Engagement Metrics
            like_count=row["like_count"],
            reply_count=row["reply_count"],
            highest_post_number=row["highest_post_number"],
            participant_count=row["participant_count"],
            word_count=row["word_count"],
            # Status & Classification (int -> bool)
            pinned=bool(row["pinned"]),
            pinned_globally=bool(row["pinned_globally"]),
            closed=bool(row["closed"]),
            archived=bool(row["archived"]),
            # Context & Metadata
            featured_link=row["featured_link"],
            has_accepted_answer=bool(row["has_accepted_answer"]),
            has_summary=bool(row["has_summary"]),
            visible=bool(row["visible"]),
            last_posted_at=datetime.fromisoformat(last_posted_at)
            if last_posted_at
            else None,
            thumbnails=json.loads(thumbnails_json) if thumbnails_json else None,
            bookmarked=bool(row["bookmarked"]),
        )

    def _row_to_user(self, row) -> User:
        """Convert database row to User object."""
        created_at = row["created_at"]
        # Handle local_avatar_path which may not exist in older databases
        try:
            local_avatar_path = row["local_avatar_path"]
        except (KeyError, IndexError):
            local_avatar_path = None
        return User(
            id=row["id"],
            username=row["username"],
            name=row["name"],
            avatar_template=row["avatar_template"],
            trust_level=row["trust_level"],
            created_at=datetime.fromisoformat(created_at) if created_at else None,
            local_avatar_path=local_avatar_path,
        )

    def _row_to_category(self, row) -> Category:
        """Convert database row to Category object."""
        return Category(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            color=row["color"],
            text_color=row["text_color"],
            description=row["description"],
            parent_category_id=row["parent_category_id"],
            topic_count=row["topic_count"],
        )
