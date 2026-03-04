#!/usr/bin/env python3
"""Regenerate example archive with all user profiles."""

from pathlib import Path
from chronicon.storage.database import ArchiveDatabase
from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.users import UserFetcher
from chronicon.exporters.html_static import HTMLStaticExporter
from chronicon.exporters.markdown_plain import MarkdownPlainExporter
from chronicon.exporters.markdown import MarkdownGitHubExporter

print("🔄 Regenerating example archive with all user profiles...\n")

db_path = Path("./examples/meta-example/archive.db")
output_dir = Path("./examples/meta-example")

db = ArchiveDatabase(db_path)

# Step 1: Fetch missing users
print("Step 1: Fetching missing user profiles...")
unique_usernames = db.get_unique_usernames()
unique_usernames = {u for u in unique_usernames if u and u != "system"}
existing_users = {u.username for u in db.get_all_users()}
usernames_to_fetch = unique_usernames - existing_users

print(f"  Total unique usernames: {len(unique_usernames)}")
print(f"  Already in database: {len(existing_users)}")
print(f"  Need to fetch: {len(usernames_to_fetch)}")

if usernames_to_fetch:
    client = DiscourseAPIClient("https://meta.discourse.org")
    user_fetcher = UserFetcher(client, db)

    fetched = 0
    failed = 0
    for i, username in enumerate(sorted(usernames_to_fetch), 1):
        try:
            user = user_fetcher.fetch_user(username)
            if user:
                db.insert_user(user)
                fetched += 1
                if i % 10 == 0:
                    print(
                        f"  Progress: {i}/{len(usernames_to_fetch)} ({fetched} fetched, {failed} failed)"
                    )
        except Exception as e:
            failed += 1

    print(f"  ✓ Fetched {fetched} user profiles ({failed} failed)")
else:
    print("  ✓ All users already in database")

# Step 2: Regenerate exports
print(f"\nStep 2: Regenerating exports for {len(db.get_all_topics())} topics...")
print(f"  Total users now: {len(db.get_all_users())}")

# HTML export with user pages
print("  Generating HTML export...")
html_exp = HTMLStaticExporter(db, output_dir / "html", include_users=True)
html_exp.export()
print("  ✓ HTML export complete")

# Markdown export with user pages
print("  Generating Markdown export...")
md_exp = MarkdownPlainExporter(db, output_dir / "markdown", include_users=True)
md_exp.export()
print("  ✓ Markdown export complete")

# GitHub Markdown export with user pages
print("  Generating GitHub Markdown export...")
gh_exp = MarkdownGitHubExporter(db, output_dir / "github", include_users=True)
gh_exp.export()
print("  ✓ GitHub Markdown export complete")

print("\n✅ Example archive regenerated successfully!")
print(f"   - {len(db.get_all_topics())} topics")
print(f"   - {len(db.get_all_posts())} posts")
print(f"   - {len(db.get_all_users())} user profiles")
