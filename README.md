# Chronicon

**[Documentation Index](DOCUMENTATION.md)** | [FAQ](FAQ.md) | [Troubleshooting](TROUBLESHOOTING.md) | [API Reference](API_REFERENCE.md)

---

A powerful, multi-format archiver for Discourse forums.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](https://unlicense.org/)
[![Tests](https://github.com/19-84/chronicon/actions/workflows/test.yml/badge.svg)](https://github.com/19-84/chronicon/actions/workflows/test.yml)

## Features

- **Three Export Formats**: Static HTML, Plain Markdown, GitHub Markdown
- **Dual Storage Backend**: SQLite (default) or PostgreSQL for large-scale deployments
- **Category Filtering**: Archive specific categories with watch mode support
- **Flexible Search Backends**: FTS (server-rendered) or static (client-side) search
- **Incremental Updates**: Only fetch new/modified content
- **Continuous Monitoring**: Watch mode with automatic updates and git integration
- **Concurrent Processing**: Fast archiving with parallel operations
- **Clean Default Theme**: Professional, readable styling for HTML exports
- **Mobile-Friendly**: Responsive design for all devices
- **Sweep Mode**: Exhaustive topic fetching for complete archives

## Installation

```bash
# Using uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install chronicon

# Or with pip
pip install chronicon

# With PostgreSQL support (optional)
pip install chronicon[postgres]
# or
uv tool install chronicon[postgres]
```

## Quick Start

```bash
# Archive a forum to all formats
chronicon archive --urls https://meta.discourse.org

# HTML only, no images
chronicon archive \
  --urls https://forum.example.com \
  --formats html \
  --text-only

# Update existing archive
chronicon update --output-dir ./archives
```

## Usage

### Archive Command

Archive one or more Discourse forums:

```bash
# Archive entire forum to all formats
chronicon archive --urls https://meta.discourse.org

# Archive specific categories only
chronicon archive \
  --urls https://meta.discourse.org \
  --categories 1,2,7

# Archive to HTML format only, skip images
chronicon archive \
  --urls https://meta.discourse.org \
  --formats html \
  --text-only

# Archive posts since a specific date
chronicon archive \
  --urls https://meta.discourse.org \
  --since 2024-01-01

# Archive with custom output directory
chronicon archive \
  --urls https://meta.discourse.org \
  --output-dir ./my-archives

# Archive multiple sites at once
chronicon archive \
  --urls https://meta.discourse.org,https://discuss.example.com

# Sweep mode - exhaustively fetch every topic ID
chronicon archive \
  --urls https://meta.discourse.org \
  --sweep \
  --start-id 10000

# HTML with offline search (no API server needed)
chronicon archive \
  --urls https://meta.discourse.org \
  --formats html \
  --search-backend static
```

**Category Filtering**: Use `--categories 1,2,7` to archive specific categories. The filter is stored in the database and will be respected by watch mode and backfill commands.

**Sweep Mode**: Use `--sweep` to exhaustively fetch every topic ID from `--start-id` (defaults to max topic ID) down to `--end-id` (defaults to 1). This is useful for recovering deleted or unlisted topics that don't appear in normal category listings.

**Search Backends**: HTML exports support two search modes:
- `--search-backend fts` (default): Server-rendered full-text search. Requires API server but provides better performance and relevance.
- `--search-backend static`: Client-side JavaScript search that works completely offline.

> **💡 Tip:** Sweep mode is slower but more thorough. See [PERFORMANCE.md](PERFORMANCE.md#sweep-mode-performance) for optimization strategies.

### Update Command

Update an existing archive with new/modified content:

```bash
# Update all export formats
chronicon update --output-dir ./archives

# Update only HTML export
chronicon update \
  --output-dir ./archives \
  --formats html

# Update multiple formats
chronicon update \
  --output-dir ./archives \
  --formats html,markdown
```

### Validate Command

Validate archive integrity:

```bash
# Validate an archive
chronicon validate --output-dir ./archives
```

This checks:
- Database file exists and is readable
- Export directories are present
- Data integrity (no orphaned posts/topics)
- Export file structure is correct

### Migrate Command

Migrate from legacy JSON-based archives:

```bash
# Migrate from JSON to SQLite
chronicon migrate --from ./legacy_json_archive

# Migrate and export to HTML
chronicon migrate \
  --from ./legacy_json_archive \
  --format html
```

### Watch Command

Continuously monitor and automatically update archives (see [WATCH_MODE.md](WATCH_MODE.md) for full documentation):

```bash
# Start watching in foreground
chronicon watch --output-dir ./archives

# Run as background daemon
chronicon watch --output-dir ./archives --daemon

# Check daemon status
chronicon watch status --output-dir ./archives

# Stop daemon
chronicon watch stop --output-dir ./archives
```

**Watch Mode Features**:
- Automatic polling for new/modified posts (configurable interval, default 10 minutes)
- Git integration with auto-commit and optional auto-push
- HTTP health check endpoints (`/health`, `/metrics`) for monitoring
- Process management with PID files and graceful shutdown
- Exponential backoff on errors with configurable thresholds

> **📚 See [WATCH_MODE.md](WATCH_MODE.md) for:**
> - Complete watch mode documentation
> - Systemd and Docker deployment examples
> - Git integration setup
> - Troubleshooting watch mode issues

## Configuration

Create `.chronicon.toml` in your home directory or project root:

```toml
[general]
output_dir = "./archives"
default_formats = ["html", "markdown", "github"]

# Optional: Use PostgreSQL instead of SQLite
# Requires: pip install chronicon[postgres]
# database_url = "postgresql://user:password@localhost/chronicon"

[fetching]
rate_limit_seconds = 0.5
max_workers = 8
retry_max = 5
timeout = 15

[export]
include_users = false
text_only = false

[export.html]
theme_adaptation = "simplified"
enable_search = true
responsive = true

[[sites]]
url = "https://meta.discourse.org"
nickname = "meta"
categories = [1, 2, 7]
rate_limit_seconds = 1.0
```

**PostgreSQL Configuration**: To use PostgreSQL instead of SQLite, install with `pip install chronicon[postgres]` and set `database_url` in the config. PostgreSQL is recommended for multi-million post archives or when multiple processes need concurrent access.

> **📚 Learn more:**
> - [MIGRATION.md](MIGRATION.md#sqlite-to-postgresql-migration) - How to migrate from SQLite to PostgreSQL
> - [PERFORMANCE.md](PERFORMANCE.md#database-optimization) - Database performance comparison
> - [ARCHITECTURE.md](ARCHITECTURE.md#storage-backend-options) - Technical details on storage backends

See `.chronicon.toml.example` for full configuration options.

### Environment Variables

Chronicon supports the following environment variables for configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string (enables PostgreSQL mode) | `postgresql://user:pass@localhost/chronicon` |
| `CHRONICON_OUTPUT_DIR` | Override default output directory | `/archives` |
| `EXPORT_FORMATS` | Comma-separated export formats for watch mode | `html,markdown` |
| `GIT_TOKEN` | Git personal access token for HTTPS push | `ghp_xxxx` |
| `GIT_USERNAME` | Git username for HTTPS authentication | `myuser` |
| `GIT_REMOTE_URL` | Git remote URL for push operations | `https://github.com/user/repo.git` |

### PostgreSQL Support

For large-scale deployments (multi-million posts) or when multiple processes need concurrent database access, use PostgreSQL instead of SQLite:

```bash
# Install with PostgreSQL support
pip install chronicon[postgres]

# Archive using PostgreSQL
DATABASE_URL="postgresql://user:pass@localhost/chronicon" \
  chronicon archive --urls https://meta.discourse.org

# Watch mode with PostgreSQL
DATABASE_URL="postgresql://user:pass@localhost/chronicon" \
  chronicon watch --output-dir ./archives
```

### Docker Deployment

Chronicon includes production-ready Docker configurations in `examples/docker/`:

```bash
cd examples/docker

# SQLite-based deployment (simple)
docker compose up -d

# PostgreSQL-based deployment (recommended for production)
cp .env.postgres.example .env
# Edit .env with your POSTGRES_PASSWORD

# Start PostgreSQL first
docker compose -f docker-compose.postgres.yml up -d postgres

# Run initial archive (all categories)
docker compose -f docker-compose.postgres.yml run --rm api \
  archive --urls https://example.com --output-dir /archives

# Or archive specific categories only
docker compose -f docker-compose.postgres.yml run --rm api \
  archive --urls https://meta.discourse.org \
  --categories 7 \
  --output-dir /archives \
  --formats html

# Start full stack (API + Watch + Nginx)
docker compose -f docker-compose.postgres.yml up -d
```

The PostgreSQL stack includes:
- **PostgreSQL 17**: Database backend with full-text search (tsvector)
- **API Server**: FastAPI REST API with OpenAPI spec
- **Watch Daemon**: Continuous monitoring with git integration
- **Nginx**: Reverse proxy serving static archives and API

Access points after deployment:
- `http://localhost/` - Static HTML archive
- `http://localhost/api/docs` - API documentation (Swagger UI)
- `http://localhost/openapi.json` - OpenAPI spec for MCP clients
- `http://localhost:8080/health` - Watch daemon health check

## Output Structure

### HTML Export

```
output_html/
├── index.html                 # Homepage with category list
├── c/
│   └── category-slug/
│       └── index.html         # Category page with topics
├── t/
│   └── topic-slug/
│       └── 123/
│           ├── index.html     # Topic page (first page)
│           └── page-2.html    # Paginated pages
├── u/
│   └── username/
│       └── index.html         # User profile page
├── assets/
│   ├── css/                   # Default theme CSS
│   ├── js/                    # Search functionality
│   ├── images/                # Downloaded post images
│   ├── emoji/                 # Shared emoji assets
│   └── site/                  # Favicon, logo, banner
└── search_index.json          # Client-side search index
```

### Markdown Export

```
output_markdown/
├── topics/
│   └── YYYY-MM-Month/
│       └── YYYY-MM-DD-topic-slug-123.md
└── .metadata.json
```

### GitHub Markdown Export

```
output_github/
├── README.md                  # TOC with all topics
├── topics/
│   └── YYYY-MM-Month/
│       └── topic-slug-123.md
└── assets/
    └── images/
        └── 123/               # Images organized by topic ID
```

## Troubleshooting

> **📚 See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive troubleshooting guide**

### Rate Limiting

If you encounter rate limiting errors (HTTP 429):

```bash
# Increase rate limit delay
chronicon archive \
  --urls https://example.com \
  --rate-limit 1.0  # Wait 1 second between requests
```

### Large Forums

For forums with 100k+ posts:

```bash
# Use category filtering
chronicon archive \
  --urls https://example.com \
  --categories 1,2,3  # Archive specific categories

# Use date filtering
chronicon archive \
  --urls https://example.com \
  --since 2023-01-01  # Archive recent content only
```

### Network Errors

The archiver includes automatic retry logic with exponential backoff. If you still encounter issues:

- Check your internet connection
- Verify the forum URL is correct
- Try increasing the timeout: edit `.chronicon.toml` and set `timeout = 30`
- Some forums may block automated access - check the forum's terms of service

### Database Corruption

If you suspect database corruption:

```bash
# Validate the archive
chronicon validate --output-dir ./archives

# If validation fails, you may need to re-archive
# Backup your database first!
cp archives/archive.db archives/archive.db.backup

# Then re-run archive command
```

## Frequently Asked Questions

> **📚 See [FAQ.md](FAQ.md) for complete FAQ with 50+ questions**

**Q: How much disk space do I need?**
A: Depends on forum size. Budget ~2-3x the size of all images. A typical forum with 10k topics and 100k posts might use 1-5GB with images, or 50-200MB text-only.

**Q: How long does archiving take?**
A: Depends on forum size and rate limiting. With default settings (0.5s between requests):
- Small forum (1k topics): 10-30 minutes
- Medium forum (10k topics): 2-5 hours
- Large forum (100k+ topics): 10+ hours

Use `--categories` to archive incrementally.

**Q: Can I archive private/authenticated forums?**
A: Currently, the tool only supports public forums. Authentication support is planned for a future release.

**Q: What about incremental backups?**
A: Use the `update` command to incrementally fetch new content. It only downloads posts modified since the last archive.

**Q: Can I customize the HTML theme?**
A: Yes! The HTML export uses a clean default theme that you can modify. Edit the CSS files in your archive's `assets/css/` directory to customize colors, fonts, and layout.

**Q: How do I search the archived content?**  
A: HTML exports support two search backends:
- **FTS (default)**: Server-rendered full-text search using SQLite FTS5 or PostgreSQL tsvector. Requires running the API server.
- **Static**: Client-side JavaScript search that works completely offline. Use `--search-backend static` during export.

For markdown exports, use your editor's search or `grep`.

## Screenshots

### HTML Export

Static HTML archive with clean, professional design and full offline functionality:

![HTML Export - Homepage](docs/screenshots/01-html-index.png)
*Homepage with topic listing and navigation*

![HTML Export - Topic Page](docs/screenshots/02-html-topic.png)
*Individual topic with rich formatting and images*

![HTML Export - Search](docs/screenshots/04-html-search.png)
*Client-side search functionality (works offline)*

![HTML Export - Mobile](docs/screenshots/06-html-mobile.png)
*Mobile-responsive design*

### Markdown Exports

Clean, organized markdown files perfect for offline reading and GitHub hosting:

```
markdown/
├── index.md                    # Main index page
├── latest/                     # Latest topics
│   └── index.md
├── top/                        # Top topics by replies/views
│   ├── replies/
│   └── views/
├── topics/                     # Topics organized by date
│   ├── 2026-01-January/
│   │   ├── 2026-01-21-activation-email-sent-*.md
│   │   └── 2026-01-23-adding-a-static-web-page-*.md
│   └── ...
└── categories/                 # Category indexes
```

See the [live demo archive](https://online-archives.github.io/chronicon-archive-example/) for a complete sample archive from meta.discourse.org, or browse the [source repository](https://github.com/online-archives/chronicon-archive-example).

## Development

> **📚 For comprehensive development guide, see [DEVELOPMENT.md](DEVELOPMENT.md)**
>
> **📚 For API documentation, see [API_REFERENCE.md](API_REFERENCE.md)**

```bash
# Clone repository
git clone https://github.com/19-84/chronicon.git
cd chronicon

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_cli.py

# Run with coverage
uv run pytest --cov=chronicon --cov-report=html
```

### Project Structure

> **📚 See also:**
> - [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
> - [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflow and guidelines
> - [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
> - [API_REFERENCE.md](API_REFERENCE.md) - Programmatic usage

### Running Tests

The project has 520+ passing tests with 80% coverage:
- CLI command tests (archive, update, validate, migrate, watch)
- Fetcher integration tests
- Concurrent processing tests
- Model serialization and edge case tests
- Export format tests (HTML, Markdown, GitHub)
- Watch mode and git integration tests
- Health monitoring tests
- Real-world integration tests

## Status

**Current Version**: v1.0.0 Production/Stable

All features complete and battle-tested:
- ✅ Foundation (database, models, API client)
- ✅ Asset & theme management
- ✅ Static HTML export with search
- ✅ Markdown exporters (plain & GitHub)
- ✅ Incremental updates
- ✅ CLI interface with rich output
- ✅ Continuous monitoring (watch mode)
- ✅ PostgreSQL support
- ✅ Comprehensive testing (350+ tests, 80% coverage)

## License

This software is released into the public domain under The Unlicense. See the [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📧 Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/19-84/chronicon/issues)
- **GitHub Discussions**: [Ask questions or share ideas](https://github.com/19-84/chronicon/discussions)
- **Security Issues**: [Report via GitHub Security Advisories](https://github.com/19-84/chronicon/security/advisories/new)

## 💰 Support the Project

**Chronicon was built by one person** as a labor of love to preserve internet history before it disappears forever.

This isn't backed by a company or institution—just an individual committed to keeping valuable discussions accessible. Your support helps:

- Continue development and bug fixes
- Maintain documentation and support
- Cover infrastructure costs (servers, storage, bandwidth)
- Preserve more data sources and platforms

Every donation, no matter the size, helps keep this preservation effort alive.

### Bitcoin (BTC)

```
bc1q8wpdldnfqt3n9jh2n9qqmhg9awx20hxtz6qdl7
```

<p align="center">
  <img src="qr-codes/btc.jpg" width="400" alt="Bitcoin QR Code">
  <br>
  <em>Scan to donate Bitcoin</em>
</p>

### Monero (XMR)

```
42zJZJCqxyW8xhhWngXHjhYftaTXhPdXd9iJ2cMp9kiGGhKPmtHV746EknriN4TNqYR2e8hoaDwrMLfv7h1wXzizMzhkeQi
```

<p align="center">
  <img src="qr-codes/xmr.jpg" width="400" alt="Monero QR Code">
  <br>
  <em>Scan to donate Monero</em>
</p>

**Thank you for supporting internet archival efforts!** Every contribution helps maintain and improve this project.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=19-84/chronicon&type=Date)](https://star-history.com/#19-84/chronicon&Date)

---

This software is provided "as is" under the Unlicense. See [LICENSE](LICENSE) for details. Users are responsible for compliance with applicable laws and terms of service when processing data.
