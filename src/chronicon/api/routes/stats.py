# ABOUTME: REST API endpoints for statistics and analytics
# ABOUTME: Archive statistics and activity timeline endpoints

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from chronicon.api.app import get_db, limiter
from chronicon.api.schemas import ActivityTimelineItem, ArchiveStatistics
from chronicon.storage.database_base import ArchiveDatabaseBase as ArchiveDatabase

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/archive", response_model=ArchiveStatistics)
@limiter.limit("100/minute")
async def get_archive_statistics(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
):
    """
    Get comprehensive archive statistics.

    Returns:
    - Basic counts (topics, posts, users, categories, views)
    - Date range (earliest and latest topic dates)
    - Top 10 contributors (users with most posts)
    - Top 5 popular categories (by topic count)
    - Last export information
    """
    stats = db.get_archive_statistics()
    return ArchiveStatistics.model_validate(stats)


@router.get("/timeline", response_model=list[ActivityTimelineItem])
@limiter.limit("100/minute")
async def get_activity_timeline(
    request: Request,  # Required by slowapi rate limiter
    db: Annotated[ArchiveDatabase, Depends(get_db)],
):
    """
    Get monthly activity timeline for visualization.

    Returns:
    - List of monthly data points with topic_count and post_count
    - Sorted chronologically by month (YYYY-MM format)
    - Useful for generating activity charts and graphs
    """
    timeline = db.get_activity_timeline()
    return [ActivityTimelineItem.model_validate(item) for item in timeline]
