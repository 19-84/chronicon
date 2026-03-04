# ABOUTME: SEO meta tag generation utilities
# ABOUTME: Generates Open Graph, Twitter Cards, JSON-LD for HTML exports

"""SEO meta tag generation utilities for HTML exports."""

import re

from bs4 import BeautifulSoup

from ..models.category import Category
from ..models.post import Post
from ..models.topic import Topic


def strip_html(html: str) -> str:
    """
    Remove HTML tags from a string, leaving only text.

    Args:
        html: HTML string to strip

    Returns:
        Plain text with HTML tags removed
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def truncate_smartly(text: str, max_length: int = 160) -> str:
    """
    Truncate text at a word boundary without cutting off mid-word.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 160 chars for meta description)

    Returns:
        Truncated text with ellipsis if needed
    """
    if not text or len(text) <= max_length:
        return text

    # Truncate to max_length
    truncated = text[:max_length]

    # Find the last space to avoid cutting mid-word
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:  # Only trim if we're not losing too much
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


def generate_meta_description(
    topic: Topic, posts: list[Post] | None = None, max_length: int = 160
) -> str:
    """
    Generate meta description from topic excerpt or first post.

    Priority:
    1. Topic excerpt (if available)
    2. First post content (stripped of HTML)
    3. Topic title (as fallback)

    Args:
        topic: Topic object
        posts: Optional list of posts (first post will be used)
        max_length: Maximum description length (default: 160)

    Returns:
        Meta description string
    """
    # Try excerpt first
    if topic.excerpt:
        return truncate_smartly(strip_html(topic.excerpt), max_length)

    # Try first post content
    if posts and len(posts) > 0:
        first_post_text = strip_html(posts[0].cooked or "")
        if first_post_text:
            return truncate_smartly(first_post_text, max_length)

    # Fallback to topic title
    return truncate_smartly(topic.title, max_length)


def generate_keywords(topic: Topic) -> str:
    """
    Generate keywords from topic tags.

    Args:
        topic: Topic object

    Returns:
        Comma-separated list of keywords
    """
    if not topic.tags:
        return ""

    return ", ".join(topic.tags)


def generate_og_tags(
    topic: Topic,
    site_title: str,
    canonical_url: str | None = None,
    local_image_path: str | None = None,
) -> dict[str, str]:
    """
    Generate Open Graph meta tags for a topic.

    Args:
        topic: Topic object
        site_title: Site title for og:site_name
        canonical_url: Optional canonical URL for og:url
        local_image_path: Optional local path to topic image (preferred
            over topic.image_url for offline archives)

    Returns:
        Dictionary of Open Graph property/content pairs
    """
    tags = {
        "og:type": "article",
        "og:title": topic.title,
        "og:site_name": site_title,
    }

    # Add optional fields if available
    if topic.excerpt:
        tags["og:description"] = strip_html(topic.excerpt)

    # Prefer local image path over remote URL for offline archives
    if local_image_path:
        tags["og:image"] = local_image_path
    elif topic.image_url:
        tags["og:image"] = topic.image_url

    if canonical_url:
        tags["og:url"] = canonical_url

    # Article metadata
    if topic.created_at:
        tags["article:published_time"] = topic.created_at.isoformat()

    if topic.last_posted_at:
        tags["article:modified_time"] = topic.last_posted_at.isoformat()

    if topic.tags:
        # Open Graph allows multiple article:tag properties
        # For simplicity, we'll join them with commas
        tags["article:tag"] = ", ".join(topic.tags)

    return tags


def generate_twitter_card(
    topic: Topic, local_image_path: str | None = None
) -> dict[str, str]:
    """
    Generate Twitter Card meta tags for a topic.

    Args:
        topic: Topic object
        local_image_path: Optional local path to topic image (preferred
            over topic.image_url for offline archives)

    Returns:
        Dictionary of Twitter Card name/content pairs
    """
    # Use summary_large_image if we have an image, otherwise summary
    has_image = local_image_path or topic.image_url
    card_type = "summary_large_image" if has_image else "summary"

    tags = {
        "twitter:card": card_type,
        "twitter:title": topic.title,
    }

    # Add optional fields if available
    if topic.excerpt:
        tags["twitter:description"] = strip_html(topic.excerpt)

    # Prefer local image path over remote URL for offline archives
    if local_image_path:
        tags["twitter:image"] = local_image_path
    elif topic.image_url:
        tags["twitter:image"] = topic.image_url

    return tags


def generate_json_ld(
    topic: Topic,
    category: Category | None,
    posts: list[Post] | None,
    site_url: str,
    local_image_path: str | None = None,
) -> dict:
    """
    Generate JSON-LD structured data for a topic.

    Uses schema.org DiscussionForumPosting type for forum topics.

    Args:
        topic: Topic object
        category: Optional category object
        posts: Optional list of posts for the topic
        site_url: Base site URL
        local_image_path: Optional local path to topic image (preferred
            over topic.image_url for offline archives)

    Returns:
        Dictionary representing JSON-LD structured data
    """
    # Get author name from first post
    author_name = "Unknown"
    if posts and len(posts) > 0:
        author_name = posts[0].username or "Unknown"

    data = {
        "@context": "https://schema.org",
        "@type": "DiscussionForumPosting",
        "headline": topic.title,
        "author": {"@type": "Person", "name": author_name},
        "interactionStatistic": [
            {
                "@type": "InteractionCounter",
                "interactionType": "https://schema.org/ViewAction",
                "userInteractionCount": topic.views,
            },
            {
                "@type": "InteractionCounter",
                "interactionType": "https://schema.org/LikeAction",
                "userInteractionCount": topic.like_count,
            },
            {
                "@type": "InteractionCounter",
                "interactionType": "https://schema.org/CommentAction",
                "userInteractionCount": topic.reply_count,
            },
        ],
        "commentCount": topic.reply_count,
    }

    # Add optional fields
    if topic.excerpt:
        data["description"] = strip_html(topic.excerpt)

    # Prefer local image path over remote URL for offline archives
    if local_image_path:
        data["image"] = local_image_path
    elif topic.image_url:
        data["image"] = topic.image_url

    if topic.created_at:
        data["datePublished"] = topic.created_at.isoformat()

    if topic.last_posted_at:
        data["dateModified"] = topic.last_posted_at.isoformat()
    elif topic.created_at:
        data["dateModified"] = topic.created_at.isoformat()

    if topic.tags:
        data["keywords"] = ", ".join(topic.tags)

    return data


def generate_category_og_tags(
    category: Category, site_title: str, canonical_url: str | None = None
) -> dict[str, str]:
    """
    Generate Open Graph tags for a category page.

    Args:
        category: Category object
        site_title: Site title for og:site_name
        canonical_url: Optional canonical URL

    Returns:
        Dictionary of Open Graph property/content pairs
    """
    tags = {
        "og:type": "website",
        "og:title": f"{category.name} - {site_title}",
        "og:site_name": site_title,
    }

    if category.description:
        tags["og:description"] = strip_html(category.description)

    if canonical_url:
        tags["og:url"] = canonical_url

    return tags


def generate_homepage_og_tags(
    site_title: str,
    site_description: str | None,
    logo_url: str | None,
    canonical_url: str | None = None,
) -> dict[str, str]:
    """
    Generate Open Graph tags for the homepage.

    Args:
        site_title: Site title
        site_description: Optional site description
        logo_url: Optional site logo URL
        canonical_url: Optional canonical URL

    Returns:
        Dictionary of Open Graph property/content pairs
    """
    tags = {
        "og:type": "website",
        "og:title": site_title,
        "og:site_name": site_title,
    }

    if site_description:
        tags["og:description"] = site_description

    if logo_url:
        tags["og:image"] = logo_url

    if canonical_url:
        tags["og:url"] = canonical_url

    return tags
