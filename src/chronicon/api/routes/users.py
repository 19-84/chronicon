# ABOUTME: REST API endpoints for users
# ABOUTME: User listing, detail, and posts endpoints with pagination

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from chronicon.api.app import get_db, limiter
from chronicon.api.schemas import (
    PaginatedPosts,
    PaginatedUsers,
    PaginationMeta,
    PostWithContext,
    UserWithStats,
)
from chronicon.storage.database_base import ArchiveDatabaseBase as ArchiveDatabase

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedUsers)
@limiter.limit("100/minute")
async def list_users(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    List users with post counts, sorted by post count descending.

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - fields: Select specific fields (e.g., "id,username,post_count")
    """
    # Get users with post counts (paginated at DB level)
    users_with_counts = db.get_users_with_post_counts(
        page=page, per_page=per_page, order_by="post_count", order_dir="DESC"
    )

    # Get total count for pagination
    total = db.get_users_count()
    total_pages = (total + per_page - 1) // per_page

    # Flatten the nested structure and convert to schemas
    selected_fields = fields.split(",") if fields else None
    users_schemas = []
    for item in users_with_counts:
        user_dict = item["user"].to_dict()
        user_dict["post_count"] = item["post_count"]
        users_schemas.append(UserWithStats.model_validate(user_dict))

    # Apply field selection if requested
    if selected_fields:
        users_data = [u.model_dump_selected(selected_fields) for u in users_schemas]
    else:
        users_data = [u.model_dump() for u in users_schemas]

    return {
        "users": users_data,
        "pagination": PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    }


@router.get("/{user_id}", response_model=UserWithStats)
@limiter.limit("100/minute")
async def get_user(
    request: Request,  # Required by slowapi rate limiter
    user_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    Get detailed information about a specific user.

    Path parameters:
    - user_id: User ID

    Query parameters:
    - fields: Select specific fields (e.g., "id,username,post_count")
    """
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get post count
    post_count = db.get_user_post_count(user_id)

    # Build user with stats
    user_dict = user.to_dict()
    user_dict["post_count"] = post_count

    schema = UserWithStats.model_validate(user_dict)

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        return schema.model_dump_selected(selected_fields)

    return schema


@router.get("/{user_id}/posts", response_model=PaginatedPosts)
@limiter.limit("100/minute")
async def get_user_posts(
    request: Request,  # Required by slowapi rate limiter
    user_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
    max_body_length: int | None = Query(
        None, ge=1, description="Truncate post body to N characters"
    ),
):
    """
    Get posts by a specific user with pagination.

    Path parameters:
    - user_id: User ID

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - fields: Select specific fields
    - max_body_length: Truncate post bodies to N characters (for token optimization)
    """
    # Check if user exists
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get total count
    total = db.get_user_post_count(user_id)
    total_pages = (total + per_page - 1) // per_page

    # Get paginated posts with context
    posts_with_context = db.get_user_posts_paginated(user_id, page, per_page)

    # Apply body truncation if requested
    if max_body_length:
        for post_data in posts_with_context:
            post = post_data["post"]
            if len(post.raw) > max_body_length:
                post.raw = post.raw[:max_body_length] + "..."
            if post.cooked and len(post.cooked) > max_body_length:
                post.cooked = post.cooked[:max_body_length] + "..."

    # Convert to schemas
    posts_schemas = []
    for post_data in posts_with_context:
        post = post_data["post"]
        post_dict = post.to_dict()
        post_dict["topic_title"] = post_data["topic_title"]
        post_dict["topic_slug"] = post_data["topic_slug"]
        post_dict["topic_id"] = post_data["topic_id"]
        post_dict["category_name"] = post_data["category_name"]
        post_dict["category_slug"] = post_data["category_slug"]
        post_dict["category_color"] = post_data["category_color"]
        posts_schemas.append(PostWithContext.model_validate(post_dict))

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        posts_data = [p.model_dump_selected(selected_fields) for p in posts_schemas]
    else:
        posts_data = [p.model_dump() for p in posts_schemas]

    return {
        "posts": posts_data,
        "pagination": PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    }
