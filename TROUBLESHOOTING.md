# Troubleshooting Guide

**[Documentation Index](DOCUMENTATION.md)** > Troubleshooting

**Quick Links:** [Error Messages](#error-messages-reference) | [FAQ](FAQ.md) | [Performance Issues](PERFORMANCE.md) | [Watch Mode Issues](WATCH_MODE.md#troubleshooting)

---

Comprehensive troubleshooting guide for Chronicon. This document consolidates common issues, error messages, and solutions.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Database Issues](#database-issues)
- [Fetching & API Issues](#fetching--api-issues)
- [Export Issues](#export-issues)
- [Watch Mode Issues](#watch-mode-issues)
- [Performance Issues](#performance-issues)
- [Docker & Deployment Issues](#docker--deployment-issues)
- [Error Messages Reference](#error-messages-reference)

## Installation Issues

### Issue: uv not found

**Symptoms:**
```bash
$ chronicon archive --urls https://meta.discourse.org
bash: chronicon: command not found
```

**Causes:**
- Chronicon not installed
- Installed in wrong Python environment
- PATH not configured

**Solutions:**

1. **Install with uv:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv tool install chronicon
   ```

2. **Verify installation:**
   ```bash
   which chronicon
   chronicon --version
   ```

3. **Check PATH:**
   ```bash
   echo $PATH
   # Should include ~/.local/bin or uv tool bin directory
   ```

4. **Alternative: Use pip:**
   ```bash
   pip install chronicon
   ```

### Issue: Python version incompatible

**Symptoms:**
```
ERROR: Package 'chronicon' requires Python >=3.11
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.11 or later
# On Ubuntu/Debian:
sudo apt install python3.11

# On macOS with Homebrew:
brew install python@3.11

# On Windows: Download from python.org
```

### Issue: PostgreSQL dependencies missing

**Symptoms:**
```
ImportError: No module named 'psycopg'
```

**Cause:** Trying to use PostgreSQL without optional dependencies

**Solution:**
```bash
# Install with PostgreSQL support
pip install chronicon[postgres]
# or
uv tool install chronicon[postgres]
```

## Database Issues

### Issue: Database is locked

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Causes:**
- Another Chronicon instance is running
- Stale lock file
- System crash left database locked

**Solutions:**

1. **Check for running processes:**
   ```bash
   ps aux | grep chronicon
   # Kill if found:
   kill <PID>
   ```

2. **Remove WAL files (SQLite only):**
   ```bash
   cd archives/
   rm -f archive.db-shm archive.db-wal
   ```

3. **Use PostgreSQL for concurrent access:**
   ```toml
   [general]
   database_url = "postgresql://user:pass@localhost/chronicon"
   ```

### Issue: Database corruption

**Symptoms:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions:**

1. **Check database integrity:**
   ```bash
   sqlite3 archives/archive.db "PRAGMA integrity_check;"
   ```

2. **Attempt repair:**
   ```bash
   # Backup first!
   cp archives/archive.db archives/archive.db.backup
   
   # Try to repair
   sqlite3 archives/archive.db ".recover" | sqlite3 archives/archive_recovered.db
   ```

3. **Restore from backup:**
   ```bash
   cp archives/archive.db.backup archives/archive.db
   ```

4. **Last resort - re-archive:**
   ```bash
   # Move corrupted database
   mv archives/archive.db archives/archive.db.corrupted
   
   # Start fresh archive
   chronicon archive --urls https://your-forum.com
   ```

### Issue: Missing columns error

**Symptoms:**
```
sqlite3.OperationalError: table site_metadata has no column named logo_url
```

**Cause:** Database created with older version of Chronicon

**Solution:** Database migrations should run automatically, but if not:

```bash
# Backup first
cp archives/archive.db archives/archive.db.backup

# Run validation (triggers migrations)
chronicon validate --output-dir archives/
```

### Issue: Disk space full

**Symptoms:**
```
sqlite3.OperationalError: database or disk is full
```

**Solutions:**

1. **Check disk space:**
   ```bash
   df -h
   ```

2. **Clean up old exports:**
   ```bash
   # Keep only essential formats
   rm -rf archives/html/ archives/markdown/
   
   # Keep only database and GitHub export
   ```

3. **Enable text-only mode:**
   ```toml
   [export]
   text_only = true  # Skip image downloads
   ```

4. **Use PostgreSQL with separate storage:**
   - Database on one disk
   - Exports on another disk

## Fetching & API Issues

### Issue: Rate limiting (HTTP 429)

**Symptoms:**
```
urllib.error.HTTPError: HTTP Error 429: Too Many Requests
```

**Solutions:**

1. **Increase rate limit:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --rate-limit 2.0  # 2 seconds between requests
   ```

2. **Configure in .chronicon.toml:**
   ```toml
   [fetching]
   rate_limit_seconds = 2.0
   
   [[sites]]
   url = "https://strict-forum.com"
   rate_limit_seconds = 3.0  # Per-site override
   ```

3. **Use sweep mode with longer delays:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --sweep \
     --rate-limit 5.0
   ```

### Issue: Connection timeout

**Symptoms:**
```
urllib.error.URLError: <urlopen error timed out>
```

**Solutions:**

1. **Increase timeout:**
   ```toml
   [fetching]
   timeout = 30  # Default is 15
   ```

2. **Check network:**
   ```bash
   curl -I https://your-forum.com
   ping your-forum.com
   ```

3. **Test with smaller batch:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --categories 1  # Just one category
   ```

### Issue: HTTP 403 Forbidden

**Symptoms:**
```
urllib.error.HTTPError: HTTP Error 403: Forbidden
```

**Causes:**
- Forum blocks automated access
- IP banned
- User-Agent blocked

**Solutions:**

1. **Check forum's robots.txt:**
   ```bash
   curl https://your-forum.com/robots.txt
   ```

2. **Respect forum's terms of service** - Some forums don't allow archiving

3. **Contact forum administrators** for permission

4. **Alternative:** Export from Discourse admin panel instead

### Issue: HTTP 404 Not Found

**Symptoms:**
```
urllib.error.HTTPError: HTTP Error 404: Not Found
```

**Causes:**
- Topic deleted
- Topic moved to private category
- Invalid topic ID

**Solution:** This is normal - Chronicon will skip and continue:
```
Skipping topic 12345: 404 Not Found
```

### Issue: SSL Certificate errors

**Symptoms:**
```
urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]>
```

**Solutions:**

1. **Update CA certificates:**
   ```bash
   # On Ubuntu/Debian:
   sudo apt update
   sudo apt install --reinstall ca-certificates
   
   # On macOS:
   /Applications/Python*/Install\ Certificates.command
   ```

2. **Check forum SSL:**
   ```bash
   openssl s_client -connect your-forum.com:443
   ```

### Issue: Partial data fetched

**Symptoms:**
- Some topics missing posts
- Incomplete archives

**Solutions:**

1. **Use sweep mode:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --sweep \
     --start-id 10000
   ```

2. **Check logs for errors:**
   ```bash
   # Look for 404s, timeouts, etc.
   grep -i error chronicon.log
   ```

3. **Re-run with specific topics:**
   ```bash
   # After identifying missing topics
   chronicon archive --urls https://meta.discourse.org --topics 123,456,789
   ```

## Export Issues

### Issue: Missing images in HTML export

**Symptoms:**
- Broken image links in HTML
- Images not downloaded

**Solutions:**

1. **Check asset downloader logs:**
   ```bash
   # Look for download failures
   grep -i "failed to download" chronicon.log
   ```

2. **Ensure not in text-only mode:**
   ```toml
   [export]
   text_only = false
   ```

3. **Re-download assets:**
   ```bash
   # Delete assets and re-export
   rm -rf archives/html/assets/images/
   chronicon update --output-dir archives/ --formats html
   ```

4. **Check disk space:**
   ```bash
   df -h
   ```

### Issue: Search not working in HTML export

**Symptoms:**
- Search box present but returns no results

**Solutions:**

1. **Increase rate limit:**
   ```bash
   chronicon archive --urls https://forum.com --rate-limit 2.0
   ```

2. **Configure in .chronicon.toml:**
   ```toml
   [fetching]
   rate_limit_seconds = 2.0
   ```

3. **Use sweep mode with longer delays:**
   ```bash
   chronicon archive --urls https://meta.discourse.org --sweep --rate-limit 5.0
   ```

> **📚 See also:**
> - [PERFORMANCE.md](PERFORMANCE.md#network-io-primary-bottleneck) - Understanding rate limiting impact
> - [FAQ.md](FAQ.md#i-get-http-429-too-many-requests) - Quick reference
> - [EXAMPLES.md](EXAMPLES.md#example-1-archive-a-public-forum) - Working examples

2. **Check search_index.json exists:**
   ```bash
   ls -lh archives/html/search_index.json
   ```

3. **Verify JavaScript enabled in browser**

4. **Check browser console for errors:**
   - Open Developer Tools (F12)
   - Look for JavaScript errors

### Issue: Export takes too long

**Symptoms:**
- Export running for hours
- Seems stuck

**Solutions:**

1. **Monitor progress:**
   ```bash
   # In another terminal
   watch -n 5 'ls -lh archives/html/topics/ | tail -20'
   ```

2. **Reduce concurrent workers:**
   ```toml
   [fetching]
   max_workers = 4  # Default is 8
   ```

3. **Export only necessary formats:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --formats html  # Skip markdown exports
   ```

4. **Use incremental updates:**
   ```bash
   # Don't re-export everything
   chronicon update --output-dir archives/
   ```

### Issue: Markdown conversion errors

**Symptoms:**
- Malformed markdown output
- Code blocks broken
- Links not working

**Solutions:**

1. **Check HTML source in database:**
   ```bash
   sqlite3 archives/archive.db "SELECT cooked FROM posts WHERE id=12345;"
   ```

2. **Update html2text dependency:**
   ```bash
   pip install --upgrade html2text
   ```

3. **Report issue with example:**
   - Save problematic post HTML
   - Open issue at https://github.com/19-84/chronicon/issues

## Watch Mode Issues

### Issue: Daemon won't start

**Symptoms:**
```
Error: Could not start watch daemon
```

**Solutions:**

1. **Check if already running:**
   ```bash
   chronicon watch status --output-dir archives/
   cat archives/.chronicon-watch.pid
   ```

2. **Remove stale PID file:**
   ```bash
   rm archives/.chronicon-watch.pid
   rm archives/.chronicon-watch.lock
   ```

3. **Check logs:**
   ```bash
   tail -f archives/chronicon-watch.log
   ```

4. **Run in foreground for debugging:**
   ```bash
   chronicon watch --output-dir archives/ --debug
   ```

### Issue: Daemon stops after errors

**Symptoms:**
```
Too many consecutive errors (5), stopping daemon
```

**Solutions:**

1. **Check error logs:**
   ```bash
   tail -50 archives/chronicon-watch.log
   ```

2. **Increase error threshold:**
   ```toml
   [continuous]
   max_consecutive_errors = 10
   ```

3. **Increase polling interval:**
   ```toml
   [continuous]
   polling_interval_minutes = 20
   ```

4. **Fix underlying issue** (rate limiting, network, etc.)

### Issue: Git push fails

**Symptoms:**
```
Failed to push to remote: Permission denied (publickey)
```

**Solutions:**

1. **Check SSH keys:**
   ```bash
   ssh -T git@github.com
   # Should say: "Hi username! You've successfully authenticated"
   ```

2. **Fix key permissions:**
   ```bash
   chmod 600 ~/.ssh/id_ed25519
   chmod 644 ~/.ssh/id_ed25519.pub
   ```

3. **Add SSH key to agent:**
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

4. **Verify remote URL:**
   ```bash
   cd archives/
   git remote -v
   ```

5. **Disable push temporarily:**
   ```toml
   [continuous.git]
   push_to_remote = false
   ```

### Issue: Health check returning unhealthy

**Symptoms:**
```bash
$ curl http://localhost:8080/health
{"status": "unhealthy", "healthy": false}
```

**Solutions:**

1. **Check daemon status:**
   ```bash
   chronicon watch status --output-dir archives/
   ```

2. **Check error count:**
   ```bash
   curl http://localhost:8080/metrics | jq '.status.consecutive_errors'
   ```

3. **Restart daemon:**
   ```bash
   chronicon watch stop --output-dir archives/
   chronicon watch --output-dir archives/ --daemon
   ```

## Performance Issues

### Issue: Slow archiving

**Symptoms:**
- Taking hours for small forums
- Low throughput

**Solutions:**

1. **Increase worker count:**
   ```toml
   [fetching]
   max_workers = 16  # Default is 8
   ```

2. **Reduce rate limit (if safe):**
   ```toml
   [fetching]
   rate_limit_seconds = 0.2  # Faster, but check forum's limits
   ```

3. **Use faster storage:**
   - SSD instead of HDD
   - Local disk instead of network mount

4. **Export fewer formats:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --formats html  # Skip markdown
   ```

5. **Skip images:**
   ```bash
   chronicon archive \
     --urls https://meta.discourse.org \
     --text-only
   ```

### Issue: High memory usage

**Symptoms:**
- Process using multiple GB of RAM
- Out of memory errors

**Solutions:**

1. **Reduce worker count:**
   ```toml
   [fetching]
   max_workers = 4
   ```

2. **Process in batches:**
   ```bash
   # Archive one category at a time
   chronicon archive --urls https://meta.discourse.org --categories 1
   chronicon archive --urls https://meta.discourse.org --categories 2
   # etc.
   ```

3. **Use PostgreSQL:**
   - SQLite loads more into memory
   - PostgreSQL better for large datasets

4. **Set resource limits (systemd):**
   ```ini
   [Service]
   MemoryMax=2G
   ```

### Issue: Slow database queries

**Symptoms:**
- Export taking long time
- Queries timing out

**Solutions:**

1. **Vacuum database:**
   ```bash
   sqlite3 archives/archive.db "VACUUM;"
   ```

2. **Analyze database:**
   ```bash
   sqlite3 archives/archive.db "ANALYZE;"
   ```

3. **Check database size:**
   ```bash
   ls -lh archives/archive.db
   # If >5GB, consider PostgreSQL
   ```

4. **Re-index:**
   ```bash
   sqlite3 archives/archive.db "REINDEX;"
   ```

## Docker & Deployment Issues

### Issue: Permission denied in container

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/archives'
```

**Solutions:**

1. **Fix volume permissions:**
   ```bash
   sudo chown -R 1000:1000 archives/
   ```

2. **Run as your user:**
   ```bash
   docker run --user $(id -u):$(id -g) \
     -v ./archives:/archives \
     chronicon:alpine archive --urls https://meta.discourse.org
   ```

3. **Check volume mount:**
   ```bash
   docker inspect <container> | jq '.[0].Mounts'
   ```

### Issue: Container exits immediately

**Symptoms:**
- Container starts then stops
- No logs

**Solutions:**

1. **Check logs:**
   ```bash
   docker logs <container>
   docker-compose logs
   ```

2. **Run interactively:**
   ```bash
   docker run -it --entrypoint /bin/sh chronicon:alpine
   ```

3. **Verify archive exists:**
   ```bash
   ls -la archives/archive.db
   ```

4. **Check command syntax:**
   ```yaml
   # In docker-compose.yml
   command: watch --output-dir /archives
   # NOT: watch start --output-dir /archives
   ```

### Issue: Health check failing

**Symptoms:**
- Container marked as unhealthy
- Kubernetes pod restarting

**Solutions:**

1. **Test health endpoint:**
   ```bash
   docker exec <container> wget -q -O- http://localhost:8080/health
   ```

2. **Check health check timing:**
   ```yaml
   healthcheck:
     interval: 30s
     timeout: 10s
     start_period: 60s  # Give more time to start
   ```

3. **Check logs:**
   ```bash
   docker logs <container> | grep health
   ```

### Issue: Out of memory (Docker)

**Symptoms:**
```
Killed
```

**Solutions:**

1. **Increase memory limit:**
   ```yaml
   # docker-compose.yml
   services:
     chronicon:
       deploy:
         resources:
           limits:
             memory: 4G  # Increase from 2G
   ```

2. **Check actual usage:**
   ```bash
   docker stats chronicon
   ```

3. **Reduce workers:**
   ```toml
   [fetching]
   max_workers = 4
   ```

## Error Messages Reference

### Common Error Messages

| Error Message | Likely Cause | Solution |
|--------------|--------------|----------|
| `database is locked` | Concurrent access | Kill other processes, remove WAL files |
| `HTTP Error 429` | Rate limiting | Increase rate_limit_seconds |
| `Connection timed out` | Network/timeout | Increase timeout setting |
| `HTTP Error 403` | Blocked access | Check robots.txt, contact admin |
| `No such file or directory` | Missing database | Create initial archive first |
| `Permission denied` | File permissions | Fix ownership/permissions |
| `database disk image is malformed` | Corruption | Restore from backup, repair |
| `Command not found` | Not installed/PATH | Install chronicon, check PATH |
| `ImportError: psycopg` | Missing dependency | Install chronicon[postgres] |
| `Killed` | Out of memory | Increase memory limit, reduce workers |

### Exit Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 0 | Success | - |
| 1 | General error | Various errors, check logs |
| 2 | Invalid arguments | Wrong CLI arguments |
| 137 | Killed (OOM) | Out of memory |
| 143 | Terminated (SIGTERM) | Clean shutdown signal |

## Getting More Help

### Diagnostic Information

When reporting issues, include:

```bash
# Version information
chronicon --version
python --version
uv --version

# System information
uname -a
df -h

# Database stats
sqlite3 archives/archive.db "SELECT COUNT(*) FROM topics;"
sqlite3 archives/archive.db "SELECT COUNT(*) FROM posts;"
ls -lh archives/archive.db

# Recent logs
tail -100 chronicon.log
```

### Enabling Debug Logging

```bash
# CLI
chronicon archive \
  --urls https://meta.discourse.org \
  --debug

# Watch mode
chronicon watch --output-dir archives/ --debug
```

### Where to Get Help

1. **Documentation:**
   - [README.md](README.md) - General usage
   - [API_REFERENCE.md](API_REFERENCE.md) - Programmatic usage
   - [WATCH_MODE.md](WATCH_MODE.md) - Continuous monitoring
   - [PERFORMANCE.md](PERFORMANCE.md) - Performance tuning

2. **Community:**
   - GitHub Issues: https://github.com/19-84/chronicon/issues
   - GitHub Discussions: https://github.com/19-84/chronicon/discussions

3. **Reporting Bugs:**
   - Check existing issues first
   - Include diagnostic information
   - Provide reproducible example
   - Attach relevant logs

## Preventive Measures

### Regular Maintenance

```bash
# Weekly
sqlite3 archives/archive.db "VACUUM;"
sqlite3 archives/archive.db "ANALYZE;"

# Monthly
chronicon validate --output-dir archives/

# Check disk space
df -h

# Review logs
tail -1000 chronicon.log | grep -i error
```

### Backup Strategy

```bash
# Backup database
cp archives/archive.db archives/backups/archive-$(date +%Y%m%d).db

# Backup exports (if regenerable, optional)
tar czf archives/backups/exports-$(date +%Y%m%d).tar.gz archives/html/

# Keep last 7 days
find archives/backups/ -name "*.db" -mtime +7 -delete
```

### Monitoring

```bash
# Set up alerts for watch mode
*/5 * * * * curl -f http://localhost:8080/health || echo "Chronicon unhealthy" | mail -s "Alert" admin@example.com

# Monitor disk space
*/30 * * * * df -h | grep -E '9[0-9]%' && echo "Disk almost full" | mail -s "Alert" admin@example.com
```

## See Also

**Related Troubleshooting:**
- [FAQ.md](FAQ.md#troubleshooting) - Quick answers to common questions
- [WATCH_MODE.md](WATCH_MODE.md#troubleshooting) - Watch mode specific issues
- [PERFORMANCE.md](PERFORMANCE.md#troubleshooting-performance-issues) - Performance problems
- [examples/docker/README.md](examples/docker/README.md) - Docker-specific troubleshooting

**Other Documentation:**
- [MIGRATION.md](MIGRATION.md) - Database migration issues
- [API_REFERENCE.md](API_REFERENCE.md#error-handling) - Error handling in code
- [SECURITY.md](SECURITY.md) - Security-related issues

**Return to:** [Documentation Index](DOCUMENTATION.md)
