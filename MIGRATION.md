# Migration & Upgrade Guide

**[Documentation Index](DOCUMENTATION.md)** > Migration

**Related:** [Changelog](CHANGELOG.md) | [Troubleshooting](TROUBLESHOOTING.md#database-issues) | [Examples](EXAMPLES.md)

---

Guide for upgrading Chronicon, migrating data, and handling breaking changes.

## Table of Contents

- [Version Compatibility](#version-compatibility)
- [Upgrading Chronicon](#upgrading-chronicon)
- [Database Migrations](#database-migrations)
- [Format Migrations](#format-migrations)
- [Backup & Restore](#backup--restore)

## Version Compatibility

### Current Version: 1.0.0

| Version | Python | SQLite | PostgreSQL | Breaking Changes |
|---------|--------|--------|------------|------------------|
| 1.0.x | 3.11+ | 3.x | 12+ | None |
| 0.x | 3.11+ | 3.x | - | See upgrade notes |

### Compatibility Matrix

**Database Format:**
- v1.0.x databases are forward and backward compatible within minor versions
- Schema migrations run automatically on first use
- PostgreSQL support added in v1.0.0

**Export Format:**
- HTML exports are stable
- Markdown format is stable
- GitHub format is stable

## Upgrading Chronicon

### From v0.x to v1.0.0

**Breaking Changes:** None for end users

**New Features:**
- PostgreSQL support
- Watch mode
- Incremental updates
- Performance improvements

**Upgrade Steps:**

1. **Backup your archives:**
   ```bash
   cp -r archives/ archives.backup/
   ```

2. **Upgrade package:**
   ```bash
   # Using uv
   uv tool upgrade chronicon
   
   # Using pip
   pip install --upgrade chronicon
   ```

3. **Verify version:**
   ```bash
   chronicon --version
   # Should show: chronicon 1.0.0
   ```

4. **Run validation:**
   ```bash
   chronicon validate --output-dir archives/
   ```

5. **Test with update:**
   ```bash
   chronicon update --output-dir archives/
   ```

**Database Migration:** Automatic on first use

### Minor Version Upgrades (1.0.x → 1.0.y)

Minor version upgrades within v1.0.x are seamless:

```bash
uv tool upgrade chronicon
# or
pip install --upgrade chronicon
```

No manual migration required.

## Database Migrations

### Automatic Migrations

Chronicon automatically migrates databases on first use:

```python
# Migrations run automatically when opening database
from chronicon.storage import ArchiveDatabase

db = ArchiveDatabase(db_path=Path("./archive.db"))
# Migrations applied here if needed
```

**Migration History:**
- v0.8 → v0.9: Added `local_avatar_path` to users table
- v0.9 → v1.0: Added site metadata fields (logo_url, banner_image_url, etc.)

### Manual Migration Check

```bash
# Validate and trigger migrations
chronicon validate --output-dir archives/

# Check migration status
sqlite3 archives/archive.db "SELECT name FROM sqlite_master WHERE type='table';"
```

### SQLite to PostgreSQL Migration

**When to Migrate:**
- Archive > 1 million posts
- Multiple concurrent users
- Need advanced features (full-text search, replication)

**Migration Steps:**

1. **Install PostgreSQL support:**
   ```bash
   pip install chronicon[postgres]
   ```

2. **Set up PostgreSQL database:**
   ```sql
   CREATE DATABASE chronicon;
   CREATE USER chronicon_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE chronicon TO chronicon_user;
   ```

3. **Export from SQLite:**
   ```bash
   sqlite3 archives/archive.db .dump > archive.sql
   ```

4. **Convert SQL (if needed):**
   ```bash
   # SQLite uses some different syntax
   # May need manual edits for:
   # - AUTOINCREMENT → SERIAL
   # - Column constraints
   # - Index definitions
   ```

5. **Import to PostgreSQL:**
   ```bash
   psql -U chronicon_user -d chronicon < archive.sql
   ```

6. **Update configuration:**
   ```toml
   [general]
   database_url = "postgresql://chronicon_user:your_password@localhost/chronicon"
   ```

7. **Verify migration:**
   ```bash
   chronicon validate --output-dir archives/
   ```

**Alternative: Fresh Archive with PostgreSQL**

Simpler approach for large archives:

```bash
# Configure PostgreSQL first
# Then create new archive
chronicon archive \
  --urls https://meta.discourse.org \
  --config .chronicon.toml  # With PostgreSQL config
```

> **💡 Tip:** For very large forums, starting fresh with PostgreSQL may be faster than migrating.
>
> **📚 See also:**
> - [PERFORMANCE.md](PERFORMANCE.md#postgresql-for-large-archives) - Performance benefits
> - [TROUBLESHOOTING.md](TROUBLESHOOTING.md#postgresql-dependencies-missing) - PostgreSQL setup issues
> - [ARCHITECTURE.md](ARCHITECTURE.md#when-to-use-postgresql) - Technical considerations

## Format Migrations

### JSON to SQLite (Legacy)

For archives created before v0.8:

```bash
# Migrate from old JSON format
chronicon migrate \
  --from ./legacy_json_archive \
  --output-dir ./new_archive

# Then export to desired formats
chronicon update --output-dir ./new_archive --formats html,markdown
```

**What Gets Migrated:**
- Topics
- Posts
- Categories
- Users
- Site metadata

**Not Migrated:**
- Old export formats (HTML/Markdown - regenerated)
- Images (need re-download)

### Re-exporting After Upgrade

After upgrading, you may want to regenerate exports to use new features:

```bash
# Regenerate all exports
chronicon update --output-dir archives/ --formats html,markdown,github

# Or just HTML with new features
chronicon update --output-dir archives/ --formats html
```

## Backup & Restore

### Backup Strategies

**1. Full Backup (Safest):**
```bash
# Backup everything
tar czf archive-backup-$(date +%Y%m%d).tar.gz archives/

# Store offsite
rclone copy archive-backup-*.tar.gz remote:backups/
```

**2. Database-Only Backup (Faster):**
```bash
# Just database (exports can be regenerated)
cp archives/archive.db archives/backups/archive-$(date +%Y%m%d).db
```

**3. Incremental Backup:**
```bash
# Using rsync
rsync -av --delete archives/ backup-server:/backups/archives/
```

**4. Database Dump (Text Format):**
```bash
# SQLite
sqlite3 archives/archive.db .dump > archive-$(date +%Y%m%d).sql

# PostgreSQL
pg_dump chronicon > archive-$(date +%Y%m%d).sql
```

### Automated Backup Script

```bash
#!/bin/bash
# backup-chronicon.sh

BACKUP_DIR="$HOME/chronicon-backups"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Backup database
cp archives/archive.db "$BACKUP_DIR/archive-$DATE.db"

# Compress old backups
find "$BACKUP_DIR" -name "*.db" -mtime +1 -exec gzip {} \;

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "*.db.gz" -mtime +30 -delete

echo "Backup complete: archive-$DATE.db"
```

**Schedule with cron:**
```bash
# Daily backup at 3 AM
0 3 * * * ~/backup-chronicon.sh
```

### Restore from Backup

**1. Full Restore:**
```bash
# Stop any running chronicon processes
chronicon watch stop --output-dir archives/

# Restore from backup
tar xzf archive-backup-20250115.tar.gz
mv archives/ archives.old/
mv archive-backup-20250115/ archives/

# Verify
chronicon validate --output-dir archives/
```

**2. Database-Only Restore:**
```bash
# Stop processes
chronicon watch stop --output-dir archives/

# Restore database
cp archives/backups/archive-20250115.db archives/archive.db

# Regenerate exports
chronicon update --output-dir archives/ --formats html,markdown,github
```

**3. Point-in-Time Recovery (PostgreSQL):**
```bash
# Restore from pg_dump
psql -U chronicon_user -d chronicon < archive-20250115.sql

# Verify
chronicon validate --output-dir archives/
```

### Disaster Recovery

**Complete data loss:**

1. **Restore database from backup**
2. **Regenerate exports:**
   ```bash
   chronicon update --output-dir archives/ --formats html,markdown,github
   ```
3. **Re-download images (if not backed up):**
   ```bash
   # Images are stored with original URLs in database
   # Export process will re-download
   ```

**Partial corruption:**

1. **Identify corrupted topics:**
   ```bash
   chronicon validate --output-dir archives/
   ```

2. **Re-fetch specific topics:**
   ```bash
   # Use API to re-fetch corrupted topics
   # See API_REFERENCE.md for programmatic approach
   ```

## Version-Specific Notes

### v1.0.0 (Current)

**Release Date:** 2025-11-11

**Upgrade from v0.x:**
- Automatic database migrations
- New watch mode available
- PostgreSQL support available
- No breaking changes

**New Features:**
- Continuous monitoring (watch mode)
- PostgreSQL backend support
- Incremental export improvements
- 350 comprehensive tests

**Known Issues:** None

### Future Versions

**v1.1.0 (Planned):**
- Enhanced search capabilities
- Multi-language support
- Improved theme customization

**v2.0.0 (Future):**
- May include breaking changes
- Will provide migration guide
- Backward compatibility tools

## Migration Best Practices

### Before Migration

1. **Backup everything**
2. **Test in staging environment** 
3. **Read release notes**
4. **Check compatibility matrix**
5. **Plan downtime** (if needed)

### During Migration

1. **Stop all Chronicon processes:**
   ```bash
   chronicon watch stop --output-dir archives/
   ps aux | grep chronicon  # Verify none running
   ```

2. **Run migration:**
   ```bash
   chronicon migrate ... # or upgrade
   ```

3. **Monitor for errors:**
   ```bash
   tail -f chronicon.log
   ```

4. **Verify completion:**
   ```bash
   chronicon validate --output-dir archives/
   ```

### After Migration

1. **Test exports:**
   ```bash
   chronicon update --output-dir archives/ --formats html
   ```

2. **Check HTML output:**
   - Open index.html
   - Test search functionality
   - Browse topics
   - Check images load

3. **Verify data integrity:**
   ```bash
   # Check record counts
   sqlite3 archive.db "SELECT COUNT(*) FROM topics;"
   sqlite3 archive.db "SELECT COUNT(*) FROM posts;"
   ```

4. **Resume operations:**
   ```bash
   chronicon watch --output-dir archives/ --daemon
   ```

### Rollback Plan

If migration fails:

```bash
# 1. Stop new version
chronicon watch stop --output-dir archives/

# 2. Restore from backup
cp archives/backups/archive-YYYYMMDD.db archives/archive.db

# 3. Downgrade chronicon
pip install chronicon==0.9.0  # Previous version

# 4. Verify
chronicon --version
chronicon validate --output-dir archives/

# 5. Resume
chronicon watch --output-dir archives/ --daemon
```

## Getting Help

### Migration Support

**Before migrating:**
- Read this guide thoroughly
- Check [CHANGELOG.md](CHANGELOG.md) for breaking changes
- Test in non-production environment

**During migration:**
- Save all error messages
- Check logs: `tail -f chronicon.log`
- Don't force if errors occur

**After migration:**
- Verify with `chronicon validate`
- Test all functionality
- Monitor for 24-48 hours

**If issues arise:**
- GitHub Issues: https://github.com/19-84/chronicon/issues
- Include:
  - Chronicon version (old and new)
  - Python version
  - Database size
  - Error messages
  - Migration steps taken

## See Also

**Upgrade Related:**
- [CHANGELOG.md](CHANGELOG.md) - Version history and breaking changes
- [FAQ.md](FAQ.md#how-do-i-upgrade-chronicon) - Upgrade FAQs
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md#database-issues) - Migration troubleshooting

**Technical Details:**
- [API_REFERENCE.md](API_REFERENCE.md) - API changes and compatibility
- [ARCHITECTURE.md](ARCHITECTURE.md) - Database architecture
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development environment migration

**Return to:** [Documentation Index](DOCUMENTATION.md)
