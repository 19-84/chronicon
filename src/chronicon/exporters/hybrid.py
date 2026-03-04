# ABOUTME: Hybrid exporter for Chronicon - combines HTML and Markdown output
# ABOUTME: Generates unified archive with shared assets for GitHub Pages + browsing

"""
Hybrid exporter that generates both HTML and Markdown with shared assets.

This exporter creates a unified output suitable for:
- GitHub Pages deployment (HTML at root)
- GitHub/Forgejo markdown browsing (/md/ directory)
- Shared assets to minimize disk usage
"""

from datetime import datetime
from pathlib import Path

from ..utils.logger import get_logger
from .base import BaseExporter
from .html_static import HTMLStaticExporter
from .markdown import MarkdownGitHubExporter

log = get_logger(__name__)


class HybridExporter(BaseExporter):
    """
    Orchestrates HTML + Markdown export with shared assets.

    Produces a unified output directory suitable for:
    - GitHub Pages deployment (from root with HTML files)
    - GitHub/Forgejo markdown browsing (from /md/)
    - Shared assets to minimize disk usage
    """

    def __init__(
        self,
        db,
        output_dir: Path,
        include_html: bool = True,
        include_md: bool = True,
        asset_downloader=None,
        include_users: bool = False,
        posts_per_page: int = 50,
        pagination_enabled: bool = True,
        config: dict | None = None,
        progress=None,
        search_backend: str = "fts",
    ):
        """
        Initialize hybrid exporter.

        Args:
            db: ArchiveDatabase instance
            output_dir: Output directory for the entire archive
            include_html: Whether to generate HTML output (default: True)
            include_md: Whether to generate Markdown output (default: True)
            asset_downloader: AssetDownloader for downloading images
            include_users: Whether to generate user profile pages
            posts_per_page: Number of posts per page
            pagination_enabled: Whether to enable pagination
            config: Optional configuration dict
            progress: Optional Rich Progress object for progress tracking
            search_backend: Search backend mode - "static" or "fts" (default)
        """
        super().__init__(db, output_dir, progress=progress)
        self.include_html = include_html
        self.include_md = include_md
        self.asset_downloader = asset_downloader
        self.include_users = include_users
        self.posts_per_page = posts_per_page
        self.pagination_enabled = pagination_enabled
        self.config = config or {}
        self.search_backend = search_backend

    def export(self) -> None:
        """Main export orchestration."""
        log.info("Starting hybrid export...")

        # Export HTML if requested (outputs to root)
        if self.include_html:
            log.info("Generating HTML export...")
            html_exporter = HTMLStaticExporter(
                self.db,
                self.output_dir,
                include_users=self.include_users,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                config=self.config,
                progress=self.progress,
                search_backend=self.search_backend,
            )
            html_exporter.export()
            log.info("HTML export complete")

        # Export Markdown if requested (outputs to /md/)
        if self.include_md:
            log.info("Generating Markdown export...")
            md_dir = self.output_dir / "md"
            md_exporter = MarkdownGitHubExporter(
                self.db,
                md_dir,
                asset_downloader=self.asset_downloader,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                include_users=self.include_users,
                progress=self.progress,
            )
            md_exporter.export()
            log.info("Markdown export complete")

        # Generate root README.md with stats
        self._generate_root_readme()

        # Generate _config.yml for GitHub Pages
        self._generate_github_pages_config()

        log.info("Hybrid export complete")

    def _generate_root_readme(self) -> None:
        """
        Generate root README.md with archive statistics and links.

        This serves as the landing page when viewing the repo on GitHub.
        """
        lines = []

        # Get site metadata
        site_url = self._get_site_url()
        site_meta = {}
        if site_url:
            site_meta = self.db.get_site_metadata(site_url)

        site_title = site_meta.get("site_title", "Forum Archive")
        site_description = site_meta.get("site_description", "")

        # Header
        lines.append(f"# {site_title} Archive")
        lines.append("")

        if site_description:
            lines.append(f"> {site_description}")
            lines.append("")

        # Archive Statistics
        stats = self.db.get_statistics()
        archive_stats = self.db.get_archive_statistics()

        lines.append("## Archive Statistics")
        lines.append("")
        lines.append(f"- **Topics:** {stats['total_topics']:,}")
        lines.append(f"- **Posts:** {stats['total_posts']:,}")
        lines.append(f"- **Users:** {stats['total_users']:,}")
        lines.append(f"- **Categories:** {stats['total_categories']}")

        if archive_stats.get("earliest_topic") and archive_stats.get("latest_topic"):
            earliest = archive_stats["earliest_topic"][:10]
            latest = archive_stats["latest_topic"][:10]
            lines.append(f"- **Date Range:** {earliest} to {latest}")

        lines.append("")

        # Browse the Archive section
        lines.append("## Browse the Archive")
        lines.append("")

        if self.include_html:
            lines.append("### Web Experience (Recommended)")
            lines.append("Deploy to GitHub Pages or open locally:")
            lines.append(
                "- **[View HTML Archive](index.html)** - Full-featured with search"
            )
            lines.append("")

        if self.include_md:
            lines.append("### Markdown Browsing")
            lines.append("Browse directly on GitHub/Forgejo:")
            lines.append(
                "- **[Browse Markdown Archive](md/index.md)** - Lightweight, readable"
            )
            lines.append("")

        # Deployment section
        if self.include_html:
            lines.append("## Deployment")
            lines.append("")
            lines.append(
                "This archive includes a `_config.yml` for GitHub Pages."
                " Enable Pages in your repository settings and select"
                " the root directory to deploy the HTML version."
            )
            lines.append("")

        # Footer
        archive_date = datetime.now().strftime("%Y-%m-%d")
        lines.append("---")
        lines.append("")
        lines.append(
            f"*Archived with [Chronicon]"
            f"(https://github.com/19-84/chronicon) on {archive_date}*"
        )
        lines.append("")

        # Write README
        readme_path = self.output_dir / "README.md"
        readme_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("Generated root README.md")

    def _generate_github_pages_config(self) -> None:
        """
        Generate _config.yml for GitHub Pages deployment.

        Configures GitHub Pages to serve HTML files from root,
        excluding the markdown directory and database files.
        """
        lines = [
            "# GitHub Pages configuration for Chronicon archive",
            "# Serves the HTML version from the root directory",
            "",
            "# Exclude markdown directory and database from site",
            "exclude:",
            "  - md",
            "  - archive.db",
            '  - "*.json"',
            "  - .chronicon*",
            "",
            "# Include HTML assets",
            "include:",
            "  - assets",
            "",
            '# Set baseurl if deploying to a subdirectory (e.g., "/my-archive")',
            "# Leave empty for deployment to root domain",
            'baseurl: ""',
            "",
            "# Disable Jekyll processing for faster builds",
            "markdown: kramdown",
            "highlighter: rouge",
        ]

        config_path = self.output_dir / "_config.yml"
        config_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("Generated _config.yml for GitHub Pages")

    def _get_site_url(self) -> str | None:
        """
        Get the primary site URL from the database.

        Returns:
            Site URL string, or None if not found
        """
        try:
            cursor = self.db.connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("SELECT site_url FROM site_metadata LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            log.warning(f"Could not retrieve site URL from database: {e}")
            return None

    def export_users_by_username(self, usernames: set[str]) -> None:
        """
        Regenerate profile pages for specific users in both HTML and Markdown.

        Args:
            usernames: Set of usernames whose profile pages need regeneration
        """
        if not usernames:
            return

        log.info(f"Regenerating {len(usernames)} user profiles in hybrid mode...")

        if self.include_html:
            html_exporter = HTMLStaticExporter(
                self.db,
                self.output_dir,
                include_users=self.include_users,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                config=self.config,
                search_backend=self.search_backend,
            )
            html_exporter.export_users_by_username(usernames)

        if self.include_md:
            md_dir = self.output_dir / "md"
            md_exporter = MarkdownGitHubExporter(
                self.db,
                md_dir,
                asset_downloader=self.asset_downloader,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                include_users=self.include_users,
            )
            md_exporter.export_users_by_username(usernames)

    def export_topics(self, topic_ids: list[int]) -> None:
        """
        Regenerate specific topics only (for incremental updates).

        Args:
            topic_ids: List of topic IDs to regenerate
        """
        if not topic_ids:
            log.info("No topics to regenerate")
            return

        log.info(f"Regenerating {len(topic_ids)} topics in hybrid mode...")

        # Regenerate HTML topics
        if self.include_html:
            html_exporter = HTMLStaticExporter(
                self.db,
                self.output_dir,
                include_users=self.include_users,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                config=self.config,
                search_backend=self.search_backend,
            )
            html_exporter.export_topics(topic_ids)

        # Regenerate Markdown topics
        if self.include_md:
            md_dir = self.output_dir / "md"
            md_exporter = MarkdownGitHubExporter(
                self.db,
                md_dir,
                asset_downloader=self.asset_downloader,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                include_users=self.include_users,
            )
            md_exporter.export_topics(topic_ids)

        log.info(f"Regenerated {len(topic_ids)} topics")

    def update_index(self) -> None:
        """
        Update indexes (for incremental updates).

        Regenerates README and indexes without touching topic files.
        """
        log.info("Updating indexes in hybrid mode...")

        # Update HTML indexes
        if self.include_html:
            html_exporter = HTMLStaticExporter(
                self.db,
                self.output_dir,
                include_users=self.include_users,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                config=self.config,
                search_backend=self.search_backend,
            )
            html_exporter.update_index()

        # Update Markdown indexes
        if self.include_md:
            md_dir = self.output_dir / "md"
            md_exporter = MarkdownGitHubExporter(
                self.db,
                md_dir,
                asset_downloader=self.asset_downloader,
                posts_per_page=self.posts_per_page,
                pagination_enabled=self.pagination_enabled,
                include_users=self.include_users,
            )
            md_exporter.update_index()

        # Regenerate root README
        self._generate_root_readme()

        log.info("Indexes updated")
