# ABOUTME: Main daemon class for continuous watch mode
# ABOUTME: Handles polling loop, signal handling, PID/lock files, and error recovery

"""Watch daemon for continuous monitoring of Discourse forums."""

import os
import signal
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console

from ..config import Config
from ..exporters.html_static import HTMLStaticExporter
from ..exporters.hybrid import HybridExporter
from ..exporters.markdown import MarkdownGitHubExporter
from ..fetchers.api_client import DiscourseAPIClient
from ..fetchers.assets import AssetDownloader
from ..processors.html_parser import HTMLProcessor
from ..storage.database import ArchiveDatabase
from ..storage.database_base import ArchiveDatabaseBase
from ..utils.logger import get_logger
from ..utils.update_manager import UpdateManager
from .git_manager import GitManager
from .status import WatchCycleResult, WatchStatus

log = get_logger(__name__)
console = Console()


class WatchDaemon:
    """Daemon for continuous monitoring and updating of archives."""

    def __init__(
        self,
        output_dir: Path,
        config: Config,
        formats: list[str] | None = None,
        daemon_mode: bool = False,
    ):
        """
        Initialize watch daemon.

        Args:
            output_dir: Archive output directory
            config: Configuration object
            formats: List of export formats to regenerate (default: all)
            daemon_mode: If True, run as background daemon
        """
        import os

        self.output_dir = Path(output_dir)
        self.config = config
        self.daemon_mode = daemon_mode

        # Check for EXPORT_FORMATS environment variable override
        env_formats = os.getenv("EXPORT_FORMATS")
        if env_formats:
            # Parse comma-separated formats from environment
            self.formats = [f.strip() for f in env_formats.split(",") if f.strip()]
            log.info(f"Using formats from EXPORT_FORMATS: {self.formats}")
        else:
            self.formats = formats or config.default_formats

        # File paths
        self.pid_file = self.output_dir / ".chronicon-watch.pid"
        self.lock_file = self.output_dir / ".chronicon-watch.lock"
        self.status_file = self.output_dir / ".chronicon-watch-status.json"
        self.log_file = self.output_dir / "chronicon-watch.log"

        # State
        self.running = False
        self.status: WatchStatus | None = None
        self.consecutive_errors = 0
        self.last_check_time: datetime | None = None

        # Database and API client (initialized in start())
        self.db: ArchiveDatabaseBase | None = None
        self.client: DiscourseAPIClient | None = None
        self.site_url: str | None = None

        # Git integration
        self.git_manager: GitManager | None = None

        # Signal handling
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGHUP, self._handle_reload_signal)

    def _handle_shutdown_signal(self, signum, frame) -> None:
        """
        Handle shutdown signals (SIGTERM, SIGINT).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        log.info(f"Received signal {signum}, shutting down gracefully...")
        console.print("\n[yellow]Shutting down...[/yellow]")
        self.stop()

    def _handle_reload_signal(self, signum, frame) -> None:
        """
        Handle reload signal (SIGHUP).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        log.info("Received SIGHUP, reloading configuration...")
        console.print("[cyan]Reloading configuration...[/cyan]")
        # Reload config without stopping
        try:
            self.config = Config.load(None)  # Reload from default location
            log.info("Configuration reloaded successfully")
        except Exception as e:
            log.error(f"Failed to reload configuration: {e}")

    def _check_lock_file(self) -> bool:
        """
        Check if another instance is running.

        Returns:
            True if lock file exists and process is running
        """
        if not self.lock_file.exists():
            return False

        # Read PID from lock file
        try:
            pid = int(self.lock_file.read_text().strip())

            # Check if process is running
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                return True
            except OSError:
                # Process doesn't exist, remove stale lock file
                log.warning(f"Removing stale lock file (PID {pid} not running)")
                self.lock_file.unlink()
                return False

        except Exception as e:
            log.error(f"Error checking lock file: {e}")
            return False

    def _create_lock_file(self) -> None:
        """Create lock file with current PID."""
        self.lock_file.write_text(str(os.getpid()))
        log.debug(f"Created lock file: {self.lock_file}")

    def _remove_lock_file(self) -> None:
        """Remove lock file."""
        if self.lock_file.exists():
            self.lock_file.unlink()
            log.debug("Removed lock file")

    def _create_pid_file(self) -> None:
        """Create PID file with current process ID."""
        self.pid_file.write_text(str(os.getpid()))
        log.debug(f"Created PID file: {self.pid_file}")

    def _remove_pid_file(self) -> None:
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
            log.debug("Removed PID file")

    def _initialize_database(self) -> bool:
        """
        Initialize database connection and detect site URL.

        Supports both SQLite (default) and PostgreSQL (via DATABASE_URL env var).

        Returns:
            True if successful, False otherwise
        """
        import os

        # Check for DATABASE_URL environment variable
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            # PostgreSQL mode
            try:
                from ..storage.factory import get_database

                self.db = get_database(database_url)
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
                log.info(f"Opened database: {masked_url}")
            except Exception as e:
                log.error(f"Failed to connect to database: {e}")
                console.print(f"[red]Error: Failed to connect to database: {e}[/red]")
                return False
        else:
            # SQLite mode (existing behavior)
            db_path = self.output_dir / "archive.db"
            if not db_path.exists():
                log.error(f"Database not found at {db_path}")
                console.print(
                    f"[red]Error: No archive database found at {db_path}[/red]"
                )
                console.print(
                    "[yellow]Hint: Run 'chronicon archive' first to create "
                    "an archive, or set DATABASE_URL for PostgreSQL[/yellow]"
                )
                return False

            try:
                self.db = ArchiveDatabase(db_path)
                log.info(f"Opened database: {db_path}")
            except Exception as e:
                log.error(f"Failed to initialize database: {e}")
                console.print(f"[red]Error initializing database: {e}[/red]")
                return False

        # Get site URL from metadata using the database-agnostic method
        try:
            assert self.db is not None
            self.site_url = self.db.get_first_site_url()
            if not self.site_url:
                log.error("No site metadata found in database")
                console.print("[red]Error: No site metadata found in database[/red]")
                return False

            log.info(f"Monitoring site: {self.site_url}")

            # Initialize API client
            self.client = DiscourseAPIClient(
                self.site_url, rate_limit=self.config.rate_limit
            )
            log.info("Initialized API client")

            # Initialize git integration
            self.git_manager = GitManager(
                repo_path=self.output_dir,
                enabled=self.config.continuous_git_enabled,
                auto_commit=self.config.continuous_git_auto_commit,
                push_to_remote=self.config.continuous_git_push_to_remote,
                remote_name=self.config.continuous_git_remote_name,
                branch=self.config.continuous_git_branch,
                commit_message_template=(
                    self.config.continuous_git_commit_message_template
                ),
            )

            if self.git_manager.enabled:
                log.info("Git integration enabled")
                git_status = self.git_manager.get_status_info()
                log.info(f"  Branch: {git_status['current_branch']}")
                log.info(f"  Remote: {git_status['remote_url']}")
                log.info(f"  Auto-commit: {git_status['auto_commit']}")
                log.info(f"  Push to remote: {git_status['push_to_remote']}")

            return True

        except Exception as e:
            log.error(f"Failed to initialize: {e}")
            console.print(f"[red]Error initializing: {e}[/red]")
            return False

    def start(self) -> None:
        """Start the watch daemon."""
        log.info("Starting watch daemon...")
        console.print("[bold blue]Starting Chronicon watch daemon...[/bold blue]")

        # Check for existing instance
        if self._check_lock_file():
            log.error("Another instance is already running")
            console.print("[red]Error: Another instance is already running[/red]")
            console.print(f"[yellow]Lock file: {self.lock_file}[/yellow]")
            sys.exit(1)

        # Create lock and PID files
        self._create_lock_file()
        self._create_pid_file()

        # Initialize database
        if not self._initialize_database():
            self._remove_lock_file()
            self._remove_pid_file()
            sys.exit(1)

        # Load or create status
        self.status = WatchStatus.load(self.status_file)
        if self.status is None:
            self.status = WatchStatus.create_initial(os.getpid())
            log.info("Created new status file")
        else:
            # Update status for restart
            self.status.is_running = True
            self.status.pid = os.getpid()
            self.status.consecutive_errors = 0
            log.info("Loaded existing status file")

        self.status.save(self.status_file)

        # Start polling loop
        self.running = True
        console.print(f"[green]✓ Watching {self.site_url}[/green]")
        console.print(
            f"[dim]Polling interval: "
            f"{self.config.continuous_polling_interval} minutes[/dim]"
        )
        console.print(f"[dim]Formats: {', '.join(self.formats)}[/dim]")
        console.print(f"[dim]PID: {os.getpid()}[/dim]\n")

        try:
            self._polling_loop()
        except KeyboardInterrupt:
            log.info("Received keyboard interrupt")
            console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            log.error(f"Fatal error in polling loop: {e}", exc_info=True)
            console.print(f"\n[red]Fatal error: {e}[/red]")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the watch daemon."""
        if not self.running:
            return

        log.info("Stopping watch daemon...")
        self.running = False

        # Update status
        if self.status:
            self.status.is_running = False
            self.status.pid = None
            try:
                self.status.save(self.status_file)
            except Exception as e:
                log.error(f"Failed to save final status: {e}")

        # Close database
        if self.db:
            try:
                self.db.close()
                log.info("Closed database connection")
            except Exception as e:
                log.error(f"Error closing database: {e}")

        # Remove lock and PID files
        self._remove_lock_file()
        self._remove_pid_file()

        console.print("[green]✓ Watch daemon stopped[/green]")
        log.info("Watch daemon stopped")

    def _polling_loop(self) -> None:
        """Main polling loop."""
        while self.running:
            cycle_start = datetime.now()

            try:
                # Run update cycle
                result = self._run_update_cycle()

                # Record result
                assert self.status is not None
                self.status.record_cycle(result)

                # Save status
                self.status.save(self.status_file)

                # Display result
                if result.success:
                    if result.new_posts > 0 or result.modified_posts > 0:
                        console.print(
                            f"[green]✓ Update complete:[/green] "
                            f"{result.new_posts} new posts, "
                            f"{result.modified_posts} modified posts, "
                            f"{result.affected_topics} topics updated "
                            f"({result.duration_seconds:.1f}s)"
                        )
                    else:
                        console.print(
                            f"[dim]✓ No changes detected "
                            f"({result.duration_seconds:.1f}s)[/dim]"
                        )
                else:
                    console.print(f"[red]✗ Update failed:[/red] {result.error_message}")

                # Reset error backoff on success
                if result.success:
                    self.consecutive_errors = 0

            except Exception as e:
                # Handle unexpected errors
                log.error(f"Unexpected error in update cycle: {e}", exc_info=True)
                result = WatchCycleResult(
                    timestamp=datetime.now().isoformat(),
                    success=False,
                    new_posts=0,
                    modified_posts=0,
                    affected_topics=0,
                    duration_seconds=(datetime.now() - cycle_start).total_seconds(),
                    error_message=str(e),
                )
                if self.status is not None:
                    self.status.record_cycle(result)
                    self.status.save(self.status_file)
                self.consecutive_errors += 1

            # Check for too many consecutive errors
            if self.consecutive_errors >= self.config.continuous_max_consecutive_errors:
                log.error(
                    f"Too many consecutive errors "
                    f"({self.consecutive_errors}), stopping daemon"
                )
                console.print(
                    f"\n[red]✗ Stopping after {self.consecutive_errors} "
                    f"consecutive errors[/red]"
                )
                break

            # Calculate next check time with exponential backoff on errors
            if self.consecutive_errors > 0:
                # Exponential backoff: interval * (2 ^ errors)
                backoff_multiplier = (
                    self.config.continuous_error_backoff_multiplier
                    ** self.consecutive_errors
                )
                sleep_minutes = (
                    self.config.continuous_polling_interval * backoff_multiplier
                )
                sleep_minutes = min(sleep_minutes, 60)  # Cap at 60 minutes
                console.print(
                    f"[yellow]⚠ Backing off: waiting {sleep_minutes:.1f} "
                    f"minutes before retry[/yellow]"
                )
            else:
                sleep_minutes = self.config.continuous_polling_interval

            next_check = datetime.now() + timedelta(minutes=sleep_minutes)
            if self.status is not None:
                self.status.next_check = next_check.isoformat()
                self.status.save(self.status_file)

            # Sleep until next check (with periodic wake-ups to check for signals)
            sleep_seconds = sleep_minutes * 60
            slept = 0
            while slept < sleep_seconds and self.running:
                time.sleep(min(1, sleep_seconds - slept))  # Sleep in 1-second intervals
                slept += 1

    def _download_assets_for_topics(self, topic_ids: list[int]) -> None:
        """Download medium and highest resolution images for the given topics."""
        assert self.client is not None
        assert self.db is not None
        html_processor = HTMLProcessor()
        asset_downloader = AssetDownloader(self.client, self.db, self.output_dir)  # type: ignore[arg-type]

        for topic_id in topic_ids:
            posts = self.db.get_topic_posts(topic_id)
            for post in posts:
                if not post.cooked:
                    continue
                try:
                    image_sets = html_processor.extract_image_sets(post.cooked)
                except Exception as e:
                    log.error(f"Error processing HTML for post {post.id}: {e}")
                    continue

                for _base_id, img_set in image_sets.items():
                    medium = img_set["medium"]
                    highest = img_set["highest"]
                    if medium:
                        try:
                            asset_downloader.download_image(medium, topic_id)
                        except Exception as e:
                            log.debug(f"Failed to download medium resolution: {e}")
                    if highest and highest != medium:
                        try:
                            asset_downloader.download_image(highest, topic_id)
                        except Exception as e:
                            log.debug(f"Failed to download highest resolution: {e}")

        log.info("Asset download for affected topics complete")

    def _run_update_cycle(self) -> WatchCycleResult:
        """
        Run a single update cycle.

        Returns:
            WatchCycleResult with cycle statistics
        """
        cycle_start = datetime.now()
        log.info("Starting update cycle...")

        assert self.db is not None
        assert self.client is not None
        assert self.site_url is not None

        try:
            # Load category filter - config takes priority, DB is fallback
            category_ids = self.config.get_category_filter(self.site_url)
            if category_ids:
                log.info(f"Using category filter from config: {category_ids}")
            else:
                category_ids = self.db.get_category_filter(self.site_url)
                if category_ids:
                    log.info(f"Using category filter from database: {category_ids}")

            # Run incremental update
            update_manager = UpdateManager(
                self.db, self.client, category_ids=category_ids
            )
            stats = update_manager.update_archive(self.site_url)

            # If there are changes, download assets then regenerate exports
            if stats.affected_topics > 0:
                log.info(f"Regenerating exports for {stats.affected_topics} topics...")
                topic_ids = list(update_manager.get_topics_to_regenerate())
                affected_usernames = update_manager.get_affected_usernames()

                try:
                    self._download_assets_for_topics(topic_ids)
                except Exception as e:
                    log.warning(f"Asset download during update failed: {e}")

                # Regenerate each format
                for format_name in self.formats:
                    try:
                        if format_name == "hybrid":
                            exporter = HybridExporter(
                                self.db,
                                self.output_dir,
                                include_html=True,
                                include_md=True,
                                include_users=self.config.include_users,
                                posts_per_page=self.config.posts_per_page,
                                pagination_enabled=self.config.pagination_enabled,
                            )
                            exporter.export_topics(topic_ids)
                            exporter.update_index()
                            if affected_usernames:
                                exporter.export_users_by_username(affected_usernames)

                        elif format_name == "html":
                            html_dir = self.output_dir / "html"
                            if html_dir.exists():
                                exporter = HTMLStaticExporter(
                                    self.db,
                                    html_dir,
                                    include_users=self.config.include_users,
                                    posts_per_page=self.config.posts_per_page,
                                    pagination_enabled=(self.config.pagination_enabled),
                                )
                                exporter.export_topics(topic_ids)
                                exporter.update_index()
                                if affected_usernames:
                                    exporter.export_users_by_username(
                                        affected_usernames
                                    )

                        elif format_name in ("md", "github"):
                            md_dir = self.output_dir / "md"
                            if md_dir.exists():
                                exporter = MarkdownGitHubExporter(
                                    self.db,
                                    md_dir,
                                    include_users=self.config.include_users,
                                )
                                exporter.export_topics(topic_ids)
                                exporter.update_index()
                                if affected_usernames:
                                    exporter.export_users_by_username(
                                        affected_usernames
                                    )

                    except Exception as e:
                        log.error(f"Error regenerating {format_name} export: {e}")
                        # Continue with other formats

            duration = (datetime.now() - cycle_start).total_seconds()

            # Git commit if enabled and there were changes
            if (
                stats.affected_topics > 0
                and self.git_manager
                and self.git_manager.enabled
            ):
                log.info("Committing changes to git...")
                try:
                    success = self.git_manager.commit_and_push(
                        formats=self.formats,
                        new_posts=stats.new_posts,
                        modified_posts=stats.modified_posts,
                        affected_topics=stats.affected_topics,
                    )
                    if success:
                        log.info("Changes committed to git successfully")
                    else:
                        log.warning("Git commit failed")
                except Exception as e:
                    log.error(f"Error during git commit: {e}")
                    # Don't fail the cycle just because git failed

            return WatchCycleResult(
                timestamp=cycle_start.isoformat(),
                success=True,
                new_posts=stats.new_posts,
                modified_posts=stats.modified_posts,
                affected_topics=stats.affected_topics,
                duration_seconds=duration,
            )

        except Exception as e:
            log.error(f"Error in update cycle: {e}", exc_info=True)
            duration = (datetime.now() - cycle_start).total_seconds()

            return WatchCycleResult(
                timestamp=cycle_start.isoformat(),
                success=False,
                new_posts=0,
                modified_posts=0,
                affected_topics=0,
                duration_seconds=duration,
                error_message=str(e),
            )

    @classmethod
    def get_status(cls, output_dir: Path) -> WatchStatus | None:
        """
        Get current status of watch daemon.

        Args:
            output_dir: Archive output directory

        Returns:
            WatchStatus if daemon is/was running, None otherwise
        """
        status_file = output_dir / ".chronicon-watch-status.json"
        return WatchStatus.load(status_file)

    @classmethod
    def stop_daemon(cls, output_dir: Path) -> bool:
        """
        Stop a running daemon by sending SIGTERM.

        Args:
            output_dir: Archive output directory

        Returns:
            True if daemon was stopped, False if not running
        """
        pid_file = output_dir / ".chronicon-watch.pid"

        if not pid_file.exists():
            console.print("[yellow]No daemon is running[/yellow]")
            return False

        try:
            pid = int(pid_file.read_text().strip())

            # Check if process exists
            try:
                os.kill(pid, 0)
            except OSError:
                console.print("[yellow]Daemon not running (stale PID file)[/yellow]")
                pid_file.unlink()
                return False

            # Send SIGTERM
            console.print(f"[yellow]Stopping daemon (PID {pid})...[/yellow]")
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit (up to 10 seconds)
            for _i in range(10):
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    # Process exited
                    console.print("[green]✓ Daemon stopped[/green]")
                    return True

            # Process didn't exit, force kill
            console.print("[yellow]Daemon didn't stop gracefully, forcing...[/yellow]")
            os.kill(pid, signal.SIGKILL)
            console.print("[green]✓ Daemon stopped (forced)[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Error stopping daemon: {e}[/red]")
            return False
