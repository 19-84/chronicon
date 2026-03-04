# ABOUTME: Command-line interface for Chronicon
# ABOUTME: Provides archive, update, validate, and migrate commands

"""Command-line interface for Chronicon."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from .config import Config
from .exporters.html_static import HTMLStaticExporter
from .exporters.hybrid import HybridExporter
from .exporters.markdown import MarkdownGitHubExporter
from .fetchers.api_client import DiscourseAPIClient
from .fetchers.assets import AssetDownloader
from .fetchers.categories import CategoryFetcher
from .fetchers.site_config import SiteConfigFetcher
from .fetchers.topics import TopicFetcher
from .processors.html_parser import HTMLProcessor
from .storage.database import ArchiveDatabase
from .utils.logger import get_logger, setup_logging
from .utils.update_manager import UpdateManager
from .utils.validators import ValidationError, validate_forum_url
from .watch.daemon import WatchDaemon

console = Console()
log = get_logger(__name__)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="chronicon",
        description="Archive Discourse forums to multiple formats",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Archive command
    archive_parser = subparsers.add_parser("archive", help="Archive forum(s)")
    archive_parser.add_argument(
        "--urls", required=True, help="Comma-separated forum URLs"
    )
    archive_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Output directory"
    )
    archive_parser.add_argument(
        "--formats",
        default="hybrid",
        help=(
            "Export formats (comma-separated: html, md, hybrid, none). "
            "Use 'none' to fetch data without exporting."
        ),
    )
    archive_parser.add_argument(
        "--text-only", action="store_true", help="Skip downloading images"
    )
    archive_parser.add_argument(
        "--include-users", action="store_true", help="Generate user profile pages"
    )
    archive_parser.add_argument(
        "--categories", help="Specific category IDs (comma-separated)"
    )
    archive_parser.add_argument("--since", help="Archive posts since date (YYYY-MM-DD)")
    archive_parser.add_argument(
        "--workers", type=int, default=8, help="Number of concurrent workers"
    )
    archive_parser.add_argument(
        "--rate-limit", type=float, default=0.5, help="Seconds between requests"
    )
    archive_parser.add_argument(
        "--sweep",
        action="store_true",
        help="Use ID sweep mode (exhaustive, fetches every topic ID)",
    )
    archive_parser.add_argument(
        "--start-id", type=int, help="Starting topic ID for sweep (defaults to max)"
    )
    archive_parser.add_argument(
        "--end-id", type=int, default=1, help="Ending topic ID for sweep (default: 1)"
    )
    archive_parser.add_argument(
        "--search-backend",
        choices=["static", "fts"],
        default="fts",
        help="Search backend: 'static' (offline) or 'fts' (server). Default: fts",
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update existing archive(s)")
    update_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )
    update_parser.add_argument("--formats", default="all", help="Formats to regenerate")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate archive")
    validate_parser.add_argument(
        "--output-dir", required=True, type=Path, help="Archive directory"
    )

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate from JSON archives")
    migrate_parser.add_argument(
        "--from", dest="source_dir", required=True, type=Path, help="Source directory"
    )
    migrate_parser.add_argument(
        "--format",
        choices=["html", "md", "hybrid"],
        help="Export format after migration",
    )

    # Watch command
    watch_parser = subparsers.add_parser(
        "watch", help="Continuously monitor and update archive"
    )
    watch_subparsers = watch_parser.add_subparsers(dest="watch_action")

    # watch start (default if no subcommand)
    watch_start_parser = watch_subparsers.add_parser(
        "start", help="Start watching (or run without subcommand)"
    )
    watch_start_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )
    watch_start_parser.add_argument(
        "--formats",
        default=None,
        help="Formats to regenerate (comma-separated, default: all)",
    )
    watch_start_parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon",
    )

    # watch stop
    watch_stop_parser = watch_subparsers.add_parser("stop", help="Stop running daemon")
    watch_stop_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )

    # watch status
    watch_status_parser = watch_subparsers.add_parser(
        "status", help="Show daemon status"
    )
    watch_status_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )

    # Allow "chronicon watch" without subcommand to default to "start"
    watch_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )
    watch_parser.add_argument(
        "--formats",
        default=None,
        help="Formats to regenerate (comma-separated, default: all)",
    )
    watch_parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon",
    )

    # Serve command (REST API)
    serve_parser = subparsers.add_parser("serve", help="Start REST API server")
    serve_parser.add_argument(
        "--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Bind port (default: 8000)"
    )
    serve_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    # MCP command (Model Context Protocol server)
    subparsers.add_parser("mcp", help="Start MCP server (stdio)")

    # Rebuild search index command
    rebuild_parser = subparsers.add_parser(
        "rebuild-search-index", help="Rebuild full-text search index"
    )
    rebuild_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )

    # Backfill missing posts command
    backfill_parser = subparsers.add_parser(
        "backfill-posts", help="Fetch posts for topics that are missing them"
    )
    backfill_parser.add_argument(
        "--output-dir", default="./archives", type=Path, help="Archive directory"
    )
    backfill_parser.add_argument(
        "--limit", type=int, default=None, help="Max topics to backfill (default: all)"
    )

    # Export command (standalone re-export from existing database)
    export_parser = subparsers.add_parser(
        "export", help="Export from existing archive database"
    )
    export_parser.add_argument(
        "--output-dir",
        default="./archives",
        type=Path,
        help="Archive directory with existing database",
    )
    export_parser.add_argument(
        "--formats",
        default="hybrid",
        help="Export formats (comma-separated: html, md, hybrid, json)",
    )
    export_parser.add_argument(
        "--include-users", action="store_true", help="Generate user profile pages"
    )
    export_parser.add_argument(
        "--search-backend",
        choices=["static", "fts"],
        default="fts",
        help="Search backend: 'static' (offline) or 'fts' (server). Default: fts",
    )

    # Global options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=Path, help="Config file path")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    # Load config
    config = Config.load(args.config)

    # Dispatch to command
    if args.command == "archive":
        run_archive(args, config)
    elif args.command == "update":
        run_update(args, config)
    elif args.command == "validate":
        run_validate(args, config)
    elif args.command == "migrate":
        run_migrate(args, config)
    elif args.command == "watch":
        run_watch(args, config)
    elif args.command == "serve":
        run_serve(args, config)
    elif args.command == "mcp":
        run_mcp(args, config)
    elif args.command == "export":
        run_export(args, config)
    elif args.command == "rebuild-search-index":
        run_rebuild_search_index(args, config)
    elif args.command == "backfill-posts":
        run_backfill_posts(args, config)


def run_archive(args: argparse.Namespace, config: Config) -> None:
    """Execute archive command."""
    console.print("[bold blue]Archiving forums...[/bold blue]")

    # Parse and validate site URLs
    try:
        sites = []
        for url in args.urls.split(","):
            url = url.strip()
            validated_url = validate_forum_url(url)
            sites.append(validated_url)

            # Warn about HTTP usage
            if (
                validated_url.startswith("http://")
                and "localhost" not in validated_url
                and "127.0.0.1" not in validated_url
            ):
                console.print(
                    "[yellow]Warning: Using unencrypted HTTP for "
                    f"{url}. Consider using HTTPS for security.[/yellow]"
                )
    except ValidationError as e:
        console.print(f"[red]Error: Invalid URL: {e}[/red]")
        return 1

    # Parse export formats
    formats = [fmt.strip() for fmt in args.formats.split(",")]

    # Parse category filter if provided
    category_ids = None
    if args.categories:
        try:
            category_ids = [
                int(cat_id.strip()) for cat_id in args.categories.split(",")
            ]
        except ValueError:
            console.print(
                "[red]Error: --categories must be comma-separated integers[/red]"
            )
            return

    # Archive each site
    for site_url in sites:
        console.print(f"\n[bold cyan]Archiving: {site_url}[/bold cyan]")

        try:
            _archive_site(
                site_url=site_url,
                output_dir=args.output_dir,
                formats=formats,
                text_only=args.text_only,
                include_users=args.include_users,
                category_ids=category_ids,
                since_date=args.since,
                workers=args.workers,
                rate_limit=args.rate_limit,
                config=config,
                use_sweep=args.sweep,
                sweep_start_id=args.start_id,
                sweep_end_id=args.end_id,
                search_backend=args.search_backend,
            )
            console.print(
                f"[bold green]✓ Successfully archived {site_url}[/bold green]"
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Archive interrupted by user[/yellow]")
            return
        except Exception as e:
            console.print(f"[red]✗ Failed to archive {site_url}: {e}[/red]")
            log.exception(f"Archive failed for {site_url}")
            continue

    console.print("\n[bold green]Archive complete![/bold green]")


def _archive_site(
    site_url: str,
    output_dir: Path,
    formats: list,
    text_only: bool,
    include_users: bool,
    category_ids: list,
    since_date: str,
    workers: int,
    rate_limit: float,
    config: Config,
    use_sweep: bool = False,
    sweep_start_id: int = None,
    sweep_end_id: int = 1,
    search_backend: str = "fts",
):
    """Archive a single site."""
    import os
    from datetime import datetime

    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )

    from chronicon.utils.progress import (
        CompactTimeElapsedColumn,
        CompactTimeRemainingColumn,
        RateColumn,
    )

    # Initialize database
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for DATABASE_URL environment variable - enables PostgreSQL support
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from chronicon.storage.factory import get_database

        db = get_database(database_url)
        # Mask password in log output
        if "@" in database_url:
            masked_url = (
                database_url.split("@")[0].rsplit(":", 1)[0]
                + ":***@"
                + database_url.split("@")[-1]
            )
        else:
            masked_url = database_url
        log.info(f"Using database: {masked_url}")
    else:
        db_path = output_dir / "archive.db"
        db = ArchiveDatabase(db_path)
        log.info(f"Using SQLite database: {db_path}")

    # If no categories specified on CLI, check config file
    if not category_ids:
        config_categories = config.get_category_filter(site_url)
        if config_categories:
            category_ids = config_categories
            log.info(f"Using category filter from config: {category_ids}")

    # Initialize API client
    client = DiscourseAPIClient(site_url, rate_limit=rate_limit)

    # Initialize fetchers
    category_fetcher = CategoryFetcher(client, db)
    topic_fetcher = TopicFetcher(client, db)

    # Track phase timings
    import time as time_module

    phase_times = {}
    overall_start = time_module.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        CompactTimeElapsedColumn(),
        CompactTimeRemainingColumn(),
        RateColumn(unit="items"),
        console=console,
    ) as progress:
        # Add a live statistics display task
        stats_task = progress.add_task(
            "[dim]Network: 0 req | Rate: 0.00 req/s | Transferred: 0.0 MB[/dim]",
            total=None,
        )

        # Reference to asset_downloader for stats (will be set later)
        asset_downloader = None

        def update_stats_display():
            """Update the live statistics display."""
            api_stats = client.get_stats()

            # Build stats text with API stats
            stats_lines = [
                f"[dim]API: {api_stats['requests_made']} req | "
                f"Success: {api_stats['requests_successful']} | "
                f"Failed: {api_stats['requests_failed']} | "
                f"Rate: {api_stats['request_rate']:.2f} req/s | "
                f"Transferred: {api_stats['bytes_transferred'] / 1024 / 1024:.1f} MB"
            ]

            # Add asset stats if available
            if asset_downloader:
                asset_stats = asset_downloader.get_stats()
                stats_lines.append(
                    f"Assets: {asset_stats['downloaded']} ok | "
                    f"{asset_stats['cached']} cached | "
                    f"{asset_stats['failed']} failed | "
                    f"Rate: {asset_stats['download_rate']:.2f}/s | "
                    f"Transferred: "
                    f"{asset_stats['bytes_downloaded'] / 1024 / 1024:.1f} MB[/dim]"
                )

            progress.update(stats_task, description="\n".join(stats_lines))

        # Choose fetching strategy: ID sweep or category-based
        all_topics = []

        if use_sweep:
            # ID SWEEP MODE: Exhaustive topic-by-topic fetching
            console.print("[bold yellow]Using ID sweep mode (exhaustive)[/bold yellow]")

            # Determine ID range
            if sweep_start_id is None:
                # Auto-detect max ID
                max_id = topic_fetcher.get_max_topic_id()
                sweep_start_id = max_id
                console.print(f"Auto-detected max topic ID: {max_id}")

            total_ids = sweep_start_id - sweep_end_id + 1
            console.print(
                f"Will sweep IDs: {sweep_start_id} → {sweep_end_id} "
                f"({total_ids:,} IDs)\n"
            )

            phase_start = time_module.time()
            task = progress.add_task(
                f"[cyan]Sweeping topic IDs {sweep_start_id} → {sweep_end_id}...",
                total=total_ids,
            )

            sweep_stats = {
                "attempted": 0,
                "found": 0,
                "already_in_db": 0,
                "not_found": 0,
                "errors": 0,
            }

            def sweep_progress(topic_id, topic, stats):
                """Update progress bar during sweep."""
                sweep_stats.update(stats)

                # Update progress bar
                progress.update(task, advance=1)

                # Update description every 100 IDs
                if stats["attempted"] % 100 == 0:
                    desc = (
                        f"[cyan]Sweeping IDs (found: {stats['found']}, "
                        f"404s: {stats['not_found']}, "
                        f"current: #{topic_id})"
                    )
                    progress.update(task, description=desc)
                    update_stats_display()

            # Run the sweep
            fetched_topics = topic_fetcher.fetch_topics_by_id_range(
                start_id=sweep_start_id,
                end_id=sweep_end_id,
                skip_existing=True,
                progress_callback=sweep_progress,
            )

            all_topics = fetched_topics
            phase_times["topics_sweep"] = time_module.time() - phase_start

            # Final stats
            progress.update(
                task,
                description=(
                    f"[green]✓ Sweep complete: {sweep_stats['found']} "
                    f"topics found, {sweep_stats['not_found']} 404s"
                ),
            )
            update_stats_display()

        else:
            # CATEGORY-BASED MODE: Original logic
            # Step 1: Fetch categories
            phase_start = time_module.time()
            task = progress.add_task("[cyan]Fetching categories...", total=None)
            categories = category_fetcher.fetch_all_categories()

            # Filter categories if requested
            if category_ids:
                categories = [c for c in categories if c.id in category_ids]

            # Store categories in database
            for category in categories:
                db.insert_category(category)

            phase_times["categories"] = time_module.time() - phase_start
            update_stats_display()
            progress.update(
                task,
                completed=True,
                description=f"[green]✓ Fetched {len(categories)} categories",
            )

            # Step 2: Fetch topics from categories with pagination
            phase_start = time_module.time()
            task = progress.add_task("[cyan]Fetching topics...", total=len(categories))
            total_topics_fetched = 0

            for idx, category in enumerate(categories):
                # Get topics for this category from database
                category_topics = db.get_topics_by_category(category.id)

                # If no topics yet, fetch from API with pagination
                if not category_topics:
                    try:
                        # Fetch ALL topics for this category using pagination
                        fetched_topics = topic_fetcher.fetch_category_topics(
                            category.id
                        )

                        # Store topics in database
                        for topic in fetched_topics:
                            db.insert_topic(topic)
                            all_topics.append(topic)

                        total_topics_fetched += len(fetched_topics)

                        # Update progress description to show running total
                        progress.update(
                            task,
                            description=(
                                f"[cyan]Fetching topics... "
                                f"({total_topics_fetched} topics so far)"
                            ),
                        )

                        log.info(
                            f"Fetched {len(fetched_topics)} topics from "
                            f"category {category.name} (ID: {category.id})"
                        )

                    except Exception as e:
                        log.error(
                            f"Error fetching topics for category {category.id}: {e}"
                        )
                else:
                    all_topics.extend(category_topics)
                    total_topics_fetched += len(category_topics)

                # Update stats every 5 categories
                if idx % 5 == 0:
                    update_stats_display()

                progress.update(task, advance=1)

            phase_times["topics"] = time_module.time() - phase_start
            update_stats_display()
            progress.update(
                task,
                description=(
                    f"[green]✓ Fetched {len(all_topics)} topics from "
                    f"{len(categories)} categories"
                ),
            )

        # Step 3: Fetch posts for each topic
        phase_start = time_module.time()
        task = progress.add_task("[cyan]Fetching posts...", total=len(all_topics))

        for idx, topic in enumerate(all_topics):
            try:
                posts = topic_fetcher.fetch_topic_posts(topic.id)

                # Store posts
                for post in posts:
                    db.insert_post(post)

            except Exception as e:
                log.error(f"Error fetching posts for topic {topic.id}: {e}")

            # Update stats every 10 topics
            if idx % 10 == 0:
                update_stats_display()

            progress.update(task, advance=1)

        phase_times["posts"] = time_module.time() - phase_start
        update_stats_display()
        progress.update(
            task, description=f"[green]✓ Fetched posts for {len(all_topics)} topics"
        )

        # Step 3b: Fetch full user profiles (for avatar_template and other metadata)
        # Collect ALL unique usernames from the database (not just from this run)
        unique_usernames = db.get_unique_usernames()
        # Filter out system and empty usernames
        unique_usernames = {u for u in unique_usernames if u and u != "system"}

        # Filter out users we already have
        existing_users = {u.username for u in db.get_all_users()}
        usernames_to_fetch = unique_usernames - existing_users

        if usernames_to_fetch:
            from .fetchers.users import UserFetcher

            phase_start = time_module.time()
            user_fetcher = UserFetcher(client, db)

            user_task = progress.add_task(
                f"[cyan]Fetching {len(usernames_to_fetch)} user profiles...",
                total=len(usernames_to_fetch),
            )

            users_fetched = 0
            for username in usernames_to_fetch:
                try:
                    user = user_fetcher.fetch_user(username)
                    if user:
                        db.insert_user(user)
                        users_fetched += 1
                except Exception as e:
                    log.debug(f"Failed to fetch profile for {username}: {e}")

                progress.advance(user_task, 1)

                # Update stats every 10 users
                if users_fetched % 10 == 0:
                    update_stats_display()

            phase_times["users"] = time_module.time() - phase_start
            update_stats_display()
            progress.update(
                user_task, description=f"[green]✓ Fetched {users_fetched} user profiles"
            )
        elif unique_usernames:
            # All users already fetched
            log.info(f"All {len(unique_usernames)} user profiles already in database")

        # Step 4: Fetch and store site metadata
        # (moved before assets for logo/banner URLs)
        phase_start = time_module.time()
        metadata_task = progress.add_task("[cyan]Fetching site metadata...", total=None)

        site_config_fetcher = SiteConfigFetcher(client, db)
        site_config_fetcher.fetch_and_store_site_metadata()

        # Update last sync date
        db.update_site_metadata(
            site_url=site_url,
            last_sync_date=datetime.now().isoformat(),
        )

        # Store category filter in database (for watch mode to use later)
        db.set_category_filter(site_url, category_ids)
        if category_ids:
            log.info(f"Stored category filter for {site_url}: {category_ids}")

        # Get metadata for asset downloads
        site_metadata = db.get_site_metadata(site_url)

        phase_times["site_metadata"] = time_module.time() - phase_start
        update_stats_display()
        progress.update(metadata_task, description="[green]✓ Site metadata fetched")

        # Step 5: Download assets (if not text-only)
        if not text_only:
            phase_start = time_module.time()

            # Initialize asset downloader (make it available to update_stats_display)
            asset_downloader = AssetDownloader(
                client=client,
                db=db,
                output_dir=output_dir / "assets",
                text_only=False,
            )

            # Phase 5a: Download site assets (logo, banner, favicon, etc.)
            site_asset_task = progress.add_task(
                "[cyan]Downloading site assets...", total=4
            )  # generic + metadata assets

            def site_asset_callback(url, success, cached, bytes_downloaded):
                progress.advance(site_asset_task, 1)
                update_stats_display()

            try:
                # Download site assets with metadata
                # (includes logo_url, banner_image_url)
                asset_downloader.download_site_assets(
                    site_metadata=site_metadata, callback=site_asset_callback
                )
                progress.update(
                    site_asset_task, description="[green]✓ Site assets downloaded"
                )
            except Exception as e:
                log.error(f"Error downloading site assets: {e}")
                progress.update(
                    site_asset_task, description="[yellow]⚠ Site assets (some failed)"
                )

            update_stats_display()

            # Phase 5b: Process HTML and download embedded images
            html_processor = HTMLProcessor(asset_downloader)

            # Count total posts for progress tracking
            total_posts = sum(len(db.get_topic_posts(t.id)) for t in all_topics)

            image_task = progress.add_task(
                f"[cyan]Extracting and downloading images from {total_posts} posts...",
                total=total_posts,
            )

            posts_processed = 0

            # Image download callback
            def image_callback(url, success, cached, bytes_downloaded):
                # Update stats display periodically
                if asset_downloader.get_stats()["total_queued"] % 10 == 0:
                    update_stats_display()

            # Get all posts and process their HTML
            for topic in all_topics:
                posts = db.get_topic_posts(topic.id)
                for post in posts:
                    if post.cooked:
                        try:
                            # Extract image sets with resolution info
                            image_sets = html_processor.extract_image_sets(post.cooked)

                            # Download only medium + highest resolution
                            # for each image set
                            for _base_id, img_set in image_sets.items():
                                # Download medium resolution if available
                                if img_set["medium"] and img_set["medium"] not in [
                                    None,
                                    "",
                                ]:
                                    try:
                                        asset_downloader.download_image(
                                            img_set["medium"],
                                            topic.id,
                                            callback=image_callback,
                                        )
                                    except Exception as img_err:
                                        log.debug(
                                            "Failed to download medium "
                                            f"resolution: {img_err}"
                                        )

                                # Download highest resolution if different from medium
                                if (
                                    img_set["highest"]
                                    and img_set["highest"] not in [None, ""]
                                    and img_set["highest"] != img_set["medium"]
                                ):
                                    try:
                                        asset_downloader.download_image(
                                            img_set["highest"],
                                            topic.id,
                                            callback=image_callback,
                                        )
                                    except Exception as img_err:
                                        log.debug(
                                            "Failed to download highest "
                                            f"resolution: {img_err}"
                                        )

                        except Exception as e:
                            log.error(f"Error processing HTML for post {post.id}: {e}")

                    # Update progress
                    posts_processed += 1
                    progress.advance(image_task, 1)

                    # Update description every 50 posts
                    if posts_processed % 50 == 0:
                        asset_stats = asset_downloader.get_stats()
                        progress.update(
                            image_task,
                            description=(
                                f"[cyan]Processing posts "
                                f"({posts_processed}/{total_posts}) | "
                                f"{asset_stats['downloaded']} images downloaded"
                            ),
                        )
                        update_stats_display()

            # Final update
            asset_stats = asset_downloader.get_stats()
            progress.update(
                image_task,
                description=(
                    f"[green]✓ Processed {total_posts} posts, "
                    f"downloaded {asset_stats['downloaded']} images "
                    f"({asset_stats['cached']} cached, "
                    f"{asset_stats['failed']} failed)"
                ),
            )
            update_stats_display()

            # Phase 5c: Download user avatars
            all_users = db.get_all_users()
            users_with_avatars = [
                u for u in all_users if u.avatar_template and u.avatar_template.strip()
            ]

            if users_with_avatars:
                avatar_task = progress.add_task(
                    f"[cyan]Downloading avatars for {len(users_with_avatars)} users...",
                    total=len(users_with_avatars),
                )

                avatar_sizes = [48, 96, 144]  # Standard Discourse avatar sizes
                avatars_downloaded = 0

                def avatar_callback(url, success, cached, bytes_downloaded):
                    update_stats_display()

                avatars_failed = 0

                for user in users_with_avatars:
                    try:
                        # Download avatar at multiple sizes
                        results, best_path = asset_downloader.download_avatar(
                            user.avatar_template, avatar_sizes, callback=avatar_callback
                        )

                        # Update user with local avatar path (best resolution)
                        if best_path:
                            user.local_avatar_path = str(best_path)
                            db.insert_user(user)
                            avatars_downloaded += 1
                        else:
                            avatars_failed += 1
                            log.warning(
                                f"Avatar download failed for user {user.username}"
                            )

                    except Exception as e:
                        avatars_failed += 1
                        log.error(
                            f"Failed to download avatar for user {user.username}: {e}"
                        )

                    progress.advance(avatar_task, 1)

                # Update progress with actual counts
                if avatars_failed > 0:
                    progress.update(
                        avatar_task,
                        description=(
                            f"[yellow]⚠ Downloaded "
                            f"{avatars_downloaded}/{len(users_with_avatars)} "
                            f"user avatars ({avatars_failed} failed)"
                        ),
                    )
                else:
                    progress.update(
                        avatar_task,
                        description=(
                            f"[green]✓ Downloaded {avatars_downloaded} user avatars"
                        ),
                    )
                update_stats_display()

            # Phase 5d: Download SEO/Open Graph images for topics
            topics_with_seo_images = [
                t for t in all_topics if t.image_url and t.image_url.strip()
            ]

            if topics_with_seo_images:
                seo_task = progress.add_task(
                    (
                        f"[cyan]Downloading SEO images for "
                        f"{len(topics_with_seo_images)} topics..."
                    ),
                    total=len(topics_with_seo_images),
                )

                seo_images_downloaded = 0

                def seo_callback(url, success, cached, bytes_downloaded):
                    update_stats_display()

                for topic in topics_with_seo_images:
                    try:
                        # Download SEO/Open Graph image
                        local_path = asset_downloader.download_seo_image(
                            topic.image_url, callback=seo_callback
                        )

                        if local_path:
                            seo_images_downloaded += 1

                    except Exception as e:
                        log.debug(
                            f"Failed to download SEO image for topic {topic.id}: {e}"
                        )

                    progress.advance(seo_task, 1)

                progress.update(
                    seo_task,
                    description=(
                        f"[green]✓ Downloaded {seo_images_downloaded} "
                        "SEO images "
                        f"({len(topics_with_seo_images) - seo_images_downloaded} "
                        "failed)"
                    ),
                )
                update_stats_display()

            phase_times["assets"] = time_module.time() - phase_start

    # Step 6: Export to requested formats
    export_times = {}

    if "none" in formats:
        console.print("\n[bold]Skipping export (--formats none)[/bold]")
    else:
        console.print("\n[bold]Exporting to formats...[/bold]")

        # Create progress context for exports
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            CompactTimeElapsedColumn(),
            console=console,
        ) as export_progress:
            if "hybrid" in formats:
                # Hybrid export - both HTML and Markdown
                try:
                    phase_start = time_module.time()
                    exporter = HybridExporter(
                        db,
                        output_dir,
                        include_html=True,
                        include_md=True,
                        asset_downloader=asset_downloader if not text_only else None,
                        include_users=include_users,
                        posts_per_page=config.posts_per_page,
                        pagination_enabled=config.pagination_enabled,
                        config={"export": config.__dict__}
                        if hasattr(config, "__dict__")
                        else {},
                        progress=export_progress,
                        search_backend=search_backend,
                    )
                    exporter.export()
                    db.record_export(
                        "hybrid",
                        len(all_topics),
                        sum(t.posts_count for t in all_topics),
                        str(output_dir),
                    )
                    export_times["hybrid"] = time_module.time() - phase_start
                except Exception as e:
                    console.print(f"[red]✗ Hybrid export failed: {e}[/red]")
                    log.exception("Hybrid export failed")
            else:
                # Individual format exports
                if "html" in formats:
                    try:
                        phase_start = time_module.time()
                        html_dir = output_dir / "html"
                        exporter = HTMLStaticExporter(
                            db,
                            html_dir,
                            include_users=include_users,
                            posts_per_page=config.posts_per_page,
                            pagination_enabled=config.pagination_enabled,
                            progress=export_progress,
                            search_backend=search_backend,
                        )
                        exporter.export()
                        db.record_export(
                            "html",
                            len(all_topics),
                            sum(t.posts_count for t in all_topics),
                            str(html_dir),
                        )
                        export_times["html"] = time_module.time() - phase_start
                    except Exception as e:
                        console.print(f"[red]✗ HTML export failed: {e}[/red]")
                        log.exception("HTML export failed")

                if "md" in formats or "github" in formats:
                    # Support both 'md' and 'github' for backwards compatibility
                    try:
                        phase_start = time_module.time()
                        md_dir = output_dir / "md"
                        exporter = MarkdownGitHubExporter(
                            db,
                            md_dir,
                            asset_downloader=asset_downloader
                            if not text_only
                            else None,
                            posts_per_page=config.posts_per_page,
                            pagination_enabled=config.pagination_enabled,
                            include_users=include_users,
                            progress=export_progress,
                        )
                        exporter.export()
                        format_name = "md" if "md" in formats else "github"
                        db.record_export(
                            format_name,
                            len(all_topics),
                            sum(t.posts_count for t in all_topics),
                            str(md_dir),
                        )
                        export_times[format_name] = time_module.time() - phase_start
                    except Exception as e:
                        console.print(f"[red]✗ Markdown export failed: {e}[/red]")
                        log.exception("Markdown export failed")

    # Calculate overall time
    overall_elapsed = time_module.time() - overall_start

    # Get API client statistics
    api_stats = client.get_stats()

    # Display statistics
    stats = db.get_statistics()
    console.print("\n[bold]Archive Statistics:[/bold]")
    console.print(f"  Categories: {stats['total_categories']}")
    console.print(f"  Topics: {stats['total_topics']}")
    console.print(f"  Posts: {stats['total_posts']}")
    console.print(f"  Users: {stats['total_users']}")

    # Display timing information
    console.print("\n[bold]Performance:[/bold]")
    console.print(f"  Total time: {overall_elapsed:.1f}s ({overall_elapsed / 60:.1f}m)")

    if "categories" in phase_times:
        console.print(f"  Fetching categories: {phase_times['categories']:.1f}s")
    if "topics" in phase_times:
        console.print(f"  Fetching topics: {phase_times['topics']:.1f}s")
    if "topics_sweep" in phase_times:
        console.print(f"  ID sweep: {phase_times['topics_sweep']:.1f}s")
    if "posts" in phase_times:
        console.print(f"  Fetching posts: {phase_times['posts']:.1f}s")
    if "assets" in phase_times:
        console.print(f"  Downloading assets: {phase_times['assets']:.1f}s")

    for format_name, duration in export_times.items():
        console.print(f"  Exporting {format_name}: {duration:.1f}s")

    # Display request statistics
    console.print("\n[bold]Network Statistics:[/bold]")
    console.print(f"  API requests: {api_stats['requests_made']}")
    console.print(f"  Successful: {api_stats['requests_successful']}")
    console.print(f"  Failed: {api_stats['requests_failed']}")
    console.print(f"  Retries: {api_stats['retries_attempted']}")
    console.print(
        f"  Data transferred: {api_stats['bytes_transferred'] / 1024 / 1024:.1f} MB"
    )
    console.print(f"  Request rate: {api_stats['request_rate']:.2f} req/s")

    # Display asset statistics (if assets were downloaded)
    if not text_only and asset_downloader:
        asset_stats = asset_downloader.get_stats()
        console.print("\n[bold]Asset Statistics:[/bold]")
        console.print(f"  Total assets: {asset_stats['total_queued']}")
        console.print(f"  Downloaded: {asset_stats['downloaded']}")
        console.print(f"  Cached (skipped): {asset_stats['cached']}")
        console.print(f"  Failed: {asset_stats['failed']}")
        console.print(
            "  Data transferred: "
            f"{asset_stats['bytes_downloaded'] / 1024 / 1024:.1f} MB"
        )
        console.print(f"  Download rate: {asset_stats['download_rate']:.2f} assets/s")

    # Close database
    db.close()


def run_update(args: argparse.Namespace, config: Config) -> None:
    """Execute update command."""
    console.print("[bold blue]Updating archives...[/bold blue]")

    # Find database in output directory
    db_path = args.output_dir / "archive.db"
    if not db_path.exists():
        console.print(f"[red]Error: No archive database found at {db_path}[/red]")
        console.print(
            "[yellow]Hint: Use 'chronicon archive' to create a new "
            "archive first[/yellow]"
        )
        return

    # Open database
    try:
        db = ArchiveDatabase(db_path)
    except Exception as e:
        console.print(f"[red]Error opening database: {e}[/red]")
        return

    # Get site metadata to determine site URL
    # We need to find at least one site_url in the metadata table
    try:
        # Get all site metadata entries
        cursor = db.connection.cursor()
        cursor.execute("SELECT site_url FROM site_metadata LIMIT 1")
        row = cursor.fetchone()

        if not row:
            console.print("[red]Error: No site metadata found in database[/red]")
            console.print(
                "[yellow]This archive may have been created without "
                "site metadata.[/yellow]"
            )
            db.close()
            return

        site_url = row["site_url"]
        log.info(f"Found site: {site_url}")

    except Exception as e:
        console.print(f"[red]Error reading site metadata: {e}[/red]")
        db.close()
        return

    # Initialize API client
    try:
        client = DiscourseAPIClient(site_url, rate_limit=config.rate_limit)
    except Exception as e:
        console.print(f"[red]Error initializing API client: {e}[/red]")
        db.close()
        return

    # Initialize update manager
    update_manager = UpdateManager(db, client)

    # Run incremental update
    try:
        console.print("[bold]Fetching new and modified content...[/bold]")
        stats = update_manager.update_archive(site_url)

        # Display summary
        console.print("\n[bold green]Update Summary:[/bold green]")
        console.print(f"  New posts: {stats.new_posts}")
        console.print(f"  Modified posts: {stats.modified_posts}")
        console.print(f"  New topics: {stats.new_topics}")
        console.print(f"  Topics needing regeneration: {stats.affected_topics}")
        console.print(f"  Fetch errors: {stats.fetch_errors}")
        console.print(f"  Duration: {stats.duration_seconds:.2f}s")

        # Check if there's anything to regenerate
        if stats.affected_topics == 0:
            console.print(
                "\n[green]Archive is up to date! No topics need regeneration.[/green]"
            )
            db.close()
            return

    except Exception as e:
        console.print(f"[red]Error during update: {e}[/red]")
        import traceback

        traceback.print_exc()
        db.close()
        return

    # Refresh site metadata before regenerating exports
    console.print("\n[bold]Refreshing site metadata...[/bold]")
    try:
        site_config_fetcher = SiteConfigFetcher(client, db)
        site_config_fetcher.fetch_and_store_site_metadata()
        console.print("[green]✓ Site metadata refreshed[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not refresh site metadata: {e}[/yellow]")
        log.warning(f"Site metadata refresh failed: {e}")

    # Get list of topics to regenerate
    topic_ids = list(update_manager.get_topics_to_regenerate())
    affected_usernames = update_manager.get_affected_usernames()

    # Download assets for affected topics (medium + highest resolution)
    console.print("\n[bold]Downloading assets for affected topics...[/bold]")
    try:
        html_processor = HTMLProcessor()
        asset_downloader = AssetDownloader(client, db, args.output_dir)
        for topic_id in topic_ids:
            posts = db.get_topic_posts(topic_id)
            for post in posts:
                if post.cooked:
                    try:
                        image_sets = html_processor.extract_image_sets(post.cooked)
                        for _base_id, img_set in image_sets.items():
                            if img_set["medium"] and img_set["medium"] not in [
                                None,
                                "",
                            ]:
                                try:
                                    asset_downloader.download_image(
                                        img_set["medium"], topic_id
                                    )
                                except Exception as img_err:
                                    log.debug(
                                        "Failed to download medium "
                                        f"resolution: {img_err}"
                                    )
                            if (
                                img_set["highest"]
                                and img_set["highest"] not in [None, ""]
                                and img_set["highest"] != img_set["medium"]
                            ):
                                try:
                                    asset_downloader.download_image(
                                        img_set["highest"], topic_id
                                    )
                                except Exception as img_err:
                                    log.debug(
                                        "Failed to download highest "
                                        f"resolution: {img_err}"
                                    )
                    except Exception as e:
                        log.error(f"Error processing HTML for post {post.id}: {e}")
        console.print("[green]✓ Asset download complete[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Asset download error: {e}[/yellow]")
        log.warning(f"Asset download during update failed: {e}")

    # Determine which formats to regenerate
    formats = (
        args.formats.split(",") if args.formats != "all" else ["html", "md", "hybrid"]
    )

    # Regenerate exports for affected topics
    console.print(f"\n[bold]Regenerating exports for {len(topic_ids)} topics...[/bold]")

    # Create progress context for export regeneration
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )

    from chronicon.utils.progress import CompactTimeElapsedColumn

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            CompactTimeElapsedColumn(),
            console=console,
        ) as regen_progress:
            # HTML export
            if "html" in formats:
                html_dir = args.output_dir / "html"
                if html_dir.exists():
                    task = regen_progress.add_task(
                        f"[cyan]Updating HTML export ({len(topic_ids)} topics)...",
                        total=len(topic_ids),
                    )
                    html_exporter = HTMLStaticExporter(
                        db,
                        html_dir,
                        include_users=config.include_users,
                        posts_per_page=config.posts_per_page,
                        pagination_enabled=config.pagination_enabled,
                        progress=regen_progress,
                    )
                    html_exporter.export_topics(topic_ids)
                    html_exporter.update_index()
                    if affected_usernames:
                        html_exporter.export_users_by_username(affected_usernames)
                    db.record_export(
                        "html",
                        stats.affected_topics,
                        stats.new_posts + stats.modified_posts,
                        str(html_dir),
                    )
                    regen_progress.update(
                        task, description="[green]✓ HTML export updated"
                    )
                else:
                    console.print(
                        "[yellow]⚠ HTML export directory not found, skipping[/yellow]"
                    )

            # Hybrid export
            if "hybrid" in formats:
                if (args.output_dir / "index.html").exists() or (
                    args.output_dir / "md"
                ).exists():
                    task = regen_progress.add_task(
                        f"[cyan]Updating Hybrid export ({len(topic_ids)} topics)...",
                        total=len(topic_ids),
                    )
                    hybrid_exporter = HybridExporter(
                        db,
                        args.output_dir,
                        include_html=True,
                        include_md=True,
                        include_users=config.include_users,
                        progress=regen_progress,
                    )
                    hybrid_exporter.export_topics(topic_ids)
                    hybrid_exporter.update_index()
                    if affected_usernames:
                        hybrid_exporter.export_users_by_username(affected_usernames)
                    db.record_export(
                        "hybrid",
                        stats.affected_topics,
                        stats.new_posts + stats.modified_posts,
                        str(args.output_dir),
                    )
                    regen_progress.update(
                        task, description="[green]✓ Hybrid export updated"
                    )
                else:
                    console.print(
                        "[yellow]⚠ Hybrid export not found, skipping[/yellow]"
                    )

            # Markdown export (support both 'md' and 'github')
            if "md" in formats or "github" in formats:
                md_dir = args.output_dir / "md"
                if md_dir.exists():
                    task = regen_progress.add_task(
                        f"[cyan]Updating Markdown export ({len(topic_ids)} topics)...",
                        total=len(topic_ids),
                    )
                    md_exporter = MarkdownGitHubExporter(
                        db,
                        md_dir,
                        include_users=config.include_users,
                        progress=regen_progress,
                    )
                    md_exporter.export_topics(topic_ids)
                    md_exporter.update_index()
                    if affected_usernames:
                        md_exporter.export_users_by_username(affected_usernames)
                    format_name = "md" if "md" in formats else "github"
                    db.record_export(
                        format_name,
                        stats.affected_topics,
                        stats.new_posts + stats.modified_posts,
                        str(md_dir),
                    )
                    regen_progress.update(
                        task, description="[green]✓ Markdown export updated"
                    )
                else:
                    console.print(
                        "[yellow]⚠ Markdown export dir not found, skipping[/yellow]"
                    )

        console.print("\n[bold green]✓ Archive update complete![/bold green]")

    except Exception as e:
        console.print(f"[red]Error during export regeneration: {e}[/red]")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


def run_validate(args: argparse.Namespace, config: Config) -> None:
    """Execute validate command."""
    console.print("[bold blue]Validating archive...[/bold blue]\n")

    output_dir = Path(args.output_dir)

    # Check if output directory exists
    if not output_dir.exists():
        console.print(f"[red]✗ Output directory does not exist: {output_dir}[/red]")
        return

    issues = []
    warnings = []

    # Check 1: Database exists and is readable
    db_path = output_dir / "archive.db"
    if not db_path.exists():
        console.print("[red]✗ Database file not found[/red]")
        issues.append("Database file missing")
        return  # Can't continue without database

    console.print("[green]✓ Database file found[/green]")

    # Try to open database
    try:
        db = ArchiveDatabase(db_path)
        console.print("[green]✓ Database is readable[/green]")
    except Exception as e:
        console.print(f"[red]✗ Cannot open database: {e}[/red]")
        issues.append(f"Database error: {e}")
        return

    # Check 2: Get and display statistics
    try:
        stats = db.get_statistics()
        console.print("\n[bold]Archive Statistics:[/bold]")
        console.print(f"  Categories: {stats['total_categories']}")
        console.print(f"  Topics: {stats['total_topics']}")
        console.print(f"  Posts: {stats['total_posts']}")
        console.print(f"  Users: {stats['total_users']}")

        if stats["total_topics"] == 0:
            warnings.append("No topics found in archive")
        if stats["total_posts"] == 0:
            warnings.append("No posts found in archive")

    except Exception as e:
        console.print(f"[red]✗ Error reading statistics: {e}[/red]")
        issues.append(f"Statistics error: {e}")

    # Check 3: Validate export directories based on export history
    console.print("\n[bold]Checking Export Directories:[/bold]")

    try:
        export_history = db.get_export_history(limit=100)

        if not export_history:
            console.print("[yellow]⚠ No export history found[/yellow]")
            warnings.append("No exports have been performed yet")
        else:
            # Group by format to check most recent export of each type
            formats_checked = set()

            for export in export_history:
                export_format = export["format"]

                # Only check each format once (most recent)
                if export_format in formats_checked:
                    continue
                formats_checked.add(export_format)

                export_dir = Path(export["output_path"])

                # Check HTML export
                if export_format == "html":
                    console.print("  Checking HTML export...")
                    if not export_dir.exists():
                        console.print(
                            f"    [red]✗ HTML directory not found: {export_dir}[/red]"
                        )
                        issues.append("HTML export directory missing")
                    else:
                        # Check critical files
                        if (export_dir / "index.html").exists():
                            console.print("    [green]✓ index.html present[/green]")
                        else:
                            console.print("    [red]✗ index.html missing[/red]")
                            issues.append("HTML export missing index.html")

                        if (export_dir / "assets").exists():
                            console.print(
                                "    [green]✓ assets directory present[/green]"
                            )
                        else:
                            console.print(
                                "    [yellow]⚠ assets directory missing[/yellow]"
                            )
                            warnings.append("HTML export missing assets directory")

                # Check Hybrid export
                elif export_format == "hybrid":
                    console.print("  Checking Hybrid export...")
                    if not export_dir.exists():
                        console.print(
                            f"    [red]✗ Hybrid directory not found: {export_dir}[/red]"
                        )
                        issues.append("Hybrid export directory missing")
                    else:
                        # Check for HTML components
                        if (export_dir / "index.html").exists():
                            console.print("    [green]✓ index.html present[/green]")
                        else:
                            console.print("    [yellow]⚠ index.html missing[/yellow]")
                            warnings.append("Hybrid export missing index.html")

                        # Check for Markdown components
                        if (export_dir / "md").exists():
                            console.print("    [green]✓ md directory present[/green]")
                        else:
                            console.print("    [yellow]⚠ md directory missing[/yellow]")
                            warnings.append("Hybrid export missing md directory")

                        # Check for root README
                        if (export_dir / "README.md").exists():
                            console.print("    [green]✓ README.md present[/green]")
                        else:
                            console.print("    [yellow]⚠ README.md missing[/yellow]")
                            warnings.append("Hybrid export missing README.md")

                        # Check for shared assets
                        if (export_dir / "assets").exists():
                            console.print(
                                "    [green]✓ assets directory present[/green]"
                            )
                        else:
                            console.print(
                                "    [yellow]⚠ assets directory missing[/yellow]"
                            )
                            warnings.append("Hybrid export missing assets directory")

                # Check Markdown export (md or github format)
                elif export_format in ("md", "github"):
                    console.print("  Checking Markdown export...")
                    if not export_dir.exists():
                        console.print(
                            f"    [red]✗ Markdown dir not found: {export_dir}[/red]"
                        )
                        issues.append("Markdown export directory missing")
                    else:
                        if (export_dir / "README.md").exists():
                            console.print("    [green]✓ README.md present[/green]")
                        else:
                            console.print("    [red]✗ README.md missing[/red]")
                            issues.append("Markdown export missing README.md")

                        if (export_dir / "t").exists():
                            console.print("    [green]✓ t directory present[/green]")
                        else:
                            console.print("    [red]✗ t directory missing[/red]")
                            issues.append("Markdown export missing t directory")

    except Exception as e:
        console.print(f"[red]✗ Error checking exports: {e}[/red]")
        issues.append(f"Export check error: {e}")

    # Check 4: Database integrity - check for orphaned posts
    console.print("\n[bold]Checking Data Integrity:[/bold]")

    try:
        # Check for posts without topics
        cursor = db.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM posts
            WHERE topic_id NOT IN (SELECT id FROM topics)
        """)
        orphaned_posts = cursor.fetchone()["count"]

        if orphaned_posts > 0:
            console.print(
                f"  [yellow]⚠ Found {orphaned_posts} orphaned posts "
                "(posts without topics)[/yellow]"
            )
            warnings.append(f"{orphaned_posts} orphaned posts")
        else:
            console.print("  [green]✓ No orphaned posts[/green]")

        # Check for topics without categories
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM topics
            WHERE category_id IS NOT NULL
              AND category_id NOT IN (SELECT id FROM categories)
        """)
        orphaned_topics = cursor.fetchone()["count"]

        if orphaned_topics > 0:
            console.print(
                f"  [yellow]⚠ Found {orphaned_topics} topics with "
                "missing categories[/yellow]"
            )
            warnings.append(f"{orphaned_topics} topics with missing categories")
        else:
            console.print("  [green]✓ All topics have valid categories[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error checking data integrity: {e}[/red]")
        issues.append(f"Data integrity check error: {e}")

    # Close database
    db.close()

    # Summary
    console.print("\n[bold]Validation Summary:[/bold]")

    if not issues and not warnings:
        console.print("[bold green]✓ Archive is valid with no issues![/bold green]")
    elif issues:
        console.print(f"[bold red]✗ Found {len(issues)} critical issue(s):[/bold red]")
        for issue in issues:
            console.print(f"  - {issue}")
        if warnings:
            console.print(f"\n[yellow]⚠ Found {len(warnings)} warning(s):[/yellow]")
            for warning in warnings:
                console.print(f"  - {warning}")
    elif warnings:
        console.print(
            f"[yellow]⚠ Archive is valid but has {len(warnings)} warning(s):[/yellow]"
        )
        for warning in warnings:
            console.print(f"  - {warning}")


def run_migrate(args: argparse.Namespace, config: Config) -> None:
    """Execute migrate command."""
    from .storage.migrations import JSONMigrator

    console.print("[bold blue]Migrating from JSON...[/bold blue]\n")

    source_dir = Path(args.source_dir)

    # Check if source directory exists
    if not source_dir.exists():
        console.print(f"[red]✗ Source directory does not exist: {source_dir}[/red]")
        return

    # Check if there are JSON files to migrate
    json_files = list(source_dir.glob("*.json"))
    if not json_files:
        console.print(f"[yellow]⚠ No JSON files found in {source_dir}[/yellow]")
        return

    console.print(f"Found {len(json_files)} JSON files to migrate")

    # Determine output directory (same as source or specified?)
    # For now, use source_dir parent with 'migrated' suffix
    output_dir = source_dir.parent / f"{source_dir.name}_migrated"
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"Output directory: {output_dir}\n")

    # Initialize database
    db_path = output_dir / "archive.db"
    db = ArchiveDatabase(db_path)

    # Initialize migrator
    migrator = JSONMigrator(db)

    # Perform migration with progress tracking
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Migrating data from JSON files...", total=None
            )

            stats = migrator.migrate_from_json(source_dir)

            progress.update(
                task, completed=True, description="[green]✓ Migration complete"
            )

        # Display statistics
        console.print("\n[bold]Migration Statistics:[/bold]")
        console.print(f"  Posts imported: {stats['posts_imported']}")
        console.print(f"  Topics imported: {stats['topics_imported']}")

        if stats["errors"] > 0:
            console.print(f"  [yellow]Errors encountered: {stats['errors']}[/yellow]")
        else:
            console.print("  [green]No errors![/green]")

    except Exception as e:
        console.print(f"\n[red]✗ Migration failed: {e}[/red]")
        log.exception("Migration failed")
        db.close()
        return

    # If format specified, export after migration
    if args.format:
        console.print(f"\n[bold]Exporting to {args.format} format...[/bold]")

        try:
            if args.format == "html":
                html_dir = output_dir / "html"
                exporter = HTMLStaticExporter(
                    db,
                    html_dir,
                    posts_per_page=config.posts_per_page,
                    pagination_enabled=config.pagination_enabled,
                )
                exporter.export()
                console.print("[green]✓ HTML export complete[/green]")

            elif args.format == "md":
                md_dir = output_dir / "md"
                exporter = MarkdownGitHubExporter(db, md_dir)
                exporter.export()
                console.print("[green]✓ Markdown export complete[/green]")

            elif args.format == "hybrid":
                exporter = HybridExporter(
                    db,
                    output_dir,
                    include_html=True,
                    include_md=True,
                )
                exporter.export()
                console.print("[green]✓ Hybrid export complete[/green]")

        except Exception as e:
            console.print(f"[red]✗ Export failed: {e}[/red]")
            log.exception("Export after migration failed")

    # Close database
    db.close()

    console.print("\n[bold green]✓ Migration complete![/bold green]")
    console.print(f"Archive saved to: {output_dir}")


def run_watch(args: argparse.Namespace, config: Config) -> None:
    """Execute watch command."""
    # Handle subcommands or default to start
    action = getattr(args, "watch_action", None) or "start"

    if action == "start" or action is None:
        # Start watching
        console.print("[bold blue]Starting watch mode...[/bold blue]\n")

        output_dir = Path(args.output_dir)

        # Parse formats if specified
        formats = None
        if hasattr(args, "formats") and args.formats:
            formats = [fmt.strip() for fmt in args.formats.split(",")]

        # Check if daemon mode
        daemon_mode = getattr(args, "daemon", False)

        if daemon_mode:
            console.print("[yellow]Daemon mode not yet implemented[/yellow]")
            console.print("[yellow]Running in foreground mode instead[/yellow]\n")

        # Create and start daemon
        daemon = WatchDaemon(
            output_dir=output_dir, config=config, formats=formats, daemon_mode=False
        )

        try:
            daemon.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            log.exception("Watch mode failed")
            sys.exit(1)

    elif action == "stop":
        # Stop daemon
        output_dir = Path(args.output_dir)
        console.print("[bold]Stopping watch daemon...[/bold]")

        if WatchDaemon.stop_daemon(output_dir):
            console.print("[green]✓ Daemon stopped[/green]")
        else:
            console.print("[yellow]No daemon running[/yellow]")

    elif action == "status":
        # Show status
        output_dir = Path(args.output_dir)
        console.print("[bold]Watch daemon status:[/bold]\n")

        status = WatchDaemon.get_status(output_dir)

        if status is None:
            console.print("[yellow]No status file found[/yellow]")
            console.print("[dim]Daemon has not been run yet[/dim]")
            return

        # Display status
        if status.is_running:
            console.print(f"[green]● Running[/green] (PID: {status.pid})")
        else:
            console.print("[red]● Stopped[/red]")

        console.print("\n[bold]Uptime:[/bold]")
        console.print(f"  Started: {status.started_at}")
        console.print(f"  Uptime: {status.uptime_seconds / 3600:.1f} hours")

        console.print("\n[bold]Cycles:[/bold]")
        console.print(f"  Total: {status.total_cycles}")
        console.print(f"  Successful: {status.successful_cycles}")
        console.print(f"  Failed: {status.failed_cycles}")
        console.print(f"  Consecutive errors: {status.consecutive_errors}")

        console.print("\n[bold]Updates:[/bold]")
        console.print(f"  Total new posts: {status.total_new_posts}")
        console.print(f"  Total modified posts: {status.total_modified_posts}")
        console.print(f"  Total affected topics: {status.total_affected_topics}")

        if status.last_check:
            console.print("\n[bold]Last Check:[/bold]")
            console.print(f"  Time: {status.last_check}")

        if status.next_check:
            console.print("\n[bold]Next Check:[/bold]")
            console.print(f"  Time: {status.next_check}")

        if status.last_error:
            console.print("\n[bold red]Last Error:[/bold red]")
            console.print(f"  {status.last_error}")

        # Show recent cycles
        if status.recent_cycles:
            console.print("\n[bold]Recent Cycles:[/bold]")
            for cycle in status.recent_cycles[-10:]:  # Show last 10
                timestamp = cycle.timestamp[:19]  # Truncate to second precision
                if cycle.success:
                    if cycle.new_posts > 0 or cycle.modified_posts > 0:
                        console.print(
                            f"  [green]✓[/green] {timestamp}: "
                            f"{cycle.new_posts} new, {cycle.modified_posts} modified, "
                            f"{cycle.affected_topics} topics "
                            f"({cycle.duration_seconds:.1f}s)"
                        )
                    else:
                        console.print(
                            f"  [dim]✓[/dim] {timestamp}: "
                            f"No changes ({cycle.duration_seconds:.1f}s)"
                        )
                else:
                    console.print(
                        f"  [red]✗[/red] {timestamp}: Failed - {cycle.error_message}"
                    )


def run_serve(args: argparse.Namespace, config: Config) -> None:
    """Execute serve command to start REST API server."""
    import os

    console.print("[bold blue]Starting REST API server...[/bold blue]")

    # Check for DATABASE_URL environment variable
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        console.print("[red]Error: DATABASE_URL environment variable not set.[/red]")
        console.print(
            "Set it to your database path, e.g.:\n"
            "  export DATABASE_URL=sqlite:///./archives/meta.discourse.org/archive.db\n"
            "  export DATABASE_URL=postgresql://localhost/chronicon"
        )
        sys.exit(1)

    console.print(f"Database: {database_url}")
    console.print(f"Server: http://{args.host}:{args.port}")
    console.print("Docs: http://{args.host}:{args.port}/docs")
    console.print("\nPress Ctrl+C to stop the server\n")

    try:
        import uvicorn

        from chronicon.api.app import app

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info" if not args.debug else "debug",
        )
    except ImportError:
        console.print(
            "[red]Error: FastAPI and uvicorn are required for the API server.[/red]"
        )
        console.print("Install with: pip install chronicon[api]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")


def run_mcp(args: argparse.Namespace, config: Config) -> None:
    """Execute mcp command to start MCP server."""
    import asyncio
    import os

    # Check for DATABASE_URL environment variable
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        console.print(
            "[red]Error: DATABASE_URL environment variable not set.[/red]",
            file=sys.stderr,
        )
        console.print(
            "Set it to your database path, e.g.:\n"
            "  export DATABASE_URL=sqlite:///./archives/meta.discourse.org/archive.db\n"
            "  export DATABASE_URL=postgresql://localhost/chronicon",
            file=sys.stderr,
        )
        sys.exit(1)

    log.info(f"Starting MCP server with database: {database_url}")

    try:
        from chronicon.mcp.server import main as mcp_main

        asyncio.run(mcp_main())
    except ImportError:
        console.print(
            "[red]Error: MCP server dependencies are required.[/red]",
            file=sys.stderr,
        )
        console.print(
            "Install with: pip install chronicon[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("MCP server stopped by user")


def run_rebuild_search_index(args: argparse.Namespace, config: Config) -> None:
    """Execute rebuild-search-index command."""
    console.print("[bold blue]Rebuilding search index...[/bold blue]")

    # Find all archive databases in output directory
    output_dir = args.output_dir
    if not output_dir.exists():
        console.print(f"[red]Error: Output directory not found: {output_dir}[/red]")
        sys.exit(1)

    # Look for archive.db files
    db_files = list(output_dir.rglob("archive.db"))
    if not db_files:
        console.print(f"[red]Error: No archive.db files found in {output_dir}[/red]")
        sys.exit(1)

    console.print(f"Found {len(db_files)} database(s)")

    from chronicon.storage.database import ArchiveDatabase

    for db_file in db_files:
        console.print(f"\n[cyan]Processing: {db_file.relative_to(output_dir)}[/cyan]")

        try:
            db = ArchiveDatabase(db_file)

            # Check if search is available
            if not db.is_search_available():
                console.print(
                    "  [yellow]Search not available in this database[/yellow]"
                )
                continue

            # Get counts before rebuild
            stats = db.get_statistics()
            topics_count = stats["total_topics"]
            posts_count = stats["total_posts"]

            console.print(f"  Topics: {topics_count}")
            console.print(f"  Posts: {posts_count}")

            # Rebuild index
            console.print("  [yellow]Rebuilding index...[/yellow]")
            db.rebuild_search_index()

            console.print("  [green]✓ Search index rebuilt successfully[/green]")

        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")
            log.exception(f"Failed to rebuild search index for {db_file}")

    console.print("\n[bold green]Search index rebuild complete![/bold green]")


def run_backfill_posts(args: argparse.Namespace, config: Config) -> None:
    """Execute backfill-posts command to fetch missing post content."""
    import os

    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )

    from chronicon.utils.progress import CompactTimeElapsedColumn

    console.print("[bold blue]Backfilling missing posts...[/bold blue]")

    output_dir = args.output_dir
    if not output_dir.exists():
        console.print(f"[red]Error: Output directory not found: {output_dir}[/red]")
        sys.exit(1)

    # Check for DATABASE_URL environment variable
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from chronicon.storage.factory import get_database

        db = get_database(database_url)
        log.info("Using PostgreSQL database from DATABASE_URL")
    else:
        db_path = output_dir / "archive.db"
        if not db_path.exists():
            console.print(f"[red]Error: No archive database found at {db_path}[/red]")
            sys.exit(1)
        db = ArchiveDatabase(db_path)
        log.info(f"Using SQLite database: {db_path}")

    # Get site URL for API client
    site_url = db.get_first_site_url()
    if not site_url:
        console.print("[red]Error: No site metadata found in database[/red]")
        db.close()
        sys.exit(1)

    console.print(f"Site: {site_url}")

    # Load category filter from database
    category_ids = db.get_category_filter(site_url)
    if category_ids:
        console.print(f"Category filter: {category_ids}")
        log.info(f"Using category filter: {category_ids}")

    # Build query with optional category filter
    base_query = """
        SELECT t.id, t.title
        FROM topics t
        LEFT JOIN posts p ON t.id = p.topic_id
        WHERE t.posts_count > 0
    """
    if category_ids:
        placeholders = ",".join("?" * len(category_ids))
        base_query += f" AND t.category_id IN ({placeholders})"

    count_query = (
        f"SELECT COUNT(*) FROM ({base_query} GROUP BY t.id HAVING COUNT(p.id) = 0) sub"
    )

    # Check how many topics need backfill
    cursor = db.connection.cursor()
    if category_ids:
        cursor.execute(count_query, category_ids)
    else:
        cursor.execute(count_query)
    total_missing = cursor.fetchone()[0]

    if total_missing == 0:
        console.print("[green]No topics with missing posts found![/green]")
        db.close()
        return

    limit = args.limit
    to_process = min(total_missing, limit) if limit else total_missing
    console.print(f"Found {total_missing} topics with missing posts")
    console.print(f"Will backfill: {to_process} topics")

    # Initialize API client
    client = DiscourseAPIClient(site_url, rate_limit=config.rate_limit)

    # Run backfill with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        CompactTimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[cyan]Backfilling {to_process} topics...", total=to_process
        )

        backfilled = 0
        errors = 0

        # Get topics to backfill
        query = base_query + " GROUP BY t.id HAVING COUNT(p.id) = 0"
        if limit:
            query += f" LIMIT {limit}"
        if category_ids:
            cursor.execute(query, category_ids)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()

        from chronicon.fetchers.topics import TopicFetcher

        topic_fetcher = TopicFetcher(client, db)

        for row in rows:
            topic_id = row[0]
            try:
                posts = topic_fetcher.fetch_topic_posts(topic_id)
                for post in posts:
                    db.insert_post(post)
                backfilled += 1
            except Exception as e:
                errors += 1
                log.error(f"Error backfilling topic {topic_id}: {e}")

            progress.advance(task, 1)

            # Update description periodically
            if backfilled % 50 == 0:
                progress.update(
                    task,
                    description=(
                        f"[cyan]Backfilling... ({backfilled} done, {errors} errors)"
                    ),
                )

        progress.update(
            task,
            description=f"[green]✓ Backfilled {backfilled} topics ({errors} errors)",
        )

    console.print("\n[bold green]Backfill complete![/bold green]")
    console.print(f"  Topics processed: {backfilled}")
    console.print(f"  Errors: {errors}")

    db.close()


def run_export(args: argparse.Namespace, config: Config) -> None:
    """Execute standalone export command against an existing database."""
    import json as json_module
    import os
    import time as time_module

    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )

    from chronicon.utils.progress import CompactTimeElapsedColumn

    console.print("[bold blue]Exporting from existing archive...[/bold blue]")

    output_dir = Path(args.output_dir)

    # Open database - check DATABASE_URL first, fall back to SQLite file
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from chronicon.storage.factory import get_database

        db = get_database(database_url)
        log.info("Using database from DATABASE_URL")
    else:
        db_path = output_dir / "archive.db"
        if not db_path.exists():
            console.print(f"[red]Error: No archive database found at {db_path}[/red]")
            console.print(
                "[yellow]Hint: Use 'chronicon archive' to create an "
                "archive first[/yellow]"
            )
            return
        db = ArchiveDatabase(db_path)
        log.info(f"Using SQLite database: {db_path}")

    # Validate data
    stats = db.get_statistics()
    if stats["total_topics"] == 0:
        console.print(
            "[yellow]Warning: Database is empty (no topics found). "
            "Export may produce empty output.[/yellow]"
        )

    console.print(
        f"  Database: {stats['total_topics']} topics, "
        f"{stats['total_posts']} posts, "
        f"{stats['total_users']} users"
    )

    # Parse formats
    formats = [fmt.strip() for fmt in args.formats.split(",")]
    include_users = args.include_users
    search_backend = args.search_backend

    overall_start = time_module.time()
    export_times = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        CompactTimeElapsedColumn(),
        console=console,
    ) as export_progress:
        # Hybrid export
        if "hybrid" in formats:
            try:
                phase_start = time_module.time()
                exporter = HybridExporter(
                    db,
                    output_dir,
                    include_html=True,
                    include_md=True,
                    include_users=include_users,
                    posts_per_page=config.posts_per_page,
                    pagination_enabled=config.pagination_enabled,
                    progress=export_progress,
                    search_backend=search_backend,
                )
                exporter.export()
                all_topics = db.get_all_topics()
                db.record_export(
                    "hybrid",
                    len(all_topics),
                    sum(t.posts_count for t in all_topics),
                    str(output_dir),
                )
                export_times["hybrid"] = time_module.time() - phase_start
                console.print("[green]✓ Hybrid export complete[/green]")
            except Exception as e:
                console.print(f"[red]✗ Hybrid export failed: {e}[/red]")
                log.exception("Hybrid export failed")

        # HTML export
        if "html" in formats and "hybrid" not in formats:
            try:
                phase_start = time_module.time()
                html_dir = output_dir / "html"
                exporter = HTMLStaticExporter(
                    db,
                    html_dir,
                    include_users=include_users,
                    posts_per_page=config.posts_per_page,
                    pagination_enabled=config.pagination_enabled,
                    progress=export_progress,
                    search_backend=search_backend,
                )
                exporter.export()
                all_topics = db.get_all_topics()
                db.record_export(
                    "html",
                    len(all_topics),
                    sum(t.posts_count for t in all_topics),
                    str(html_dir),
                )
                export_times["html"] = time_module.time() - phase_start
                console.print("[green]✓ HTML export complete[/green]")
            except Exception as e:
                console.print(f"[red]✗ HTML export failed: {e}[/red]")
                log.exception("HTML export failed")

        # Markdown export
        if ("md" in formats or "github" in formats) and "hybrid" not in formats:
            try:
                phase_start = time_module.time()
                md_dir = output_dir / "md"
                exporter = MarkdownGitHubExporter(
                    db,
                    md_dir,
                    posts_per_page=config.posts_per_page,
                    pagination_enabled=config.pagination_enabled,
                    include_users=include_users,
                    progress=export_progress,
                )
                exporter.export()
                format_name = "md" if "md" in formats else "github"
                all_topics = db.get_all_topics()
                db.record_export(
                    format_name,
                    len(all_topics),
                    sum(t.posts_count for t in all_topics),
                    str(md_dir),
                )
                export_times[format_name] = time_module.time() - phase_start
                console.print("[green]✓ Markdown export complete[/green]")
            except Exception as e:
                console.print(f"[red]✗ Markdown export failed: {e}[/red]")
                log.exception("Markdown export failed")

        # JSON export
        if "json" in formats:
            try:
                phase_start = time_module.time()
                json_dir = output_dir / "json"
                json_dir.mkdir(parents=True, exist_ok=True)

                task = export_progress.add_task(
                    "[cyan]Generating JSON export...", total=None
                )

                # Build complete archive dump
                all_topics = db.get_all_topics()
                all_categories = db.get_all_categories()
                all_users = db.get_all_users()

                topics_data = []
                for topic in all_topics:
                    topic_dict = topic.to_dict()
                    # Embed posts in each topic
                    posts = db.get_topic_posts(topic.id)
                    topic_dict["posts"] = [p.to_dict() for p in posts]
                    topics_data.append(topic_dict)

                archive_data = {
                    "topics": topics_data,
                    "categories": [c.to_dict() for c in all_categories],
                    "users": [u.to_dict() for u in all_users],
                    "statistics": stats,
                }

                json_path = json_dir / "archive.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json_module.dump(archive_data, f, indent=2, default=str)

                db.record_export(
                    "json",
                    len(all_topics),
                    sum(t.posts_count for t in all_topics),
                    str(json_dir),
                )
                export_times["json"] = time_module.time() - phase_start

                export_progress.update(
                    task,
                    description=(
                        f"[green]✓ JSON export: {len(all_topics)} topics, "
                        f"{sum(len(t.get('posts', [])) for t in topics_data)} posts"
                    ),
                )
                console.print("[green]✓ JSON export complete[/green]")
            except Exception as e:
                console.print(f"[red]✗ JSON export failed: {e}[/red]")
                log.exception("JSON export failed")

    # Display timing
    overall_elapsed = time_module.time() - overall_start
    console.print(f"\n[bold]Export completed in {overall_elapsed:.1f}s[/bold]")
    for format_name, duration in export_times.items():
        console.print(f"  {format_name}: {duration:.1f}s")

    db.close()
    console.print("\n[bold green]Export complete![/bold green]")


if __name__ == "__main__":
    main()
