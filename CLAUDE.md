# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Commits

**No attribution.** Never include `Co-Authored-By` lines in commit messages. Do not attribute commits to Claude or any AI assistant.

## Project Overview

Chronicon is a multi-format Discourse forum archiving tool built with Python 3.11+. It exports forums to three formats:
- **Static HTML** - Fully offline-viewable with clean default theme, client-side search
- **Plain Markdown** - Clean, readable markdown files for offline reading
- **GitHub Markdown** - GFM with embedded images, optimized for GitHub Pages

Uses SQLite for efficient storage and querying (not JSON) to handle 100k+ posts with indexed queries and O(1) duplicate detection. PostgreSQL is also supported for large-scale deployments.

## Development Commands

### Testing
```bash
# Run all tests (PREFERRED METHOD)
.venv/bin/python -m pytest

# Run specific test file
.venv/bin/python -m pytest tests/test_database.py

# Run with verbose output
.venv/bin/python -m pytest tests/test_processors.py -v

# Run with coverage
.venv/bin/python -m pytest --cov=chronicon --cov-report=term-missing

# Run specific test class
.venv/bin/python -m pytest tests/test_processors.py::TestHTMLProcessor -v

# Alternative: Using uv (less reliable for module imports)
uv run pytest tests/test_database.py
```

### Code Quality Tools
```bash
# Format code with ruff (replaces black)
.venv/bin/ruff format src/ tests/

# Check formatting without making changes
.venv/bin/ruff format --check src/ tests/

# Lint code with ruff
.venv/bin/ruff check src/ tests/

# Lint with auto-fix
.venv/bin/ruff check src/ tests/ --fix

# Type check with pyright (replaces mypy)
.venv/bin/pyright src/ tests/

# Run all quality checks (format + lint + type check)
.venv/bin/ruff format --check src/ tests/ && \
.venv/bin/ruff check src/ tests/ && \
.venv/bin/pyright src/ tests/

# Alternative: Using uv run
uv run ruff format src/ tests/
uv run ruff check src/ tests/ --fix
uv run pyright src/ tests/
```

### Dependencies
```bash
# Install/sync all dependencies including dev
uv sync --all-extras

# Sync without extras (production only)
uv sync

# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Install package in editable mode (after adding to pyproject.toml)
uv pip install -e .
```

### Git Operations
```bash
# Commit changes
git add <files>
git commit -m "commit message"

# Check status
git status

# View diff statistics
git diff --stat
```

### Running the CLI
```bash
# Run archive command via venv
.venv/bin/python -m chronicon.cli archive --urls https://meta.discourse.org

# Alternative: Using uv run
uv run chronicon archive --urls https://meta.discourse.org
```

### Python Environment
```bash
# Verify venv Python
.venv/bin/python --version

# Check installed packages
.venv/bin/python -m pip list

# Run Python REPL with package available
.venv/bin/python
```

## Real World Testing

**Always use meta.discourse.org for real world testing.** This is the official Discourse meta forum and provides a reliable, well-maintained test target. Example commands:

```bash
# Test archiving a single category
.venv/bin/python -m chronicon.cli archive --urls https://meta.discourse.org --categories 1

# Test incremental update
.venv/bin/python -m chronicon.cli update --output-dir ./archives

# Test sweep mode (exhaustive topic fetching)
.venv/bin/python -m chronicon.cli archive --urls https://meta.discourse.org --sweep --start-id 1000

# Test watch mode
.venv/bin/python -m chronicon.cli watch --output-dir ./archives

# Alternative with uv
uv run chronicon archive --urls https://meta.discourse.org --categories 1
```

**Sweep Mode**: Use `--sweep` to exhaustively fetch every topic ID from `--start-id` (defaults to max topic ID) down to `--end-id` (defaults to 1). This is useful for recovering deleted or unlisted topics that don't appear in category listings.

## Architecture

The codebase follows a 7-layer modular architecture with clear separation of concerns:

### 1. Models (`src/chronicon/models/`)
Dataclasses for domain objects: Post, Topic, User, Category, SiteConfig

**Key convention:** All models must implement:
- `from_dict(cls, data: dict)` - Create from API JSON
- `to_dict(self) -> dict` - Serialize to dict

**Storage models only** (Post, Topic, Category) additionally implement:
- `to_db_row(self) -> tuple` - Convert to database row format

Note: User and SiteConfig models do NOT implement `to_db_row()` as they use different storage patterns.

### 2. Storage (`src/chronicon/storage/`)
Database abstraction layer supporting both SQLite and PostgreSQL backends.

**Key files:**
- `database_base.py` - Abstract base class defining database interface
- `database.py` - SQLite implementation (default, zero-dependency)
- `postgres_database.py` - PostgreSQL implementation (optional, requires `chronicon[postgres]`)
- `factory.py` - Database factory for selecting backend based on connection string
- `schema.py` - SQLite schema definitions with FTS5 full-text search
- `schema_postgres.py` - PostgreSQL schema definitions with tsvector full-text search
- `migrations.py` - JSON migration utilities for legacy archives

**Important:** The database uses `INSERT OR REPLACE` (SQLite) or `INSERT ... ON CONFLICT` (PostgreSQL) for upserts. All timestamps stored as ISO format strings. PostgreSQL support is optional and requires installing with `pip install chronicon[postgres]`.

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@localhost/chronicon`)
- When set, CLI and watch daemon automatically use PostgreSQL instead of SQLite

### 3. Fetchers (`src/chronicon/fetchers/`)
HTTP API clients for different Discourse endpoints with rate limiting and retry logic.

**Key classes:**
- `DiscourseAPIClient` - Base HTTP client with exponential backoff
- `PostFetcher` - Fetch posts with pagination handling
- `TopicFetcher` - Fetch topics and their full post streams
- `AssetDownloader` - Concurrent asset downloads (images, avatars, emoji)

### 4. Processors (`src/chronicon/processors/`)
Content transformation and processing.

**Key components:**
- `HTMLProcessor` - Parse and process post HTML content
- `URLRewriter` - Convert absolute URLs to relative paths for offline viewing

### 5. Exporters (`src/chronicon/exporters/`)
Generate output files in different formats.

**Key convention:** All exporters subclass `BaseExporter` and implement `export()` method.

**Exporters:**
- `HTMLStaticExporter` - Static HTML site with Jinja2 templates
- `MarkdownPlainExporter` - Simple markdown files
- `MarkdownGitHubExporter` - GitHub-flavored markdown with image embedding

### 6. Utils (`src/chronicon/utils/`)
Cross-cutting utilities.

**Components:**
- `logger.py` - Rich-based logging setup
- `concurrency.py` - ThreadPoolExecutor helpers for concurrent operations
- `search_indexer.py` - Generate search index JSON for HTML export
- `update_manager.py` - Orchestrates incremental updates with date-based and category filtering

### 7. Watch Mode (`src/chronicon/watch/`)
Continuous monitoring and automatic archive updates.

**Components:**
- `daemon.py` - Long-running daemon for continuous monitoring
- `git_manager.py` - Git integration (auto-commit, auto-push, HTTPS token auth)
- `status.py` - Status tracking and history management
- `health_server.py` - HTTP health check endpoints for monitoring

**Features:**
- Automatic polling for new/modified posts at configurable intervals
- Git integration with customizable commit messages and auto-push
- HTTPS token authentication via `GIT_TOKEN`, `GIT_USERNAME`, `GIT_REMOTE_URL` env vars
- HTTP health endpoints (`/health`, `/metrics`) for monitoring
- Process management with PID files and graceful shutdown
- Exponential backoff on errors with configurable thresholds
- Comprehensive status tracking with cycle history
- `EXPORT_FORMATS` environment variable to override export formats

See WATCH_MODE.md for complete documentation on continuous monitoring features.

## Key Design Decisions

### Storage Backend: SQLite vs PostgreSQL

**Why SQLite (default)?**
- **Zero dependencies:** Built into Python stdlib
- **Performance:** Indexed queries, handles 100k+ posts efficiently
- **Portability:** Single file, easy to backup and move
- **Relationships:** Native JOINs for post/topic/user relationships
- **Incremental Updates:** O(1) duplicate detection

**When to use PostgreSQL?**
- **Scale:** Multi-million post archives
- **Concurrent access:** Multiple processes/users accessing archive
- **Server deployments:** Centralized archive management
- **Advanced features:** Full-text search with specialized indexes

### Data Flow
1. **Fetching:** API Client → Database (store raw data)
2. **Processing:** Database → Processors → Database (rewrite URLs, download assets)
3. **Exporting:** Database → Exporters → Files (generate outputs)

### Three Export Formats
Each format serves a different use case:
- **HTML:** Best for full-fidelity browsing with search and navigation
- **Plain Markdown:** Best for archival and simple offline reading
- **GitHub Markdown:** Best for hosting on GitHub Pages or documentation sites

### Category Filtering
Chronicon supports filtering archives to specific categories:

**Setting the filter:**
- **CLI**: Use `--categories 1,2,7` during archive command
- **Config**: Define per-site category filters in `.chronicon.toml`:
  ```toml
  [[sites]]
  url = "https://meta.discourse.org"
  categories = [61]  # Only archive Theme category
  ```

**How it works:**
- Archive command reads from CLI first, then config file
- Filter is stored in `site_metadata.category_filter` for persistence
- Watch mode reads from config first, falls back to database
- Backfill command respects the database filter
- UpdateManager checks topic categories before processing posts

**Priority order:**
- **Archive command**: CLI `--categories` > Config `[[sites]]` categories
- **Watch mode**: Config `[[sites]]` categories > Database `site_metadata.category_filter`

**Docker example:**
```bash
docker compose run --rm api archive \
  --urls https://meta.discourse.org \
  --categories 61 \
  --output-dir /archives
```

### Search Backends
HTML exports support two search modes:
- **FTS (default)**: Server-rendered using SQLite FTS5 or PostgreSQL tsvector
  - Best performance and relevance ranking
  - Requires running the API server
  - Use `--search-backend fts` (or omit for default)
- **Static**: Client-side JavaScript search
  - Works completely offline
  - Generates `search_index.json` for client-side searching
  - Use `--search-backend static`

## Code Conventions

### File Headers
Every code file must start with two ABOUTME comments:
```python
# ABOUTME: Brief description of what this file does
# ABOUTME: Second line with additional context
```

### Model Structure
Models are dataclasses with conversion methods. Example pattern:
```python
@dataclass
class Post:
    id: int
    topic_id: int
    # ... fields ...

    @classmethod
    def from_dict(cls, data: dict) -> 'Post':
        """Create from API JSON response."""
        pass

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        pass

    def to_db_row(self) -> tuple:
        """Convert to SQLite row format."""
        pass
```

### Exporter Structure
All exporters follow this pattern:
```python
class MyExporter(BaseExporter):
    def __init__(self, db: ArchiveDatabase, output_dir: Path):
        super().__init__(db, output_dir)

    def export(self) -> None:
        """Main export method - orchestrates the export process."""
        pass
```

## Test Structure

Tests are organized by component in `tests/`:
- `test_models.py` - Model serialization/deserialization with validation
- `test_models_edge_cases.py` - Edge case testing for models
- `test_database.py` - Database CRUD operations (SQLite)
- `test_database_factory.py` - Database factory pattern tests
- `test_postgres_integration.py` - PostgreSQL integration tests (requires `TEST_POSTGRES_URL`)
- `test_api_client.py` - API client and retry logic
- `test_fetchers.py` - Fetcher integration tests
- `test_processors.py` - HTMLProcessor, URLRewriter
- `test_asset_downloader.py` - Concurrent asset downloads
- `test_local_assets.py` - Local asset management
- `test_asset_pipeline_integration.py` - Asset management pipeline integration
- `test_exporters.py` - All three exporter formats (HTML, Markdown, GitHub)
- `test_markdown_export_integration.py` - Markdown exporter integration
- `test_update_manager.py` - Incremental update logic
- `test_incremental_update_integration.py` - Incremental update integration
- `test_config.py` - TOML configuration loading
- `test_cli.py` - CLI command handlers
- `test_cli_database_url.py` - DATABASE_URL and environment variable tests
- `test_concurrency.py` - Concurrent processing utilities
- `test_watch_daemon.py` - Watch mode daemon
- `test_git_manager.py` - Git integration
- `test_watch_status.py` - Status tracking
- `test_health_server.py` - Health monitoring endpoints
- `test_real_world_integration.py` - End-to-end integration tests
- `fixtures/` - Sample API responses and test data

## Important Files

- `ARCHITECTURE.md` - High-level architecture documentation
- `WATCH_MODE.md` - Comprehensive watch mode and continuous monitoring guide
- `.chronicon.toml.example` - Example configuration file
- `pyproject.toml` - Project metadata and dependencies
- `templates/` - Jinja2 templates for HTML export
- `static/` - CSS and JS for HTML export
