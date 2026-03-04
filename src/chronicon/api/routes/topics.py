# ABOUTME: REST API endpoints for topics
# ABOUTME: List, detail, posts, and context endpoints with pagination

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from chronicon.api.app import get_db, limiter
from chronicon.api.schemas import (
    PaginatedPosts,
    PaginationMeta,
)
from chronicon.storage.database_base import ArchiveDatabaseBase as ArchiveDatabase

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("")
@limiter.limit("100/minute")
async def list_topics(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    List topics with pagination and optional category filtering.

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - category_id: Filter by category (optional)
    - fields: Select specific fields (e.g., "id,title,slug")
    """
    # Get topics based on filter
    if category_id:
        all_topics = db.get_topics_by_category_with_info(category_id)
    else:
        all_topics = db.get_all_topics_with_category()

    # Calculate pagination
    total = len(all_topics)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_topics[start:end]

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        topics_data = [
            {k: v for k, v in topic.items() if k in selected_fields}
            for topic in paginated
        ]
    else:
        topics_data = paginated

    return {
        "topics": topics_data,
        "pagination": PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    }


@router.get("/{topic_id}")
@limiter.limit("100/minute")
async def get_topic(
    request: Request,  # Required by slowapi rate limiter
    topic_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    Get detailed information about a specific topic.

    Path parameters:
    - topic_id: Topic ID

    Query parameters:
    - fields: Select specific fields (e.g., "id,title,posts_count")
    """
    topic = db.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic_dict = topic.to_dict()

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        return {k: v for k, v in topic_dict.items() if k in selected_fields}

    return topic_dict


@router.get("/{topic_id}/posts", response_model=PaginatedPosts)
@limiter.limit("100/minute")
async def get_topic_posts(
    request: Request,  # Required by slowapi rate limiter
    topic_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
    max_body_length: int | None = Query(
        None, ge=1, description="Truncate post body to N characters"
    ),
):
    """
    Get posts for a specific topic with pagination.

    Path parameters:
    - topic_id: Topic ID

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - fields: Select specific fields
    - max_body_length: Truncate post bodies to N characters (for token optimization)
    """
    # Check if topic exists
    topic = db.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get total count
    total = db.get_topic_posts_count(topic_id)
    total_pages = (total + per_page - 1) // per_page

    # Get paginated posts
    posts = db.get_topic_posts_paginated(topic_id, page, per_page)

    # Convert to schemas with context
    posts_with_context = []
    for post in posts:
        # Get category info if available
        category = db.get_category(topic.category_id) if topic.category_id else None

        post_dict = post.to_dict()
        post_dict["topic_title"] = topic.title
        post_dict["topic_slug"] = topic.slug
        if category:
            post_dict["category_name"] = category.name
            post_dict["category_slug"] = category.slug
            post_dict["category_color"] = category.color

        # Apply body truncation if requested
        if max_body_length and len(post_dict.get("raw", "")) > max_body_length:
            post_dict["raw"] = post_dict["raw"][:max_body_length] + "..."
        if (
            max_body_length
            and post_dict.get("cooked")
            and len(post_dict["cooked"]) > max_body_length
        ):
            post_dict["cooked"] = post_dict["cooked"][:max_body_length] + "..."

        posts_with_context.append(post_dict)

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        posts_data = [
            {k: v for k, v in p.items() if k in selected_fields}
            for p in posts_with_context
        ]
    else:
        posts_data = posts_with_context

    return {
        "posts": posts_data,
        "pagination": PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    }


@router.get("/{topic_id}/posts/{post_number}/context")
@limiter.limit("100/minute")
async def get_post_context(
    request: Request,  # Required by slowapi rate limiter
    topic_id: int,
    post_number: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    before: int = Query(3, ge=0, le=10, description="Posts before target"),
    after: int = Query(3, ge=0, le=10, description="Posts after target"),
):
    """
    Get a post with surrounding context (posts before and after).

    Useful for LLM clients that need context around a specific post.

    Path parameters:
    - topic_id: Topic ID
    - post_number: Post number in topic

    Query parameters:
    - before: Number of posts before target (default: 3, max: 10)
    - after: Number of posts after target (default: 3, max: 10)
    """
    # Get target post
    posts = db.get_topic_posts(topic_id)
    target_post = next((p for p in posts if p.post_number == post_number), None)

    if not target_post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get context posts
    context_posts = [
        p for p in posts if post_number - before <= p.post_number <= post_number + after
    ]

    # Convert to schemas
    topic = db.get_topic(topic_id)
    category = (
        db.get_category(topic.category_id) if topic and topic.category_id else None
    )

    result = []
    for post in context_posts:
        post_dict = post.to_dict()
        post_dict["topic_title"] = topic.title if topic else None
        post_dict["topic_slug"] = topic.slug if topic else None
        if category:
            post_dict["category_name"] = category.name
            post_dict["category_slug"] = category.slug
            post_dict["category_color"] = category.color

        result.append(post_dict)

    return {
        "target_post_number": post_number,
        "context_before": before,
        "context_after": after,
        "posts": result,
    }
