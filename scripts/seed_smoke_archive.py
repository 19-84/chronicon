#!/usr/bin/env python3
# ABOUTME: Creates a tiny archive database for smoke-testing exports without network access
# ABOUTME: Used by CI to run a real HTML export inside the built Docker images

"""Usage: seed_smoke_archive.py OUTPUT_DIR  (writes OUTPUT_DIR/archive.db)"""

import sys
from datetime import datetime
from pathlib import Path

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


def main() -> None:
    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    db = ArchiveDatabase(output_dir / "archive.db")

    db.insert_category(
        Category(
            id=1,
            name="General",
            slug="general",
            color="0088CC",
            text_color="FFFFFF",
            description="General discussion",
            parent_category_id=None,
            topic_count=1,
        )
    )
    db.insert_user(
        User(
            id=1,
            username="alice",
            name="Alice Smith",
            trust_level=3,
            avatar_template="/avatar/{size}/1.png",
            created_at=datetime(2024, 1, 1),
        )
    )
    db.insert_topic(
        Topic(
            id=1,
            title="Python Programming",
            slug="python-programming",
            posts_count=2,
            views=100,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
            last_posted_at=datetime(2024, 1, 2),
            user_id=1,
            category_id=1,
            closed=False,
            archived=False,
            pinned=False,
            visible=True,
            excerpt="Learn Python basics",
        )
    )
    for post_id, day, text in [
        (1, 1, "This is a post about Python programming"),
        (2, 2, "More details about Python"),
    ]:
        db.insert_post(
            Post(
                id=post_id,
                topic_id=1,
                post_number=post_id,
                user_id=1,
                username="alice",
                created_at=datetime(2024, 1, day),
                updated_at=datetime(2024, 1, day),
                raw=text,
                cooked=f"<p>{text}</p>",
            )
        )
    db.close()


if __name__ == "__main__":
    main()
