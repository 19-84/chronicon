# ABOUTME: Server-rendered HTML search page for FTS mode
# ABOUTME: Searches topics (by title) and posts (by content) with distinction

import html
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from chronicon.api.app import get_db, limiter
from chronicon.storage.database_base import ArchiveDatabaseBase

router = APIRouter(tags=["search-html"])

# Initialize Jinja2 environment with templates directory
_template_env: Environment | None = None


def get_template_env() -> Environment:
    """Get or create Jinja2 template environment."""
    global _template_env
    if _template_env is None:
        # Find templates directory relative to this file
        # Path: src/chronicon/api/routes/search_html.py -> templates/
        package_dir = Path(__file__).parent.parent.parent.parent.parent
        template_dir = package_dir / "templates"

        _template_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

        # Add helper functions used by templates
        _template_env.globals["rel_path"] = lambda path, depth: f"/archive/{path}"
        _template_env.globals["asset_path"] = (
            lambda path, depth: f"/archive/assets/{path}"
        )
        _template_env.globals["get_local_logo"] = lambda depth: None
        _template_env.globals["search_backend"] = "fts"
        _template_env.globals["chronicon_repo"] = (
            "https://github.com/Chronicon/chronicon"
        )
        _template_env.globals["chronicon_version"] = "1.0.0"

    return _template_env


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    clean = html.unescape(clean)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def get_excerpt(text: str, query: str, max_length: int = 200) -> str:
    """
    Extract an excerpt from text, centered around the query term if found.

    Args:
        text: The full text to extract from
        query: The search query to center on
        max_length: Maximum length of excerpt

    Returns:
        Excerpt string with ... if truncated
    """
    if not text:
        return ""

    clean_text = strip_html_tags(text)

    if len(clean_text) <= max_length:
        return clean_text

    # Try to find query term and center excerpt around it
    query_lower = query.lower()
    text_lower = clean_text.lower()
    pos = text_lower.find(query_lower)

    if pos >= 0:
        # Center around the match
        start = max(0, pos - max_length // 3)
        end = min(len(clean_text), start + max_length)
        if start > 0:
            # Find word boundary
            space_pos = clean_text.find(" ", start)
            if space_pos > 0 and space_pos < start + 20:
                start = space_pos + 1
        excerpt = clean_text[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(clean_text):
            # Find word boundary
            space_pos = excerpt.rfind(" ")
            if space_pos > len(excerpt) - 30:
                excerpt = excerpt[:space_pos]
            excerpt = excerpt + "..."
        return excerpt
    else:
        # No match found, just return beginning
        excerpt = clean_text[:max_length]
        space_pos = excerpt.rfind(" ")
        if space_pos > max_length - 30:
            excerpt = excerpt[:space_pos]
        return excerpt + "..."


@router.get("/search", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def search_page(
    request: Request,
    db: Annotated[ArchiveDatabaseBase, Depends(get_db)],
    q: str | None = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
) -> HTMLResponse:
    """
    Server-rendered search page.

    - Without query: renders empty search form
    - With query: executes FTS search on topics AND posts, renders results

    Results are grouped into:
    - Topic matches (title/tags match)
    - Post matches (content matches) - labeled as "Original Post" or "Reply"
    """
    topic_results = []
    post_results = []
    total_topics = 0
    total_posts = 0
    error = None

    # Get site metadata
    site_url = db.get_first_site_url()
    site_meta = db.get_site_metadata(site_url) if site_url else {}
    site_title = site_meta.get("site_title", "Forum Archive")

    if q:
        # Check if search is available
        if not db.is_search_available():
            error = "Search is not available. Please rebuild the search index."
        else:
            try:
                # Allocate results between topics and posts
                # Show up to 5 topic matches, rest are post matches
                topic_limit = min(5, per_page)
                post_limit = per_page - topic_limit

                # Search topics (title/tags)
                topics = db.search_topics(
                    q, limit=topic_limit, offset=0 if page == 1 else 0
                )
                total_topics = db.search_topics_count(q)

                # Build set of topic IDs we're showing from topic search
                shown_topic_ids = set()

                for topic in topics:
                    shown_topic_ids.add(topic.id)
                    topic_dict = {
                        "result_type": "topic",
                        "id": topic.id,
                        "title": topic.title,
                        "slug": topic.slug,
                        "created_at": topic.created_at.isoformat()
                        if topic.created_at
                        else None,
                        "posts_count": topic.posts_count,
                        "excerpt": topic.excerpt or "",
                        "category_id": topic.category_id,
                        "category_name": None,
                        "category_color": None,
                    }
                    if topic.category_id:
                        category = db.get_category(topic.category_id)
                        if category:
                            topic_dict["category_name"] = category.name
                            topic_dict["category_color"] = category.color
                    topic_results.append(topic_dict)

                # Search posts (content)
                # Adjust offset for pagination - on page 1, no offset for posts
                # On subsequent pages, offset by full amount
                post_offset = 0 if page == 1 else (page - 1) * per_page
                posts = db.search_posts(q, limit=post_limit + 10, offset=post_offset)
                total_posts = db.search_posts_count(q)

                # Process post results
                post_count = 0
                for post in posts:
                    if post_count >= post_limit:
                        break

                    # Get the topic for this post
                    topic = db.get_topic(post.topic_id)
                    if not topic:
                        continue

                    # Determine if this is the original post or a reply
                    is_original = post.post_number == 1
                    post_type = (
                        "Original Post" if is_original else f"Reply #{post.post_number}"
                    )

                    # Get excerpt from post content
                    excerpt = get_excerpt(post.cooked or post.raw or "", q)

                    post_dict = {
                        "result_type": "post",
                        "post_type": post_type,
                        "is_original": is_original,
                        "post_id": post.id,
                        "post_number": post.post_number,
                        "topic_id": topic.id,
                        "title": topic.title,
                        "slug": topic.slug,
                        "username": post.username,
                        "created_at": post.created_at.isoformat()
                        if post.created_at
                        else None,
                        "excerpt": excerpt,
                        "category_id": topic.category_id,
                        "category_name": None,
                        "category_color": None,
                    }
                    if topic.category_id:
                        category = db.get_category(topic.category_id)
                        if category:
                            post_dict["category_name"] = category.name
                            post_dict["category_color"] = category.color
                    post_results.append(post_dict)
                    post_count += 1

            except Exception as e:
                error = f"Search error: {str(e)}"

    # Calculate total for pagination
    total = total_topics + total_posts

    # Render template
    env = get_template_env()
    template = env.get_template("search-results.html")

    html_content = template.render(
        query=q,
        topic_results=topic_results,
        post_results=post_results,
        total=total,
        total_topics=total_topics,
        total_posts=total_posts,
        page=page,
        per_page=per_page,
        error=error,
        site_title=site_title,
        site_description=site_meta.get("site_description", ""),
        logo_url=site_meta.get("logo_url"),
        depth=0,
    )

    return HTMLResponse(content=html_content)
