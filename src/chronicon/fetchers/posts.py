# ABOUTME: Post fetcher for Chronicon
# ABOUTME: Fetches individual posts and post collections from Discourse API

"""Post fetching logic for Discourse API."""

from datetime import datetime

from ..models.post import Post
from ..storage.database import ArchiveDatabase
from ..utils.logger import get_logger
from .api_client import DiscourseAPIClient

log = get_logger(__name__)


class PostFetcher:
    """Fetches posts from Discourse API."""

    def __init__(self, client: DiscourseAPIClient, db: ArchiveDatabase):
        """
        Initialize post fetcher.

        Args:
            client: API client instance
            db: Database instance
        """
        self.client = client
        self.db = db

    def fetch_latest_posts(self, since: datetime | None = None) -> list[Post]:
        """
        Fetch latest posts from the forum.

        Args:
            since: Only fetch posts created/updated after this date

        Returns:
            List of Post objects
        """
        # Discourse API endpoint for latest posts
        path = "/posts.json"
        response = self.client.get_json(path)

        posts = []
        if "latest_posts" in response:
            for post_data in response["latest_posts"]:
                try:
                    post = Post.from_dict(post_data)
                    # Filter by date if specified
                    if since and post.updated_at < since:
                        continue
                    posts.append(post)
                except Exception as e:
                    log.warning(f"Error parsing post {post_data.get('id')}: {e}")

        return posts

    def fetch_post(self, post_id: int) -> Post | None:
        """
        Fetch a single post by ID.

        Args:
            post_id: Post ID

        Returns:
            Post object or None if not found
        """
        try:
            path = f"/posts/{post_id}.json"
            response = self.client.get_json(path)
            return Post.from_dict(response)
        except Exception as e:
            log.warning(f"Error fetching post {post_id}: {e}")
            return None

    def fetch_posts_before(self, post_id: int, limit: int = 20) -> list[Post]:
        """
        Fetch posts before a specific post ID.

        Args:
            post_id: Reference post ID
            limit: Maximum number of posts to fetch

        Returns:
            List of Post objects
        """
        try:
            path = f"/posts/before/{post_id}.json?limit={limit}"
            response = self.client.get_json(path)

            posts = []
            if "posts" in response:
                for post_data in response["posts"]:
                    try:
                        posts.append(Post.from_dict(post_data))
                    except Exception as e:
                        log.warning(f"Error parsing post {post_data.get('id')}: {e}")

            return posts
        except Exception as e:
            log.warning(f"Error fetching posts before {post_id}: {e}")
            return []
