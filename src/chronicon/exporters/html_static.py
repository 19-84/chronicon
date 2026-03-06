# ABOUTME: Static HTML exporter for Chronicon
# ABOUTME: Generates fully offline-viewable HTML archive with preserved themes

"""Generate static HTML site from database."""

import math
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..processors.html_parser import HTMLProcessor
from ..utils.logger import get_logger
from ..utils.search_indexer import SearchIndexer
from ..utils.seo import (
    generate_category_og_tags,
    generate_homepage_json_ld,
    generate_homepage_og_tags,
    generate_json_ld,
    generate_keywords,
    generate_meta_description,
    generate_og_tags,
    generate_twitter_card,
)
from .base import BaseExporter

log = get_logger(__name__)

# Pagination constants
TOPICS_PER_INDEX_PAGE = 50
TOPICS_PER_CATEGORY_PAGE = 50


class HTMLStaticExporter(BaseExporter):
    """Generate static HTML site from database."""

    def __init__(
        self,
        db,
        output_dir: Path,
        template_dir: Path | None = None,
        include_users: bool = False,
        config: dict | None = None,
        posts_per_page: int = 50,
        pagination_enabled: bool = True,
        progress=None,
        search_backend: str = "fts",
    ):
        """
        Initialize HTML static exporter.

        Args:
            db: ArchiveDatabase instance
            output_dir: Output directory
            template_dir: Directory containing Jinja2 templates
            include_users: Whether to generate user profile pages
            config: Optional configuration dict with canonical_base_url
            posts_per_page: Number of posts per page (default: 50)
            pagination_enabled: Whether to enable pagination (default: True)
            progress: Optional Rich Progress object for progress tracking
            search_backend: Search backend mode - "static" or "fts" (default)
        """
        super().__init__(db, output_dir, progress=progress)
        self.include_users = include_users
        self.config = config or {}
        self.posts_per_page = posts_per_page
        self.pagination_enabled = pagination_enabled
        self.search_backend = search_backend

        # Get canonical base URL from config if provided
        self.canonical_base_url = None
        if config and "export" in config:
            self.canonical_base_url = config["export"].get("canonical_base_url")

        # Initialize HTML processor for URL rewriting
        self.html_processor = HTMLProcessor()

        # Set up template directory
        if template_dir is None:
            # Use default templates directory
            package_dir = Path(__file__).parent.parent.parent.parent
            self.template_dir = package_dir / "templates"
        else:
            self.template_dir = Path(template_dir)

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date

        # Add global functions for relative path calculation
        self.env.globals["rel_path"] = self._rel_path
        self.env.globals["asset_path"] = self._asset_path

        # Add site metadata to globals (available to all templates)
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        self.env.globals["site_title"] = site_meta.get("site_title", "Forum Archive")
        self.env.globals["logo_url"] = site_meta.get("logo_url")

        # Add helper functions for local asset paths
        self.env.globals["get_local_logo"] = self._get_local_logo
        self.env.globals["get_local_banner"] = self._get_local_banner
        self.env.globals["get_local_avatar"] = self._get_local_avatar

        # Add version information
        self.env.globals["chronicon_version"] = self._get_version()
        self.env.globals["chronicon_repo"] = "https://github.com/19-84/chronicon"

        # Add search backend mode to globals
        self.env.globals["search_backend"] = self.search_backend

    def _get_version(self) -> str:
        """Get Chronicon version from package metadata."""
        try:
            from importlib.metadata import version

            return version("chronicon")
        except Exception:
            # Fallback if package not installed or version unavailable
            return "1.0.0"

    def _format_date(self, dt) -> str:
        """Format datetime for display."""
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M")

    def _rel_path(self, target: str, depth: int = 0) -> str:
        """
        Calculate relative path from current page to target.

        Args:
            target: Target path (e.g., "index.html", "search.html")
            depth: Depth of current page (0=root, 1=users/, 2=categories/*/or topics/*/)

        Returns:
            Relative path with appropriate ../ prefixes
        """
        if depth == 0:
            return target
        return "../" * depth + target

    def _asset_path(self, asset: str, depth: int = 0) -> str:
        """
        Calculate relative path to an asset.

        Args:
            asset: Asset path relative to assets dir (e.g., "css/archive.css")
            depth: Depth of current page

        Returns:
            Relative path to asset
        """
        if depth == 0:
            return f"assets/{asset}"
        return "../" * depth + f"assets/{asset}"

    def _get_topic_author_username(self, topic) -> str:
        """
        Get the username of the topic author.

        Tries topic.user_id first, then falls back to getting the first post's username.

        Args:
            topic: Topic object

        Returns:
            Username string, or "Unknown" if not found
        """
        # Try topic.user_id first
        if topic.user_id:
            user = self.db.get_user(topic.user_id)
            if user:
                return user.username

        # Fall back to first post's username
        posts = self.db.get_topic_posts(topic.id)
        if posts and posts[0].username:
            return posts[0].username

        return "Unknown"

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

    def _get_local_logo(self, depth: int = 0) -> str | None:
        """
        Get local relative path to site logo (if downloaded).

        Args:
            depth: Page depth for calculating relative path

        Returns:
            Relative path to local logo, or None if not available
        """
        site_url = self._get_site_url()
        if not site_url:
            return None

        # Get logo URL from metadata
        site_meta = self.db.get_site_metadata(site_url)
        logo_url = site_meta.get("logo_url")
        if not logo_url:
            return None

        # Get local path from assets table
        local_path = self.db.get_asset_path(logo_url)
        if not local_path:
            return None

        # Convert absolute local path to relative path for HTML
        # local_path is like: /path/to/archives/assets/site/logo.png
        # We want: assets/site/logo.png (or ../assets/site/logo.png for depth > 0)
        from pathlib import Path

        local_path_obj = Path(local_path)

        # Extract the relative path from the assets directory
        try:
            # Find 'assets' in the path
            parts = local_path_obj.parts
            assets_idx = parts.index("assets")
            rel_parts = parts[assets_idx:]
            asset_rel_path = "/".join(rel_parts)

            # Apply depth prefix
            if depth == 0:
                return asset_rel_path
            return "../" * depth + asset_rel_path
        except (ValueError, IndexError):
            # Fallback: just use filename
            return self._asset_path(f"site/{local_path_obj.name}", depth)

    def _get_local_banner(self, depth: int = 0) -> str | None:
        """
        Get local relative path to site banner (if downloaded).

        Args:
            depth: Page depth for calculating relative path

        Returns:
            Relative path to local banner, or None if not available
        """
        site_url = self._get_site_url()
        if not site_url:
            return None

        # Get banner URL from metadata
        site_meta = self.db.get_site_metadata(site_url)
        banner_url = site_meta.get("banner_image_url")
        if not banner_url:
            return None

        # Get local path from assets table
        local_path = self.db.get_asset_path(banner_url)
        if not local_path:
            return None

        # Convert absolute local path to relative path for HTML
        from pathlib import Path

        local_path_obj = Path(local_path)

        # Extract the relative path from the assets directory
        try:
            # Find 'assets' in the path
            parts = local_path_obj.parts
            assets_idx = parts.index("assets")
            rel_parts = parts[assets_idx:]
            asset_rel_path = "/".join(rel_parts)

            # Apply depth prefix
            if depth == 0:
                return asset_rel_path
            return "../" * depth + asset_rel_path
        except (ValueError, IndexError):
            # Fallback: just use filename
            return self._asset_path(f"site/{local_path_obj.name}", depth)

    def _get_local_avatar(self, user_id: int, depth: int = 0) -> str | None:
        """
        Get local relative path to user avatar (if downloaded).

        Args:
            user_id: User ID
            depth: Page depth for calculating relative path

        Returns:
            Relative path to local avatar, or None if not available
        """
        user = self.db.get_user(user_id)
        if not user or not user.local_avatar_path:
            return None

        # Convert absolute local path to relative path for HTML
        from pathlib import Path

        local_path_obj = Path(user.local_avatar_path)

        # Extract the relative path from the assets directory
        try:
            # Find 'assets' in the path
            parts = local_path_obj.parts
            assets_idx = parts.index("assets")
            rel_parts = parts[assets_idx:]
            asset_rel_path = "/".join(rel_parts)

            # Apply depth prefix
            if depth == 0:
                return asset_rel_path
            return "../" * depth + asset_rel_path
        except (ValueError, IndexError):
            # Fallback: just use filename
            return self._asset_path(f"avatars/{local_path_obj.name}", depth)

    def _generate_topic_seo_context(self, topic, posts, category) -> dict:
        """
        Generate SEO context for a topic.

        Args:
            topic: Topic object
            posts: List of Post objects
            category: Category object or None

        Returns:
            Dictionary with SEO metadata fields
        """
        # Get site metadata
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        site_title = site_meta.get("site_title", "Forum Archive")

        # Generate canonical URL if configured (Discourse-compatible, no .html)
        canonical_url = None
        if self.canonical_base_url:
            canonical_url = f"{self.canonical_base_url}/t/{topic.slug}/{topic.id}"

        # Get author name from first post
        author_name = posts[0].username if posts else "Unknown"

        # Get local path for topic SEO image if it was downloaded
        # OG/Twitter/JSON-LD require absolute URLs for social crawlers
        local_image_path = None
        if topic.image_url:
            local_path_abs = self.db.get_asset_path(topic.image_url)
            if local_path_abs and self.canonical_base_url:
                from pathlib import Path

                local_path_obj = Path(local_path_abs)
                try:
                    parts = local_path_obj.parts
                    assets_idx = parts.index("assets")
                    rel_parts = parts[assets_idx:]
                    local_image_path = (
                        f"{self.canonical_base_url}/{'/'.join(rel_parts)}"
                    )
                except (ValueError, IndexError):
                    local_image_path = None

        # Generate SEO metadata with local image path
        meta_description = generate_meta_description(topic, posts)
        keywords = generate_keywords(topic)
        og_tags = generate_og_tags(topic, site_title, canonical_url, local_image_path)
        twitter_tags = generate_twitter_card(topic, local_image_path)
        json_ld = generate_json_ld(
            topic, category, posts, site_url or "", local_image_path
        )

        return {
            "meta_description": meta_description,
            "keywords": keywords,
            "author_name": author_name,
            "og_tags": og_tags,
            "twitter_tags": twitter_tags,
            "json_ld": json_ld,
            "canonical_url": canonical_url,
            "site_description": site_meta.get("site_description", ""),
        }

    def _generate_topic_page(
        self,
        topic,
        page_num: int,
        total_pages: int,
        posts: list,
        category,
        template,
        seo_context: dict,
    ) -> str:
        """
        Generate HTML for a single topic page.

        Args:
            topic: Topic object
            page_num: Current page number (1-indexed)
            total_pages: Total number of pages
            posts: List of Post objects for this page
            category: Category object or None
            template: Jinja2 template
            seo_context: SEO metadata dictionary

        Returns:
            Path to the generated HTML file
        """
        # Determine canonical URL for this specific page
        canonical_url = seo_context.get("canonical_url")
        if canonical_url and page_num > 1:
            # Update canonical URL for paginated pages
            canonical_url = f"{canonical_url}/page-{page_num}.html"

        # Create pagination context
        pagination = {
            "current_page": page_num,
            "total_pages": total_pages,
            "has_prev": page_num > 1,
            "has_next": page_num < total_pages,
            "prev_page": page_num - 1,
            "next_page": page_num + 1,
        }

        # Update SEO context for pagination
        page_seo_context = seo_context.copy()
        if page_num > 1:
            # Adjust title for paginated pages
            page_seo_context["canonical_url"] = canonical_url

        # Get source URL for linking back to original posts
        source_url = self._get_site_url()

        # Render template
        html = template.render(
            topic=topic,
            posts=posts,
            category=category,
            pagination=pagination,
            depth=3,  # /t/{slug}/{id}/index.html - 3 levels deep
            source_url=source_url,  # For linking to original Discourse posts
            **page_seo_context,  # Include SEO metadata
        )

        # Determine file path: /t/{slug}/{id}/index.html (Discourse-compatible)
        topic_id_dir = self.output_dir / "t" / topic.slug / str(topic.id)
        topic_id_dir.mkdir(parents=True, exist_ok=True)

        if page_num == 1:
            topic_path = topic_id_dir / "index.html"
        else:
            topic_path = topic_id_dir / f"page-{page_num}.html"

        # Write to file
        topic_path.write_text(html, encoding="utf-8")
        return str(topic_path)

    def export(self) -> None:
        """Main export orchestration."""
        main_task = None
        if self.progress:
            # Calculate total steps for progress tracking
            # Base steps: index, latest, top, categories, topics, assets
            total_steps = 6
            if self.search_backend == "static":
                total_steps += 2  # search page + search index
            if self.include_users:
                total_steps += 2  # users index + user detail pages
            main_task = self.progress.add_task(
                "[cyan]Exporting HTML...", total=total_steps
            )

        # Generate all pages
        self.generate_index()
        if self.progress:
            self.progress.advance(main_task, 1)

        # Only generate search page and index for static mode
        if self.search_backend == "static":
            self.generate_search_page()
            if self.progress:
                self.progress.advance(main_task, 1)

        # Generate topic indexes
        self.generate_latest_index()
        if self.progress:
            self.progress.advance(main_task, 1)

        self.generate_top_indexes()
        if self.progress:
            self.progress.advance(main_task, 1)

        self.generate_categories()
        if self.progress:
            self.progress.advance(main_task, 1)

        self.generate_topics()
        if self.progress:
            self.progress.advance(main_task, 1)

        if self.include_users:
            self.generate_users_index()
            if self.progress:
                self.progress.advance(main_task, 1)

            self.generate_users()
            if self.progress:
                self.progress.advance(main_task, 1)

        # Generate search index (only for static mode)
        if self.search_backend == "static":
            self.generate_search_index()
            if self.progress:
                self.progress.advance(main_task, 1)

        # Copy static assets
        self.copy_assets()

        # Generate sitemap.xml and robots.txt
        self.generate_sitemap()
        self.generate_robots_txt()

        if self.progress:
            self.progress.advance(main_task, 1)
            self.progress.update(main_task, description="[green]✓ HTML export complete")

    def generate_index(self) -> None:
        """Generate homepage."""

        # Get data for homepage
        stats = self.db.get_statistics()
        archive_stats = self.db.get_archive_statistics()
        categories = self.db.get_all_categories()
        recent_topics = self.db.get_recent_topics(limit=7)

        # Get top 7 topics by views
        top_views = self.db.get_topics_paginated(
            page=1, per_page=7, order_by="views", order_dir="DESC"
        )

        # Get top 7 topics by replies (posts_count)
        top_replies = self.db.get_topics_paginated(
            page=1, per_page=7, order_by="posts_count", order_dir="DESC"
        )

        # Add username and category to recent topics
        for topic in recent_topics:
            topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]
            if topic.category_id:
                topic.category = self.db.get_category(topic.category_id)  # type: ignore[attr-defined]
            else:
                topic.category = None  # type: ignore[attr-defined]

        # Add username and category to top views
        for topic in top_views:
            topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]
            if topic.category_id:
                topic.category = self.db.get_category(topic.category_id)  # type: ignore[attr-defined]
            else:
                topic.category = None  # type: ignore[attr-defined]

        # Add username and category to top replies
        for topic in top_replies:
            topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]
            if topic.category_id:
                topic.category = self.db.get_category(topic.category_id)  # type: ignore[attr-defined]
            else:
                topic.category = None  # type: ignore[attr-defined]

        # Get site metadata for banner/hero section
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        site_title = site_meta.get("site_title", "Forum Archive")
        site_description = site_meta.get("site_description", "")
        logo_url = site_meta.get("logo_url")
        source_url = site_meta.get("site_url", site_url or "")

        # Resolve logo to absolute URL for OG tags if canonical URL is set
        og_logo_url = logo_url
        if logo_url and self.canonical_base_url:
            local_logo_path = self.db.get_asset_path(logo_url)
            if local_logo_path:
                local_path_obj = Path(local_logo_path)
                try:
                    parts = local_path_obj.parts
                    assets_idx = parts.index("assets")
                    rel_parts = parts[assets_idx:]
                    og_logo_url = f"{self.canonical_base_url}/{'/'.join(rel_parts)}"
                except (ValueError, IndexError):
                    pass  # Keep original logo_url

        # Prepare date range
        date_range = None
        if archive_stats.get("earliest_topic") and archive_stats.get("latest_topic"):
            date_range = {
                "start": archive_stats["earliest_topic"][:10],  # YYYY-MM-DD
                "end": archive_stats["latest_topic"][:10],
            }

        # Get top 5 contributors
        top_contributors = archive_stats.get("top_contributors", [])[:5]

        # Generate canonical URL if configured
        canonical_url = None
        if self.canonical_base_url:
            canonical_url = self.canonical_base_url

        # Generate homepage Open Graph tags
        og_tags = generate_homepage_og_tags(
            site_title, site_description, og_logo_url, canonical_url
        )

        # Generate homepage JSON-LD
        json_ld = generate_homepage_json_ld(
            site_title, site_description, canonical_url, og_logo_url
        )

        # Render template
        template = self.env.get_template("index.html")
        html = template.render(
            statistics=stats,
            categories=categories,
            recent_topics=recent_topics,
            top_views=top_views,
            top_replies=top_replies,
            top_contributors=top_contributors,
            site_title=site_title,
            site_description=site_description,
            source_url=source_url,
            date_range=date_range,
            banner_image_url=site_meta.get("banner_image_url"),
            og_tags=og_tags,
            twitter_tags={
                "twitter:card": "summary",
                "twitter:title": site_title,
                "twitter:description": site_description,
            }
            if site_description
            else {},
            json_ld=json_ld,
            canonical_url=canonical_url,
            archiver_version=self._get_version(),
            discourse_version=site_meta.get("discourse_version"),
            depth=0,  # Root level
        )

        # Write to file
        index_path = self.output_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")

    def generate_search_page(self) -> None:
        """Generate search page."""

        # Get site metadata for description
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        site_title = site_meta.get("site_title", "Forum Archive")

        # Generate meta description for search page
        total_topics = self.db.get_topics_count()
        total_posts = self.db.get_statistics().get("total_posts", 0)
        meta_description = (
            f"Search {total_topics} topics and {total_posts} posts in "
            f"the {site_title} archive. Find discussions, answers, and "
            "community content."
        )

        # Render template
        template = self.env.get_template("search.html")
        html = template.render(
            depth=0,  # Root level
            meta_description=meta_description,
            site_title=site_title,
        )

        # Write to file
        search_path = self.output_dir / "search.html"
        search_path.write_text(html, encoding="utf-8")

    def generate_about_page(self) -> None:
        """Generate About page with archive statistics and information."""

        # Get extended statistics for About page
        stats = self.db.get_archive_statistics()

        # Get site metadata
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        # Render template
        template = self.env.get_template("about.html")
        html = template.render(
            site_title=site_meta.get("site_title", "Forum Archive"),
            site_description=site_meta.get("site_description", ""),
            source_url=site_meta.get("site_url", site_url or ""),
            banner_image=site_meta.get("banner_image_url"),
            discourse_version=site_meta.get("discourse_version"),
            contact_email=site_meta.get("contact_email"),
            statistics=stats,
            depth=0,  # Root level
        )

        # Write to file
        about_path = self.output_dir / "about.html"
        about_path.write_text(html, encoding="utf-8")

    def generate_categories(self) -> None:
        """Generate category pages with pagination."""

        categories = self.db.get_all_categories()
        template = self.env.get_template("category.html")

        for category in categories:
            # Get total topic count for pagination
            total_topics = category.topic_count
            total_pages = (
                math.ceil(total_topics / TOPICS_PER_CATEGORY_PAGE)
                if total_topics > 0
                else 1
            )

            # Generate each page
            for page_num in range(1, total_pages + 1):
                # Get topics for this page
                topics = self.db.get_category_topics_paginated(
                    category.id, page_num, TOPICS_PER_CATEGORY_PAGE
                )

                # Add username to topics
                for topic in topics:
                    topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]

                # Generate SEO context for category
                site_url = self._get_site_url()
                site_meta = {}
                if site_url:
                    site_meta = self.db.get_site_metadata(site_url)

                site_title = site_meta.get("site_title", "Forum Archive")
                site_description = site_meta.get("site_description", "")

                # Generate canonical URL if configured
                canonical_url = None
                if self.canonical_base_url:
                    if page_num == 1:
                        canonical_url = (
                            f"{self.canonical_base_url}/c/{category.slug}/"
                            f"{category.id}/index.html"
                        )
                    else:
                        canonical_url = (
                            f"{self.canonical_base_url}/c/{category.slug}/"
                            f"{category.id}/page-{page_num}.html"
                        )

                # Generate category Open Graph tags
                og_tags = generate_category_og_tags(category, site_title, canonical_url)

                # Generate meta description for category
                if category.description:
                    category_description_text = category.description[
                        :150
                    ]  # Limit to 150 chars
                    meta_description = (
                        f"{category.name} - {category_description_text}. "
                        f"Browse {category.topic_count} topics."
                    )
                else:
                    meta_description = (
                        f"Browse {category.topic_count} topics in "
                        f"{category.name} category from {site_title}."
                    )

                # Update for paginated pages
                if page_num > 1:
                    meta_description = (
                        f"{category.name} - Page {page_num}. {meta_description}"
                    )

                # Create pagination context
                pagination = (
                    {
                        "current_page": page_num,
                        "total_pages": total_pages,
                        "has_prev": page_num > 1,
                        "has_next": page_num < total_pages,
                        "prev_page": page_num - 1,
                        "next_page": page_num + 1,
                    }
                    if total_pages > 1
                    else None
                )

                # Render template
                html = template.render(
                    category=category,
                    topics=topics,
                    pagination=pagination,
                    depth=3,  # /c/{slug}/{id}/index.html
                    site_description=site_description,
                    meta_description=meta_description,
                    og_tags=og_tags,
                    canonical_url=canonical_url,
                )

                # Create category directory using Discourse-compatible
                # structure: /c/{slug}/{id}/
                category_dir = self.output_dir / "c" / category.slug / str(category.id)
                category_dir.mkdir(parents=True, exist_ok=True)

                # Write page file
                if page_num == 1:
                    category_path = category_dir / "index.html"
                else:
                    category_path = category_dir / f"page-{page_num}.html"

                category_path.write_text(html, encoding="utf-8")

    def generate_latest_index(self) -> None:
        """Generate paginated index of topics by date (most recent first)."""

        total_topics = self.db.get_topics_count()
        total_pages = (
            math.ceil(total_topics / TOPICS_PER_INDEX_PAGE) if total_topics > 0 else 1
        )

        template = self.env.get_template("topic_index.html")

        # Create /latest/ directory
        latest_dir = self.output_dir / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            # Get topics for this page, sorted by created_at DESC
            topics = self.db.get_topics_paginated(
                page_num, TOPICS_PER_INDEX_PAGE, order_by="created_at", order_dir="DESC"
            )

            # Add username and category to each topic
            for topic in topics:
                topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]
                if topic.category_id:
                    topic.category = self.db.get_category(topic.category_id)  # type: ignore[attr-defined]
                else:
                    topic.category = None  # type: ignore[attr-defined]

            # Create pagination context
            pagination = (
                {
                    "current_page": page_num,
                    "total_pages": total_pages,
                    "has_prev": page_num > 1,
                    "has_next": page_num < total_pages,
                    "prev_page": page_num - 1,
                    "next_page": page_num + 1,
                }
                if total_pages > 1
                else None
            )

            # Render template
            html = template.render(
                page_title="Latest Topics",
                page_description="Browse topics by date",
                topics=topics,
                pagination=pagination,
                base_path="latest",
                depth=1,  # /latest/index.html
            )

            # Write page file
            if page_num == 1:
                page_path = latest_dir / "index.html"
            else:
                page_path = latest_dir / f"page-{page_num}.html"

            page_path.write_text(html, encoding="utf-8")

        log.info(f"Generated {total_pages} pages for latest topics index")

    def generate_top_indexes(self) -> None:
        """Generate paginated indexes for top topics (by replies and by views)."""

        # Create /top/ directory
        top_dir = self.output_dir / "top"
        top_dir.mkdir(parents=True, exist_ok=True)

        # Generate default /top/index.html that redirects to replies
        default_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=replies/index.html">
    <title>Top Topics</title>
</head>
<body>
    <p>Redirecting to <a href="replies/index.html">top topics by replies</a>...</p>
</body>
</html>"""
        (top_dir / "index.html").write_text(default_html, encoding="utf-8")

        # Generate top by replies
        self._generate_top_index(
            "replies", "posts_count", "Top Topics by Replies", "Most discussed topics"
        )

        # Generate top by views
        self._generate_top_index(
            "views", "views", "Top Topics by Views", "Most viewed topics"
        )

    def _generate_top_index(
        self, index_name: str, order_by: str, page_title: str, page_description: str
    ) -> None:
        """Helper to generate a specific top topics index."""

        total_topics = self.db.get_topics_count()
        total_pages = (
            math.ceil(total_topics / TOPICS_PER_INDEX_PAGE) if total_topics > 0 else 1
        )

        template = self.env.get_template("topic_index.html")

        # Create subdirectory
        index_dir = self.output_dir / "top" / index_name
        index_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            # Get topics for this page, sorted by specified column DESC
            topics = self.db.get_topics_paginated(
                page_num, TOPICS_PER_INDEX_PAGE, order_by=order_by, order_dir="DESC"
            )

            # Add username and category to each topic
            for topic in topics:
                topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]
                if topic.category_id:
                    topic.category = self.db.get_category(topic.category_id)  # type: ignore[attr-defined]
                else:
                    topic.category = None  # type: ignore[attr-defined]

            # Create pagination context
            pagination = (
                {
                    "current_page": page_num,
                    "total_pages": total_pages,
                    "has_prev": page_num > 1,
                    "has_next": page_num < total_pages,
                    "prev_page": page_num - 1,
                    "next_page": page_num + 1,
                }
                if total_pages > 1
                else None
            )

            # Render template
            html = template.render(
                page_title=page_title,
                page_description=page_description,
                topics=topics,
                pagination=pagination,
                base_path=f"top/{index_name}",
                depth=2,  # /top/{index_name}/index.html
            )

            # Write page file
            if page_num == 1:
                page_path = index_dir / "index.html"
            else:
                page_path = index_dir / f"page-{page_num}.html"

            page_path.write_text(html, encoding="utf-8")

        log.info(f"Generated {total_pages} pages for top/{index_name} index")

    def generate_topics(self) -> None:
        """Generate topic pages with pagination support."""

        topics = self.db.get_all_topics()
        template = self.env.get_template("topic.html")
        total_pages_generated = 0

        for topic in topics:
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

                    # Process post HTML to rewrite image URLs using asset registry
                    for post in posts:
                        if post.cooked:
                            post.cooked = (
                                self.html_processor.rewrite_with_full_resolution_links(
                                    post.cooked, topic.id, self.db, page_depth=3
                                )
                            )
                            # Enhance emoji with Unicode fallbacks
                            post.cooked = (
                                self.html_processor.enhance_emoji_with_unicode(
                                    post.cooked
                                )
                            )
                            # Enhance all image alt text for accessibility
                            post.cooked = (
                                self.html_processor.enhance_all_image_alt_text(
                                    post.cooked
                                )
                            )

                    # Get category info (only once per topic)
                    category = None
                    if topic.category_id:
                        category = self.db.get_category(topic.category_id)

                    # Generate SEO context (use all posts for SEO on first page)
                    if page_num == 1:
                        all_posts = self.db.get_topic_posts(topic.id)
                        seo_context = self._generate_topic_seo_context(
                            topic, all_posts, category
                        )
                    else:
                        seo_context = self._generate_topic_seo_context(
                            topic, posts, category
                        )

                    # Generate the page
                    self._generate_topic_page(
                        topic=topic,
                        page_num=page_num,
                        total_pages=total_pages,
                        posts=posts,
                        category=category,
                        template=template,
                        seo_context=seo_context,
                    )
                    total_pages_generated += 1

            else:
                # Non-paginated mode: single page with all posts
                posts = self.db.get_topic_posts(topic.id)

                # Process post HTML to rewrite image URLs using asset registry
                for post in posts:
                    if post.cooked:
                        post.cooked = (
                            self.html_processor.rewrite_with_full_resolution_links(
                                post.cooked, topic.id, self.db, page_depth=3
                            )
                        )
                        # Enhance emoji with Unicode fallbacks
                        post.cooked = self.html_processor.enhance_emoji_with_unicode(
                            post.cooked
                        )
                        # Enhance all image alt text for accessibility
                        post.cooked = self.html_processor.enhance_all_image_alt_text(
                            post.cooked
                        )

                # Get category info
                category = None
                if topic.category_id:
                    category = self.db.get_category(topic.category_id)

                # Generate SEO context
                seo_context = self._generate_topic_seo_context(topic, posts, category)

                # Generate single page
                self._generate_topic_page(
                    topic=topic,
                    page_num=1,
                    total_pages=1,
                    posts=posts,
                    category=category,
                    template=template,
                    seo_context=seo_context,
                )
                total_pages_generated += 1

    def generate_users(self) -> None:
        """Generate user profile pages with pagination support."""

        users = self.db.get_all_users()
        template = self.env.get_template("user.html")

        user_dir = self.output_dir / "u"
        user_dir.mkdir(parents=True, exist_ok=True)
        total_pages_generated = 0

        # Get site title for meta descriptions
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)
        site_title = site_meta.get("site_title", "Forum Archive")

        for user in users:
            # Get total post count for pagination
            post_count = self.db.get_user_post_count(user.id)

            # Generate meta description
            if post_count == 0:
                meta_description = f"Profile page for {user.username} in {site_title}."
            elif post_count == 1:
                meta_description = (
                    f"{user.username}'s profile - 1 post in {site_title}."
                )
            else:
                meta_description = (
                    f"{user.username}'s profile - {post_count} posts in "
                    f"{site_title}. View discussions and contributions."
                )

            if self.pagination_enabled and post_count > 0:
                # Calculate number of pages needed
                total_pages = math.ceil(post_count / self.posts_per_page)

                # Generate each page
                for page_num in range(1, total_pages + 1):
                    # Get posts for this page
                    user_posts = self.db.get_user_posts_paginated(
                        user.id, page_num, self.posts_per_page
                    )

                    # Create pagination context
                    pagination = (
                        {
                            "current_page": page_num,
                            "total_pages": total_pages,
                            "has_prev": page_num > 1,
                            "has_next": page_num < total_pages,
                            "prev_page": page_num - 1,
                            "next_page": page_num + 1,
                        }
                        if total_pages > 1
                        else None
                    )

                    # Update meta description for paginated pages
                    page_meta_description = meta_description
                    if page_num > 1:
                        page_meta_description = (
                            f"{user.username}'s profile - Page {page_num} of "
                            f"{total_pages}. {post_count} total posts."
                        )

                    # Render template
                    html = template.render(
                        user=user,
                        user_posts=user_posts,
                        post_count=post_count,
                        pagination=pagination,
                        meta_description=page_meta_description,
                        depth=2,  # /u/{username}/index.html
                    )

                    # Determine file path: /u/{username}/index.html
                    user_subdir = user_dir / user.username
                    user_subdir.mkdir(parents=True, exist_ok=True)
                    if page_num == 1:
                        user_path = user_subdir / "index.html"
                    else:
                        user_path = user_subdir / f"page-{page_num}.html"

                    # Write file
                    user_path.write_text(html, encoding="utf-8")
                    total_pages_generated += 1

            else:
                # Non-paginated mode or no posts: single page
                user_posts = self.db.get_user_posts(user.id, limit=50)

                # Render template without pagination
                html = template.render(
                    user=user,
                    user_posts=user_posts,
                    post_count=post_count,
                    pagination=None,
                    meta_description=meta_description,
                    depth=2,  # /u/{username}/index.html
                )

                # Write file: /u/{username}/index.html
                user_subdir = user_dir / user.username
                user_subdir.mkdir(parents=True, exist_ok=True)
                user_path = user_subdir / "index.html"
                user_path.write_text(html, encoding="utf-8")
                total_pages_generated += 1

        log.info(f"Generated {total_pages_generated} user profile pages")

    def generate_users_index(self) -> None:
        """Generate paginated users index sorted by post count."""

        total_users = self.db.get_users_count()
        total_pages = (
            math.ceil(total_users / TOPICS_PER_INDEX_PAGE) if total_users > 0 else 1
        )

        template = self.env.get_template("user_index.html")

        # Create /u/ directory
        users_dir = self.output_dir / "u"
        users_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            # Get users for this page, sorted by post_count DESC
            users = self.db.get_users_with_post_counts(
                page_num, TOPICS_PER_INDEX_PAGE, order_by="post_count", order_dir="DESC"
            )

            # Create pagination context
            pagination = (
                {
                    "current_page": page_num,
                    "total_pages": total_pages,
                    "has_prev": page_num > 1,
                    "has_next": page_num < total_pages,
                    "prev_page": page_num - 1,
                    "next_page": page_num + 1,
                }
                if total_pages > 1
                else None
            )

            # Render template
            html = template.render(
                users=users,
                pagination=pagination,
                base_path="u",
                depth=1,  # /u/index.html
            )

            # Write page file
            if page_num == 1:
                page_path = users_dir / "index.html"
            else:
                page_path = users_dir / f"page-{page_num}.html"

            page_path.write_text(html, encoding="utf-8")

        log.info(f"Generated {total_pages} pages for users index")

    def generate_search_index(self) -> None:
        """Generate search index JSON."""

        indexer = SearchIndexer(self.db)
        search_index_path = self.output_dir / "search_index.json"
        indexer.generate_index(search_index_path)

    def copy_assets(self) -> None:
        """Copy static assets to output (CSS/JS only)."""

        # Get static directory (same parent as templates)
        package_dir = Path(__file__).parent.parent.parent.parent
        static_dir = package_dir / "static"

        # Define target assets directory
        assets_dir = self.output_dir / "assets"

        # Copy CSS/JS/static files to output/assets
        # Only copy if they don't already exist (to avoid overwriting downloaded assets)
        css_dir = assets_dir / "css"
        js_dir = assets_dir / "js"

        # Copy CSS files
        source_css = static_dir / "css"
        if source_css.exists():
            css_dir.mkdir(parents=True, exist_ok=True)
            for css_file in source_css.glob("*.css"):
                dest_file = css_dir / css_file.name
                if not dest_file.exists() or css_file.name == "archive.css":
                    shutil.copy(css_file, dest_file)

        # Copy font files
        source_fonts = static_dir / "fonts"
        if source_fonts.exists():
            fonts_dir = assets_dir / "fonts"
            fonts_dir.mkdir(parents=True, exist_ok=True)
            for font_file in source_fonts.glob("*"):
                if font_file.is_file():
                    dest_file = fonts_dir / font_file.name
                    if not dest_file.exists():
                        shutil.copy(font_file, dest_file)

        # Copy JS files (only for static search mode)
        if self.search_backend == "static":
            source_js = static_dir / "js"
            if source_js.exists():
                js_dir.mkdir(parents=True, exist_ok=True)
                for js_file in source_js.glob("*.js"):
                    dest_file = js_dir / js_file.name
                    if not dest_file.exists():
                        shutil.copy(js_file, dest_file)

        # Copy favicon from its CDN filename to favicon.ico for template compatibility
        site_favicon_dir = assets_dir / "site"
        site_favicon = site_favicon_dir / "favicon.ico"
        if not site_favicon.exists():
            # Favicon was downloaded under its CDN filename — find and copy it
            site_url = self.db.get_first_site_url()
            if site_url:
                site_metadata = self.db.get_site_metadata(site_url)
                favicon_url = site_metadata.get("favicon_url")
                if favicon_url:
                    favicon_local = self.db.get_asset_path(favicon_url)
                    if favicon_local and Path(favicon_local).exists():
                        site_favicon_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy(Path(favicon_local), site_favicon)

        # Copy favicon to root for browser auto-discovery (/favicon.ico)
        if site_favicon.exists():
            root_favicon = self.output_dir / "favicon.ico"
            if not root_favicon.exists():
                shutil.copy(site_favicon, root_favicon)

        # Note: Downloaded assets (images, avatars, emoji, site) are already
        # in output_dir/assets/ from the AssetDownloader in CLI.
        # We don't need to copy them - they're already in the right place.

    def export_topics(self, topic_ids: list[int]) -> None:
        """
        Regenerate specific topics only (for incremental updates).

        Args:
            topic_ids: List of topic IDs to regenerate
        """
        if not topic_ids:
            log.info("No topics to regenerate")
            return

        log.info(f"Regenerating {len(topic_ids)} topics...")

        topics = self.db.get_topics_by_ids(topic_ids)
        if not topics:
            log.warning("None of the requested topics were found in database")
            return

        template = self.env.get_template("topic.html")
        affected_categories: set[int] = set()
        total_pages_generated = 0

        for topic in topics:
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

                    # Process post HTML to rewrite image URLs using asset registry
                    for post in posts:
                        if post.cooked:
                            post.cooked = (
                                self.html_processor.rewrite_with_full_resolution_links(
                                    post.cooked, topic.id, self.db, page_depth=3
                                )
                            )
                            # Enhance emoji with Unicode fallbacks
                            post.cooked = (
                                self.html_processor.enhance_emoji_with_unicode(
                                    post.cooked
                                )
                            )
                            # Enhance all image alt text for accessibility
                            post.cooked = (
                                self.html_processor.enhance_all_image_alt_text(
                                    post.cooked
                                )
                            )

                    # Get category info (only once per topic)
                    category = None
                    if topic.category_id:
                        category = self.db.get_category(topic.category_id)
                        affected_categories.add(topic.category_id)

                    # Generate SEO context (use all posts for SEO on first page)
                    if page_num == 1:
                        all_posts = self.db.get_topic_posts(topic.id)
                        seo_context = self._generate_topic_seo_context(
                            topic, all_posts, category
                        )
                    else:
                        seo_context = self._generate_topic_seo_context(
                            topic, posts, category
                        )

                    # Generate the page
                    path = self._generate_topic_page(
                        topic=topic,
                        page_num=page_num,
                        total_pages=total_pages,
                        posts=posts,
                        category=category,
                        template=template,
                        seo_context=seo_context,
                    )
                    log.debug(f"Regenerated {path}")
                    total_pages_generated += 1

            else:
                # Non-paginated mode: single page with all posts
                posts = self.db.get_topic_posts(topic.id)

                # Process post HTML to rewrite image URLs using asset registry
                for post in posts:
                    if post.cooked:
                        post.cooked = (
                            self.html_processor.rewrite_with_full_resolution_links(
                                post.cooked, topic.id, self.db, page_depth=3
                            )
                        )
                        # Enhance emoji with Unicode fallbacks
                        post.cooked = self.html_processor.enhance_emoji_with_unicode(
                            post.cooked
                        )
                        # Enhance all image alt text for accessibility
                        post.cooked = self.html_processor.enhance_all_image_alt_text(
                            post.cooked
                        )

                # Get category info
                category = None
                if topic.category_id:
                    category = self.db.get_category(topic.category_id)
                    affected_categories.add(topic.category_id)

                # Generate SEO context
                seo_context = self._generate_topic_seo_context(topic, posts, category)

                # Generate single page
                path = self._generate_topic_page(
                    topic=topic,
                    page_num=1,
                    total_pages=1,
                    posts=posts,
                    category=category,
                    template=template,
                    seo_context=seo_context,
                )
                log.debug(f"Regenerated {path}")
                total_pages_generated += 1

        log.info(f"Regenerated {total_pages_generated} pages for {len(topics)} topics")

        # Regenerate affected category pages
        if affected_categories:
            log.info(
                f"Regenerating {len(affected_categories)} affected category pages..."
            )
            self._regenerate_categories(list(affected_categories))

    def _regenerate_categories(self, category_ids: list[int]) -> None:
        """
        Regenerate specific category pages with pagination.

        Args:
            category_ids: List of category IDs to regenerate
        """
        template = self.env.get_template("category.html")

        for category_id in category_ids:
            category = self.db.get_category(category_id)
            if not category:
                log.warning(f"Category {category_id} not found in database")
                continue

            # Get total topic count for pagination
            total_topics = category.topic_count
            total_pages = (
                math.ceil(total_topics / TOPICS_PER_CATEGORY_PAGE)
                if total_topics > 0
                else 1
            )

            # Generate each page
            for page_num in range(1, total_pages + 1):
                # Get topics for this page
                topics = self.db.get_category_topics_paginated(
                    category.id, page_num, TOPICS_PER_CATEGORY_PAGE
                )

                # Add username to topics
                for topic in topics:
                    topic.username = self._get_topic_author_username(topic)  # type: ignore[attr-defined]

                # Generate SEO context for category
                site_url = self._get_site_url()
                site_meta = {}
                if site_url:
                    site_meta = self.db.get_site_metadata(site_url)

                site_title = site_meta.get("site_title", "Forum Archive")
                site_description = site_meta.get("site_description", "")

                # Generate canonical URL if configured
                canonical_url = None
                if self.canonical_base_url:
                    if page_num == 1:
                        canonical_url = (
                            f"{self.canonical_base_url}/c/{category.slug}/"
                            f"{category.id}/index.html"
                        )
                    else:
                        canonical_url = (
                            f"{self.canonical_base_url}/c/{category.slug}/"
                            f"{category.id}/page-{page_num}.html"
                        )

                # Generate category Open Graph tags
                og_tags = generate_category_og_tags(category, site_title, canonical_url)

                # Generate meta description for category
                if category.description:
                    category_description_text = category.description[
                        :150
                    ]  # Limit to 150 chars
                    meta_description = (
                        f"{category.name} - {category_description_text}. "
                        f"Browse {category.topic_count} topics."
                    )
                else:
                    meta_description = (
                        f"Browse {category.topic_count} topics in "
                        f"{category.name} category from {site_title}."
                    )

                # Update for paginated pages
                if page_num > 1:
                    meta_description = (
                        f"{category.name} - Page {page_num}. {meta_description}"
                    )

                # Create pagination context
                pagination = (
                    {
                        "current_page": page_num,
                        "total_pages": total_pages,
                        "has_prev": page_num > 1,
                        "has_next": page_num < total_pages,
                        "prev_page": page_num - 1,
                        "next_page": page_num + 1,
                    }
                    if total_pages > 1
                    else None
                )

                # Render template
                html = template.render(
                    category=category,
                    topics=topics,
                    pagination=pagination,
                    depth=3,  # /c/{slug}/{id}/index.html
                    site_description=site_description,
                    meta_description=meta_description,
                    og_tags=og_tags,
                    canonical_url=canonical_url,
                )

                # Create category directory using Discourse-compatible
                # structure: /c/{slug}/{id}/
                category_dir = self.output_dir / "c" / category.slug / str(category.id)
                category_dir.mkdir(parents=True, exist_ok=True)

                # Write page file
                if page_num == 1:
                    category_path = category_dir / "index.html"
                else:
                    category_path = category_dir / f"page-{page_num}.html"

                category_path.write_text(html, encoding="utf-8")
                log.debug(f"Regenerated {category_path}")

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

        log.info(f"Regenerating {len(usernames)} user profile pages...")

        template = self.env.get_template("user.html")

        user_dir = self.output_dir / "u"
        user_dir.mkdir(parents=True, exist_ok=True)

        # Get site title for meta descriptions
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)
        site_title = site_meta.get("site_title", "Forum Archive")

        regenerated = 0
        for username in usernames:
            user = self.db.get_user_by_username(username)
            if user is None:
                log.debug(f"User '{username}' not found in database, skipping")
                continue

            post_count = self.db.get_user_post_count(user.id)

            # Generate meta description
            if post_count == 0:
                meta_description = f"Profile page for {user.username} in {site_title}."
            elif post_count == 1:
                meta_description = (
                    f"{user.username}'s profile - 1 post in {site_title}."
                )
            else:
                meta_description = (
                    f"{user.username}'s profile - {post_count} posts in "
                    f"{site_title}. View discussions and contributions."
                )

            if self.pagination_enabled and post_count > 0:
                total_pages = math.ceil(post_count / self.posts_per_page)

                for page_num in range(1, total_pages + 1):
                    user_posts = self.db.get_user_posts_paginated(
                        user.id, page_num, self.posts_per_page
                    )

                    pagination = (
                        {
                            "current_page": page_num,
                            "total_pages": total_pages,
                            "has_prev": page_num > 1,
                            "has_next": page_num < total_pages,
                            "prev_page": page_num - 1,
                            "next_page": page_num + 1,
                        }
                        if total_pages > 1
                        else None
                    )

                    page_meta_description = meta_description
                    if page_num > 1:
                        page_meta_description = (
                            f"{user.username}'s profile - Page {page_num} of "
                            f"{total_pages}. {post_count} total posts."
                        )

                    html = template.render(
                        user=user,
                        user_posts=user_posts,
                        post_count=post_count,
                        pagination=pagination,
                        meta_description=page_meta_description,
                        depth=2,  # /u/{username}/index.html
                    )

                    user_subdir = user_dir / user.username
                    user_subdir.mkdir(parents=True, exist_ok=True)
                    if page_num == 1:
                        user_path = user_subdir / "index.html"
                    else:
                        user_path = user_subdir / f"page-{page_num}.html"

                    user_path.write_text(html, encoding="utf-8")
            else:
                user_posts = self.db.get_user_posts(user.id, limit=50)

                html = template.render(
                    user=user,
                    user_posts=user_posts,
                    post_count=post_count,
                    pagination=None,
                    meta_description=meta_description,
                    depth=2,  # /u/{username}/index.html
                )

                user_subdir = user_dir / user.username
                user_subdir.mkdir(parents=True, exist_ok=True)
                user_path = user_subdir / "index.html"
                user_path.write_text(html, encoding="utf-8")

            regenerated += 1

        log.info(f"Regenerated {regenerated} user profile pages")

        # Regenerate users index since post counts may have changed
        if regenerated > 0:
            self.generate_users_index()

    def generate_sitemap(self) -> None:
        """Generate sitemap.xml for search engine discovery.

        Only generates when canonical_base_url is configured, since sitemaps
        require absolute URLs per the sitemap protocol.
        """
        if not self.canonical_base_url:
            log.debug("Skipping sitemap: no canonical_base_url configured")
            return

        base = self.canonical_base_url.rstrip("/")
        urls: list[tuple[str, str | None, str, str]] = []

        # Homepage
        urls.append((f"{base}/", None, "weekly", "1.0"))

        # Latest index pages
        total_topics = self.db.get_topics_count()
        total_latest_pages = (
            math.ceil(total_topics / TOPICS_PER_INDEX_PAGE) if total_topics > 0 else 1
        )
        for p in range(1, total_latest_pages + 1):
            page_file = "index.html" if p == 1 else f"page-{p}.html"
            urls.append((f"{base}/latest/{page_file}", None, "daily", "0.7"))

        # Top indexes
        urls.append((f"{base}/top/index.html", None, "weekly", "0.5"))
        for sub in ["replies", "views"]:
            for p in range(1, total_latest_pages + 1):
                page_file = "index.html" if p == 1 else f"page-{p}.html"
                urls.append((f"{base}/top/{sub}/{page_file}", None, "weekly", "0.5"))

        # Category pages
        categories = self.db.get_all_categories()
        for cat in categories:
            cat_pages = (
                math.ceil(cat.topic_count / TOPICS_PER_CATEGORY_PAGE)
                if cat.topic_count > 0
                else 1
            )
            for p in range(1, cat_pages + 1):
                page_file = "index.html" if p == 1 else f"page-{p}.html"
                urls.append(
                    (
                        f"{base}/c/{cat.slug}/{cat.id}/{page_file}",
                        None,
                        "weekly",
                        "0.6",
                    )
                )

        # Topic pages
        topics = self.db.get_all_topics()
        for topic in topics:
            lastmod = None
            lastmod_dt = topic.last_posted_at or topic.created_at
            if lastmod_dt:
                lastmod = lastmod_dt.strftime("%Y-%m-%d")
            topic_pages = (
                math.ceil(topic.posts_count / self.posts_per_page)
                if topic.posts_count > 0
                else 1
            )
            for p in range(1, topic_pages + 1):
                if p == 1:
                    loc = f"{base}/t/{topic.slug}/{topic.id}"
                else:
                    loc = f"{base}/t/{topic.slug}/{topic.id}/page-{p}.html"
                urls.append((loc, lastmod, "monthly", "0.8"))

        # User pages (if enabled)
        if self.include_users:
            users = self.db.get_all_users()
            for user in users:
                urls.append((f"{base}/u/{user.username}", None, "monthly", "0.3"))

        # Search page (if static mode)
        if self.search_backend == "static":
            urls.append((f"{base}/search.html", None, "monthly", "0.4"))

        # Build XML
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for loc, lastmod, changefreq, priority in urls:
            lines.append("  <url>")
            lines.append(f"    <loc>{loc}</loc>")
            if lastmod:
                lines.append(f"    <lastmod>{lastmod}</lastmod>")
            lines.append(f"    <changefreq>{changefreq}</changefreq>")
            lines.append(f"    <priority>{priority}</priority>")
            lines.append("  </url>")
        lines.append("</urlset>")

        sitemap_path = self.output_dir / "sitemap.xml"
        sitemap_path.write_text("\n".join(lines), encoding="utf-8")
        log.info(f"Generated sitemap.xml with {len(urls)} URLs")

    def generate_robots_txt(self) -> None:
        """Generate robots.txt for crawler guidance."""
        lines = [
            "User-agent: *",
            "Allow: /",
            "",
            "Disallow: /archive.db",
            "Disallow: /search_index.json",
            "",
        ]

        if self.canonical_base_url:
            base = self.canonical_base_url.rstrip("/")
            lines.append(f"Sitemap: {base}/sitemap.xml")
            lines.append("")

        robots_path = self.output_dir / "robots.txt"
        robots_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("Generated robots.txt")

    def update_index(self) -> None:
        """
        Update index, search page, and search index (for incremental updates).

        Regenerates homepage and search-related files without touching topic pages.
        """
        log.info("Updating index pages...")

        self.generate_index()

        # Only regenerate search page and index for static mode
        if self.search_backend == "static":
            self.generate_search_page()
            self.generate_search_index()

        # Refresh sitemap and robots.txt
        self.generate_sitemap()
        self.generate_robots_txt()

        log.info("Index pages updated")
