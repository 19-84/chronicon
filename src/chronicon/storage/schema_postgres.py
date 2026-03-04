# ABOUTME: PostgreSQL schema definitions for Chronicon
# ABOUTME: CREATE TABLE and CREATE INDEX statements for PostgreSQL with FTS

"""SQL schema definitions for PostgreSQL archive database."""

# Schema version for migrations
SCHEMA_VERSION = 4  # Incremented for top_tags table and FTS trigger fixes

# Core tables
CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    user_id INTEGER,
    post_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cooked TEXT,
    raw TEXT,
    username TEXT,
    search_vector tsvector
);
"""

CREATE_POSTS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic_id);
CREATE INDEX IF NOT EXISTS idx_posts_updated ON posts(updated_at);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_search_gin ON posts USING GIN(search_vector);
"""

CREATE_TOPICS_TABLE = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    category_id INTEGER,
    user_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,
    posts_count INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,

    -- Content & Discovery
    tags JSONB,
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
    pinned BOOLEAN DEFAULT FALSE,
    pinned_globally BOOLEAN DEFAULT FALSE,
    closed BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,

    -- Context & Metadata
    featured_link TEXT,
    has_accepted_answer BOOLEAN DEFAULT FALSE,
    has_summary BOOLEAN DEFAULT FALSE,
    visible BOOLEAN DEFAULT TRUE,
    last_posted_at TIMESTAMP WITH TIME ZONE,
    thumbnails JSONB,
    bookmarked BOOLEAN DEFAULT FALSE,

    -- Full-text search
    search_vector tsvector
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
CREATE INDEX IF NOT EXISTS idx_topics_tags_gin ON topics USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_topics_search_gin ON topics USING GIN(search_vector);
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_template TEXT,
    trust_level INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE
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
    topic_count INTEGER DEFAULT 0
);
"""

CREATE_ASSETS_TABLE = """
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    local_path TEXT NOT NULL,
    content_type TEXT,
    downloaded_at TIMESTAMP WITH TIME ZONE NOT NULL
);
"""

CREATE_ASSETS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_assets_url ON assets(url);
"""

CREATE_SITE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS site_metadata (
    site_url TEXT PRIMARY KEY,
    last_sync_date TIMESTAMP WITH TIME ZONE,
    theme_version TEXT,
    site_title TEXT,
    site_description TEXT,
    banner_image_url TEXT,
    contact_email TEXT,
    discourse_version TEXT,
    logo_url TEXT,
    category_filter JSONB
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
    id SERIAL PRIMARY KEY,
    format TEXT NOT NULL,
    exported_at TIMESTAMP WITH TIME ZONE NOT NULL,
    topic_count INTEGER,
    post_count INTEGER,
    output_path TEXT
);
"""

# Full-text search triggers - split into separate statements for proper execution
CREATE_TOPICS_FTS_FUNCTION = """
CREATE OR REPLACE FUNCTION topics_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.excerpt, '')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;
"""

CREATE_TOPICS_FTS_TRIGGER = """
DROP TRIGGER IF EXISTS topics_search_vector_trigger ON topics;
CREATE TRIGGER topics_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, excerpt
    ON topics
    FOR EACH ROW
    EXECUTE FUNCTION topics_search_vector_update();
"""

CREATE_POSTS_FTS_FUNCTION = """
CREATE OR REPLACE FUNCTION posts_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(
            regexp_replace(COALESCE(NEW.raw, NEW.cooked, ''), '<[^>]+>', ' ', 'g'),
        '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.username, '')), 'C');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;
"""

CREATE_POSTS_FTS_TRIGGER = """
DROP TRIGGER IF EXISTS posts_search_vector_trigger ON posts;
CREATE TRIGGER posts_search_vector_trigger
    BEFORE INSERT OR UPDATE OF raw, cooked, username
    ON posts
    FOR EACH ROW
    EXECUTE FUNCTION posts_search_vector_update();
"""

# Schema version tracking
CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL
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
    # Full-text search functions (contain $$, executed as-is)
    CREATE_TOPICS_FTS_FUNCTION,
    CREATE_POSTS_FTS_FUNCTION,
    # Full-text search triggers (no $$, split on semicolons)
    CREATE_TOPICS_FTS_TRIGGER,
    CREATE_POSTS_FTS_TRIGGER,
]


def create_schema(connection):
    """
    Create all tables and indices in the PostgreSQL database.

    Args:
        connection: PostgreSQL database connection
    """
    cursor = connection.cursor()

    # Check if schema is already at current version
    try:
        cursor.execute(
            "SELECT version FROM schema_version WHERE version = %s",
            (SCHEMA_VERSION,),
        )
        if cursor.fetchone():
            # Schema already at current version, skip creation
            connection.commit()
            return
    except Exception:
        # Table doesn't exist yet, continue with schema creation
        connection.rollback()

    for statement in ALL_SCHEMA_STATEMENTS:
        statement = statement.strip()
        if not statement:
            continue

        # If statement contains dollar-quoting ($$), execute as-is
        # This handles function definitions with embedded semicolons
        if "$$" in statement:
            cursor.execute(statement)
        else:
            # Split on semicolons for regular statements (CREATE TABLE, CREATE INDEX)
            for sql in statement.split(";"):
                sql = sql.strip()
                if sql:
                    cursor.execute(sql)

    # Record schema version
    cursor.execute(
        "INSERT INTO schema_version (version, applied_at) "
        "VALUES (%s, NOW()) ON CONFLICT (version) DO NOTHING",
        (SCHEMA_VERSION,),
    )

    connection.commit()
