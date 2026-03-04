# Frequently Asked Questions (FAQ)

**[Documentation Index](DOCUMENTATION.md)** > FAQ

**Need More Help?** [Troubleshooting](TROUBLESHOOTING.md) | [Examples](EXAMPLES.md) | [API Reference](API_REFERENCE.md)

---

Common questions and answers about Chronicon.

## Table of Contents

- [General Questions](#general-questions)
- [Installation & Setup](#installation--setup)
- [Usage & Features](#usage--features)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

## General Questions

### What is Chronicon?

Chronicon is a multi-format Discourse forum archiving tool. It downloads and preserves forum content in three formats:
- **Static HTML** - Fully offline-viewable with search and navigation
- **Plain Markdown** - Clean, readable files for archival
- **GitHub Markdown** - Optimized for GitHub Pages hosting

### Why archive a Discourse forum?

Common reasons:
- **Backup:** Protect against data loss
- **Compliance:** Legal/regulatory requirements
- **Offline Access:** Read without internet
- **Migration:** Moving to different platform
- **Preservation:** Keep historical record
- **Analysis:** Research or analytics

### Is Chronicon free?

Yes! Chronicon is released into the public domain under The Unlicense. You can use it for any purpose, commercial or non-commercial, with no restrictions.

### What Discourse versions are supported?

Chronicon works with all modern Discourse versions (2.x and 3.x). It uses the public API, which has been stable for years.

### Can I archive private/authenticated forums?

Currently, Chronicon only supports public forums. Authentication support is being considered for future releases. You can use Discourse's built-in backup feature for private forums.

### How does Chronicon compare to Discourse's backup?

| Feature | Chronicon | Discourse Backup |
|---------|-----------|------------------|
| Format | HTML, Markdown | JSON, SQL dump |
| Browsable | ✅ Yes | ❌ No |
| Searchable | ✅ Yes (HTML) | ❌ No |
| Offline | ✅ Yes | Requires restoration |
| Incremental | ✅ Yes | ❌ No |
| Hosting | GitHub Pages, etc. | Requires Discourse |

**Use both:** Discourse backups for restoration, Chronicon for browsing/hosting.

## Installation & Setup

### How do I install Chronicon?

**Recommended (uv):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install chronicon
```

**Alternative (pip):**
```bash
pip install chronicon
```

**From source:**
```bash
git clone https://github.com/19-84/chronicon.git
cd chronicon
uv sync
```

### What are the system requirements?

**Minimum:**
- Python 3.11+
- 512 MB RAM
- 1 GB disk space (varies with forum size)

**Recommended:**
- Python 3.11+
- 2-4 GB RAM
- SSD storage
- Stable internet connection

### Do I need to install a database?

No! SQLite is built into Python. For large archives (1M+ posts), you can optionally use PostgreSQL:
```bash
pip install chronicon[postgres]
```

### How do I upgrade Chronicon?

```bash
# Using uv
uv tool upgrade chronicon

# Using pip
pip install --upgrade chronicon
```

## Usage & Features

### How do I create my first archive?

```bash
chronicon archive --urls https://meta.discourse.org
```

That's it! Archives are saved to `./archives/` by default.

### How long does archiving take?

Depends on forum size:
- **Small (1k topics):** 10-20 minutes
- **Medium (10k topics):** 1-3 hours
- **Large (50k+ topics):** 5-15 hours

See [PERFORMANCE.md](PERFORMANCE.md) for detailed benchmarks.

### How much disk space do I need?

Budget 2-3x the size of forum images:

| Forum Size | With Images | Text-Only |
|-----------|-------------|-----------|
| Small (1k topics) | 500 MB | 50 MB |
| Medium (10k topics) | 5 GB | 200 MB |
| Large (50k+ topics) | 25+ GB | 1+ GB |

### Can I archive just specific categories?

Yes! Find category IDs and specify them:
```bash
chronicon archive \
  --urls https://meta.discourse.org \
  --categories 1,2,7
```

### How do I update an existing archive?

```bash
chronicon update --output-dir ./archives
```

This only fetches new/modified content (much faster than re-archiving).

### Can I archive multiple forums?

Yes! Either run separate commands:
```bash
chronicon archive --urls https://meta.discourse.org --output-dir ./meta
chronicon archive --urls https://forum2.com --output-dir ./forum2
```

Or use programmatic API:
```python
# See API_REFERENCE.md and EXAMPLES.md
```

### What export formats are available?

Three formats:

1. **HTML** (`--formats html`)
   - Full-featured browsing
   - Client-side search
   - Mobile-friendly
   - Best for: Online viewing, GitHub Pages

2. **Markdown** (`--formats markdown`)
   - Clean, readable text
   - Organized by date
   - Best for: Archival, grep searching

3. **GitHub Markdown** (`--formats github`)
   - GitHub-flavored markdown
   - Embedded images
   - README with TOC
   - Best for: GitHub Pages, documentation

### Can I skip downloading images?

Yes! Use `--text-only`:
```bash
chronicon archive --urls https://meta.discourse.org --text-only
```

Benefits: 40-60% faster, 90% less disk space.

### How does the search feature work?

The HTML export includes:
- Search index generated at export time
- Client-side JavaScript search (no server needed)
- Works completely offline
- Searches topic titles and content

### Can I customize the HTML theme?

Yes! The HTML export uses clean default CSS that you can modify:
```bash
# Edit CSS files
nano archives/html/assets/css/theme.css
```

### What is sweep mode?

Sweep mode exhaustively fetches every topic ID:
```bash
chronicon archive \
  --urls https://meta.discourse.org \
  --sweep \
  --start-id 10000
```

Useful for recovering deleted/unlisted topics that don't appear in category listings.

## Performance

### How can I make archiving faster?

**Quick wins:**
1. Use `--text-only` (skip images)
2. Archive specific categories (`--categories`)
3. Increase workers (`--max-workers 16`)
4. Use faster storage (SSD)
5. Export fewer formats (`--formats html` only)

See [PERFORMANCE.md](PERFORMANCE.md) for comprehensive guide.

### Why is my archive slow?

Common bottlenecks:
1. **Network I/O** (60-70% of time) - Try faster internet
2. **Rate limiting** - Forum may be throttling you
3. **Image downloads** (20-30%) - Use `--text-only`
4. **Slow disk** - Use SSD instead of HDD

### My forum is huge. How do I handle it?

**Strategies:**
1. Archive by category (one at a time)
2. Use PostgreSQL instead of SQLite
3. Use text-only mode
4. Archive incrementally over time
5. Use dedicated server with good network

### Can I run multiple archives in parallel?

Yes, but:
- Each archive needs separate output directory
- Watch forum's rate limits
- Don't run multiple updates on same archive (database locking)

```bash
# OK: Different forums
chronicon archive --urls https://forum1.com --output-dir ./f1 &
chronicon archive --urls https://forum2.com --output-dir ./f2 &

# NOT OK: Same archive
chronicon update --output-dir ./archives &  # Will conflict
chronicon update --output-dir ./archives &  # Will conflict
```

## Troubleshooting

### I get "HTTP 429: Too Many Requests"

The forum is rate limiting you. Solutions:
```bash
# Slow down requests
chronicon archive --urls https://forum.com --rate-limit 2.0
```

Or configure in `.chronicon.toml`:
```toml
[fetching]
rate_limit_seconds = 2.0
```

### Database is locked error

Another process is using the database. Solutions:
1. Stop other Chronicon processes
2. Remove stale lock files:
   ```bash
   rm archives/archive.db-wal archives/archive.db-shm
   ```

### Images aren't downloading

Check:
1. Not in text-only mode
2. Disk space available
3. Network connectivity
4. Image URLs accessible
5. Check logs for errors

### Search doesn't work in HTML export

1. Verify `search_index.json` exists
2. Check JavaScript enabled in browser
3. Regenerate index:
   ```bash
   chronicon update --output-dir archives/ --formats html
   ```

### Archive is corrupted

1. **Validate:**
   ```bash
   chronicon validate --output-dir archives/
   ```

2. **Restore from backup** (if available)

3. **Last resort:** Re-archive
   ```bash
   mv archives/archive.db archives/archive.db.backup
   chronicon archive --urls https://forum.com
   ```

### Watch mode keeps stopping

Check logs for errors:
```bash
tail -100 archives/chronicon-watch.log
```

Common causes:
- Network issues
- Rate limiting
- Disk space full
- Permission problems

Increase error tolerance:
```toml
[continuous]
max_consecutive_errors = 10
```

## Advanced Topics

### Can I use Chronicon as a Python library?

Yes! See [API_REFERENCE.md](API_REFERENCE.md) for comprehensive API documentation.

Example:
```python
from chronicon.storage import ArchiveDatabase
from chronicon.exporters import HTMLStaticExporter

db = ArchiveDatabase(db_path=Path("./archive.db"))
exporter = HTMLStaticExporter(db, output_dir=Path("./html"))
exporter.export()
db.close()
```

> **📚 Learn more:**
> - [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation with 50+ examples
> - [EXAMPLES.md](EXAMPLES.md#advanced-use-cases) - Real-world code examples
> - [DEVELOPMENT.md](DEVELOPMENT.md) - Development environment setup

### How do I host archives on GitHub Pages?

1. Archive with GitHub format:
   ```bash
   chronicon archive --urls https://forum.com --formats github
   ```

2. Push to GitHub:
   ```bash
   cd archives/github/
   git init
   git add .
   git commit -m "Initial archive"
   git push origin main
   ```

3. Enable GitHub Pages (Settings → Pages → Source: main branch)

4. Access at: `https://username.github.io/repo-name/`

> **📚 Complete guides:**
> - [EXAMPLES.md](EXAMPLES.md#example-14-mirror-to-github-pages) - Full GitHub Pages setup
> - [WATCH_MODE.md](WATCH_MODE.md#git-integration) - Automated GitHub updates
> - [TROUBLESHOOTING.md](TROUBLESHOOTING.md#git-push-fails) - Git troubleshooting

### Can I automate archiving?

Yes! Several options:

**Cron (Linux/Mac):**
```bash
# Daily at 2 AM
0 2 * * * chronicon update --output-dir /path/to/archives
```

**Watch Mode:**
```bash
chronicon watch --output-dir ./archives --daemon
```

**Systemd Service:**
See [examples/systemd/](examples/systemd/) for complete setup.

**Docker:**
See [examples/docker/](examples/docker/) for containerized deployment.

### How do I migrate from SQLite to PostgreSQL?

See [MIGRATION.md](MIGRATION.md) for detailed guide.

Quick version:
1. Install PostgreSQL support: `pip install chronicon[postgres]`
2. Set up PostgreSQL database
3. Configure connection in `.chronicon.toml`
4. Export from SQLite, import to PostgreSQL
5. Verify with `chronicon validate`

### Can I filter archives by date?

Yes:
```bash
chronicon archive \
  --urls https://forum.com \
  --since 2024-01-01
```

Only archives posts created after specified date.

### How do I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete guide.

Quick start:
1. Fork repository
2. Clone and set up dev environment
3. Make changes and add tests
4. Submit pull request

### Where can I get help?

**Quick Reference:**
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed problem solving
- [EXAMPLES.md](EXAMPLES.md) - Step-by-step workflows
- [PERFORMANCE.md](PERFORMANCE.md) - Speed optimization

**Complete Documentation:**
- [README.md](README.md) - Installation and basic usage
- [API_REFERENCE.md](API_REFERENCE.md) - Programmatic usage
- [WATCH_MODE.md](WATCH_MODE.md) - Continuous monitoring
- [MIGRATION.md](MIGRATION.md) - Upgrading versions
- [DEVELOPMENT.md](DEVELOPMENT.md) - Contributing code

**Get Help:**
- GitHub Issues: https://github.com/19-84/chronicon/issues
- GitHub Discussions: https://github.com/19-84/chronicon/discussions
- Security: GitHub Security Advisories

**Return to:** [Documentation Index](DOCUMENTATION.md)

### Is Chronicon actively maintained?

Yes! Current status:
- **Version:** 1.0.0 (Production/Stable)
- **Tests:** 350 passing tests
- **Coverage:** 80%+
- **Status:** Actively maintained

### Can I use Chronicon commercially?

Yes! Chronicon is released under The Unlicense (public domain). You can:
- Use for commercial purposes
- Modify and distribute
- Use in closed-source products
- No attribution required (but appreciated!)

### What about GDPR/privacy concerns?

Chronicon archives publicly available data. Considerations:
- Only archives public content
- Includes usernames (public information)
- Does not access private messages
- Does not require authentication
- Respects forum's robots.txt

If hosting archives publicly:
- Consider privacy implications
- May need to honor deletion requests
- Check local regulations
- Consider anonymizing usernames

### How can I support the project?

Ways to help:
- ⭐ Star the repository
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Contribute code
- 💬 Answer questions in discussions
- 📢 Share with others

## Still Have Questions?

**Search first:**
- This FAQ
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Existing GitHub issues

**Then ask:**
- Open a [GitHub Discussion](https://github.com/19-84/chronicon/discussions)
- Create an [issue](https://github.com/19-84/chronicon/issues) for bugs

We're here to help!
