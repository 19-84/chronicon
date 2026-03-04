# ABOUTME: REST API endpoints for full-text search
# ABOUTME: Search topics and posts with FTS5 (SQLite) or tsvector (PostgreSQL)

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from chronicon.api.app import get_db, limiter
from chronicon.storage.database_base import ArchiveDatabaseBase as ArchiveDatabase

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/topics")
@limiter.limit("100/minute")
async def search_topics(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    Search topics using full-text search.

    Query parameters:
    - q: Search query (required)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - fields: Select specific fields

    Search is powered by:
    - SQLite: FTS5 with BM25 ranking
    - PostgreSQL: tsvector with ts_rank
    """
    # Check if search is available
    if not db.is_search_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Full-text search is not available."
                " Run 'chronicon rebuild-search-index' to enable it."
            ),
        )

    # Get total count
    try:
        total = db.search_topics_count(q)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid search query: {str(e)}"
        ) from e

    # Calculate pagination
    offset = (page - 1) * per_page

    # Execute search
    try:
        results = db.search_topics(q, limit=per_page, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Search error: {str(e)}") from e

    # Convert to dicts with category context
    results_with_context = []
    for topic in results:
        topic_dict = topic.to_dict()
        # Add category info if available
        if topic.category_id:
            category = db.get_category(topic.category_id)
            if category:
                topic_dict["category_name"] = category.name
                topic_dict["category_slug"] = category.slug
                topic_dict["category_color"] = category.color
        results_with_context.append(topic_dict)

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        results_data = [
            {k: v for k, v in r.items() if k in selected_fields}
            for r in results_with_context
        ]
    else:
        results_data = results_with_context

    return {
        "query": q,
        "results": results_data,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/posts")
@limiter.limit("100/minute")
async def search_posts(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
    max_body_length: int | None = Query(
        None, ge=1, description="Truncate post body to N characters"
    ),
):
    """
    Search posts using full-text search.

    Query parameters:
    - q: Search query (required)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - fields: Select specific fields
    - max_body_length: Truncate post bodies to N characters (for token optimization)

    Search is powered by:
    - SQLite: FTS5 with BM25 ranking
    - PostgreSQL: tsvector with ts_rank
    """
    # Check if search is available
    if not db.is_search_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Full-text search is not available."
                " Run 'chronicon rebuild-search-index' to enable it."
            ),
        )

    # Get total count
    try:
        total = db.search_posts_count(q)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid search query: {str(e)}"
        ) from e

    # Calculate pagination
    offset = (page - 1) * per_page

    # Execute search
    try:
        results = db.search_posts(q, limit=per_page, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Search error: {str(e)}") from e

    # Convert to schemas with topic/category context
    results_with_context = []
    for post in results:
        post_dict = post.to_dict()

        # Get topic info
        topic = db.get_topic(post.topic_id)
        if topic:
            post_dict["topic_title"] = topic.title
            post_dict["topic_slug"] = topic.slug

            # Get category info if available
            if topic.category_id:
                category = db.get_category(topic.category_id)
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

        results_with_context.append(post_dict)

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        results_data = [
            {k: v for k, v in r.items() if k in selected_fields}
            for r in results_with_context
        ]
    else:
        results_data = results_with_context

    return {
        "query": q,
        "results": results_data,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
