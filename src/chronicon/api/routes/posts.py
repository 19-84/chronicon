# ABOUTME: REST API endpoints for posts
# ABOUTME: Post detail endpoint with field selection and body truncation

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from chronicon.api.app import get_db, limiter
from chronicon.api.schemas import PostWithContext
from chronicon.storage.database_base import ArchiveDatabaseBase as ArchiveDatabase

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/{post_id}", response_model=PostWithContext)
@limiter.limit("100/minute")
async def get_post(
    request: Request,  # Required by slowapi rate limiter
    post_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    fields: str | None = Query(None, description="Comma-separated list of fields"),
    max_body_length: int | None = Query(
        None, ge=1, description="Truncate post body to N characters"
    ),
):
    """
    Get detailed information about a specific post.

    Path parameters:
    - post_id: Post ID

    Query parameters:
    - fields: Select specific fields (e.g., "id,raw,username")
    - max_body_length: Truncate post bodies to N characters (for token optimization)
    """
    post = db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get topic and category context
    topic = db.get_topic(post.topic_id)
    category = (
        db.get_category(topic.category_id) if topic and topic.category_id else None
    )

    # Build post with context
    post_dict = post.to_dict()
    post_dict["topic_title"] = topic.title if topic else None
    post_dict["topic_slug"] = topic.slug if topic else None
    if category:
        post_dict["category_name"] = category.name
        post_dict["category_slug"] = category.slug
        post_dict["category_color"] = category.color

    # Apply body truncation if requested
    if max_body_length:
        if len(post_dict.get("raw", "")) > max_body_length:
            post_dict["raw"] = post_dict["raw"][:max_body_length] + "..."
        if post_dict.get("cooked") and len(post_dict["cooked"]) > max_body_length:
            post_dict["cooked"] = post_dict["cooked"][:max_body_length] + "..."

    schema = PostWithContext.model_validate(post_dict)

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        return schema.model_dump_selected(selected_fields)

    return schema
