# ABOUTME: MCP (Model Context Protocol) server for Chronicon archives
# ABOUTME: Auto-generates tools from REST API spec and provides custom resources/prompts

import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from chronicon.storage.database_base import ArchiveDatabaseBase
from chronicon.storage.factory import get_database
from chronicon.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global database instance
_db_instance: ArchiveDatabaseBase | None = None


def get_db() -> ArchiveDatabaseBase:
    """Get database instance."""
    global _db_instance
    if _db_instance is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        _db_instance = get_database(database_url)
    return _db_instance


# Create MCP server
mcp_server = Server("chronicon-archive")


@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    """
    List available MCP resources.

    Resources provide read-only access to archive data:
    - archive://stats - Archive statistics
    - archive://categories - All categories
    - archive://timeline - Activity timeline
    """
    return [
        Resource(
            uri="archive://stats",
            name="Archive Statistics",
            description="Comprehensive statistics about the archived forum",
            mimeType="application/json",
        ),
        Resource(
            uri="archive://categories",
            name="Forum Categories",
            description="List of all categories in the archive",
            mimeType="application/json",
        ),
        Resource(
            uri="archive://timeline",
            name="Activity Timeline",
            description="Monthly activity timeline showing topics and posts over time",
            mimeType="application/json",
        ),
    ]


@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    """
    Read a resource by URI.

    Args:
        uri: Resource URI (e.g., "archive://stats")

    Returns:
        Resource content as JSON string
    """
    db = get_db()

    if uri == "archive://stats":
        stats = db.get_archive_statistics()
        return TextContent(
            type="text",
            text=f"Archive Statistics:\n\n{_format_stats(stats)}",
        )

    if uri == "archive://categories":
        categories = db.get_all_categories()
        return TextContent(
            type="text",
            text=(
                f"Categories ({len(categories)} total):"
                f"\n\n{_format_categories(categories)}"
            ),
        )

    if uri == "archive://timeline":
        timeline = db.get_activity_timeline()
        return TextContent(
            type="text",
            text=f"Activity Timeline:\n\n{_format_timeline(timeline)}",
        )

    raise ValueError(f"Unknown resource URI: {uri}")


@mcp_server.list_prompts()
async def list_prompts() -> list[dict[str, Any]]:
    """
    List available MCP prompts.

    Prompts provide guidance for LLM clients:
    - token-safety-guide - How to use field selection and body truncation
    - search-query-guide - How to construct effective search queries
    """
    return [
        {
            "name": "token-safety-guide",
            "description": (
                "Guide for using field selection and body"
                " truncation to minimize token usage"
            ),
        },
        {
            "name": "search-query-guide",
            "description": "Guide for constructing effective search queries",
        },
    ]


@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> str:
    """
    Get a prompt by name.

    Args:
        name: Prompt name
        arguments: Optional prompt arguments

    Returns:
        Prompt content
    """
    if name == "token-safety-guide":
        return """# Token Safety Guide for Chronicon API

When querying the Chronicon API, minimize token usage with these parameters:

## Field Selection
Use `?fields=field1,field2` to request only specific fields:
- Example: `?fields=id,title,posts_count`
- Works on: topics, posts, users, categories endpoints

## Body Truncation
Use `?max_body_length=N` to truncate post bodies:
- Example: `?max_body_length=500` (first 500 characters only)
- Works on: posts endpoints and topic posts endpoints
- Useful when you only need post metadata or summaries

## Combining Both
You can combine field selection and truncation:
- Example: `?fields=id,username,raw&max_body_length=200`

## Pagination
Always use pagination for large result sets:
- `?page=1&per_page=20` (default: 20 per page, max: 100)
- Check `pagination.total_pages` to know how many pages exist
"""

    if name == "search-query-guide":
        return """# Search Query Guide for Chronicon API

The search API uses different backends depending on the database:

## SQLite (FTS5)
Uses FTS5 syntax with these operators:
- `word1 word2` - Match both words (AND)
- `word1 OR word2` - Match either word
- `"exact phrase"` - Match exact phrase
- `word1 NOT word2` - Match word1 but not word2
- `word*` - Prefix search

## PostgreSQL (tsvector)
Uses `plainto_tsquery` which:
- Automatically handles word stemming (e.g., "running" matches "run")
- Treats all words as AND (space-separated)
- Use plain text queries (no special operators needed)

## Best Practices
1. Start with simple single-word queries
2. Use specific terms rather than common words
3. For topics: searches title and excerpt
4. For posts: searches content and username
5. Results are ranked by relevance (BM25 for SQLite, ts_rank for PostgreSQL)

## Examples
- Topics about Python: `GET /api/v1/search/topics?q=python`
- Posts mentioning "docker": `GET /api/v1/search/posts?q=docker`
- Exact phrase: `GET /api/v1/search/posts?q="error message"`
"""

    raise ValueError(f"Unknown prompt: {name}")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available MCP tools.

    Tools are auto-generated from the REST API endpoints:
    - get_topics - List topics with pagination
    - get_topic - Get topic details
    - get_topic_posts - Get posts in a topic
    - get_post - Get post details
    - search_topics - Search topics
    - search_posts - Search posts
    - get_users - List users
    - get_user - Get user details
    - get_categories - List categories
    - get_category - Get category details
    - get_statistics - Get archive statistics
    """
    return [
        Tool(
            name="get_topics",
            description="List topics with optional category filtering and pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "default": 1},
                    "per_page": {"type": "integer", "default": 20},
                    "category_id": {"type": "integer"},
                    "fields": {"type": "string"},
                },
            },
        ),
        Tool(
            name="get_topic",
            description="Get detailed information about a specific topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_id": {"type": "integer"},
                    "fields": {"type": "string"},
                },
                "required": ["topic_id"],
            },
        ),
        Tool(
            name="get_topic_posts",
            description="Get posts in a topic with pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_id": {"type": "integer"},
                    "page": {"type": "integer", "default": 1},
                    "per_page": {"type": "integer", "default": 20},
                    "fields": {"type": "string"},
                    "max_body_length": {"type": "integer"},
                },
                "required": ["topic_id"],
            },
        ),
        Tool(
            name="search_topics",
            description="Search topics using full-text search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "page": {"type": "integer", "default": 1},
                    "per_page": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_posts",
            description="Search posts using full-text search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "page": {"type": "integer", "default": 1},
                    "per_page": {"type": "integer", "default": 20},
                    "max_body_length": {"type": "integer"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_users",
            description="List users with post counts",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "default": 1},
                    "per_page": {"type": "integer", "default": 20},
                },
            },
        ),
        Tool(
            name="get_categories",
            description="List all categories",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_statistics",
            description="Get comprehensive archive statistics",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Call a tool by name.

    This delegates to the appropriate database methods.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as list of TextContent objects
    """
    db = get_db()

    if name == "get_topics":
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 20)
        category_id = arguments.get("category_id")

        if category_id:
            topics = db.get_topics_by_category_with_info(category_id)
        else:
            topics = db.get_all_topics_with_category()

        # Paginate
        total = len(topics)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = topics[start:end]

        return [
            TextContent(
                type="text", text=_format_topics(paginated, page, per_page, total)
            )
        ]

    if name == "get_topic":
        topic_id = arguments["topic_id"]
        topic = db.get_topic(topic_id)
        if not topic:
            return [TextContent(type="text", text=f"Topic {topic_id} not found")]
        return [TextContent(type="text", text=_format_topic_detail(topic))]

    if name == "get_topic_posts":
        topic_id = arguments["topic_id"]
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 20)

        posts = db.get_topic_posts_paginated(topic_id, page, per_page)
        total = db.get_topic_posts_count(topic_id)

        return [
            TextContent(type="text", text=_format_posts(posts, page, per_page, total))
        ]

    if name == "search_topics":
        query = arguments["query"]
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 20)

        if not db.is_search_available():
            return [
                TextContent(type="text", text="Search is not available in this archive")
            ]

        offset = (page - 1) * per_page
        results = db.search_topics(query, limit=per_page, offset=offset)
        total = db.search_topics_count(query)

        return [
            TextContent(
                type="text",
                text=_format_search_topics(query, results, page, per_page, total),
            )
        ]

    if name == "search_posts":
        query = arguments["query"]
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 20)

        if not db.is_search_available():
            return [
                TextContent(type="text", text="Search is not available in this archive")
            ]

        offset = (page - 1) * per_page
        results = db.search_posts(query, limit=per_page, offset=offset)
        total = db.search_posts_count(query)

        return [
            TextContent(
                type="text",
                text=_format_search_posts(query, results, page, per_page, total),
            )
        ]

    if name == "get_users":
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 20)

        users_with_counts = db.get_users_with_post_counts(
            page=page, per_page=per_page, order_by="post_count", order_dir="DESC"
        )
        total = db.get_users_count()

        return [
            TextContent(
                type="text",
                text=_format_users(users_with_counts, page, per_page, total),
            )
        ]

    if name == "get_categories":
        categories = db.get_all_categories()
        return [TextContent(type="text", text=_format_categories(categories))]

    if name == "get_statistics":
        stats = db.get_archive_statistics()
        return [TextContent(type="text", text=_format_stats(stats))]

    raise ValueError(f"Unknown tool: {name}")


# Formatting helpers
def _format_stats(stats: dict[str, Any]) -> str:
    """Format statistics for display."""
    lines = [
        f"Total Topics: {stats['total_topics']}",
        f"Total Posts: {stats['total_posts']}",
        f"Total Users: {stats['total_users']}",
        f"Total Categories: {stats['total_categories']}",
        f"Total Views: {stats['total_views']}",
    ]
    if stats.get("earliest_topic"):
        lines.append(f"Earliest Topic: {stats['earliest_topic']}")
    if stats.get("latest_topic"):
        lines.append(f"Latest Topic: {stats['latest_topic']}")
    return "\n".join(lines)


def _format_categories(categories: list[Any]) -> str:
    """Format categories for display."""
    lines = []
    for cat in categories:
        cat_dict = cat.to_dict() if hasattr(cat, "to_dict") else cat
        lines.append(f"- {cat_dict['name']} ({cat_dict['topic_count']} topics)")
    return "\n".join(lines)


def _format_timeline(timeline: list[dict[str, Any]]) -> str:
    """Format timeline for display."""
    lines = []
    for item in timeline:
        lines.append(
            f"{item['month']}: {item['topic_count']} topics, {item['post_count']} posts"
        )
    return "\n".join(lines)


def _format_topics(topics: list[Any], page: int, per_page: int, total: int) -> str:
    """Format topics list for display."""
    lines = [f"Topics (page {page}, showing {len(topics)} of {total} total):"]
    for topic in topics:
        topic_dict = topic if isinstance(topic, dict) else topic.to_dict()
        lines.append(
            f"- [{topic_dict['id']}] {topic_dict['title']}"
            f" ({topic_dict['posts_count']} posts)"
        )
    return "\n".join(lines)


def _format_topic_detail(topic: Any) -> str:
    """Format topic detail for display."""
    topic_dict = topic.to_dict() if hasattr(topic, "to_dict") else topic
    return f"""Topic: {topic_dict["title"]}
ID: {topic_dict["id"]}
Posts: {topic_dict["posts_count"]}
Views: {topic_dict["views"]}
Created: {topic_dict["created_at"]}
"""


def _format_posts(posts: list[Any], page: int, per_page: int, total: int) -> str:
    """Format posts list for display."""
    lines = [f"Posts (page {page}, showing {len(posts)} of {total} total):"]
    for post in posts:
        post_dict = post.to_dict() if hasattr(post, "to_dict") else post
        raw_content = post_dict.get("raw") or post_dict.get("cooked") or "[No content]"
        preview = raw_content[:100] + "..." if len(raw_content) > 100 else raw_content
        lines.append(
            f"- Post #{post_dict['post_number']} by {post_dict['username']}: {preview}"
        )
    return "\n".join(lines)


def _format_search_topics(
    query: str, results: list[Any], page: int, per_page: int, total: int
) -> str:
    """Format search topics results for display."""
    lines = [
        f"Search results for '{query}' (page {page}, {len(results)} of {total} total):"
    ]
    for topic in results:
        topic_dict = topic.to_dict() if hasattr(topic, "to_dict") else topic
        lines.append(f"- [{topic_dict['id']}] {topic_dict['title']}")
    return "\n".join(lines)


def _format_search_posts(
    query: str, results: list[Any], page: int, per_page: int, total: int
) -> str:
    """Format search posts results for display."""
    lines = [
        f"Search results for '{query}' (page {page}, {len(results)} of {total} total):"
    ]
    for post in results:
        post_dict = post.to_dict() if hasattr(post, "to_dict") else post
        raw_content = post_dict.get("raw") or post_dict.get("cooked") or "[No content]"
        preview = raw_content[:100] + "..." if len(raw_content) > 100 else raw_content
        lines.append(f"- Post by {post_dict['username']}: {preview}")
    return "\n".join(lines)


def _format_users(users: list[Any], page: int, per_page: int, total: int) -> str:
    """Format users list for display."""
    lines = [f"Users (page {page}, showing {len(users)} of {total} total):"]
    for item in users:
        # Handle nested structure from get_users_with_post_counts
        if isinstance(item, dict) and "user" in item:
            user = item["user"]
            user_dict = user.to_dict() if hasattr(user, "to_dict") else user
            user_dict["post_count"] = item["post_count"]
        else:
            user_dict = item if isinstance(item, dict) else item.to_dict()
        lines.append(f"- {user_dict['username']} ({user_dict['post_count']} posts)")
    return "\n".join(lines)


async def main():
    """Run the MCP server."""
    logger.info("Starting Chronicon MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream, write_stream, mcp_server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
