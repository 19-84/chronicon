# API Reference

**[Documentation Index](DOCUMENTATION.md)** > API Reference

**Related:** [Examples](EXAMPLES.md) | [Development Guide](DEVELOPMENT.md) | [Troubleshooting](TROUBLESHOOTING.md)

---

Comprehensive API documentation for using Chronicon programmatically as a Python library.

## Table of Contents

- [Quick Start](#quick-start)
- [Database API](#database-api)
- [Exporters API](#exporters-api)
- [Fetchers API](#fetchers-api)
- [Models](#models)
- [Configuration](#configuration)
- [Complete Examples](#complete-examples)

## Quick Start

### Basic Archive Creation

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.fetchers import DiscourseAPIClient, PostFetcher, TopicFetcher
from chronicon.exporters import HTMLStaticExporter

# Initialize database
db = ArchiveDatabase(db_path=Path("./my_archive/archive.db"))

# Fetch data
client = DiscourseAPIClient(base_url="https://meta.discourse.org")
topic_fetcher = TopicFetcher(client, db)
topics = topic_fetcher.fetch_recent_topics(category_id=1, limit=100)

# Export to HTML
exporter = HTMLStaticExporter(db, output_dir=Path("./my_archive/html"))
exporter.export()

# Clean up
db.close()
```

## Database API

### ArchiveDatabase

Main interface for storing and retrieving archived data.

#### Constructor

```python
from chronicon.storage import ArchiveDatabase
from pathlib import Path

# SQLite (default)
db = ArchiveDatabase(db_path=Path("./archive.db"))

# PostgreSQL (optional, requires chronicon[postgres])
db = ArchiveDatabase(connection_string="postgresql://user:pass@localhost/chronicon")
```

**Parameters:**
- `db_path` (Path, optional): Path to SQLite database file
- `connection_string` (str, optional): Database connection string (overrides db_path)

**Raises:**
- `ValueError`: If neither db_path nor connection_string provided

#### Post Operations

```python
# Save a post
from chronicon.models import Post

post = Post(
    id=12345,
    topic_id=100,
    post_number=1,
    username="alice",
    created_at="2025-01-01T00:00:00Z",
    updated_at="2025-01-01T00:00:00Z",
    cooked="<p>Hello world</p>",
    raw="Hello world",
    reply_count=5,
    like_count=10
)
db.save_post(post)

# Get post by ID
post = db.get_post(12345)

# Get all posts in a topic
posts = db.get_posts_by_topic(topic_id=100)

# Get posts by user
posts = db.get_posts_by_user(username="alice")

# Get recent posts
posts = db.get_recent_posts(limit=50, since="2025-01-01T00:00:00Z")
```

**Methods:**
- `save_post(post: Post) -> None`: Save or update a post
- `get_post(post_id: int) -> Post | None`: Retrieve post by ID
- `get_posts_by_topic(topic_id: int) -> list[Post]`: Get all posts in topic (ordered by post_number)
- `get_posts_by_user(username: str) -> list[Post]`: Get all posts by user
- `get_recent_posts(limit: int, since: str = None) -> list[Post]`: Get recent posts, optionally filtered by date

#### Topic Operations

```python
# Save a topic
from chronicon.models import Topic

topic = Topic(
    id=100,
    title="Welcome to the forum",
    slug="welcome-to-the-forum",
    created_at="2025-01-01T00:00:00Z",
    updated_at="2025-01-02T00:00:00Z",
    category_id=1,
    views=500,
    reply_count=10,
    like_count=25,
    archived=False,
    closed=False,
    pinned=True
)
db.save_topic(topic)

# Get topic by ID
topic = db.get_topic(100)

# Get topics in category
topics = db.get_topics_by_category(category_id=1)

# Get all topics
topics = db.get_all_topics()

# Get topics by IDs (for incremental updates)
topics = db.get_topics_by_ids([100, 101, 102])
```

**Methods:**
- `save_topic(topic: Topic) -> None`: Save or update a topic
- `get_topic(topic_id: int) -> Topic | None`: Retrieve topic by ID
- `get_topics_by_category(category_id: int) -> list[Topic]`: Get all topics in category
- `get_all_topics() -> list[Topic]`: Get all archived topics
- `get_topics_by_ids(topic_ids: list[int]) -> list[Topic]`: Get specific topics by IDs

#### Category Operations

```python
# Save a category
from chronicon.models import Category

category = Category(
    id=1,
    name="General",
    slug="general",
    description="General discussion",
    parent_category_id=None,
    topic_count=100
)
db.save_category(category)

# Get category
category = db.get_category(1)

# Get all categories
categories = db.get_all_categories()
```

**Methods:**
- `save_category(category: Category) -> None`: Save or update category
- `get_category(category_id: int) -> Category | None`: Retrieve category by ID
- `get_all_categories() -> list[Category]`: Get all categories

#### User Operations

```python
# Save user
from chronicon.models import User

user = User(
    id=42,
    username="alice",
    name="Alice Smith",
    avatar_template="/user_avatar/meta.discourse.org/alice/{size}/12345.png",
    trust_level=2
)
db.save_user(user)

# Get user
user = db.get_user(42)

# Get user by username
user = db.get_user_by_username("alice")
```

**Methods:**
- `save_user(user: User) -> None`: Save or update user
- `get_user(user_id: int) -> User | None`: Retrieve user by ID
- `get_user_by_username(username: str) -> User | None`: Retrieve user by username

#### Site Metadata

```python
# Save site configuration
from chronicon.models import SiteConfig

config = SiteConfig(
    title="My Forum",
    description="A place for discussion",
    base_url="https://forum.example.com"
)
db.save_site_metadata(config)

# Get site configuration
config = db.get_site_metadata()
```

**Methods:**
- `save_site_metadata(config: SiteConfig) -> None`: Save site configuration
- `get_site_metadata() -> SiteConfig | None`: Retrieve site configuration

#### Export History

```python
# Record export for incremental updates
db.record_export(
    format="html",
    topic_ids=[100, 101, 102],
    timestamp="2025-01-15T10:30:00Z"
)

# Get last export time for format
last_export = db.get_last_export_time(format="html")
print(f"Last HTML export: {last_export}")
```

**Methods:**
- `record_export(format: str, topic_ids: list[int], timestamp: str) -> None`: Record export for tracking
- `get_last_export_time(format: str) -> str | None`: Get timestamp of last export for format

#### Statistics

```python
# Get archive statistics
stats = db.get_statistics()
print(f"Topics: {stats['total_topics']}")
print(f"Posts: {stats['total_posts']}")
print(f"Users: {stats['total_users']}")
print(f"Categories: {stats['total_categories']}")
```

**Returns:** Dictionary with keys:
- `total_topics`: Number of archived topics
- `total_posts`: Number of archived posts
- `total_users`: Number of users
- `total_categories`: Number of categories

## Exporters API

All exporters inherit from `BaseExporter` and follow the same interface.

### Base Interface

```python
from chronicon.exporters import BaseExporter

class MyExporter(BaseExporter):
    def export(self) -> None:
        """Main export method - implement your export logic here."""
        pass
```

### HTMLStaticExporter

Generate static HTML site with navigation and search.

```python
from chronicon.exporters import HTMLStaticExporter
from chronicon.storage import ArchiveDatabase
from pathlib import Path

db = ArchiveDatabase(db_path=Path("./archive.db"))
exporter = HTMLStaticExporter(
    db=db,
    output_dir=Path("./output/html"),
    progress=None  # Optional Rich Progress object
)

# Full export
exporter.export()

# Incremental export (specific topics)
exporter.export_topics(topic_ids=[100, 101, 102])
exporter.update_index()  # Update search index and category pages
```

**Methods:**
- `export() -> None`: Export all content to HTML
- `export_topics(topic_ids: list[int]) -> None`: Export specific topics only
- `update_index() -> None`: Regenerate index pages and search index

**Output Structure:**
```
output/html/
├── index.html                 # Homepage
├── c/
│   └── category-slug/
│       └── index.html
├── t/
│   └── topic-slug/
│       └── 123/
│           ├── index.html     # Topic page
│           └── page-2.html    # Paginated pages
├── u/
│   └── username/
│       └── index.html         # User profile
├── assets/
│   ├── css/
│   ├── js/
│   ├── images/
│   ├── emoji/
│   └── site/
└── search_index.json
```

### MarkdownPlainExporter

Export to plain Markdown files.

```python
from chronicon.exporters import MarkdownPlainExporter

exporter = MarkdownPlainExporter(
    db=db,
    output_dir=Path("./output/markdown")
)
exporter.export()
```

**Methods:**
- `export() -> None`: Export all content to Markdown
- `export_topics(topic_ids: list[int]) -> None`: Export specific topics

**Output Structure:**
```
output/markdown/
├── topics/
│   └── YYYY-MM-Month/
│       └── YYYY-MM-DD-topic-slug-123.md
├── categories/
│   └── category-slug/
│       └── index.md
└── index.md
```

### MarkdownGitHubExporter

Export GitHub-flavored Markdown optimized for GitHub Pages.

```python
from chronicon.exporters import MarkdownGitHubExporter

exporter = MarkdownGitHubExporter(
    db=db,
    output_dir=Path("./output/github")
)
exporter.export()
```

**Methods:**
- `export() -> None`: Export all content as GitHub Markdown
- `export_topics(topic_ids: list[int]) -> None`: Export specific topics

**Output Structure:**
```
output/github/
├── README.md                  # TOC with all topics
├── topics/
│   └── YYYY-MM-Month/
│       └── topic-slug-123.md
└── assets/
    └── images/
        └── 123/               # Images by topic ID
```

## Fetchers API

### DiscourseAPIClient

Low-level HTTP client with rate limiting and retry logic.

```python
from chronicon.fetchers import DiscourseAPIClient

client = DiscourseAPIClient(
    base_url="https://meta.discourse.org",
    rate_limit=0.5,     # Seconds between requests
    timeout=15,         # Request timeout
    max_retries=5       # Retry attempts
)

# Fetch JSON endpoint
data = client.get_json("/latest.json")

# Fetch raw text
html = client.get("/about")

# Get statistics
print(f"Requests made: {client.requests_made}")
print(f"Success rate: {client.requests_successful / client.requests_made * 100}%")
print(f"Data transferred: {client.bytes_transferred / 1024 / 1024:.2f} MB")
```

**Methods:**
- `get(path: str) -> str`: Fetch URL and return response body
- `get_json(path: str) -> dict`: Fetch URL and return parsed JSON

**Attributes:**
- `requests_made`: Total requests attempted
- `requests_successful`: Successful requests
- `requests_failed`: Failed requests
- `retries_attempted`: Number of retries
- `bytes_transferred`: Total bytes downloaded

### TopicFetcher

Fetch topics from Discourse API.

```python
from chronicon.fetchers import TopicFetcher

fetcher = TopicFetcher(client, db)

# Fetch recent topics
topics = fetcher.fetch_recent_topics(limit=100)

# Fetch category topics
topics = fetcher.fetch_category_topics(category_id=1, limit=50)

# Fetch specific topic with all posts
topic = fetcher.fetch_topic_with_posts(topic_id=12345)

# Sweep mode: exhaustively fetch all topics
topics = fetcher.sweep_topics(
    start_id=10000,  # Start from this ID
    end_id=1,        # Go down to this ID
    batch_size=50    # Topics per batch
)
```

**Methods:**
- `fetch_recent_topics(limit: int, page: int = 0) -> list[Topic]`: Fetch recent topics
- `fetch_category_topics(category_id: int, limit: int) -> list[Topic]`: Fetch topics in category
- `fetch_topic_with_posts(topic_id: int) -> Topic`: Fetch topic with all posts
- `sweep_topics(start_id: int, end_id: int, batch_size: int) -> list[Topic]`: Exhaustive topic fetch

### PostFetcher

Fetch posts from Discourse API.

```python
from chronicon.fetchers import PostFetcher

fetcher = PostFetcher(client, db)

# Fetch posts for topic
posts = fetcher.fetch_topic_posts(topic_id=12345)

# Fetch recent posts (for incremental updates)
posts = fetcher.fetch_recent_posts(
    since="2025-01-01T00:00:00Z",
    limit=100
)
```

**Methods:**
- `fetch_topic_posts(topic_id: int) -> list[Post]`: Fetch all posts in topic
- `fetch_recent_posts(since: str, limit: int) -> list[Post]`: Fetch posts since timestamp

### CategoryFetcher

Fetch categories from Discourse API.

```python
from chronicon.fetchers import CategoryFetcher

fetcher = CategoryFetcher(client, db)

# Fetch all categories
categories = fetcher.fetch_categories()
```

**Methods:**
- `fetch_categories() -> list[Category]`: Fetch all categories

### UserFetcher

Fetch user information.

```python
from chronicon.fetchers import UserFetcher

fetcher = UserFetcher(client, db)

# Fetch user by username
user = fetcher.fetch_user(username="alice")
```

**Methods:**
- `fetch_user(username: str) -> User`: Fetch user by username

### AssetDownloader

Download images, avatars, and emoji with concurrency.

```python
from chronicon.fetchers import AssetDownloader
from pathlib import Path

downloader = AssetDownloader(
    base_url="https://meta.discourse.org",
    output_dir=Path("./assets"),
    max_workers=20  # Concurrent downloads
)

# Download single asset
local_path = downloader.download_asset(
    url="https://meta.discourse.org/uploads/default/123/image.png",
    relative_path="images/123/image.png"
)

# Download multiple assets concurrently
urls = [
    ("https://example.com/image1.png", "images/image1.png"),
    ("https://example.com/image2.png", "images/image2.png"),
]
results = downloader.download_assets(urls)
```

**Methods:**
- `download_asset(url: str, relative_path: str) -> Path`: Download single asset
- `download_assets(assets: list[tuple[str, str]]) -> list[Path]`: Download multiple assets concurrently

## Models

All models are dataclasses with conversion methods.

### Post

```python
from chronicon.models import Post

# Create from API response
post = Post.from_dict(api_response)

# Convert to dict
data = post.to_dict()

# Convert to database row
row = post.to_db_row()

# Access fields
print(f"Post #{post.post_number} by {post.username}")
print(f"Likes: {post.like_count}, Replies: {post.reply_count}")
```

**Fields:**
- `id` (int): Post ID
- `topic_id` (int): Parent topic ID
- `post_number` (int): Post number in topic (1 = OP)
- `username` (str): Author username
- `created_at` (str): ISO timestamp
- `updated_at` (str): ISO timestamp
- `cooked` (str): Rendered HTML content
- `raw` (str): Raw Markdown content
- `reply_count` (int): Number of replies
- `like_count` (int): Number of likes

### Topic

```python
from chronicon.models import Topic

topic = Topic.from_dict(api_response)

# Access fields
print(f"{topic.title} ({topic.views} views)")
print(f"Category: {topic.category_id}")
print(f"Replies: {topic.reply_count}, Likes: {topic.like_count}")
```

**Fields:**
- `id` (int): Topic ID
- `title` (str): Topic title
- `slug` (str): URL-safe slug
- `created_at` (str): ISO timestamp
- `updated_at` (str): ISO timestamp
- `category_id` (int): Parent category ID
- `views` (int): View count
- `reply_count` (int): Number of replies
- `like_count` (int): Number of likes
- `archived` (bool): Is archived
- `closed` (bool): Is closed
- `pinned` (bool): Is pinned

### Category

```python
from chronicon.models import Category

category = Category.from_dict(api_response)

# Access fields
print(f"{category.name}: {category.topic_count} topics")
if category.parent_category_id:
    print(f"Subcategory of {category.parent_category_id}")
```

**Fields:**
- `id` (int): Category ID
- `name` (str): Category name
- `slug` (str): URL-safe slug
- `description` (str): Category description
- `parent_category_id` (int | None): Parent category ID (for subcategories)
- `topic_count` (int): Number of topics

### User

```python
from chronicon.models import User

user = User.from_dict(api_response)

# Access fields
print(f"{user.name} (@{user.username})")
print(f"Trust level: {user.trust_level}")
```

**Fields:**
- `id` (int): User ID
- `username` (str): Username
- `name` (str): Display name
- `avatar_template` (str): Avatar URL template
- `trust_level` (int): Discourse trust level (0-4)

### SiteConfig

```python
from chronicon.models import SiteConfig

config = SiteConfig.from_dict(api_response)

# Access fields
print(f"{config.title}: {config.description}")
print(f"URL: {config.base_url}")
```

**Fields:**
- `title` (str): Site title
- `description` (str): Site description
- `base_url` (str): Base URL

## Configuration

### Loading Configuration

```python
from chronicon.config import ChronionConfig
from pathlib import Path

# Load from file
config = ChronionConfig.from_file(Path(".chronicon.toml"))

# Or from default locations
config = ChronionConfig.from_defaults()

# Access settings
print(f"Output dir: {config.output_dir}")
print(f"Formats: {config.default_formats}")
print(f"Rate limit: {config.rate_limit_seconds}")

# Site-specific config
for site in config.sites:
    print(f"Site: {site.url} (nickname: {site.nickname})")
```

### Configuration Structure

```python
# General settings
config.output_dir: Path
config.default_formats: list[str]  # ["html", "markdown", "github"]

# Fetching settings
config.rate_limit_seconds: float
config.max_workers: int
config.retry_max: int
config.timeout: int

# Export settings
config.include_users: bool
config.text_only: bool

# Continuous mode settings
config.polling_interval_minutes: int
config.max_consecutive_errors: int
config.git_enabled: bool
config.git_auto_commit: bool
config.git_push_to_remote: bool

# Site configurations
config.sites: list[SiteConfig]
```

## Complete Examples

### Example 1: Archive Specific Categories

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.fetchers import DiscourseAPIClient, TopicFetcher, CategoryFetcher
from chronicon.exporters import HTMLStaticExporter

# Setup
db = ArchiveDatabase(db_path=Path("./archive.db"))
client = DiscourseAPIClient(base_url="https://meta.discourse.org", rate_limit=1.0)

# Fetch categories
category_fetcher = CategoryFetcher(client, db)
categories = category_fetcher.fetch_categories()

# Archive specific categories
topic_fetcher = TopicFetcher(client, db)
for category in categories:
    if category.id in [1, 2, 7]:  # Only these categories
        print(f"Archiving category: {category.name}")
        topics = topic_fetcher.fetch_category_topics(category.id, limit=1000)
        
        for topic in topics:
            topic_fetcher.fetch_topic_with_posts(topic.id)

# Export
exporter = HTMLStaticExporter(db, output_dir=Path("./output/html"))
exporter.export()

db.close()
```

### Example 2: Incremental Updates

```python
from pathlib import Path
from datetime import datetime, timedelta
from chronicon.storage import ArchiveDatabase
from chronicon.utils import UpdateManager

# Setup
db = ArchiveDatabase(db_path=Path("./archive.db"))

# Get last export time
last_export = db.get_last_export_time("html")
if not last_export:
    last_export = (datetime.now() - timedelta(days=7)).isoformat()

# Fetch updates
manager = UpdateManager(db, base_url="https://meta.discourse.org")
updated_topics = manager.fetch_updates(since=last_export)

print(f"Found {len(updated_topics)} updated topics")

# Export only updated topics
if updated_topics:
    from chronicon.exporters import HTMLStaticExporter
    exporter = HTMLStaticExporter(db, output_dir=Path("./output/html"))
    exporter.export_topics([t.id for t in updated_topics])
    exporter.update_index()

db.close()
```

> **📚 Learn more:**
> - [PERFORMANCE.md](PERFORMANCE.md#strategy-1-incremental-archiving) - Why incremental updates are faster
> - [EXAMPLES.md](EXAMPLES.md#example-3-weekly-updates) - Automated update examples
> - [WATCH_MODE.md](WATCH_MODE.md) - Automated continuous updates

### Example 3: Custom Processing Pipeline

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.fetchers import DiscourseAPIClient, TopicFetcher
from chronicon.processors import HTMLProcessor, URLRewriter

# Setup
db = ArchiveDatabase(db_path=Path("./archive.db"))
client = DiscourseAPIClient(base_url="https://meta.discourse.org")
fetcher = TopicFetcher(client, db)

# Fetch and process
topics = fetcher.fetch_recent_topics(limit=10)

processor = HTMLProcessor(base_url="https://meta.discourse.org")
rewriter = URLRewriter(
    base_url="https://meta.discourse.org",
    output_dir=Path("./output")
)

for topic in topics:
    # Fetch posts
    posts = fetcher.fetch_topic_posts(topic.id)
    
    # Process each post
    for post in posts:
        # Parse HTML
        images = processor.extract_images(post.cooked)
        
        # Rewrite URLs
        post.cooked = rewriter.rewrite_post_html(
            post.cooked,
            topic_id=topic.id
        )
        
        # Save processed post
        db.save_post(post)

db.close()
```

### Example 4: Multi-Forum Archiver

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.fetchers import DiscourseAPIClient, TopicFetcher
from chronicon.exporters import MarkdownGitHubExporter

forums = [
    ("meta", "https://meta.discourse.org"),
    ("community", "https://community.example.com"),
]

for nickname, url in forums:
    print(f"Archiving {nickname}...")
    
    # Separate database per forum
    db = ArchiveDatabase(db_path=Path(f"./{nickname}/archive.db"))
    client = DiscourseAPIClient(base_url=url, rate_limit=1.0)
    
    # Fetch
    fetcher = TopicFetcher(client, db)
    topics = fetcher.fetch_recent_topics(limit=100)
    
    for topic in topics:
        fetcher.fetch_topic_with_posts(topic.id)
    
    # Export to separate directories
    exporter = MarkdownGitHubExporter(
        db,
        output_dir=Path(f"./{nickname}/github")
    )
    exporter.export()
    
    db.close()

print("All forums archived!")
```

### Example 5: Statistical Analysis

```python
from pathlib import Path
from collections import Counter
from chronicon.storage import ArchiveDatabase

db = ArchiveDatabase(db_path=Path("./archive.db"))

# Get statistics
stats = db.get_statistics()
print("Archive Statistics:")
print(f"  Topics: {stats['total_topics']}")
print(f"  Posts: {stats['total_posts']}")
print(f"  Users: {stats['total_users']}")
print(f"  Categories: {stats['total_categories']}")

# Top posters
posts = db.get_all_posts()
user_counts = Counter(post.username for post in posts)
print("\nTop 10 Posters:")
for username, count in user_counts.most_common(10):
    print(f"  {username}: {count} posts")

# Most viewed topics
topics = db.get_all_topics()
topics_sorted = sorted(topics, key=lambda t: t.views, reverse=True)
print("\nTop 10 Most Viewed Topics:")
for topic in topics_sorted[:10]:
    print(f"  {topic.title}: {topic.views} views")

db.close()
```

## Error Handling

```python
from chronicon.storage import ArchiveDatabase
from chronicon.fetchers import DiscourseAPIClient
import sqlite3
import urllib.error

try:
    db = ArchiveDatabase(db_path=Path("./archive.db"))
    client = DiscourseAPIClient(base_url="https://meta.discourse.org")
    
    # Operations here...
    
except sqlite3.Error as e:
    print(f"Database error: {e}")
except urllib.error.HTTPError as e:
    print(f"HTTP error {e.code}: {e.reason}")
except urllib.error.URLError as e:
    print(f"Network error: {e.reason}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    if 'db' in locals():
        db.close()
```

## Best Practices

1. **Always close database connections:**
   ```python
   try:
       db = ArchiveDatabase(db_path=Path("./archive.db"))
       # work...
   finally:
       db.close()
   ```

2. **Respect rate limits:**
   ```python
   # For public forums, use slower rate limits
   client = DiscourseAPIClient(base_url=url, rate_limit=1.0)
   ```

3. **Use incremental updates:**
   ```python
   # Don't re-fetch everything every time
   last_export = db.get_last_export_time("html")
   updated_topics = manager.fetch_updates(since=last_export)
   ```

4. **Handle errors gracefully:**
   ```python
   for topic_id in topic_ids:
       try:
           fetcher.fetch_topic_with_posts(topic_id)
       except Exception as e:
           print(f"Failed to fetch topic {topic_id}: {e}")
           continue
   ```

5. **Use progress tracking:**
   ```python
   from rich.progress import Progress
   
   with Progress() as progress:
       task = progress.add_task("Exporting...", total=len(topics))
       exporter = HTMLStaticExporter(db, output_dir, progress=progress)
       exporter.export()
   ```

## See Also

**Next Steps:**
- [EXAMPLES.md](EXAMPLES.md) - Real-world workflow examples using this API
- [DEVELOPMENT.md](DEVELOPMENT.md) - Setting up development environment
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions

**Related Documentation:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture details
- [README.md](README.md) - CLI usage and installation
- [PERFORMANCE.md](PERFORMANCE.md) - Performance optimization tips
- [MIGRATION.md](MIGRATION.md) - Upgrading and database migrations

**Return to:** [Documentation Index](DOCUMENTATION.md)
