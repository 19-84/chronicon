# ABOUTME: Update manager for incremental archive updates
# ABOUTME: Orchestrates fetching new/modified content and regenerating affected exports

"""Manages incremental updates to existing archives."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..fetchers.api_client import DiscourseAPIClient
from ..fetchers.posts import PostFetcher
from ..fetchers.topics import TopicFetcher
from ..models.post import Post
from ..storage.database_base import ArchiveDatabaseBase
from .logger import get_logger

log = get_logger(__name__)


@dataclass
class UpdateStatistics:
    """Statistics from an incremental update."""

    new_posts: int
    modified_posts: int
    new_topics: int
    affected_topics: int
    affected_usernames: int
    fetch_errors: int
    duration_seconds: float


class UpdateManager:
    """Orchestrates incremental updates to existing archives."""

    def __init__(
        self,
        db: ArchiveDatabaseBase,
        client: DiscourseAPIClient,
        category_ids: list[int] | None = None,
    ):
        """
        Initialize update manager.

        Args:
            db: Archive database instance
            client: Discourse API client
            category_ids: Optional list of category IDs to filter (None = all)
        """
        self.db = db
        self.client = client
        self.category_ids = category_ids
        self.post_fetcher = PostFetcher(client, db)  # type: ignore[arg-type]
        self.topic_fetcher = TopicFetcher(client, db)  # type: ignore[arg-type]
        self._topics_to_regenerate: set[int] = set()
        self._new_topic_ids: set[int] = set()  # Track truly new topics
        self._affected_usernames: set[str] = set()
        self._fetch_errors: list[str] = []

        if category_ids:
            log.info(f"Category filter active: {category_ids}")

    def update_archive(self, site_url: str) -> UpdateStatistics:
        """
        Perform incremental update of an archive.

        Args:
            site_url: Base URL of the Discourse site

        Returns:
            Statistics about the update operation
        """
        start_time = datetime.now()
        log.info(f"Starting incremental update for {site_url}")

        # Load site metadata
        metadata = self.db.get_site_metadata(site_url)
        if not metadata or "last_sync_date" not in metadata:
            log.warning(
                "No previous sync date found. This appears to be a new archive."
            )
            log.info("For initial archiving, use 'chronicon archive' instead.")
            return UpdateStatistics(
                new_posts=0,
                modified_posts=0,
                new_topics=0,
                affected_topics=0,
                affected_usernames=0,
                fetch_errors=0,
                duration_seconds=0.0,
            )

        last_sync_value = metadata["last_sync_date"]
        if not last_sync_value:
            # No last sync date - do a full initial fetch
            log.info("No last sync date found, performing initial archive")
            last_sync = datetime.now(UTC) - timedelta(days=365)  # Fetch last year
        else:
            # Handle both string (SQLite) and datetime (PostgreSQL) values
            if isinstance(last_sync_value, datetime):
                last_sync = last_sync_value
            else:
                last_sync = datetime.fromisoformat(last_sync_value)
            # Ensure last_sync is timezone-aware (UTC) for comparison with API datetimes
            if last_sync.tzinfo is None:
                last_sync = last_sync.replace(tzinfo=UTC)
        log.info(f"Last sync was at {last_sync.isoformat()}")

        # Fetch posts since last sync with 1-day buffer
        resync_from = last_sync - timedelta(days=1)
        log.info(f"Fetching posts since {resync_from.isoformat()} (with 1-day buffer)")

        new_posts, modified_posts = self._fetch_new_and_modified_posts(resync_from)

        # Calculate statistics
        stats = UpdateStatistics(
            new_posts=len(new_posts),
            modified_posts=len(modified_posts),
            new_topics=len(self._new_topic_ids),
            affected_topics=len(self._topics_to_regenerate),
            affected_usernames=len(self._affected_usernames),
            fetch_errors=len(self._fetch_errors),
            duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

        # Update metadata
        if stats.new_posts > 0 or stats.modified_posts > 0:
            self._update_site_metadata(site_url)
            log.info("Updated site metadata with new sync date")

        # Log summary
        log.info("Update complete:")
        log.info(f"  New posts: {stats.new_posts}")
        log.info(f"  Modified posts: {stats.modified_posts}")
        log.info(f"  New topics: {stats.new_topics}")
        log.info(f"  Topics needing regeneration: {stats.affected_topics}")
        log.info(f"  Fetch errors: {stats.fetch_errors}")
        log.info(f"  Duration: {stats.duration_seconds:.2f}s")

        if self._fetch_errors:
            log.warning("Errors encountered during fetch:")
            for error in self._fetch_errors[:10]:  # Show first 10
                log.warning(f"  {error}")
            if len(self._fetch_errors) > 10:
                log.warning(f"  ... and {len(self._fetch_errors) - 10} more")

        return stats

    def _fetch_new_and_modified_posts(
        self, since: datetime
    ) -> tuple[list[Post], list[Post]]:
        """
        Fetch posts created or modified since a date.

        Args:
            since: Fetch posts updated after this date

        Returns:
            Tuple of (new_posts, modified_posts)
        """
        log.info("Fetching latest posts from API...")

        try:
            fetched_posts = self.post_fetcher.fetch_latest_posts(since=since)
            log.info(f"Fetched {len(fetched_posts)} posts from API")
        except Exception as e:
            log.error(f"Error fetching latest posts: {e}")
            self._fetch_errors.append(f"fetch_latest_posts: {e}")
            return [], []

        new_posts = []
        modified_posts = []
        skipped_by_category = 0

        for post in fetched_posts:
            # Check category filter before processing
            if not self._should_include_topic(post.topic_id):
                skipped_by_category += 1
                continue

            existing = self.db.get_post(post.id)

            if existing is None:
                # New post
                new_posts.append(post)
                self.db.insert_post(post)
                self._mark_topic_for_regeneration(post.topic_id)
                if post.username:
                    self._affected_usernames.add(post.username)
                log.debug(f"New post {post.id} in topic {post.topic_id}")

            elif existing.updated_at != post.updated_at:
                # Modified post
                modified_posts.append(post)
                self.db.update_post(post)
                self._mark_topic_for_regeneration(post.topic_id)
                if post.username:
                    self._affected_usernames.add(post.username)
                log.debug(
                    f"Modified post {post.id} in topic {post.topic_id} "
                    f"(was {existing.updated_at}, now {post.updated_at})"
                )

        if skipped_by_category > 0:
            log.info(f"Skipped {skipped_by_category} posts not in filtered categories")
        log.info(f"Detected {len(new_posts)} new posts, {len(modified_posts)} modified")

        # For new posts, we might need to fetch the parent topics if not in DB
        self._fetch_missing_topics(new_posts)

        return new_posts, modified_posts

    def _should_include_topic(self, topic_id: int) -> bool:
        """
        Check if a topic should be included based on category filter.

        Args:
            topic_id: Topic ID to check

        Returns:
            True if topic should be included, False otherwise
        """
        # No filter = include all
        if not self.category_ids:
            return True

        # Check if topic's category is in our filter
        topic = self.db.get_topic(topic_id)
        if topic is None:
            # Topic not in DB yet, we'll need to fetch it to check
            # For now, include it - the filtering will happen when we fetch the topic
            try:
                topic = self.topic_fetcher.fetch_topic(topic_id)
                if topic is None:
                    log.warning(f"Could not fetch topic {topic_id} for category check")
                    return False
            except Exception as e:
                log.warning(f"Error fetching topic {topic_id} for category check: {e}")
                return False

        # Check category
        if topic.category_id in self.category_ids:
            return True

        log.debug(
            f"Topic {topic_id} in category {topic.category_id} "
            f"not in filter {self.category_ids}"
        )
        return False

    def _fetch_missing_topics(self, posts: list[Post]) -> None:
        """
        Fetch topic metadata and posts for topics that aren't in the database.

        Args:
            posts: Posts to check
        """
        topic_ids = {p.topic_id for p in posts}
        missing_topic_ids = []

        for topic_id in topic_ids:
            if self.db.get_topic(topic_id) is None:
                missing_topic_ids.append(topic_id)
                # Track this as a new topic
                self._new_topic_ids.add(topic_id)

        if not missing_topic_ids:
            return

        log.info(f"Fetching {len(missing_topic_ids)} missing topics...")

        for topic_id in missing_topic_ids:
            try:
                topic = self.topic_fetcher.fetch_topic(topic_id)
                if topic:
                    # Double-check category filter before storing
                    if self.category_ids and topic.category_id not in self.category_ids:
                        log.debug(
                            f"Skipping topic {topic_id} - category {topic.category_id} "
                            f"not in filter"
                        )
                        continue

                    self.db.insert_topic(topic)
                    log.debug(f"Fetched topic {topic_id}: {topic.title}")

                    # Also fetch all posts for this topic
                    topic_posts = self.topic_fetcher.fetch_topic_posts(topic_id)
                    for post in topic_posts:
                        self.db.insert_post(post)
                        if post.username:
                            self._affected_usernames.add(post.username)
                    log.debug(f"Fetched {len(topic_posts)} posts for topic {topic_id}")
                else:
                    log.warning(f"Could not fetch topic {topic_id}")
                    self._fetch_errors.append(f"fetch_topic {topic_id}: Not found")
            except Exception as e:
                log.error(f"Error fetching topic {topic_id}: {e}")
                self._fetch_errors.append(f"fetch_topic {topic_id}: {e}")

    def _mark_topic_for_regeneration(self, topic_id: int) -> None:
        """
        Mark a topic as needing regeneration.

        Args:
            topic_id: Topic ID to mark
        """
        self._topics_to_regenerate.add(topic_id)

    def get_topics_to_regenerate(self) -> set[int]:
        """
        Get the set of topic IDs that need regeneration.

        Returns:
            Set of topic IDs
        """
        return self._topics_to_regenerate.copy()

    def get_affected_usernames(self) -> set[str]:
        """
        Get the set of usernames affected by new/modified posts.

        Returns:
            Set of usernames
        """
        return self._affected_usernames.copy()

    def backfill_missing_posts(self, limit: int | None = None) -> int:
        """
        Find topics with missing posts and fetch them.

        This handles archives where topics were saved but posts weren't fetched.

        Args:
            limit: Maximum number of topics to backfill (None for all)

        Returns:
            Number of topics backfilled
        """
        log.info("Checking for topics with missing posts...")

        # Find topics that claim to have posts but don't have any in the DB
        cursor = self.db.connection.cursor()  # type: ignore[attr-defined]
        query = """
            SELECT t.id, t.title, t.posts_count
            FROM topics t
            LEFT JOIN posts p ON t.id = p.topic_id
            WHERE t.posts_count > 0
            GROUP BY t.id
            HAVING COUNT(p.id) = 0
        """
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            log.info("No topics with missing posts found")
            return 0

        log.info(f"Found {len(rows)} topics with missing posts, backfilling...")

        backfilled = 0
        for row in rows:
            topic_id = row[0]
            try:
                posts = self.topic_fetcher.fetch_topic_posts(topic_id)
                for post in posts:
                    self.db.insert_post(post)
                self._mark_topic_for_regeneration(topic_id)
                backfilled += 1
                log.debug(f"Backfilled {len(posts)} posts for topic {topic_id}")
            except Exception as e:
                log.error(f"Error backfilling topic {topic_id}: {e}")
                self._fetch_errors.append(f"backfill_topic {topic_id}: {e}")

        log.info(f"Backfilled posts for {backfilled} topics")
        return backfilled

    def _update_site_metadata(self, site_url: str) -> None:
        """
        Update site metadata with current sync date.

        Args:
            site_url: Site URL to update
        """
        self.db.update_site_metadata(
            site_url, last_sync_date=datetime.now().isoformat()
        )
