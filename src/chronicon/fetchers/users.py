# ABOUTME: User fetcher for Chronicon
# ABOUTME: Fetches user profiles and information from Discourse API

"""User fetching logic for Discourse API."""

import urllib.parse

from ..models.user import User
from ..storage.database import ArchiveDatabase
from ..utils.logger import get_logger
from .api_client import DiscourseAPIClient

log = get_logger(__name__)


class UserFetcher:
    """Fetches users from Discourse API."""

    def __init__(self, client: DiscourseAPIClient, db: ArchiveDatabase):
        """
        Initialize user fetcher.

        Args:
            client: API client instance
            db: Database instance
        """
        self.client = client
        self.db = db

    def fetch_user(self, username: str) -> User | None:
        """
        Fetch a single user by username.

        Args:
            username: Username to fetch

        Returns:
            User object or None if not found
        """
        try:
            # URL-encode the username to handle special characters
            encoded_username = urllib.parse.quote(username, safe="")
            path = f"/users/{encoded_username}.json"
            response = self.client.get_json(path)

            if "user" in response:
                return User.from_dict(response["user"])

        except Exception as e:
            log.warning(f"Error fetching user {username}: {e}")

        return None

    def fetch_user_by_id(self, user_id: int) -> User | None:
        """
        Fetch a single user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        try:
            path = f"/admin/users/{user_id}.json"
            response = self.client.get_json(path)
            return User.from_dict(response)
        except Exception as e:
            log.warning(f"Error fetching user ID {user_id}: {e}")
            return None
