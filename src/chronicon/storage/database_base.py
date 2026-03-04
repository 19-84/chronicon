# ABOUTME: Abstract base class for database implementations
# ABOUTME: Defines the interface for SQLite and PostgreSQL implementations

"""Abstract database interface for archive storage."""

from abc import ABC, abstractmethod
from datetime import datetime

from ..models.category import Category
from ..models.post import Post
from ..models.topic import Topic
from ..models.user import User


class ArchiveDatabaseBase(ABC):
    """Abstract base class for archive database implementations."""

    @abstractmethod
    def __init__(self, connection_string: str):
        """
        Initialize database connection.

        Args:
            connection_string: Database connection string (path for SQLite,
                URL for PostgreSQL)
        """
        pass

    @abstractmethod
    def close(self):
        """Close database connection."""
        pass

    # Post operations
    @abstractmethod
    def insert_post(self, post: Post) -> None:
        """Insert or update a post in the database."""
        pass

    @abstractmethod
    def update_post(self, post: Post) -> None:
        """Update an existing post."""
        pass

    @abstractmethod
    def get_post(self, post_id: int) -> Post | None:
        """Retrieve a post by ID."""
        pass

    @abstractmethod
    def get_posts_since(self, date: datetime) -> list[Post]:
        """Get all posts created or updated since a specific date."""
        pass

    @abstractmethod
    def get_topic_posts(self, topic_id: int) -> list[Post]:
        """Get all posts for a specific topic."""
        pass

    @abstractmethod
    def post_exists(self, post_id: int) -> bool:
        """Check if a post exists in the database."""
        pass

    # Topic operations
    @abstractmethod
    def insert_topic(self, topic: Topic) -> None:
        """Insert or update a topic in the database."""
        pass

    @abstractmethod
    def get_topic(self, topic_id: int) -> Topic | None:
        """Retrieve a topic by ID."""
        pass

    @abstractmethod
    def get_topics_by_category(self, category_id: int) -> list[Topic]:
        """Get all topics in a specific category."""
        pass

    @abstractmethod
    def get_all_topics(self) -> list[Topic]:
        """Get all topics in the database."""
        pass

    @abstractmethod
    def get_topics_by_ids(self, topic_ids: list[int]) -> list[Topic]:
        """Get multiple topics by their IDs."""
        pass

    @abstractmethod
    def get_topics_by_tag(self, tag: str) -> list[Topic]:
        """Get all topics with a specific tag."""
        pass

    @abstractmethod
    def get_pinned_topics(self, globally_pinned_only: bool = False) -> list[Topic]:
        """Get all pinned topics."""
        pass

    @abstractmethod
    def get_closed_topics(self) -> list[Topic]:
        """Get all closed topics."""
        pass

    @abstractmethod
    def get_archived_topics(self) -> list[Topic]:
        """Get all archived topics."""
        pass

    @abstractmethod
    def get_all_topics_with_category(self) -> list[dict]:
        """Get all topics with category information included."""
        pass

    @abstractmethod
    def get_topics_by_category_with_info(self, category_id: int) -> list[dict]:
        """Get topics in a category with category information included."""
        pass

    # User operations
    @abstractmethod
    def insert_user(self, user: User) -> None:
        """Insert or update a user in the database."""
        pass

    @abstractmethod
    def get_user(self, user_id: int) -> User | None:
        """Retrieve a user by ID."""
        pass

    @abstractmethod
    def get_user_by_username(self, username: str) -> User | None:
        """Retrieve a user by username."""
        pass

    @abstractmethod
    def get_all_users(self) -> list[User]:
        """Get all users in the database."""
        pass

    @abstractmethod
    def get_unique_usernames(self) -> set[str]:
        """Get all unique usernames from posts in the database."""
        pass

    @abstractmethod
    def get_users_count(self) -> int:
        """Get the total number of users in the database."""
        pass

    @abstractmethod
    def get_users_with_post_counts(
        self,
        page: int,
        per_page: int,
        order_by: str = "post_count",
        order_dir: str = "DESC",
    ) -> list[dict]:
        """Get paginated list of users with their post counts."""
        pass

    @abstractmethod
    def get_user_posts(self, user_id: int, limit: int = 50) -> list[dict]:
        """Get posts by a specific user with topic information."""
        pass

    @abstractmethod
    def get_user_posts_paginated(
        self, user_id: int, page: int, per_page: int
    ) -> list[dict]:
        """Get a paginated list of posts by a specific user with topic information."""
        pass

    @abstractmethod
    def get_user_post_count(self, user_id: int) -> int:
        """Get the total number of posts by a user."""
        pass

    # Category operations
    @abstractmethod
    def insert_category(self, category: Category) -> None:
        """Insert or update a category in the database."""
        pass

    @abstractmethod
    def get_all_categories(self) -> list[Category]:
        """Get all categories in the database."""
        pass

    @abstractmethod
    def get_category(self, category_id: int) -> Category | None:
        """Get a single category by ID."""
        pass

    # Query operations for exporters
    @abstractmethod
    def get_recent_topics(self, limit: int = 20) -> list[Topic]:
        """Get recent topics for homepage."""
        pass

    @abstractmethod
    def get_topics_count(self) -> int:
        """Get the total number of topics in the database."""
        pass

    @abstractmethod
    def get_topics_paginated(
        self,
        page: int,
        per_page: int,
        order_by: str = "created_at",
        order_dir: str = "DESC",
    ) -> list[Topic]:
        """Get a paginated list of topics with flexible sorting."""
        pass

    @abstractmethod
    def get_category_topics_paginated(
        self, category_id: int, page: int, per_page: int
    ) -> list[Topic]:
        """Get a paginated list of topics for a specific category."""
        pass

    @abstractmethod
    def get_statistics(self) -> dict:
        """Get overall statistics for the archive."""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_activity_timeline(self) -> list[dict]:
        """
        Get monthly activity timeline for visualization.

        Returns:
            List of dictionaries with month, topic_count, and post_count
        """
        pass

    @abstractmethod
    def get_topic_posts_paginated(
        self, topic_id: int, page: int, per_page: int
    ) -> list[Post]:
        """Get a paginated list of posts for a specific topic."""
        pass

    @abstractmethod
    def get_topic_posts_count(self, topic_id: int) -> int:
        """Get the total number of posts in a topic."""
        pass

    # Full-text search operations
    @abstractmethod
    def search_topics(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> list[Topic]:
        """
        Full-text search across topics.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of matching Topic objects, ranked by relevance
        """
        pass

    @abstractmethod
    def search_posts(self, query: str, limit: int = 50, offset: int = 0) -> list[Post]:
        """
        Full-text search across posts.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of matching Post objects, ranked by relevance
        """
        pass

    @abstractmethod
    def search_topics_count(self, query: str) -> int:
        """
        Get the total number of topics matching a search query.

        Args:
            query: Search query string

        Returns:
            Total count of matching topics
        """
        pass

    @abstractmethod
    def search_posts_count(self, query: str) -> int:
        """
        Get the total number of posts matching a search query.

        Args:
            query: Search query string

        Returns:
            Total count of matching posts
        """
        pass

    @abstractmethod
    def rebuild_search_index(self) -> None:
        """
        Rebuild the full-text search index.

        This populates the search tables/columns with data from existing posts
        and topics. Should be called after migrating an existing database or
        if the search index becomes corrupted.
        """
        pass

    @abstractmethod
    def is_search_available(self) -> bool:
        """
        Check if full-text search is available and properly configured.

        Returns:
            True if search is available, False otherwise
        """
        pass

    # Asset operations
    @abstractmethod
    def register_asset(
        self, url: str, local_path: str, content_type: str | None = None
    ) -> None:
        """Register a downloaded asset."""
        pass

    @abstractmethod
    def get_asset_path(self, url: str) -> str | None:
        """Get local path for a previously downloaded asset."""
        pass

    @abstractmethod
    def find_asset_by_url_prefix(self, url_prefix: str) -> str | None:
        """
        Find asset path by URL prefix match (ignoring query params).

        Useful when the stored URL has a different query string than the
        one referenced in HTML (e.g., emoji ?v=15 vs ?v=9).

        Args:
            url_prefix: Base URL without query params

        Returns:
            Local path string if a matching asset is found, None otherwise
        """
        pass

    # Metadata operations
    @abstractmethod
    def update_site_metadata(self, site_url: str, **kwargs) -> None:
        """Update site metadata."""
        pass

    @abstractmethod
    def get_site_metadata(self, site_url: str) -> dict:
        """Get site metadata."""
        pass

    @abstractmethod
    def get_first_site_url(self) -> str | None:
        """
        Get the first site URL from the database.

        Used by watch daemon to discover which site to monitor when
        DATABASE_URL is set but site URL is not explicitly provided.

        Returns:
            Site URL string or None if no sites in database
        """
        pass

    # Export tracking operations
    @abstractmethod
    def record_export(
        self,
        format: str,
        topic_count: int,
        post_count: int,
        output_path: str,
    ) -> None:
        """Record an export operation in the export history."""
        pass

    @abstractmethod
    def get_export_history(self, limit: int = 10) -> list[dict]:
        """Get recent export history."""
        pass

    # Category filter operations
    @abstractmethod
    def set_category_filter(
        self, site_url: str, category_ids: list[int] | None
    ) -> None:
        """
        Set the category filter for a site.

        Args:
            site_url: Site URL
            category_ids: List of category IDs to archive, or None for all categories
        """
        pass

    @abstractmethod
    def get_category_filter(self, site_url: str) -> list[int] | None:
        """
        Get the category filter for a site.

        Args:
            site_url: Site URL

        Returns:
            List of category IDs, or None if archiving all categories
        """
        pass
