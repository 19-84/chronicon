# ABOUTME: PostgreSQL database implementation for Chronicon
# ABOUTME: Provides CRUD operations using psycopg3 and PostgreSQL

"""Archive database interface using PostgreSQL."""

import json
from datetime import datetime

import psycopg

from ..models.category import Category
from ..models.post import Post
from ..models.topic import Topic
from ..models.user import User
from .database_base import ArchiveDatabaseBase
from .schema_postgres import create_schema


class PostgresArchiveDatabase(ArchiveDatabaseBase):
    """PostgreSQL database interface for the archive."""

    def __init__(self, connection_string: str):
        """
        Initialize PostgreSQL database connection and create schema if needed.

        Args:
            connection_string: PostgreSQL connection string
                              e.g., "postgresql://user:password@localhost/dbname"
                              or "host=localhost dbname=discourse user=postgres"
        """
        self.connection_string = connection_string
        self.connection = psycopg.connect(connection_string)
        self.connection.autocommit = False  # Manual transaction control
        self._create_schema()

    def _create_schema(self):
        """Create database schema if it doesn't exist."""
        create_schema(self.connection)

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
            INSERT INTO posts
            (id, topic_id, user_id, post_number, created_at, updated_at,
             cooked, raw, username)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                topic_id = EXCLUDED.topic_id,
                user_id = EXCLUDED.user_id,
                post_number = EXCLUDED.post_number,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                cooked = EXCLUDED.cooked,
                raw = EXCLUDED.raw,
                username = EXCLUDED.username
            """,
            post.to_db_row(),
        )
        self.connection.commit()

    def update_post(self, post: Post) -> None:
        """Update an existing post."""
        self.insert_post(post)  # ON CONFLICT handles updates

    def get_post(self, post_id: int) -> Post | None:
        """Retrieve a post by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_post(row)
        return None

    def get_posts_since(self, date: datetime) -> list[Post]:
        """Get all posts created or updated since a specific date."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM posts WHERE updated_at >= %s ORDER BY updated_at",
            (date,),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_topic_posts(self, topic_id: int) -> list[Post]:
        """Get all posts for a specific topic."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM posts WHERE topic_id = %s ORDER BY post_number",
            (topic_id,),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def post_exists(self, post_id: int) -> bool:
        """Check if a post exists in the database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1 FROM posts WHERE id = %s", (post_id,))
        return cursor.fetchone() is not None

    # Topic operations
    def insert_topic(self, topic: Topic) -> None:
        """Insert a topic into the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO topics
            (id, title, slug, category_id, user_id, created_at, updated_at,
             posts_count, views, tags, excerpt, image_url, fancy_title,
             like_count, reply_count, highest_post_number, participant_count,
             word_count, pinned, pinned_globally, closed, archived,
             featured_link, has_accepted_answer, has_summary, visible,
             last_posted_at, thumbnails, bookmarked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                slug = EXCLUDED.slug,
                category_id = EXCLUDED.category_id,
                user_id = EXCLUDED.user_id,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                posts_count = EXCLUDED.posts_count,
                views = EXCLUDED.views,
                tags = EXCLUDED.tags,
                excerpt = EXCLUDED.excerpt,
                image_url = EXCLUDED.image_url,
                fancy_title = EXCLUDED.fancy_title,
                like_count = EXCLUDED.like_count,
                reply_count = EXCLUDED.reply_count,
                highest_post_number = EXCLUDED.highest_post_number,
                participant_count = EXCLUDED.participant_count,
                word_count = EXCLUDED.word_count,
                pinned = EXCLUDED.pinned,
                pinned_globally = EXCLUDED.pinned_globally,
                closed = EXCLUDED.closed,
                archived = EXCLUDED.archived,
                featured_link = EXCLUDED.featured_link,
                has_accepted_answer = EXCLUDED.has_accepted_answer,
                has_summary = EXCLUDED.has_summary,
                visible = EXCLUDED.visible,
                last_posted_at = EXCLUDED.last_posted_at,
                thumbnails = EXCLUDED.thumbnails,
                bookmarked = EXCLUDED.bookmarked
            """,
            (
                # Core fields
                topic.id,
                topic.title,
                topic.slug,
                topic.category_id,
                topic.user_id,
                topic.created_at,
                topic.updated_at,
                topic.posts_count,
                topic.views,
                # Content & Discovery - Use JSONB directly for PostgreSQL
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
                # Status & Classification - PostgreSQL uses native BOOLEAN
                topic.pinned,
                topic.pinned_globally,
                topic.closed,
                topic.archived,
                # Context & Metadata
                topic.featured_link,
                topic.has_accepted_answer,
                topic.has_summary,
                topic.visible,
                topic.last_posted_at,
                json.dumps(topic.thumbnails) if topic.thumbnails else None,
                topic.bookmarked,
            ),
        )
        self.connection.commit()

    def get_topic(self, topic_id: int) -> Topic | None:
        """Retrieve a topic by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = %s", (topic_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_topic(row)
        return None

    def get_topics_by_category(self, category_id: int) -> list[Topic]:
        """Get all topics in a specific category."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM topics WHERE category_id = %s ORDER BY created_at DESC",
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
        cursor.execute(
            "SELECT * FROM topics WHERE id = ANY(%s) ORDER BY created_at DESC",
            (topic_ids,),
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
        # Use JSONB containment operator for efficient tag search
        cursor.execute(
            """SELECT * FROM topics
               WHERE tags @> %s
               ORDER BY created_at DESC""",
            (json.dumps([tag]),),
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
                WHERE pinned_globally = TRUE
                ORDER BY created_at DESC
                """
            )
        else:
            cursor.execute(
                """
                SELECT * FROM topics
                WHERE pinned = TRUE OR pinned_globally = TRUE
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
        cursor.execute(
            "SELECT * FROM topics WHERE closed = TRUE ORDER BY created_at DESC"
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def get_archived_topics(self) -> list[Topic]:
        """
        Get all archived topics.

        Returns:
            List of archived Topic objects sorted by created_at descending
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM topics WHERE archived = TRUE ORDER BY created_at DESC"
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
            SELECT t.*, c.name as category_name,
                   c.slug as category_slug,
                   c.color as category_color
            FROM topics t
            LEFT JOIN categories c ON t.category_id = c.id
            ORDER BY t.created_at DESC
            """
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(colnames, row, strict=True)))
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
            SELECT t.*, c.name as category_name,
                   c.slug as category_slug,
                   c.color as category_color
            FROM topics t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.category_id = %s
            ORDER BY t.created_at DESC
            """,
            (category_id,),
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(colnames, row, strict=True)))
        return results

    # User operations
    def insert_user(self, user: User) -> None:
        """Insert a user into the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO users
            (id, username, name, avatar_template, trust_level, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                username = EXCLUDED.username,
                name = EXCLUDED.name,
                avatar_template = EXCLUDED.avatar_template,
                trust_level = EXCLUDED.trust_level,
                created_at = EXCLUDED.created_at
            """,
            (
                user.id,
                user.username,
                user.name,
                user.avatar_template,
                user.trust_level,
                user.created_at,
            ),
        )
        self.connection.commit()

    def get_user(self, user_id: int) -> User | None:
        """Retrieve a user by ID."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_user(row)
        return None

    def get_user_by_username(self, username: str) -> User | None:
        """Retrieve a user by username."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
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
            INSERT INTO categories
            (id, name, slug, color, text_color, description,
             parent_category_id, topic_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                color = EXCLUDED.color,
                text_color = EXCLUDED.text_color,
                description = EXCLUDED.description,
                parent_category_id = EXCLUDED.parent_category_id,
                topic_count = EXCLUDED.topic_count
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
        cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
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
            "SELECT * FROM topics ORDER BY created_at DESC LIMIT %s", (limit,)
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
        return row[0] if row else 0

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

        query = (
            f"SELECT * FROM topics ORDER BY {order_by} {order_dir} LIMIT %s OFFSET %s"
        )
        cursor.execute(query, (per_page, offset))  # type: ignore[arg-type]
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
            WHERE category_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
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
        """Get the total number of users in the database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]  # type: ignore[index]

    def get_users_with_post_counts(
        self,
        page: int,
        per_page: int,
        order_by: str = "post_count",
        order_dir: str = "DESC",
    ) -> list[dict]:
        """Get paginated list of users with their post counts."""
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page
        valid_columns = ["post_count", "username"]
        if order_by not in valid_columns:
            order_by = "post_count"
        if order_dir.upper() not in ["ASC", "DESC"]:
            order_dir = "DESC"

        query = f"""
            SELECT u.*, COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.username = p.username
            GROUP BY u.id, u.username, u.name,
                     u.avatar_template, u.trust_level,
                     u.created_at
            ORDER BY {order_by} {order_dir}
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (per_page, offset))  # type: ignore[arg-type]
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(colnames, row, strict=True))
            user = self._row_to_user(row)
            results.append({"user": user, "post_count": row_dict["post_count"]})
        return results

    def get_user_posts(self, user_id: int, limit: int = 50) -> list[dict]:
        """Get posts by a specific user with topic information."""
        user = self.get_user(user_id)
        if not user:
            return []
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT p.*, t.title as topic_title,
                   t.slug as topic_slug,
                   t.id as topic_id,
                   c.name as category_name,
                   c.slug as category_slug,
                   c.color as category_color
            FROM posts p
            JOIN topics t ON p.topic_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE p.username = %s
            ORDER BY p.created_at DESC
            LIMIT %s
            """,
            (user.username, limit),
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(colnames, row, strict=True))
            results.append(
                {
                    "post": self._row_to_post(row),
                    "topic_title": row_dict["topic_title"],
                    "topic_slug": row_dict["topic_slug"],
                    "topic_id": row_dict["topic_id"],
                    "category_name": row_dict["category_name"],
                    "category_slug": row_dict["category_slug"],
                    "category_color": row_dict["category_color"],
                }
            )
        return results

    def get_user_posts_paginated(
        self, user_id: int, page: int, per_page: int
    ) -> list[dict]:
        """Get a paginated list of posts by a specific user with topic information."""
        user = self.get_user(user_id)
        if not user:
            return []
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT p.*, t.title as topic_title,
                   t.slug as topic_slug,
                   t.id as topic_id,
                   c.name as category_name,
                   c.slug as category_slug,
                   c.color as category_color
            FROM posts p
            JOIN topics t ON p.topic_id = t.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE p.username = %s
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user.username, per_page, offset),
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(colnames, row, strict=True))
            results.append(
                {
                    "post": self._row_to_post(row),
                    "topic_title": row_dict["topic_title"],
                    "topic_slug": row_dict["topic_slug"],
                    "topic_id": row_dict["topic_id"],
                    "category_name": row_dict["category_name"],
                    "category_slug": row_dict["category_slug"],
                    "category_color": row_dict["category_color"],
                }
            )
        return results

    def get_user_post_count(self, user_id: int) -> int:
        """Get the total number of posts by a user."""
        user = self.get_user(user_id)
        if not user:
            return 0
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM posts WHERE username = %s", (user.username,)
        )
        return cursor.fetchone()[0]  # type: ignore[index]

    def get_statistics(self) -> dict:
        """
        Get overall statistics for the archive.

        Returns:
            Dictionary with total_topics, total_posts, total_users,
            total_categories, total_views counts
        """
        cursor = self.connection.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM topics")
        total_topics = cursor.fetchone()[0]  # type: ignore[index]

        cursor.execute("SELECT COUNT(*) as count FROM posts")
        total_posts = cursor.fetchone()[0]  # type: ignore[index]

        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()[0]  # type: ignore[index]

        cursor.execute("SELECT COUNT(*) as count FROM categories")
        total_categories = cursor.fetchone()[0]  # type: ignore[index]

        cursor.execute("SELECT COALESCE(SUM(views), 0) as count FROM topics")
        total_views = cursor.fetchone()[0]  # type: ignore[index]

        return {
            "total_topics": total_topics,
            "total_posts": total_posts,
            "total_users": total_users,
            "total_categories": total_categories,
            "total_views": total_views,
        }

    def get_archive_statistics(self) -> dict:
        """Get extended statistics for About page."""
        cursor = self.connection.cursor()
        stats = self.get_statistics()

        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM topics")
        row = cursor.fetchone()
        if row and row[0]:
            # Convert datetime objects to ISO format strings for compatibility
            stats["earliest_topic"] = row[0].isoformat() if row[0] else None
            stats["latest_topic"] = row[1].isoformat() if row[1] else None
        else:
            stats["earliest_topic"] = None
            stats["latest_topic"] = None

        cursor.execute("""
            SELECT username, COUNT(*) as post_count
            FROM posts
            WHERE username IS NOT NULL
            GROUP BY username
            ORDER BY post_count DESC LIMIT 10
        """)
        stats["top_contributors"] = [
            {"username": row[0], "post_count": row[1]} for row in cursor.fetchall()
        ]

        cursor.execute(
            "SELECT id, name, slug, color, topic_count"
            " FROM categories"
            " ORDER BY topic_count DESC LIMIT 5"
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        stats["popular_categories"] = [
            dict(zip(colnames, row, strict=True)) for row in cursor.fetchall()
        ]

        cursor.execute(
            "SELECT format, exported_at, topic_count, post_count"
            " FROM export_history"
            " WHERE format = 'html'"
            " ORDER BY exported_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
            export_data = dict(zip(colnames, row, strict=True))
            # Convert datetime to ISO format string for compatibility
            if export_data.get("exported_at"):
                export_data["exported_at"] = export_data["exported_at"].isoformat()
            stats["last_export"] = export_data
        else:
            stats["last_export"] = None
        return stats

    def get_activity_timeline(self) -> list[dict]:
        """Get monthly activity timeline for visualization."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT TO_CHAR(created_at, 'YYYY-MM') as month,
                   COUNT(*) as topic_count,
                   SUM(posts_count) as post_count
            FROM topics
            GROUP BY month
            ORDER BY month
        """)
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        return [dict(zip(colnames, row, strict=True)) for row in cursor.fetchall()]

    def get_topic_posts_paginated(
        self, topic_id: int, page: int, per_page: int
    ) -> list[Post]:
        """Get a paginated list of posts for a specific topic."""
        cursor = self.connection.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            "SELECT * FROM posts WHERE topic_id = %s"
            " ORDER BY post_number LIMIT %s OFFSET %s",
            (topic_id, per_page, offset),
        )
        return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_topic_posts_count(self, topic_id: int) -> int:
        """Get the total number of posts in a topic."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts WHERE topic_id = %s", (topic_id,))
        return cursor.fetchone()[0]  # type: ignore[index]

    # Full-text search operations (PostgreSQL tsvector/tsquery)
    def search_topics(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> list[Topic]:
        """
        Full-text search across topics using PostgreSQL tsvector.

        Args:
            query: Search query string (plain text, will be converted to tsquery)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching Topic objects, ranked by relevance (ts_rank)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM topics
            WHERE search_vector @@ plainto_tsquery('english', %s)
            ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC
            LIMIT %s OFFSET %s
            """,
            (query, query, limit, offset),
        )
        return [self._row_to_topic(row) for row in cursor.fetchall()]

    def search_posts(self, query: str, limit: int = 50, offset: int = 0) -> list[Post]:
        """
        Full-text search across posts using PostgreSQL tsvector.

        Args:
            query: Search query string (plain text, will be converted to tsquery)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching Post objects, ranked by relevance (ts_rank)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM posts
            WHERE search_vector @@ plainto_tsquery('english', %s)
            ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC
            LIMIT %s OFFSET %s
            """,
            (query, query, limit, offset),
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
            SELECT COUNT(*) FROM topics
            WHERE search_vector @@ plainto_tsquery('english', %s)
            """,
            (query,),
        )
        return cursor.fetchone()[0]  # type: ignore[index]

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
            SELECT COUNT(*) FROM posts
            WHERE search_vector @@ plainto_tsquery('english', %s)
            """,
            (query,),
        )
        return cursor.fetchone()[0]  # type: ignore[index]

    def rebuild_search_index(self) -> None:
        """
        Rebuild the full-text search index.

        This repopulates the search_vector columns for all topics and posts.
        Should be called after migrating an existing database or if the search
        index needs to be refreshed.
        """
        cursor = self.connection.cursor()

        # Rebuild topics search_vector
        cursor.execute("""
            UPDATE topics
            SET search_vector =
                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(excerpt, '')), 'B')
        """)

        # Rebuild posts search_vector
        cursor.execute("""
            UPDATE posts
            SET search_vector =
                setweight(to_tsvector('english', COALESCE(raw, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(username, '')), 'B')
        """)

        self.connection.commit()

    def is_search_available(self) -> bool:
        """
        Check if full-text search is available and properly configured.

        Returns:
            True if search_vector columns exist and are indexed, False otherwise
        """
        cursor = self.connection.cursor()
        try:
            # Check if search_vector column exists in topics table
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'topics' AND column_name = 'search_vector'
            """)
            if not cursor.fetchone():
                return False

            # Check if search_vector column exists in posts table
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'posts' AND column_name = 'search_vector'
            """)
            return bool(cursor.fetchone())
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
            INSERT INTO assets (url, local_path, content_type, downloaded_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (url) DO UPDATE SET
                local_path = EXCLUDED.local_path,
                content_type = EXCLUDED.content_type,
                downloaded_at = EXCLUDED.downloaded_at
            """,
            (url, local_path, content_type),
        )
        self.connection.commit()

    def get_asset_path(self, url: str) -> str | None:
        """Get local path for a previously downloaded asset."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT local_path FROM assets WHERE url = %s", (url,))
        row = cursor.fetchone()
        return row[0] if row else None

    def find_asset_by_url_prefix(self, url_prefix: str) -> str | None:
        """Find asset path by URL prefix match (ignoring query params)."""
        # Escape LIKE wildcards to prevent false matches
        escaped = (
            url_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT local_path FROM assets WHERE url LIKE %s ESCAPE '\\' LIMIT 1",
            (escaped + "%",),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_asset(self, url: str) -> dict | None:
        """Get a single asset by URL."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM assets WHERE url = %s", (url,))
        row = cursor.fetchone()
        if row:
            colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
            return dict(zip(colnames, row, strict=True))
        return None

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
            "SELECT * FROM assets WHERE local_path LIKE %s ORDER BY url",
            (f"%/images/{topic_id}/%",),
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        return [dict(zip(colnames, row, strict=True)) for row in cursor.fetchall()]

    def get_all_assets(self) -> list[dict]:
        """
        Get all registered assets.

        Returns:
            List of all asset dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM assets ORDER BY url")
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        return [dict(zip(colnames, row, strict=True)) for row in cursor.fetchall()]

    # Metadata operations
    def update_site_metadata(self, site_url: str, **kwargs) -> None:
        """Update site metadata."""
        cursor = self.connection.cursor()
        # Check if record exists
        cursor.execute("SELECT 1 FROM site_metadata WHERE site_url = %s", (site_url,))
        exists = cursor.fetchone() is not None

        if exists:
            # Build UPDATE statement dynamically
            fields = ", ".join([f"{k} = %s" for k in kwargs])
            values = list(kwargs.values()) + [site_url]
            cursor.execute(
                f"UPDATE site_metadata SET {fields} WHERE site_url = %s",  # type: ignore[arg-type]
                values,
            )
        else:
            # INSERT with provided kwargs
            kwargs["site_url"] = site_url
            fields = ", ".join(kwargs.keys())
            placeholders = ", ".join(["%s" for _ in kwargs])
            cursor.execute(
                f"INSERT INTO site_metadata ({fields}) VALUES ({placeholders})",  # type: ignore[arg-type]
                list(kwargs.values()),
            )
        self.connection.commit()

    def get_site_metadata(self, site_url: str) -> dict:
        """Get site metadata."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM site_metadata WHERE site_url = %s", (site_url,))
        row = cursor.fetchone()
        if row:
            # Get column names
            colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
            return dict(zip(colnames, row, strict=True))
        return {}

    def get_first_site_url(self) -> str | None:
        """
        Get the first site URL from the database.

        Used by watch daemon to discover which site to monitor when
        DATABASE_URL is set but site URL is not explicitly provided.

        Returns:
            Site URL string or None if no sites in database
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT site_url FROM site_metadata LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

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
                INSERT INTO top_tags (tag, topic_count)
                VALUES (%s, COALESCE(
                    (SELECT topic_count FROM top_tags WHERE tag = %s), 0))
                ON CONFLICT (tag) DO UPDATE SET topic_count = EXCLUDED.topic_count
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
                LIMIT %s
                """,
                (limit,),
            )
        else:
            cursor.execute(
                "SELECT tag, topic_count FROM top_tags ORDER BY topic_count DESC, tag"
            )
        return [{"tag": row[0], "topic_count": row[1]} for row in cursor.fetchall()]

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
            VALUES (%s, NOW(), %s, %s, %s)
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
            "SELECT * FROM export_history ORDER BY exported_at DESC LIMIT %s",
            (limit,),
        )
        colnames = [desc[0] for desc in cursor.description]  # type: ignore[union-attr]
        return [dict(zip(colnames, row, strict=True)) for row in cursor.fetchall()]

    # Category filter operations
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
        # PostgreSQL uses JSONB, so we pass the list directly or None
        filter_json = json.dumps(category_ids) if category_ids else None

        # Use upsert with ON CONFLICT
        cursor.execute(
            """
            INSERT INTO site_metadata (site_url, category_filter)
            VALUES (%s, %s)
            ON CONFLICT (site_url) DO UPDATE
                SET category_filter = EXCLUDED.category_filter
            """,
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
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT category_filter FROM site_metadata WHERE site_url = %s",
            (site_url,),
        )
        row = cursor.fetchone()

        if row and row[0]:
            # PostgreSQL JSONB is returned as a Python object directly
            # but we stored it as JSON string for consistency with SQLite
            if isinstance(row[0], str):
                import json

                return json.loads(row[0])
            return row[0]
        return None

    # Helper methods
    def _row_to_post(self, row) -> Post:
        """Convert database row to Post object."""
        return Post(
            id=row[0],
            topic_id=row[1],
            user_id=row[2],
            post_number=row[3],
            created_at=row[4],
            updated_at=row[5],
            cooked=row[6],
            raw=row[7],
            username=row[8],
        )

    def _row_to_topic(self, row) -> Topic:
        """Convert database row to Topic object."""
        # PostgreSQL returns actual types (JSONB, BOOLEAN, TIMESTAMP)
        return Topic(
            # Core fields
            id=row[0],
            title=row[1],
            slug=row[2],
            category_id=row[3],
            user_id=row[4],
            created_at=row[5],
            updated_at=row[6],
            posts_count=row[7],
            views=row[8],
            # Content & Discovery - PostgreSQL JSONB comes as dict/list
            # Extract tag names if stored as dicts
            tags=[t["name"] if isinstance(t, dict) else t for t in (row[9] or [])],
            excerpt=row[10],
            image_url=row[11],
            fancy_title=row[12],
            # Engagement Metrics
            like_count=row[13],
            reply_count=row[14],
            highest_post_number=row[15],
            participant_count=row[16],
            word_count=row[17],
            # Status & Classification - PostgreSQL BOOLEAN comes as bool
            pinned=row[18],
            pinned_globally=row[19],
            closed=row[20],
            archived=row[21],
            # Context & Metadata
            featured_link=row[22],
            has_accepted_answer=row[23],
            has_summary=row[24],
            visible=row[25],
            last_posted_at=row[26],
            thumbnails=row[27],
            bookmarked=row[28],
        )

    def _row_to_user(self, row) -> User:
        """Convert database row to User object."""
        return User(
            id=row[0],
            username=row[1],
            name=row[2],
            avatar_template=row[3],
            trust_level=row[4],
            created_at=row[5],
        )

    def _row_to_category(self, row) -> Category:
        """Convert database row to Category object."""
        return Category(
            id=row[0],
            name=row[1],
            slug=row[2],
            color=row[3],
            text_color=row[4],
            description=row[5],
            parent_category_id=row[6],
            topic_count=row[7],
        )
