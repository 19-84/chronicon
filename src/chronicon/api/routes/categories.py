# ABOUTME: REST API endpoints for categories
# ABOUTME: Category listing, detail, and topics endpoints

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from chronicon.api.app import get_db, limiter
from chronicon.api.schemas import (
    CategoryDetail,
    PaginatedTopics,
    PaginationMeta,
    TopicWithCategory,
)
from chronicon.storage.database_base import ArchiveDatabaseBase as ArchiveDatabase

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
@limiter.limit("100/minute")
async def list_categories(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    List all categories.

    Query parameters:
    - fields: Select specific fields (e.g., "id,name,slug,topic_count")
    """
    categories = db.get_all_categories()

    # Convert to schemas
    selected_fields = fields.split(",") if fields else None
    categories_schemas = [CategoryDetail.model_validate(cat) for cat in categories]

    # Apply field selection if requested
    if selected_fields:
        return [c.model_dump_selected(selected_fields) for c in categories_schemas]

    return [c.model_dump() for c in categories_schemas]


@router.get("/{category_id}", response_model=CategoryDetail)
@limiter.limit("100/minute")
async def get_category(
    request: Request,  # Required by slowapi rate limiter
    category_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    Get detailed information about a specific category.

    Path parameters:
    - category_id: Category ID

    Query parameters:
    - fields: Select specific fields (e.g., "id,name,topic_count")
    """
    category = db.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    schema = CategoryDetail.model_validate(category)

    # Apply field selection if requested
    selected_fields = fields.split(",") if fields else None
    if selected_fields:
        return schema.model_dump_selected(selected_fields)

    return schema


@router.get("/{category_id}/topics", response_model=PaginatedTopics)
@limiter.limit("100/minute")
async def get_category_topics(
    request: Request,  # Required by slowapi rate limiter
    category_id: int,
    db: Annotated[ArchiveDatabase, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    fields: str | None = Query(None, description="Comma-separated list of fields"),
):
    """
    Get topics in a specific category with pagination.

    Path parameters:
    - category_id: Category ID

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - fields: Select specific fields
    """
    # Check if category exists
    category = db.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get all topics in category
    all_topics = db.get_topics_by_category_with_info(category_id)

    # Calculate pagination
    total = len(all_topics)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_topics[start:end]

    # Convert to schemas
    selected_fields = fields.split(",") if fields else None
    topics_schemas = [TopicWithCategory.model_validate(topic) for topic in paginated]

    # Apply field selection if requested
    if selected_fields:
        topics_data = [t.model_dump_selected(selected_fields) for t in topics_schemas]
    else:
        topics_data = [t.model_dump() for t in topics_schemas]

    return {
        "topics": topics_data,
        "pagination": PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    }
