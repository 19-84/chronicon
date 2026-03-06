# ABOUTME: Search indexer for Chronicon
# ABOUTME: Generates JSON search index for client-side search functionality

"""Search index generation for client-side search."""

import json
from datetime import datetime
from pathlib import Path


class SearchIndexer:
    """Generate search index for client-side search."""

    def __init__(self, db, posts_per_page: int = 50):
        """
        Initialize search indexer.

        Args:
            db: ArchiveDatabase instance
            posts_per_page: Posts per page for computing paginated URLs
        """
        self.db = db
        self.posts_per_page = posts_per_page

    def generate_index(self, output_path: Path) -> None:
        """
        Generate search index JSON file.

        Args:
            output_path: Path to output search_index.json
        """
        # Placeholder implementation - will be implemented in Phase 3
        index = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "items": self._build_index_items(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _build_index_items(self) -> list[dict]:
        """
        Build list of searchable items.

        Returns:
            List of index items
        """
        from bs4 import BeautifulSoup

        items = []

        # Index all topics
        topics = self.db.get_all_topics()
        for topic in topics:
            # Get first post for excerpt
            posts = self.db.get_topic_posts(topic.id)
            excerpt = ""
            if posts:
                # Strip HTML from first post
                soup = BeautifulSoup(posts[0].cooked, "html.parser")
                content = soup.get_text()
                excerpt = self.extract_excerpt(content)

            # Get category name if available
            category_name = ""
            if topic.category_id:
                category = self.db.get_category(topic.category_id)
                if category:
                    category_name = category.name

            # Generate topic URL (matches HTML export structure: t/{slug}/{id}/)
            topic_url = f"t/{topic.slug}/{topic.id}/"

            items.append(
                {
                    "type": "topic",
                    "id": topic.id,
                    "title": topic.title,
                    "url": topic_url,
                    "excerpt": excerpt,
                    "category": category_name,
                    "author": posts[0].username if posts else "unknown",
                    "created_at": topic.created_at.strftime("%Y-%m-%d"),
                }
            )

        # Index all posts (except first post which is already in topic)
        all_topics = self.db.get_all_topics()
        for topic in all_topics:
            posts = self.db.get_topic_posts(topic.id)
            for idx, post in enumerate(posts):
                if idx == 0:
                    continue  # Skip first post (already indexed as topic)

                # Strip HTML
                soup = BeautifulSoup(post.cooked, "html.parser")
                content = soup.get_text()
                excerpt = self.extract_excerpt(content)

                # Compute which page this post is on
                page_num = (idx // self.posts_per_page) + 1
                if page_num == 1:
                    post_url = (
                        f"t/{topic.slug}/{topic.id}/#post-{post.post_number}"
                    )
                else:
                    post_url = (
                        f"t/{topic.slug}/{topic.id}/"
                        f"page-{page_num}.html#post-{post.post_number}"
                    )

                items.append(
                    {
                        "type": "post",
                        "id": post.id,
                        "topic_id": topic.id,
                        "title": f"Reply in: {topic.title}",
                        "url": post_url,
                        "excerpt": excerpt,
                        "author": post.username,
                        "created_at": post.created_at.strftime("%Y-%m-%d"),
                    }
                )

        return items

    def extract_excerpt(self, content: str, max_length: int = 200) -> str:
        """
        Extract excerpt from content.

        Args:
            content: Full content text
            max_length: Maximum excerpt length

        Returns:
            Excerpt string
        """
        if len(content) <= max_length:
            return content

        # Truncate at word boundary
        excerpt = content[:max_length]
        last_space = excerpt.rfind(" ")
        if last_space > 0:
            excerpt = excerpt[:last_space]

        return excerpt + "..."
