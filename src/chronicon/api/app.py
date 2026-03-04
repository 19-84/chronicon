# ABOUTME: FastAPI application entry point for Chronicon REST API
# ABOUTME: Read-only access to archived Discourse forums with rate limiting

import os
import urllib.parse
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from chronicon.storage.database_base import ArchiveDatabaseBase
from chronicon.storage.factory import get_database
from chronicon.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Rate limiter (100 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Global database instance (initialized in lifespan)
_db_instance: ArchiveDatabaseBase | None = None


def get_db() -> ArchiveDatabaseBase:
    """
    FastAPI dependency to provide database instance.

    Returns:
        ArchiveDatabaseBase instance

    Raises:
        RuntimeError: If database not initialized (should never happen in production)
    """
    if _db_instance is None:
        raise RuntimeError("Database not initialized. This should not happen.")
    return _db_instance


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    FastAPI lifespan context manager.

    Handles:
    - Database initialization from DATABASE_URL environment variable
    - Automatic FTS index building if search is empty
    - Clean shutdown

    Yields:
        Control to FastAPI application
    """
    global _db_instance

    # Get database connection string from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Example: DATABASE_URL=sqlite:///archive.db or "
            "DATABASE_URL=postgresql://localhost/chronicon"
        )

    # Mask password in log output
    try:
        parsed = urllib.parse.urlparse(database_url)
        if parsed.password:
            masked_url = parsed._replace(
                netloc=f"{parsed.username}:***@{parsed.hostname}"
                + (f":{parsed.port}" if parsed.port else "")
            ).geturl()
        else:
            masked_url = database_url
    except Exception:
        masked_url = database_url
    logger.info(f"Connecting to database: {masked_url}")
    _db_instance = get_database(database_url)

    # Auto-build search index if available but empty
    if _db_instance.is_search_available():
        logger.info("Search is available")
    else:
        logger.warning("Full-text search is not available in this database")

    yield

    # Cleanup (close database connection if needed)
    logger.info("Shutting down API server")
    _db_instance = None


# Create FastAPI application
app = FastAPI(
    title="Chronicon API",
    description="Read-only REST API for archived Discourse forums",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Add CORS middleware (allow all origins for public archives)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Wildcard origin is incompatible with credentials
    allow_methods=["GET"],  # Only allow GET (read-only API)
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Chronicon API",
        "version": "1.0.0",
        "description": "Read-only REST API for archived Discourse forums",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health(db: ArchiveDatabaseBase = Depends(get_db)) -> dict:  # noqa: B008
    """
    Health check endpoint.

    Returns:
        Health status including database connectivity and search availability
    """
    stats = db.get_statistics()
    return {
        "status": "healthy",
        "database": "connected",
        "search_available": db.is_search_available(),
        "total_topics": stats["total_topics"],
        "total_posts": stats["total_posts"],
    }


# Import and register API routes (must be after app creation)
from chronicon.api.routes import (  # noqa: E402
    categories,
    posts,
    search,
    search_html,
    stats,
    topics,
    users,
)

app.include_router(topics.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(search_html.router)  # No prefix - serves at /search
