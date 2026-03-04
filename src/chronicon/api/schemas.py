# ABOUTME: Pydantic schemas for API request/response models
# ABOUTME: Supports field selection and body truncation for token optimization

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FieldSelectionMixin:
    """
    Mixin to support field selection in API responses.

    Allows clients to request specific fields using ?fields=id,title,author
    to reduce response size and token usage (useful for LLM clients).
    """

    def model_dump_selected(self, fields: list[str] | None = None, **kwargs) -> dict:
        """
        Dump model with optional field selection.

        Args:
            fields: List of field names to include, or None for all fields
            **kwargs: Additional arguments to pass to model_dump()

        Returns:
            Dictionary with selected fields only
        """
        data = self.model_dump(**kwargs)  # type: ignore[attr-defined]
        if fields:
            return {k: v for k, v in data.items() if k in fields}
        return data


# Topic schemas
class TopicBase(BaseModel, FieldSelectionMixin):
    """Base topic response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    posts_count: int
    views: int
    created_at: datetime
    last_posted_at: datetime | None = None
    closed: bool
    archived: bool
    pinned: bool
    visible: bool


class TopicDetail(TopicBase):
    """Detailed topic response with category and user info."""

    category_id: int | None = None
    user_id: int | None = None
    excerpt: str | None = None
    fancy_title: str | None = None


class TopicWithCategory(TopicDetail):
    """Topic with embedded category information."""

    category_name: str | None = None
    category_slug: str | None = None
    category_color: str | None = None


# Post schemas
class PostBase(BaseModel, FieldSelectionMixin):
    """Base post response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    post_number: int
    username: str
    created_at: datetime
    updated_at: datetime | None = None
    reply_count: int | None = None
    quote_count: int | None = None
    score: float | None = None
    reads: int | None = None


class PostDetail(PostBase):
    """Detailed post response with content."""

    raw: str | None = None
    cooked: str | None = None
    user_id: int | None = None


class PostWithContext(PostDetail):
    """Post with topic and category context."""

    topic_title: str
    topic_slug: str
    category_name: str | None = None
    category_slug: str | None = None
    category_color: str | None = None


# User schemas
class UserBase(BaseModel, FieldSelectionMixin):
    """Base user response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str | None = None
    trust_level: int
    created_at: datetime | None = None


class UserDetail(UserBase):
    """Detailed user response."""

    avatar_template: str | None = None


class UserWithStats(UserDetail):
    """User with post count statistics."""

    post_count: int = 0


# Category schemas
class CategoryBase(BaseModel, FieldSelectionMixin):
    """Base category response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    color: str
    text_color: str
    topic_count: int


class CategoryDetail(CategoryBase):
    """Detailed category response."""

    description: str | None = None
    parent_category_id: int | None = None


# Search schemas
class SearchTopicResult(TopicWithCategory):
    """Topic search result with relevance score."""

    relevance: float | None = None


class SearchPostResult(PostWithContext):
    """Post search result with relevance score."""

    relevance: float | None = None


# Statistics schemas
class ArchiveStatistics(BaseModel):
    """Archive-wide statistics."""

    total_topics: int
    total_posts: int
    total_users: int
    total_categories: int
    total_views: int
    earliest_topic: datetime | None = None
    latest_topic: datetime | None = None
    top_contributors: list[dict[str, Any]] = Field(default_factory=list)
    popular_categories: list[dict[str, Any]] = Field(default_factory=list)
    last_export: dict[str, Any] | None = None


class ActivityTimelineItem(BaseModel):
    """Single month of activity timeline."""

    month: str
    topic_count: int
    post_count: int


# Pagination schemas
class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedTopics(BaseModel):
    """Paginated list of topics."""

    topics: list[TopicWithCategory]
    pagination: PaginationMeta


class PaginatedPosts(BaseModel):
    """Paginated list of posts."""

    posts: list[PostWithContext]
    pagination: PaginationMeta


class PaginatedUsers(BaseModel):
    """Paginated list of users."""

    users: list[UserWithStats]
    pagination: PaginationMeta


# Search response schemas
class SearchTopicsResponse(BaseModel):
    """Search topics response."""

    query: str
    results: list[SearchTopicResult]
    total: int
    page: int
    per_page: int


class SearchPostsResponse(BaseModel):
    """Search posts response."""

    query: str
    results: list[SearchPostResult]
    total: int
    page: int
    per_page: int
