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

        Streams items to disk in batches to avoid loading all topics/posts
        into memory at once.

        Args:
            output_path: Path to output search_index.json
        """
        from bs4 import BeautifulSoup

        with open(output_path, "w", encoding="utf-8") as f:
            f.write('{"version":"1.0",')
            f.write(f'"generated_at":"{datetime.now().isoformat()}",')
            f.write('"items":[')

            first_item = True
            category_cache: dict[int, str] = {}

            for topic in self.db.iter_topics_batched(batch_size=500):
                # Cache category lookups
                category_name = ""
                if topic.category_id:
                    if topic.category_id not in category_cache:
                        cat = self.db.get_category(topic.category_id)
                        category_cache[topic.category_id] = cat.name if cat else ""
                    category_name = category_cache[topic.category_id]

                # Get posts for this topic in one query
                posts = self.db.get_topic_posts(topic.id)

                # Index the topic itself (from first post)
                excerpt = ""
                author = "unknown"
                if posts:
                    soup = BeautifulSoup(posts[0].cooked, "html.parser")
                    excerpt = self.extract_excerpt(soup.get_text())
                    author = posts[0].username

                topic_url = f"t/{topic.slug}/{topic.id}/"

                item = {
                    "type": "topic",
                    "id": topic.id,
                    "title": topic.title,
                    "url": topic_url,
                    "excerpt": excerpt,
                    "category": category_name,
                    "author": author,
                    "created_at": topic.created_at.strftime("%Y-%m-%d"),
                }

                if not first_item:
                    f.write(",")
                json.dump(item, f, separators=(",", ":"))
                first_item = False

                # Index remaining posts (skip first — already indexed as topic)
                for idx, post in enumerate(posts):
                    if idx == 0:
                        continue

                    soup = BeautifulSoup(post.cooked, "html.parser")
                    excerpt = self.extract_excerpt(soup.get_text())

                    page_num = (idx // self.posts_per_page) + 1
                    if page_num == 1:
                        post_url = f"t/{topic.slug}/{topic.id}/#post-{post.post_number}"
                    else:
                        post_url = (
                            f"t/{topic.slug}/{topic.id}/"
                            f"page-{page_num}.html#post-{post.post_number}"
                        )

                    item = {
                        "type": "post",
                        "id": post.id,
                        "topic_id": topic.id,
                        "title": f"Reply in: {topic.title}",
                        "url": post_url,
                        "excerpt": excerpt,
                        "author": post.username,
                        "created_at": post.created_at.strftime("%Y-%m-%d"),
                    }

                    f.write(",")
                    json.dump(item, f, separators=(",", ":"))

            f.write("]}")

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
