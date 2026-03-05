#!/usr/bin/env python3
# ABOUTME: Script to fetch missing users from posts
# ABOUTME: Fetches user profiles for all user_ids referenced in posts but not in users table

"""Fetch missing user profiles from Discourse API."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chronicon.storage.database import ArchiveDatabase
from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.models.user import User
import sqlite3


def main():
    """Fetch all missing users."""
    db_path = Path("archives/archive.db")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    # Open database
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get missing user IDs
    cursor.execute("""
        SELECT DISTINCT user_id FROM posts 
        WHERE user_id NOT IN (SELECT id FROM users)
        AND user_id IS NOT NULL
        ORDER BY user_id
    """)
    missing_ids = [row[0] for row in cursor.fetchall()]

    print(f"Found {len(missing_ids)} missing users")

    if not missing_ids:
        print("No missing users!")
        conn.close()
        return 0

    # Create API client
    base_url = "https://meta.discourse.org"
    client = DiscourseAPIClient(base_url)

    # Fetch each user
    fetched = 0
    failed = 0

    for i, user_id in enumerate(missing_ids, 1):
        try:
            print(f"[{i}/{len(missing_ids)}] Fetching user {user_id}...", end=" ")

            # Fetch from API
            response = client.get(f"/u/by-external/{user_id}.json")
            if response and "user" in response:
                user_data = response["user"]

                # Insert into database
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO users 
                    (id, username, name, avatar_template, trust_level, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_data.get("id"),
                        user_data.get("username"),
                        user_data.get("name"),
                        user_data.get("avatar_template"),
                        user_data.get("trust_level", 0),
                        user_data.get("created_at"),
                    ),
                )
                conn.commit()

                fetched += 1
                print(f"✓ {user_data.get('username')}")
            else:
                print("✗ No data")
                failed += 1

        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1

        # Rate limiting
        time.sleep(0.5)

    conn.close()

    print(f"\n✓ Fetched {fetched} users, {failed} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
