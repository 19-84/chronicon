# Changelog

**[Documentation Index](DOCUMENTATION.md)** > Changelog

**See Also:** [Migration Guide](MIGRATION.md) | [FAQ](FAQ.md#how-do-i-upgrade-chronicon)

---

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-09-29

### Fixed

- Source distributions build again: stray pytest temp output with absolute symlinks is no longer tracked in the repository
- Wheels now include the HTML templates and static assets, so HTML export and the search pages work after `pip install`; they moved into `src/chronicon/`, and the build config uses the `[tool.hatch]` table hatch actually reads
- Image pipeline: downloaded media is copied into the HTML asset tree, relative and CDN-mismatched assets resolve correctly, and Markdown exporters match assets by exact filename
- Lightbox originals are fetched and stored under `assets/` in watch mode; lightbox click-through opens the original without JavaScript
- Concurrent asset filename assignment is now atomic
- Off-domain upload fetching restored with an anchored domain check, closing an SSRF path through lightbox and asset URLs
- Markdown image and anchor URLs are rewritten to local assets; sitemap uses correct extensions
- Search index links to the correct page for paginated posts
- Template URL patterns and SEO tags
- Docker builds copy `README.md` so package metadata installs correctly
- `get_assets_for_topic` added to the abstract database base class
- MCP integration test called the decorator instead of the tool handlers

### Security

- Resolved Dependabot advisories in locked dependencies, including anyio 4.14.2+ (TLS host name spoofing), PyJWT 2.14.0+ (HMAC/asymmetric key confusion, JWKS redirect and fetch amplification), cryptography, starlette, soupsieve, mcp, and pydantic-settings

### Changed

- Refreshed locked dependencies to latest compatible minor and patch releases
- `mcp` capped at `<2.0.0`; the 2.x SDK removed the low-level decorator API the MCP server uses
- Dev dependencies now include `pytest-asyncio` (async MCP tests previously skipped) and `httpx2` (Starlette's test client no longer supports `httpx`)
- Dependabot tracks Python dependencies through the `uv` ecosystem so `uv.lock` updates are grouped

## [1.0.0] - 2025-11-11

### Added

**Core Features:**
- Multi-format export: Static HTML, Plain Markdown, and GitHub-flavored Markdown
- SQLite-based efficient storage for 100k+ posts
- PostgreSQL support for large-scale deployments
- Incremental update system (only fetch new/modified content)
- Concurrent processing with ThreadPoolExecutor for fast archiving
- Comprehensive CLI with `archive`, `update`, `validate`, and `migrate` commands
- Configuration file support (.chronicon.toml)
- Rate limiting and exponential backoff for API calls
- Asset downloading with deduplication (images, avatars, emoji)
- **Category Filtering**: Archive specific categories with `--categories` flag. Filter is stored in database and respected by watch mode and backfill commands.
- **Per-Site Configuration**: Configure category filters per site in `.chronicon.toml`

**HTML Export:**
- Clean, professional default theme for all archives
- Category pages with pagination
- Topic pages with full post history
- User profile pages with post listings
- **FTS Search Backend**: Server-rendered full-text search using SQLite FTS5 or PostgreSQL tsvector
- Static client-side search as offline alternative
- SEO-friendly metadata and canonical URLs
- Breadcrumb navigation
- Responsive design for mobile/tablet/desktop

**Markdown Exports:**
- Plain Markdown: Clean, readable files organized by date
- GitHub Markdown: GitHub Pages ready with embedded images and README TOC
- Proper formatting preservation from HTML
- User profile pages in Markdown format
- Relative path navigation between files

**Database:**
- Schema versioning and migrations
- Indexed queries for fast lookups
- Export history tracking
- Asset registry for downloaded files
- Site metadata storage

**Watch Mode:**
- Continuous monitoring daemon for automatic archive updates
- Git integration with auto-commit and auto-push
- HTTP health endpoints for monitoring
- Process management with PID files and graceful shutdown

**Testing:**
- 350 passing tests (100% pass rate)
- 80%+ code coverage
- Integration tests for all major workflows
- Fixture-based testing for reproducibility

### Changed
- HTML search defaults to FTS mode (server-rendered) instead of static (client-side)
- UpdateManager filters posts by category when category filter is active
- Archive command reads categories from config file if not provided via CLI

### Fixed
- Watch daemon prioritizes config file category filter over database value
- Docker command format in documentation

### Documentation
- Comprehensive README with usage examples
- ARCHITECTURE.md explaining design decisions
- WATCH_MODE.md for continuous monitoring
- CONTRIBUTING.md with development workflow
- API reference and troubleshooting guides
- Example configuration file

### License
- Unlicense

[Unreleased]: https://github.com/19-84/chronicon/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/19-84/chronicon/releases/tag/v1.0.0
