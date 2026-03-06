# ABOUTME: Markdown exporter for Chronicon
# ABOUTME: Exports topics to GitHub-flavored markdown with Discourse-style URLs

"""Export to GitHub-flavored markdown with images and Discourse-style URLs."""

import contextlib
import math
import os
from datetime import datetime
from pathlib import Path

import html2text
from bs4 import BeautifulSoup

from ..models.topic import Topic
from ..processors.emoji_mapper import get_unicode_emoji, has_unicode_emoji
from ..utils.logger import get_logger
from .base import BaseExporter

log = get_logger(__name__)


class MarkdownGitHubExporter(BaseExporter):
    """Export to GitHub-flavored markdown with images."""

    def __init__(
        self,
        db,
        output_dir: Path,
        asset_downloader=None,
        posts_per_page: int = 50,
        pagination_enabled: bool = True,
        include_users: bool = False,
        progress=None,
    ):
        """
        Initialize GitHub markdown exporter.

        Args:
            db: ArchiveDatabase instance
            output_dir: Output directory
            asset_downloader: AssetDownloader for downloading images
            posts_per_page: Number of posts per page (default: 50)
            pagination_enabled: Whether to enable pagination (default: True)
            include_users: Whether to generate user profile pages (default: False)
            progress: Optional Rich Progress object for progress tracking
        """
        super().__init__(db, output_dir, progress=progress)
        self.asset_downloader = asset_downloader
        self.posts_per_page = posts_per_page
        self.pagination_enabled = pagination_enabled
        self.include_users = include_users

        # Configure html2text for GitHub-flavored markdown
        self.html_converter = html2text.HTML2Text()
        self.html_converter.body_width = 0  # Don't wrap lines
        self.html_converter.unicode_snob = True
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False

    def export(self) -> None:
        """Main export method."""
        # Get all topics
        topics = self.db.get_all_topics()

        # Calculate total work items: homepage + indexes + topics + users + README
        total_items = (
            len(topics) + 6
        )  # topics + homepage + latest + top + categories + README + metadata
        if self.include_users:
            total_items += self.db.get_users_count() + 1  # users + user index

        task = None
        if self.progress:
            task = self.progress.add_task(
                "[cyan]Exporting GitHub Markdown...", total=total_items
            )

        # Generate homepage and indexes first
        self.generate_index()
        if self.progress:
            self.progress.advance(task, 1)

        self.generate_latest_index()
        if self.progress:
            self.progress.advance(task, 1)

        self.generate_top_indexes()
        if self.progress:
            self.progress.advance(task, 1)

        self.generate_category_indexes()
        if self.progress:
            self.progress.advance(task, 1)

        # Export each topic
        for _i, topic in enumerate(topics, 1):
            self.export_topic(topic)
            if self.progress:
                self.progress.advance(task, 1)

        # Export users if enabled
        if self.include_users:
            self.generate_users_index()
            if self.progress:
                self.progress.advance(task, 1)

            self.export_users()

        # Generate README with table of contents
        self.generate_readme()
        if self.progress:
            self.progress.advance(task, 1)

        if self.progress:
            desc = f"[green]✓ GitHub Markdown export complete ({len(topics)} topics"
            if self.include_users:
                desc += f", {self.db.get_users_count()} users"
            desc += ")"
            self.progress.update(task, description=desc)

    def export_topic(self, topic: Topic) -> Path:
        """
        Export a single topic to GitHub markdown (with pagination if enabled).

        Args:
            topic: Topic to export

        Returns:
            Path to exported markdown file (first page if paginated)
        """
        # Get category info once
        category = None
        if topic.category_id:
            category = self.db.get_category(topic.category_id)

        # Create directory structure using Discourse-style: /t/{slug}/
        topic_dir = self.output_dir / "t" / topic.slug
        topic_dir.mkdir(parents=True, exist_ok=True)

        first_page_path = None

        if self.pagination_enabled:
            # Get post count for pagination
            post_count = self.db.get_topic_posts_count(topic.id)

            # Calculate number of pages needed
            total_pages = (
                math.ceil(post_count / self.posts_per_page) if post_count > 0 else 1
            )

            # Generate each page
            for page_num in range(1, total_pages + 1):
                # Get posts for this page
                posts = self.db.get_topic_posts_paginated(
                    topic.id, page_num, self.posts_per_page
                )

                # Build markdown content for this page
                lines = self._build_topic_page(
                    topic, posts, category, page_num, total_pages
                )

                # Write to file: /t/{slug}/{id}.md or /t/{slug}/{id}-page-{N}.md
                if page_num == 1:
                    filename = f"{topic.id}.md"
                    first_page_path = topic_dir / filename
                else:
                    filename = f"{topic.id}-page-{page_num}.md"

                topic_path = topic_dir / filename
                topic_path.write_text("\n".join(lines), encoding="utf-8")

                if page_num == 1:
                    first_page_path = topic_path
        else:
            # Non-paginated mode: single file with all posts
            posts = self.db.get_topic_posts(topic.id)

            # Build markdown content
            lines = self._build_topic_page(topic, posts, category, 1, 1)

            # Write to file: /t/{slug}/{id}.md
            filename = f"{topic.id}.md"
            topic_path = topic_dir / filename

            topic_path.write_text("\n".join(lines), encoding="utf-8")
            first_page_path = topic_path

        assert first_page_path is not None
        return first_page_path

    def _get_site_url(self) -> str | None:
        """
        Get the primary site URL from the database.

        Returns:
            Site URL string, or None if not found
        """
        try:
            # Query database for site URL
            cursor = self.db.connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("SELECT site_url FROM site_metadata LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            log.warning(f"Could not retrieve site URL from database: {e}")
            return None

    def _build_topic_page(
        self, topic: Topic, posts: list, category, page_num: int, total_pages: int
    ) -> list[str]:
        """
        Build markdown content for a single topic page.

        Args:
            topic: Topic object
            posts: List of Post objects for this page
            category: Category object or None
            page_num: Current page number (1-indexed)
            total_pages: Total number of pages

        Returns:
            List of lines for the markdown file
        """
        lines = []

        # Navigation header - topic files are in /t/{slug}/, depth = 2
        nav_home = "../../index.md"
        nav_latest = "../../latest/index.md"
        nav_top = "../../top/replies/index.md"
        nav_users = "../../users/index.md"

        lines.append(
            f"[🏠 Home]({nav_home}) | [📋 Latest]({nav_latest}) | "
            f"[🔥 Top]({nav_top}) | [👥 Users]({nav_users})"
        )
        lines.append("")

        # Breadcrumbs
        breadcrumb_parts = [f"[Home]({nav_home})"]
        if category:
            cat_path = f"../../c/{category.slug}/index.md"
            breadcrumb_parts.append(f"[{category.name}]({cat_path})")
        breadcrumb_parts.append(topic.title)

        lines.append(" » ".join(breadcrumb_parts))
        lines.append("")
        lines.append("---")
        lines.append("")

        # Title (include page number if paginated)
        if total_pages > 1:
            lines.append(f"# {topic.title} (Page {page_num} of {total_pages})")
        else:
            lines.append(f"# {topic.title}")
        lines.append("")

        # Metadata in blockquote style
        lines.append(
            "> **Category:** " + (category.name if category else "Uncategorized")
        )
        lines.append(f"> **Author:** {posts[0].username if posts else 'Unknown'}")
        lines.append(f"> **Created:** {topic.created_at.strftime('%Y-%m-%d %H:%M')}")
        if topic.updated_at and topic.updated_at != topic.created_at:
            lines.append(
                f"> **Last Updated:** {topic.updated_at.strftime('%Y-%m-%d %H:%M')}"
            )
        lines.append("")

        # Pagination navigation (if multiple pages)
        if total_pages > 1:
            nav_parts = []

            if page_num > 1:
                # Link to previous page
                if page_num == 2:
                    prev_filename = f"{topic.id}.md"
                else:
                    prev_filename = f"{topic.id}-page-{page_num - 1}.md"
                nav_parts.append(f"[← Previous]({prev_filename})")
            else:
                nav_parts.append("← Previous")

            nav_parts.append(f"**Page {page_num} of {total_pages}**")

            if page_num < total_pages:
                # Link to next page
                next_filename = f"{topic.id}-page-{page_num + 1}.md"
                nav_parts.append(f"[Next →]({next_filename})")
            else:
                nav_parts.append("Next →")

            lines.append(" | ".join(nav_parts))
            lines.append("")

        lines.append("---")
        lines.append("")

        # Posts
        for post in posts:
            # Make username clickable - link to user profile
            user_link = f"../../users/{post.username}.md"
            lines.append(
                f"### Post #{post.post_number} by [{post.username}]({user_link})"
            )
            posted_date = post.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"*Posted: {posted_date}*")
            lines.append("")

            # Convert HTML to GFM
            content = self.convert_html_to_gfm(post.cooked, topic.id)
            lines.append(content.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

        # Add pagination footer
        if total_pages > 1:
            lines.append("")
            nav_parts = []

            if page_num > 1:
                if page_num == 2:
                    prev_filename = f"{topic.id}.md"
                else:
                    prev_filename = f"{topic.id}-page-{page_num - 1}.md"
                nav_parts.append(f"[← Previous]({prev_filename})")
            else:
                nav_parts.append("← Previous")

            nav_parts.append(f"**Page {page_num} of {total_pages}**")

            if page_num < total_pages:
                next_filename = f"{topic.id}-page-{page_num + 1}.md"
                nav_parts.append(f"[Next →]({next_filename})")
            else:
                nav_parts.append("Next →")

            lines.append(" | ".join(nav_parts))
            lines.append("")

        return lines

    def export_users(self) -> None:
        """Export user profile pages with their posts."""
        users = self.db.get_all_users()

        # Create users directory
        user_dir = self.output_dir / "users"
        user_dir.mkdir(parents=True, exist_ok=True)

        for user in users:
            # Get user's posts with topic information (returns list of dicts)
            user_posts_data = self.db.get_user_posts(
                user.id, limit=100
            )  # Limit to 100 most recent
            post_count = self.db.get_user_post_count(user.id)

            # Build markdown content
            lines = []

            # Navigation header - user files are in users/, depth = 1
            nav_home = "../index.md"
            nav_latest = "../latest/index.md"
            nav_top = "../top/replies/index.md"
            nav_users = "../users/index.md"

            lines.append(
                f"[🏠 Home]({nav_home}) | [📋 Latest]({nav_latest}) | "
                f"[🔥 Top]({nav_top}) | [👥 Users]({nav_users})"
            )
            lines.append("")

            # Breadcrumb
            lines.append(f"[Home]({nav_home}) » [Users]({nav_users}) » {user.username}")
            lines.append("")
            lines.append("---")
            lines.append("")

            # Title
            lines.append(f"# {user.username}")
            lines.append("")

            # User metadata in blockquote style
            lines.append(f"> **Name:** {user.name or user.username}")
            lines.append(f"> **Trust Level:** {user.trust_level}")
            if user.created_at:
                lines.append(
                    f"> **Member Since:** {user.created_at.strftime('%Y-%m-%d')}"
                )
            lines.append(f"> **Total Posts:** {post_count}")
            lines.append("")
            lines.append("---")
            lines.append("")

            if not user_posts_data:
                lines.append("*No posts found for this user.*")
            else:
                # List of user's posts
                recent_count = min(len(user_posts_data), 100)
                lines.append(f"## Recent Posts ({recent_count} of {post_count})")
                lines.append("")

                for post_data in user_posts_data:
                    # Extract post and topic info from dict
                    post = post_data["post"]
                    topic_id = post_data["topic_id"]
                    topic_title = post_data["topic_title"]
                    # Get topic for slug information
                    topic = self.db.get_topic(topic_id)
                    if not topic:
                        continue

                    # Build relative path to topic using Discourse-style URLs
                    topic_link = f"../t/{topic.slug}/{topic_id}.md"

                    # Post entry
                    lines.append(f"### [{topic_title}]({topic_link})")
                    posted_date = post.created_at.strftime("%Y-%m-%d %H:%M")
                    lines.append(f"*Posted: {posted_date} | Post #{post.post_number}*")
                    lines.append("")

                    # Convert and include post excerpt (first 200 chars)
                    content = self.convert_html_to_gfm(post.cooked, topic_id)
                    excerpt = content[:200] + "..." if len(content) > 200 else content
                    lines.append(excerpt)
                    lines.append("")
                    lines.append("---")
                    lines.append("")

            # Write to file: users/{username}.md
            user_path = user_dir / f"{user.username}.md"
            user_path.write_text("\n".join(lines), encoding="utf-8")

        log.info(f"Generated {len(users)} user profile pages")

    def generate_index(self) -> None:
        """Generate homepage (index.md) with site overview and navigation."""
        lines = []

        # Get site metadata
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        site_title = site_meta.get("site_title", "Forum Archive")
        site_description = site_meta.get("site_description", "")

        # Header
        lines.append(f"# {site_title}")
        lines.append("")

        if site_description:
            lines.append(f"> {site_description}")
            lines.append("")

        # Navigation
        lines.append(
            "[📋 Latest](latest/index.md) | [🔥 Top Replies](top/replies/index.md) | "
            "[👁️ Top Views](top/views/index.md) | [👥 Users](users/index.md)"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # Statistics
        stats = self.db.get_statistics()
        archive_stats = self.db.get_archive_statistics()

        lines.append("## Archive Statistics")
        lines.append("")
        lines.append(f"- **Topics:** {stats['total_topics']}")
        lines.append(f"- **Posts:** {stats['total_posts']}")
        lines.append(f"- **Categories:** {stats['total_categories']}")
        lines.append(f"- **Users:** {stats['total_users']}")
        lines.append(f"- **Total Views:** {stats.get('total_views', 0):,}")

        if archive_stats.get("earliest_topic") and archive_stats.get("latest_topic"):
            earliest = archive_stats["earliest_topic"][:10]
            latest = archive_stats["latest_topic"][:10]
            lines.append(f"- **Date Range:** {earliest} to {latest}")

        lines.append("")

        # Recent Topics
        recent_topics = self.db.get_recent_topics(limit=7)
        if recent_topics:
            lines.append("## Recent Topics")
            lines.append("")
            for topic in recent_topics:
                topic_link = f"t/{topic.slug}/{topic.id}.md"
                lines.append(
                    f"- [{topic.title}]({topic_link}) - "
                    f"{topic.views} views, {topic.posts_count - 1} replies"
                )
            lines.append("")

        # Top Topics by Replies
        top_replies = self.db.get_topics_paginated(
            page=1, per_page=7, order_by="posts_count", order_dir="DESC"
        )
        if top_replies:
            lines.append("## Top Topics by Replies")
            lines.append("")
            for topic in top_replies:
                topic_link = f"t/{topic.slug}/{topic.id}.md"
                lines.append(
                    f"- [{topic.title}]({topic_link}) - {topic.posts_count - 1} replies"
                )
            lines.append("")

        # Top Topics by Views
        top_views = self.db.get_topics_paginated(
            page=1, per_page=7, order_by="views", order_dir="DESC"
        )
        if top_views:
            lines.append("## Top Topics by Views")
            lines.append("")
            for topic in top_views:
                topic_link = f"t/{topic.slug}/{topic.id}.md"
                lines.append(f"- [{topic.title}]({topic_link}) - {topic.views:,} views")
            lines.append("")

        # Categories
        categories = self.db.get_all_categories()
        if categories:
            lines.append("## Categories")
            lines.append("")
            for category in categories:
                cat_link = f"c/{category.slug}/index.md"
                lines.append(
                    f"- [{category.name}]({cat_link}) - {category.topic_count} topics"
                )
            lines.append("")

        # Write to file
        index_path = self.output_dir / "index.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")

    def generate_latest_index(self) -> None:
        """Generate latest topics index with pagination."""
        total_topics = self.db.get_topics_count()
        total_pages = math.ceil(total_topics / 50) if total_topics > 0 else 1

        latest_dir = self.output_dir / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            lines = []
            lines.append(
                "[🏠 Home](../index.md) | [📋 Latest](../latest/index.md) | "
                "[🔥 Top](../top/replies/index.md) | "
                "[👥 Users](../users/index.md)"
            )
            lines.append("")
            lines.append("[Home](../index.md) » Latest Topics")
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(
                f"# Latest Topics (Page {page_num} of {total_pages})"
                if total_pages > 1
                else "# Latest Topics"
            )
            lines.append("")

            nav_parts: list[str] = []
            if total_pages > 1:
                nav_parts = self._build_pagination_nav(page_num, total_pages)
                lines.append(" | ".join(nav_parts))
                lines.append("")

            topics = self.db.get_topics_paginated(
                page_num, 50, order_by="created_at", order_dir="DESC"
            )
            for topic in topics:
                first_post = self.db.get_topic_posts(topic.id)
                author = first_post[0].username if first_post else "Unknown"
                category = (
                    self.db.get_category(topic.category_id)
                    if topic.category_id
                    else None
                )
                cat_name = category.name if category else "Uncategorized"

                topic_link = f"../t/{topic.slug}/{topic.id}.md"

                lines.append(f"### [{topic.title}]({topic_link})")
                date_str = topic.created_at.strftime("%Y-%m-%d")
                lines.append(
                    f"*{cat_name} | {author} | {date_str} | "
                    f"{topic.posts_count - 1} replies | {topic.views} views*"
                )
                lines.append("")

            if total_pages > 1:
                lines.append("---")
                lines.append("")
                lines.append(" | ".join(nav_parts))
                lines.append("")

            page_path = latest_dir / (
                "index.md" if page_num == 1 else f"page-{page_num}.md"
            )
            page_path.write_text("\n".join(lines), encoding="utf-8")

        log.info(f"Generated {total_pages} pages for latest index")

    def generate_top_indexes(self) -> None:
        """Generate top topics indexes."""
        top_dir = self.output_dir / "top"
        top_dir.mkdir(parents=True, exist_ok=True)

        # Default /top/index.md
        lines = [
            "[🏠 Home](../index.md) | [📋 Latest](../latest/index.md) | "
            "[🔥 Top](../top/replies/index.md) | [👥 Users](../users/index.md)",
            "",
            "[Home](../index.md) » Top Topics",
            "",
            "---",
            "",
            "# Top Topics",
            "",
            "- [Top by Replies](replies/index.md)",
            "- [Top by Views](views/index.md)",
            "",
        ]
        (top_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")

        self._generate_top_index("replies", "posts_count", "Top Topics by Replies")
        self._generate_top_index("views", "views", "Top Topics by Views")

    def _generate_top_index(
        self, index_name: str, order_by: str, page_title: str
    ) -> None:
        """Helper to generate a specific top topics index."""
        total_topics = self.db.get_topics_count()
        total_pages = math.ceil(total_topics / 50) if total_topics > 0 else 1

        index_dir = self.output_dir / "top" / index_name
        index_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            lines = []
            lines.append(
                "[🏠 Home](../index.md) | [📋 Latest](../latest/index.md) | "
                "[🔥 Top](../top/replies/index.md) | [👥 Users](../users/index.md)"
            )
            lines.append("")
            lines.append(f"[Home](../../index.md) » [Top](../index.md) » {page_title}")
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(
                f"# {page_title} (Page {page_num} of {total_pages})"
                if total_pages > 1
                else f"# {page_title}"
            )
            lines.append("")

            nav_parts: list[str] = []
            if total_pages > 1:
                nav_parts = self._build_pagination_nav(page_num, total_pages)
                lines.append(" | ".join(nav_parts))
                lines.append("")

            topics = self.db.get_topics_paginated(
                page_num, 50, order_by=order_by, order_dir="DESC"
            )
            for topic in topics:
                first_post = self.db.get_topic_posts(topic.id)
                author = first_post[0].username if first_post else "Unknown"
                category = (
                    self.db.get_category(topic.category_id)
                    if topic.category_id
                    else None
                )
                cat_name = category.name if category else "Uncategorized"

                topic_link = f"../../t/{topic.slug}/{topic.id}.md"

                metric = (
                    f"{topic.posts_count - 1} replies"
                    if order_by == "posts_count"
                    else f"{topic.views:,} views"
                )
                lines.append(f"### [{topic.title}]({topic_link})")
                date_str = topic.created_at.strftime("%Y-%m-%d")
                lines.append(f"*{cat_name} | {author} | {date_str} | {metric}*")
                lines.append("")

            if total_pages > 1:
                lines.append("---")
                lines.append("")
                lines.append(" | ".join(nav_parts))
                lines.append("")

            page_path = index_dir / (
                "index.md" if page_num == 1 else f"page-{page_num}.md"
            )
            page_path.write_text("\n".join(lines), encoding="utf-8")

        log.info(f"Generated {total_pages} pages for top/{index_name} index")

    def generate_category_indexes(self) -> None:
        """Generate per-category indexes with pagination."""
        categories = self.db.get_all_categories()
        categories_dir = self.output_dir / "c"
        categories_dir.mkdir(parents=True, exist_ok=True)

        for category in categories:
            cat_dir = categories_dir / category.slug
            cat_dir.mkdir(parents=True, exist_ok=True)

            total_topics = category.topic_count
            total_pages = math.ceil(total_topics / 50) if total_topics > 0 else 1

            for page_num in range(1, total_pages + 1):
                lines = []
                lines.append(
                    "[🏠 Home](../../index.md) | [📋 Latest](../../latest/index.md) | "
                    "[🔥 Top](../../top/replies/index.md) | "
                    "[👥 Users](../../users/index.md)"
                )
                lines.append("")
                lines.append(f"[Home](../../index.md) » {category.name}")
                lines.append("")
                lines.append("---")
                lines.append("")
                lines.append(
                    f"# {category.name} (Page {page_num} of {total_pages})"
                    if total_pages > 1
                    else f"# {category.name}"
                )
                lines.append("")

                if category.description:
                    lines.append(f"> {category.description}")
                    lines.append("")

                lines.append(f"**{category.topic_count} topics in this category**")
                lines.append("")

                nav_parts: list[str] = []
                if total_pages > 1:
                    nav_parts = self._build_pagination_nav(page_num, total_pages)
                    lines.append(" | ".join(nav_parts))
                    lines.append("")

                topics = self.db.get_category_topics_paginated(
                    category.id, page_num, 50
                )
                for topic in topics:
                    first_post = self.db.get_topic_posts(topic.id)
                    author = first_post[0].username if first_post else "Unknown"

                    topic_link = f"../../t/{topic.slug}/{topic.id}.md"

                    lines.append(f"### [{topic.title}]({topic_link})")
                    date_str = topic.created_at.strftime("%Y-%m-%d")
                    lines.append(
                        f"*{author} | {date_str} | "
                        f"{topic.posts_count - 1} replies | {topic.views} views*"
                    )
                    lines.append("")

                if total_pages > 1:
                    lines.append("---")
                    lines.append("")
                    lines.append(" | ".join(nav_parts))
                    lines.append("")

                page_path = cat_dir / (
                    "index.md" if page_num == 1 else f"page-{page_num}.md"
                )
                page_path.write_text("\n".join(lines), encoding="utf-8")

        log.info(f"Generated category indexes for {len(categories)} categories")

    def generate_users_index(self) -> None:
        """Generate users index sorted by post count with pagination."""
        total_users = self.db.get_users_count()
        total_pages = math.ceil(total_users / 50) if total_users > 0 else 1

        users_dir = self.output_dir / "users"
        users_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            lines = []
            lines.append(
                "[🏠 Home](../index.md) | [📋 Latest](../latest/index.md) | "
                "[🔥 Top](../top/replies/index.md) | "
                "[👥 Users](../users/index.md)"
            )
            lines.append("")
            lines.append("[Home](../index.md) » Users")
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(
                f"# Users (Page {page_num} of {total_pages})"
                if total_pages > 1
                else "# Users"
            )
            lines.append("")

            nav_parts: list[str] = []
            if total_pages > 1:
                nav_parts = self._build_pagination_nav(page_num, total_pages)
                lines.append(" | ".join(nav_parts))
                lines.append("")

            users_with_counts = self.db.get_users_with_post_counts(
                page_num, 50, order_by="post_count", order_dir="DESC"
            )
            for user_data in users_with_counts:
                user = user_data["user"]
                post_count = user_data["post_count"]

                lines.append(f"### [{user.username}]({user.username}.md)")
                lines.append(
                    f"*{user.name or user.username} | {post_count} posts | "
                    f"Trust Level {user.trust_level}*"
                )
                lines.append("")

            if total_pages > 1:
                lines.append("---")
                lines.append("")
                lines.append(" | ".join(nav_parts))
                lines.append("")

            page_path = users_dir / (
                "index.md" if page_num == 1 else f"page-{page_num}.md"
            )
            page_path.write_text("\n".join(lines), encoding="utf-8")

        log.info(f"Generated {total_pages} pages for users index")

    def _build_pagination_nav(self, page_num: int, total_pages: int) -> list[str]:
        """Helper to build pagination navigation."""
        nav_parts = []

        if page_num > 1:
            prev_file = "index.md" if page_num == 2 else f"page-{page_num - 1}.md"
            nav_parts.append(f"[← Previous]({prev_file})")
        else:
            nav_parts.append("← Previous")

        nav_parts.append(f"**Page {page_num} of {total_pages}**")

        if page_num < total_pages:
            nav_parts.append(f"[Next →](page-{page_num + 1}.md)")
        else:
            nav_parts.append("Next →")

        return nav_parts

    def generate_readme(self) -> None:
        """Generate README.md landing page with archive overview."""

        lines = []

        # Get site metadata for branding
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        site_title = site_meta.get("site_title", "Forum Archive")
        site_description = site_meta.get("site_description", "")

        # Header with site title
        lines.append(f"# {site_title} - Archived Forum")
        lines.append("")

        # Site description if available, otherwise use generic description
        if site_description:
            lines.append(f"> {site_description}")
        else:
            lines.append(
                "> A complete archive of forum discussions preserved in markdown format"
            )
        lines.append("")

        # Getting Started section
        lines.append("## Getting Started")
        lines.append("")
        lines.append(
            "**[Browse the Archive](index.md)** - Explore topics and discussions"
        )
        lines.append("")
        # Build description text - avoid redundancy with default site_title
        if site_title and site_title != "Forum Archive":
            description_text = (
                f"This is a complete offline archive of {site_title}. "
                "All content is preserved in readable markdown format"
                " and works entirely offline."
            )
        else:
            description_text = (
                "This is a complete offline archive of forum discussions. "
                "All content is preserved in readable markdown format"
                " and works entirely offline."
            )
        lines.append(description_text)
        lines.append("")

        # About This Archive section
        lines.append("## About This Archive")
        lines.append("")
        archive_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"- **Archive Date:** {archive_date}")

        if site_url:
            lines.append(f"- **Original Site:** {site_url}")

        # Archive statistics
        stats = self.db.get_statistics()
        archive_stats = self.db.get_archive_statistics()

        # Add date range if available
        if archive_stats.get("earliest_topic") and archive_stats.get("latest_topic"):
            earliest = archive_stats["earliest_topic"][:10]  # YYYY-MM-DD
            latest = archive_stats["latest_topic"][:10]
            lines.append(f"- **Archive Coverage:** {earliest} to {latest}")

        # Content summary
        content_parts = [f"{stats['total_topics']} topics"]
        content_parts.append(f"{stats['total_posts']} posts")
        if self.include_users:
            content_parts.append(f"{stats['total_users']} users")
        lines.append(f"- **Content:** {', '.join(content_parts)}")

        lines.append("")

        # Navigation section
        lines.append("## Navigation")
        lines.append("")
        lines.append("Explore the archive through these main sections:")
        lines.append("")
        lines.append("- **[Latest Topics](latest/index.md)** - Browse chronologically")
        lines.append(
            "- **[Top Topics](top/replies/index.md)** - Most active conversations"
        )
        if self.include_users:
            lines.append(
                "- **[User Directory](users/index.md)** - Browse by contributor"
            )
        lines.append("")

        # How to Browse section
        lines.append("## How to Browse")
        lines.append("")
        lines.append("This archive is completely self-contained:")
        lines.append("")
        lines.append("- ✅ **Works offline** - No internet connection required")
        lines.append(
            "- ✅ **Browse on GitHub** - Click through files in the repository"
        )
        lines.append("- **GitHub Pages** - Enable in Settings for a web interface")
        lines.append("- **Local viewing** - Clone and open files in any text editor")
        lines.append("")
        lines.append(
            "Start with **[index.md](index.md)** for the best browsing experience."
        )
        lines.append("")

        # About Chronicon footer
        lines.append("## About Chronicon")
        lines.append("")
        lines.append(
            "This archive was generated using"
            " [Chronicon](https://github.com/19-84/chronicon) -"
            " a multi-format Discourse forum archiving tool that"
            " creates portable, offline-ready archives in HTML,"
            " Markdown, and GitHub-flavored formats."
        )
        lines.append("")

        # Write README
        readme_path = self.output_dir / "README.md"
        readme_path.write_text("\n".join(lines), encoding="utf-8")

    def convert_html_to_gfm(self, html: str, topic_id: int) -> str:
        """
        Convert HTML to GitHub-flavored markdown.

        Args:
            html: HTML content
            topic_id: Topic ID for asset organization

        Returns:
            GitHub-flavored markdown
        """
        if not html or not html.strip():
            return ""

        # Clean up lightbox metadata BEFORE conversion to prevent visible text
        html = self._clean_lightbox_metadata(html)

        # Enhance emoji with Unicode characters before conversion
        html = self._enhance_emoji_for_markdown(html)

        # Rewrite image URLs to local asset paths
        html = self._handle_images(html, topic_id)

        # Convert using html2text
        markdown = self.html_converter.handle(html)

        # Clean up excessive whitespace
        markdown = markdown.strip()

        return markdown

    def _clean_lightbox_metadata(self, html: str) -> str:
        """
        Remove lightbox metadata divs to prevent them appearing as text in markdown.

        Discourse wraps images in lightbox divs with visible metadata like:
        <div class="meta">
          <span class="filename">Screenshot.png</span>
          <span class="informations">1920×1325 92 KB</span>
        </div>

        This gets converted to visible text by html2text. We remove it and move
        the info to alt/title attributes instead.

        Args:
            html: HTML content

        Returns:
            HTML with lightbox metadata removed
        """
        if not html:
            return html

        soup = BeautifulSoup(html, "html.parser")

        # Find all lightbox wrappers
        for lightbox in soup.find_all("div", class_="lightbox-wrapper"):
            img = lightbox.find("img")
            meta_div = lightbox.find("div", class_="meta")

            if img and meta_div:
                # Extract metadata text
                filename_span = meta_div.find("span", class_="filename")
                info_span = meta_div.find("span", class_="informations")

                filename = filename_span.get_text(strip=True) if filename_span else ""
                info_span.get_text(strip=True) if info_span else ""

                # Update image alt text with just the filename (not the dimensions)
                if filename:
                    img["alt"] = filename
                    img["title"] = filename

                # Remove the metadata div completely (prevents text conversion)
                meta_div.decompose()

        return str(soup)

    def _enhance_emoji_for_markdown(self, html: str) -> str:
        """
        Replace emoji images with Unicode characters for better accessibility.

        Args:
            html: HTML content with emoji images

        Returns:
            HTML with emoji images replaced by Unicode characters
        """
        if not html:
            return html

        soup = BeautifulSoup(html, "html.parser")

        # Find all emoji images
        for img in soup.find_all("img", class_="emoji"):
            # Get shortcode from title or alt attribute
            shortcode = img.get("title") or img.get("alt") or ""

            # Ensure shortcode has colons
            if shortcode and not shortcode.startswith(":"):
                shortcode = f":{shortcode}:"

            # Check if we have a Unicode mapping for this emoji
            if shortcode and has_unicode_emoji(shortcode):
                unicode_emoji = get_unicode_emoji(shortcode)

                # Replace the img tag with the Unicode emoji
                img.replace_with(unicode_emoji)

        return str(soup)

    def _handle_images(self, html: str, topic_id: int) -> str:
        """
        Rewrite image and anchor URLs to local asset paths from the DB.

        Rewrites both ``<img src>`` and ``<a href>`` (lightbox links) so that
        the resulting markdown references local files instead of remote CDNs.

        Args:
            html: HTML content
            topic_id: Topic ID for organizing images

        Returns:
            HTML with rewritten image/anchor URLs
        """
        soup = BeautifulSoup(html, "html.parser")

        # Build lookup map from topic-specific assets
        topic_assets: dict[str, str] = {}
        try:
            for asset in self.db.get_assets_for_topic(topic_id):
                topic_assets[asset["url"]] = asset["local_path"]
        except Exception:
            pass

        # Representative topic dir for relative path computation.
        # Topic files live at: output_dir/t/{slug}/{id}.md
        # We only need the correct depth (2 levels below output_dir).
        topic_dir = (self.output_dir / "t" / "_").resolve()

        # Rewrite <img src> attributes
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src or src.startswith("data:"):
                continue
            # Normalize protocol-relative URLs
            if src.startswith("//"):
                src = "https:" + src
            if not src.startswith("http"):
                continue
            rel = self._resolve_asset_url(src, topic_id, topic_assets, topic_dir)
            if rel:
                img["src"] = rel

        # Rewrite <a> href attributes that point to downloadable assets
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if href.startswith("//"):
                href = "https:" + href
            if not href.startswith("http"):
                continue
            rel = self._resolve_asset_url(href, topic_id, topic_assets, topic_dir)
            if rel:
                anchor["href"] = rel

        return str(soup)

    def _resolve_asset_url(
        self,
        url: str,
        topic_id: int,
        topic_assets: dict[str, str],
        topic_dir: Path,
    ) -> str | None:
        """
        Resolve a remote URL to a relative local asset path.

        Tries topic-scoped DB lookup, global DB lookup, then download fallback.

        Returns:
            Relative path string, or None if the asset is not available locally.
        """
        # 1. Topic-specific asset lookup
        local_path_str = topic_assets.get(url)

        # 2. Global asset lookup (emoji, site assets, cross-topic images)
        if not local_path_str:
            with contextlib.suppress(Exception):
                local_path_str = self.db.get_asset_path(url)

        # 3. Filename-based fallback within topic assets
        #    Handles CDN hostname mismatches (e.g. S3 vs CloudFront) and
        #    original-vs-optimized variants (base hash matches with a
        #    resolution suffix like _2_690x351).
        if not local_path_str:
            filename = url.split("/")[-1].split("?")[0]
            if filename:
                stem = Path(filename).stem
                for _u, path in topic_assets.items():
                    pname = Path(path).name
                    if pname == filename or pname.startswith(stem):
                        local_path_str = path
                        break

        # 4. Fallback: download if asset_downloader is available
        if not local_path_str and self.asset_downloader:
            try:
                downloaded = self.asset_downloader.download_image(url, topic_id)
                if downloaded:
                    local_path_str = str(downloaded)
            except Exception as e:
                log.debug(f"Error downloading image {url}: {e}")

        if not local_path_str:
            return None

        asset_path = Path(local_path_str).resolve()
        if asset_path.exists():
            return os.path.relpath(asset_path, topic_dir)

        log.debug(f"Asset file not found: {local_path_str}")
        return None

    def export_users_by_username(self, usernames: set[str]) -> None:
        """
        Regenerate profile pages for specific users only (for incremental updates).

        Also regenerates the users index since post counts may have changed.

        Args:
            usernames: Set of usernames whose profile pages need regeneration
        """
        if not self.include_users:
            return

        if not usernames:
            log.info("No users to regenerate")
            return

        log.info(f"Regenerating {len(usernames)} user markdown profiles...")

        user_dir = self.output_dir / "users"
        user_dir.mkdir(parents=True, exist_ok=True)

        regenerated = 0
        for username in usernames:
            user = self.db.get_user_by_username(username)
            if user is None:
                log.debug(f"User '{username}' not found in database, skipping")
                continue

            user_posts_data = self.db.get_user_posts(user.id, limit=100)
            post_count = self.db.get_user_post_count(user.id)

            lines = []

            # Navigation header
            nav_home = "../index.md"
            nav_latest = "../latest/index.md"
            nav_top = "../top/replies/index.md"
            nav_users = "../users/index.md"

            lines.append(
                f"[Home]({nav_home}) | [Latest]({nav_latest}) | "
                f"[Top]({nav_top}) | [Users]({nav_users})"
            )
            lines.append("")

            lines.append(f"[Home]({nav_home}) > [Users]({nav_users}) > {user.username}")
            lines.append("")
            lines.append("---")
            lines.append("")

            lines.append(f"# {user.username}")
            lines.append("")

            lines.append(f"> **Name:** {user.name or user.username}")
            lines.append(f"> **Trust Level:** {user.trust_level}")
            if user.created_at:
                lines.append(
                    f"> **Member Since:** {user.created_at.strftime('%Y-%m-%d')}"
                )
            lines.append(f"> **Total Posts:** {post_count}")
            lines.append("")
            lines.append("---")
            lines.append("")

            if not user_posts_data:
                lines.append("*No posts found for this user.*")
            else:
                recent_count = min(len(user_posts_data), 100)
                lines.append(f"## Recent Posts ({recent_count} of {post_count})")
                lines.append("")

                for post_data in user_posts_data:
                    post = post_data["post"]
                    topic_id = post_data["topic_id"]
                    topic_title = post_data["topic_title"]

                    topic = self.db.get_topic(topic_id)
                    if not topic:
                        continue

                    topic_link = f"../t/{topic.slug}/{topic_id}.md"

                    lines.append(f"### [{topic_title}]({topic_link})")
                    posted_date = post.created_at.strftime("%Y-%m-%d %H:%M")
                    lines.append(f"*Posted: {posted_date} | Post #{post.post_number}*")
                    lines.append("")

                    content = self.convert_html_to_gfm(post.cooked, topic_id)
                    excerpt = content[:200] + "..." if len(content) > 200 else content
                    lines.append(excerpt)
                    lines.append("")
                    lines.append("---")
                    lines.append("")

            user_path = user_dir / f"{user.username}.md"
            user_path.write_text("\n".join(lines), encoding="utf-8")
            regenerated += 1

        log.info(f"Regenerated {regenerated} user markdown profiles")

        # Regenerate users index since post counts may have changed
        if regenerated > 0:
            self.generate_users_index()

    def export_topics(self, topic_ids: list[int]) -> None:
        """
        Regenerate specific topics only (for incremental updates).

        Args:
            topic_ids: List of topic IDs to regenerate
        """
        if not topic_ids:
            log.info("No topics to regenerate")
            return

        log.info(f"Regenerating {len(topic_ids)} GitHub markdown files...")

        topics = self.db.get_topics_by_ids(topic_ids)
        if not topics:
            log.warning("None of the requested topics were found in database")
            return

        for topic in topics:
            topic_path = self.export_topic(topic)
            log.debug(f"Regenerated {topic_path}")

        log.info(f"Regenerated {len(topics)} GitHub markdown files")

    def update_index(self) -> None:
        """
        Update README.md landing page (for incremental updates).

        Regenerates README with updated archive statistics.
        """
        log.info("Updating README.md...")

        self.generate_readme()

        log.info("README.md updated")
