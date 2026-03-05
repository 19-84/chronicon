# ABOUTME: Database schema definitions for Chronicon
# ABOUTME: CREATE TABLE and CREATE INDEX statements for SQLite with FTS5

"""SQL schema definitions for the archive database."""

# Schema version for migrations
SCHEMA_VERSION = 3  # Incremented for category_filter support

# Core tables
CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    user_id INTEGER,
    post_number INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    cooked TEXT,
    raw TEXT,
    username TEXT,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_POSTS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic_id);
CREATE INDEX IF NOT EXISTS idx_posts_updated ON posts(updated_at);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
"""

CREATE_TOPICS_TABLE = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    category_id INTEGER,
    user_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    posts_count INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,

    -- Content & Discovery
    tags TEXT,
    excerpt TEXT,
    image_url TEXT,
    fancy_title TEXT,

    -- Engagement Metrics
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    highest_post_number INTEGER DEFAULT 0,
    participant_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,

    -- Status & Classification
    pinned INTEGER DEFAULT 0,
    pinned_globally INTEGER DEFAULT 0,
    closed INTEGER DEFAULT 0,
    archived INTEGER DEFAULT 0,

    -- Context & Metadata
    featured_link TEXT,
    has_accepted_answer INTEGER DEFAULT 0,
    has_summary INTEGER DEFAULT 0,
    visible INTEGER DEFAULT 1,
    last_posted_at TEXT,
    thumbnails TEXT,
    bookmarked INTEGER DEFAULT 0,

    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_TOPICS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_topics_category ON topics(category_id);
CREATE INDEX IF NOT EXISTS idx_topics_created ON topics(created_at);
CREATE INDEX IF NOT EXISTS idx_topics_updated ON topics(updated_at);
CREATE INDEX IF NOT EXISTS idx_topics_pinned ON topics(pinned);
CREATE INDEX IF NOT EXISTS idx_topics_closed ON topics(closed);
CREATE INDEX IF NOT EXISTS idx_topics_archived ON topics(archived);
CREATE INDEX IF NOT EXISTS idx_topics_like_count ON topics(like_count);
CREATE INDEX IF NOT EXISTS idx_topics_last_posted ON topics(last_posted_at);
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_template TEXT,
    trust_level INTEGER DEFAULT 0,
    created_at TEXT,
    local_avatar_path TEXT
);
"""

CREATE_USERS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
"""

CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    color TEXT,
    text_color TEXT,
    description TEXT,
    parent_category_id INTEGER,
    topic_count INTEGER DEFAULT 0,
    FOREIGN KEY (parent_category_id) REFERENCES categories(id)
);
"""

CREATE_ASSETS_TABLE = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    local_path TEXT NOT NULL,
    content_type TEXT,
    downloaded_at TEXT NOT NULL
);
"""

CREATE_ASSETS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_assets_url ON assets(url);
"""

CREATE_SITE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS site_metadata (
    site_url TEXT PRIMARY KEY,
    last_sync_date TEXT,
    theme_version TEXT,
    site_title TEXT,
    site_description TEXT,
    banner_image_url TEXT,
    contact_email TEXT,
    discourse_version TEXT,
    logo_url TEXT,
    favicon_url TEXT,
    category_filter TEXT
);
"""

CREATE_TOP_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS top_tags (
    tag TEXT PRIMARY KEY,
    topic_count INTEGER DEFAULT 0
);
"""

CREATE_EXPORT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS export_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    format TEXT NOT NULL,
    exported_at TEXT NOT NULL,
    topic_count INTEGER,
    post_count INTEGER,
    output_path TEXT
);
"""

# Full-Text Search (FTS5) tables and triggers
CREATE_TOPICS_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
    title,
    excerpt,
    content='topics',
    content_rowid='id'
);
"""

CREATE_POSTS_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
    raw,
    username,
    content='posts',
    content_rowid='id'
);
"""

# Triggers to keep topics_fts in sync with topics table
CREATE_TOPICS_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS topics_fts_ai AFTER INSERT ON topics BEGIN
    INSERT INTO topics_fts(rowid, title, excerpt)
    VALUES (new.id, new.title, new.excerpt);
END;

CREATE TRIGGER IF NOT EXISTS topics_fts_ad AFTER DELETE ON topics BEGIN
    INSERT INTO topics_fts(topics_fts, rowid, title, excerpt)
    VALUES ('delete', old.id, old.title, old.excerpt);
END;

CREATE TRIGGER IF NOT EXISTS topics_fts_au AFTER UPDATE ON topics BEGIN
    INSERT INTO topics_fts(topics_fts, rowid, title, excerpt)
    VALUES ('delete', old.id, old.title, old.excerpt);
    INSERT INTO topics_fts(rowid, title, excerpt)
    VALUES (new.id, new.title, new.excerpt);
END;
"""

# Triggers to keep posts_fts in sync with posts table
CREATE_POSTS_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS posts_fts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, raw, username)
    VALUES (new.id, new.raw, new.username);
END;

CREATE TRIGGER IF NOT EXISTS posts_fts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, raw, username)
    VALUES ('delete', old.id, old.raw, old.username);
END;

CREATE TRIGGER IF NOT EXISTS posts_fts_au AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, raw, username)
    VALUES ('delete', old.id, old.raw, old.username);
    INSERT INTO posts_fts(rowid, raw, username)
    VALUES (new.id, new.raw, new.username);
END;
"""

# Schema version tracking
CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""

# All schema statements in order
ALL_SCHEMA_STATEMENTS = [
    CREATE_SCHEMA_VERSION_TABLE,
    CREATE_USERS_TABLE,
    CREATE_USERS_INDICES,
    CREATE_CATEGORIES_TABLE,
    CREATE_TOPICS_TABLE,
    CREATE_TOPICS_INDICES,
    CREATE_POSTS_TABLE,
    CREATE_POSTS_INDICES,
    CREATE_ASSETS_TABLE,
    CREATE_ASSETS_INDICES,
    CREATE_SITE_METADATA_TABLE,
    CREATE_TOP_TAGS_TABLE,
    CREATE_EXPORT_HISTORY_TABLE,
    # Full-text search tables and triggers
    CREATE_TOPICS_FTS_TABLE,
    CREATE_POSTS_FTS_TABLE,
    CREATE_TOPICS_FTS_TRIGGERS,
    CREATE_POSTS_FTS_TRIGGERS,
]


def create_schema(connection):
    """
    Create all tables and indices in the database.

    Args:
        connection: SQLite database connection
    """
    cursor = connection.cursor()

    for statement in ALL_SCHEMA_STATEMENTS:
        # Use executescript for complex statements (triggers with semicolons inside)
        # executescript can handle multiple statements separated by semicolons
        if statement.strip():
            connection.executescript(statement)

    # Record schema version
    cursor.execute(
        "INSERT OR REPLACE INTO schema_version (version, applied_at) "
        "VALUES (?, datetime('now'))",
        (SCHEMA_VERSION,),
    )

    connection.commit()
