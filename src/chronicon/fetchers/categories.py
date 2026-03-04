# ABOUTME: Category fetcher for Chronicon
# ABOUTME: Fetches category information and hierarchy from Discourse API

"""Category fetching logic for Discourse API."""

from ..models.category import Category
from ..storage.database import ArchiveDatabase
from ..utils.logger import get_logger
from .api_client import DiscourseAPIClient

log = get_logger(__name__)


class CategoryFetcher:
    """Fetches categories from Discourse API."""

    def __init__(self, client: DiscourseAPIClient, db: ArchiveDatabase):
        """
        Initialize category fetcher.

        Args:
            client: API client instance
            db: Database instance
        """
        self.client = client
        self.db = db

    def fetch_all_categories(self) -> list[Category]:
        """
        Fetch all categories from the forum.

        Returns:
            List of Category objects
        """
        categories = []
        try:
            path = "/categories.json"
            response = self.client.get_json(path)

            if (
                "category_list" in response
                and "categories" in response["category_list"]
            ):
                for cat_data in response["category_list"]["categories"]:
                    try:
                        categories.append(Category.from_dict(cat_data))
                    except Exception as e:
                        log.warning(f"Error parsing category {cat_data.get('id')}: {e}")

        except Exception as e:
            log.warning(f"Error fetching categories: {e}")

        return categories

    def fetch_category(self, category_id: int) -> Category:
        """
        Fetch a single category by ID.

        Args:
            category_id: Category ID

        Returns:
            Category object or None if not found
        """
        try:
            path = f"/c/{category_id}/show.json"
            response = self.client.get_json(path)

            if "category" in response:
                return Category.from_dict(response["category"])

        except Exception as e:
            log.warning(f"Error fetching category {category_id}: {e}")

        return None  # type: ignore[return-value]
