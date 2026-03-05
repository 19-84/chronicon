from pathlib import Path
from chronicon.storage.database import ArchiveDatabase
from chronicon.fetchers.api_client import DiscourseAPIClient
from chronicon.fetchers.topics import TopicFetcher
from chronicon.fetchers.users import UserFetcher
from chronicon.exporters.html_static import HTMLStaticExporter
from chronicon.exporters.markdown_plain import MarkdownPlainExporter
from chronicon.exporters.markdown import MarkdownGitHubExporter

print("Completing archive process...\n")

db_path = Path("./archives/archive.db")
output_dir = Path("./archives")
db = ArchiveDatabase(db_path)
client = DiscourseAPIClient("https://meta.discourse.org")

topics = db.get_all_topics()
print(f"Step 1: Fetching posts for {len(topics)} topics...")
topic_fetcher = TopicFetcher(client, db)

for i, topic in enumerate(topics, 1):
    try:
        posts = topic_fetcher.fetch_topic_posts(topic.id)
        for post in posts:
            db.insert_post(post)
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(topics)}")
    except Exception as e:
        print(f"  Error topic {topic.id}: {e}")

print(f"✓ Posts fetched\n")

# Now fetch ALL users using the fixed method
print("Step 2: Fetching user profiles...")
unique_usernames = db.get_unique_usernames()
unique_usernames = {u for u in unique_usernames if u and u != "system"}
existing_users = {u.username for u in db.get_all_users()}
usernames_to_fetch = unique_usernames - existing_users

print(f"  Total unique usernames: {len(unique_usernames)}")
print(f"  Already in DB: {len(existing_users)}")
print(f"  Need to fetch: {len(usernames_to_fetch)}")

if usernames_to_fetch:
    user_fetcher = UserFetcher(client, db)
    fetched = 0
    failed = 0

    for i, username in enumerate(sorted(usernames_to_fetch), 1):
        try:
            user = user_fetcher.fetch_user(username)
            if user:
                db.insert_user(user)
                fetched += 1
            else:
                failed += 1
            if i % 10 == 0:
                print(
                    f"  Progress: {i}/{len(usernames_to_fetch)} ({fetched} fetched, {failed} failed)"
                )
        except Exception as e:
            failed += 1
            if "ascii" not in str(e):
                print(f"  Failed {username}: {str(e)[:50]}")

    print(f"✓ Fetched {fetched} users ({failed} failed)\n")

# Validate
final_unique = len(db.get_unique_usernames() - {"system"})
final_users = len(db.get_all_users())
print(f"VALIDATION:")
print(f"  Unique usernames in posts (excluding system): {final_unique}")
print(f"  Users in database: {final_users}")
print(f"  Missing: {final_unique - final_users}")

if final_unique == final_users:
    print(f"  ✅ ALL USERS FETCHED!")
else:
    print(f"  ⚠️  Still missing {final_unique - final_users} users")

# Generate exports
print(f"\nStep 3: Generating exports...")
html_exp = HTMLStaticExporter(db, output_dir / "html", include_users=True)
html_exp.export()
print("  ✓ HTML")

md_exp = MarkdownPlainExporter(db, output_dir / "markdown", include_users=True)
md_exp.export()
print("  ✓ Markdown")

gh_exp = MarkdownGitHubExporter(db, output_dir / "github", include_users=True)
gh_exp.export()
print("  ✓ GitHub")

print(f"\n✅ Complete: {len(topics)} topics, {final_users} users")
