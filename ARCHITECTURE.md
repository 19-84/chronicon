# Architecture Documentation

**[Documentation Index](DOCUMENTATION.md)** > Architecture

**For Developers:** [Development Guide](DEVELOPMENT.md) | [Contributing](CONTRIBUTING.md) | [API Reference](API_REFERENCE.md)

---

## Overview

Chronicon is a multi-format forum archiving tool built with Python 3.11+.

## Design Principles

1. **Performance First** - SQLite for fast queries at scale
2. **Incremental Updates** - Smart fetching only of new/modified content
3. **Modular Architecture** - Separation of concerns: fetching, storage, export
4. **User Control** - Extensive CLI flags for customization
5. **Fail Gracefully** - Exponential backoff, retry logic, error handling

## Architecture Layers

### Data Models (`models/`)
- Dataclasses for Post, Topic, User, Category, SiteConfig
- Conversion methods between API JSON and internal representation

### Storage Layer (`storage/`)
- Database abstraction layer (`database_base.py`)
- SQLite implementation (default, zero dependencies)
- PostgreSQL implementation (optional, `chronicon[postgres]`)
- Schema management for both backends
- CRUD operations for all entities
- JSON migration utilities for legacy archives

### Fetchers (`fetchers/`)
- HTTP API client with rate limiting and retry logic
- Specialized fetchers for posts, topics, users, categories
- Asset downloader for images and avatars

### Processors (`processors/`)
- HTML content processing
- URL rewriting for offline viewing
- Content sanitization and transformation

### Exporters (`exporters/`)
- Base exporter class
- HTML static site generator
- Plain markdown exporter
- GitHub markdown exporter

### Utilities (`utils/`)
- Logging with rich formatting
- Concurrent processing helpers
- Search index generation
- Update manager for incremental updates

### Watch Mode (`watch/`)
- Continuous monitoring daemon
- Git integration (auto-commit, auto-push)
- Status tracking and history
- HTTP health check endpoints

## Data Flow

1. **Fetching**: API Client → Database
2. **Processing**: Database → Processors → Database
3. **Exporting**: Database → Exporters → Files

## Storage Backend Options

### Why SQLite (Default)?

- **Zero Dependencies**: Built into Python stdlib
- **Performance**: Indexed queries, handles 100k+ posts efficiently
- **Portability**: Single file, easy to backup and move
- **Relationships**: Native JOINs for post/topic/user relationships
- **Incremental Updates**: O(1) duplicate detection
- **FTS Support**: Full-text search indexing capability
- **Simplicity**: No server setup required

### When to Use PostgreSQL?

- **Scale**: Multi-million post archives
- **Concurrent Access**: Multiple processes/users need simultaneous access
- **Server Deployments**: Centralized archive management across teams
- **Advanced Features**: Complex queries, specialized indexes, replication
- **Integration**: Existing PostgreSQL infrastructure

### Migration Between Backends

The abstract `ArchiveDatabaseBase` class ensures both backends implement the same interface, making migration straightforward. Both backends support the same CRUD operations and data integrity guarantees.

## Extension Points

- Add new exporters by subclassing `BaseExporter`
- Add new fetchers for different API endpoints
- Customize templates for HTML export
- Add processors for content transformation
- Extend watch mode with custom monitoring logic

## Continuous Monitoring (Watch Mode)

Watch mode provides automated, continuous archiving with the following architecture:

### Daemon Management
- Long-running process with PID file management
- Graceful shutdown on SIGTERM/SIGINT
- Configurable polling intervals (default: 10 minutes)
- Exponential backoff on consecutive errors

### Update Cycle
1. **Poll**: Check for new/modified posts since last check
2. **Fetch**: Download new content via API
3. **Process**: Rewrite URLs, download assets
4. **Export**: Regenerate affected topic pages
5. **Git**: Optional auto-commit and push
6. **Status**: Update cycle history and metrics

### Git Integration
- Automatic commits after each update
- Template-based commit messages with variables
- Optional auto-push to remote repositories
- Safety checks for working tree conflicts

### Health Monitoring
- HTTP server on configurable port (default: 8080)
- `/health` endpoint: Returns 200 if healthy, 503 if not
- `/metrics` endpoint: Detailed statistics and cycle history
- Integration with Docker healthchecks and Kubernetes probes

### Status Tracking
- JSON status file with daemon state
- Cycle history (last 50 cycles)
- Error tracking and consecutive error count
- Uptime and success rate metrics

See [WATCH_MODE.md](WATCH_MODE.md) for deployment guides (systemd, Docker, Kubernetes).

---

**Related Documentation:**
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflow and project structure
- [API_REFERENCE.md](API_REFERENCE.md) - Detailed API documentation
- [PERFORMANCE.md](PERFORMANCE.md) - Performance characteristics
- [EXAMPLES.md](EXAMPLES.md) - Architectural patterns in practice

**Return to:** [Documentation Index](DOCUMENTATION.md)
