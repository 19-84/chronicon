# ABOUTME: Topic fetcher for Chronicon
# ABOUTME: Fetches topics and their posts from Discourse API

"""Topic fetching logic for Discourse API."""

from ..models.post import Post
from ..models.topic import Topic
from ..storage.database import ArchiveDatabase
from ..utils.logger import get_logger
from .api_client import DiscourseAPIClient

log = get_logger(__name__)


class TopicFetcher:
    """Fetches topics from Discourse API."""

    def __init__(self, client: DiscourseAPIClient, db: ArchiveDatabase):
        """
        Initialize topic fetcher.

        Args:
            client: API client instance
            db: Database instance
        """
        self.client = client
        self.db = db

    def fetch_topic(self, topic_id: int) -> Topic | None:
        """
        Fetch a single topic by ID.

        Args:
            topic_id: Topic ID

        Returns:
            Topic object or None if not found
        """
        try:
            path = f"/t/{topic_id}.json"
            response = self.client.get_json(path)
            return Topic.from_dict(response)
        except Exception as e:
            log.warning(f"Error fetching topic {topic_id}: {e}")
            return None

    def fetch_topic_posts(self, topic_id: int) -> list[Post]:
        """
        Fetch all posts for a specific topic.

        Args:
            topic_id: Topic ID

        Returns:
            List of Post objects
        """
        try:
            path = f"/t/{topic_id}.json"
            response = self.client.get_json(path)

            posts = []
            if "post_stream" in response and "posts" in response["post_stream"]:
                for post_data in response["post_stream"]["posts"]:
                    try:
                        posts.append(Post.from_dict(post_data))
                    except Exception as e:
                        log.warning(f"Error parsing post {post_data.get('id')}: {e}")

                # Handle pagination - fetch additional posts if needed
                if "stream" in response["post_stream"]:
                    all_post_ids = response["post_stream"]["stream"]
                    loaded_post_ids = [p.id for p in posts]
                    missing_ids = [
                        pid for pid in all_post_ids if pid not in loaded_post_ids
                    ]

                    if missing_ids:
                        additional_posts = self._fetch_posts_by_ids(
                            topic_id, missing_ids
                        )
                        posts.extend(additional_posts)

            return posts
        except Exception as e:
            log.warning(f"Error fetching topic posts for {topic_id}: {e}")
            return []

    def _fetch_posts_by_ids(self, topic_id: int, post_ids: list[int]) -> list[Post]:
        """
        Fetch specific posts by their IDs.

        Args:
            topic_id: Topic ID
            post_ids: List of post IDs to fetch

        Returns:
            List of Post objects
        """
        all_posts = []

        # Batch into chunks of 50 to avoid "414 URI Too Long" errors
        # Discourse API can handle ~50 post IDs per request safely
        batch_size = 50

        for i in range(0, len(post_ids), batch_size):
            batch = post_ids[i : i + batch_size]

            try:
                # Batch fetch posts
                ids_param = "&".join([f"post_ids[]={pid}" for pid in batch])
                path = f"/t/{topic_id}/posts.json?{ids_param}"
                response = self.client.get_json(path)

                if "post_stream" in response and "posts" in response["post_stream"]:
                    for post_data in response["post_stream"]["posts"]:
                        try:
                            all_posts.append(Post.from_dict(post_data))
                        except Exception as e:
                            log.warning(
                                f"Error parsing post {post_data.get('id')}: {e}"
                            )

            except Exception as e:
                log.warning(f"Error fetching post batch for topic {topic_id}: {e}")
                # Continue with next batch even if this one fails
                continue

        return all_posts

    def fetch_all_topic_ids(self) -> list[int]:
        """
        Fetch all topic IDs from the forum.

        Returns:
            List of topic IDs
        """
        topic_ids = []
        try:
            # Fetch from latest topics endpoint
            path = "/latest.json"
            response = self.client.get_json(path)

            if "topic_list" in response and "topics" in response["topic_list"]:
                topic_ids = [t["id"] for t in response["topic_list"]["topics"]]

        except Exception as e:
            log.warning(f"Error fetching topic IDs: {e}")

        return topic_ids

    def fetch_category_topics(self, category_id: int) -> list[Topic]:
        """
        Fetch ALL topics from a category with pagination support.

        Args:
            category_id: Category ID

        Returns:
            List of Topic objects from all pages
        """
        all_topics = []
        page = 0

        while True:
            try:
                path = f"/c/{category_id}.json?page={page}"
                response = self.client.get_json(path)

                if (
                    "topic_list" not in response
                    or "topics" not in response["topic_list"]
                ):
                    break

                topics_on_page = response["topic_list"]["topics"]

                # If no topics on this page, we've reached the end
                if not topics_on_page:
                    break

                # Parse and add topics from this page
                for topic_data in topics_on_page:
                    try:
                        topic = Topic.from_dict(topic_data)
                        all_topics.append(topic)
                    except Exception as e:
                        log.warning(f"Error parsing topic {topic_data.get('id')}: {e}")

                # If we got fewer topics than expected, this is likely the last page
                # Discourse typically returns 30 topics per page
                if len(topics_on_page) < 30:
                    break

                page += 1

            except Exception as e:
                log.warning(
                    f"Error fetching topics for category {category_id}, "
                    f"page {page}: {e}"
                )
                break

        return all_topics

    def fetch_all_topics(self) -> list[Topic]:
        """
        Fetch ALL topics from the entire forum with pagination support.

        Returns:
            List of Topic objects from all pages
        """
        all_topics = []
        page = 0

        while True:
            try:
                path = f"/latest.json?page={page}"
                response = self.client.get_json(path)

                if (
                    "topic_list" not in response
                    or "topics" not in response["topic_list"]
                ):
                    break

                topics_on_page = response["topic_list"]["topics"]

                # If no topics on this page, we've reached the end
                if not topics_on_page:
                    break

                # Parse and add topics from this page
                for topic_data in topics_on_page:
                    try:
                        topic = Topic.from_dict(topic_data)
                        all_topics.append(topic)
                    except Exception as e:
                        log.warning(f"Error parsing topic {topic_data.get('id')}: {e}")

                # If we got fewer topics than expected, this is likely the last page
                if len(topics_on_page) < 30:
                    break

                page += 1

            except Exception as e:
                log.warning(f"Error fetching topics from forum, page {page}: {e}")
                break

        return all_topics

    def get_max_topic_id(self) -> int:
        """
        Get the maximum topic ID from the forum.

        Returns:
            Highest topic ID found, or 0 if unable to determine
        """
        try:
            path = "/latest.json"
            response = self.client.get_json(path)

            if "topic_list" in response and "topics" in response["topic_list"]:
                topics = response["topic_list"]["topics"]
                if topics:
                    # Get the highest ID from the first page
                    max_id = max(t["id"] for t in topics)
                    return max_id

        except Exception as e:
            log.warning(f"Error getting max topic ID: {e}")

        return 0

    def fetch_topics_by_id_range(
        self,
        start_id: int,
        end_id: int,
        skip_existing: bool = True,
        progress_callback=None,
    ) -> list[Topic]:
        """
        Fetch topics by iterating through a range of IDs.

        This is the exhaustive method that tries every ID to ensure complete archival.
        Works best when start_id > end_id (reverse order, newest first).

        Args:
            start_id: Starting topic ID
            end_id: Ending topic ID (inclusive)
            skip_existing: Skip IDs that already exist in database
            progress_callback: Optional callback function(current_id, topic, stats)

        Returns:
            List of successfully fetched Topic objects

        Example:
            # Fetch from newest (5000) to oldest (1)
            topics = fetcher.fetch_topics_by_id_range(5000, 1)
        """
        topics = []

        # Stats tracking
        stats = {
            "attempted": 0,
            "found": 0,
            "already_in_db": 0,
            "not_found": 0,  # 404s - deleted or private
            "errors": 0,
        }

        # Determine direction
        if start_id > end_id:
            # Reverse: newest to oldest
            id_range = range(start_id, end_id - 1, -1)
        else:
            # Forward: oldest to newest
            id_range = range(start_id, end_id + 1)

        for topic_id in id_range:
            stats["attempted"] += 1

            # Skip if already in database
            if skip_existing and self.db.get_topic(topic_id) is not None:
                stats["already_in_db"] += 1
                if progress_callback:
                    progress_callback(topic_id, None, stats)
                continue

            # Try to fetch topic
            try:
                topic = self.fetch_topic(topic_id)

                if topic is not None:
                    topics.append(topic)
                    stats["found"] += 1

                    # Store in database immediately
                    self.db.insert_topic(topic)

                    if progress_callback:
                        progress_callback(topic_id, topic, stats)
                else:
                    # fetch_topic returned None (404 or other issue)
                    stats["not_found"] += 1
                    if progress_callback:
                        progress_callback(topic_id, None, stats)

            except Exception as e:
                stats["errors"] += 1
                log.warning(f"Error fetching topic {topic_id}: {e}")
                if progress_callback:
                    progress_callback(topic_id, None, stats)

        return topics
