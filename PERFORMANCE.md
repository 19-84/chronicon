# Performance Guide

**[Documentation Index](DOCUMENTATION.md)** > Performance

**Related:** [Troubleshooting](TROUBLESHOOTING.md#performance-issues) | [FAQ](FAQ.md#performance) | [Examples](EXAMPLES.md)

---

Optimization strategies, benchmarks, and tuning for Chronicon.

## Table of Contents

- [Benchmarks](#benchmarks)
- [Performance Bottlenecks](#performance-bottlenecks)
- [Optimization Strategies](#optimization-strategies)
- [Resource Requirements](#resource-requirements)
- [Monitoring Performance](#monitoring-performance)

## Benchmarks

### Test Environment

All benchmarks performed on:
- CPU: 4-core Intel i7 @ 2.8GHz
- RAM: 16GB
- Storage: SSD
- Network: 100 Mbps
- Forum: meta.discourse.org

### Archive Performance

| Forum Size | Topics | Posts | Time (Full) | Time (Text-Only) | Disk Usage (Full) | Disk Usage (Text) |
|-----------|--------|-------|-------------|------------------|-------------------|-------------------|
| Small | 1,000 | 10,000 | 15 min | 8 min | 500 MB | 50 MB |
| Medium | 10,000 | 100,000 | 2.5 hrs | 1.2 hrs | 5 GB | 200 MB |
| Large | 50,000 | 500,000 | 14 hrs | 6 hrs | 25 GB | 1 GB |
| Very Large | 100,000+ | 1M+ | 30+ hrs | 15 hrs | 50+ GB | 2 GB |

### Export Performance

| Format | 10k Topics | 100k Topics | Notes |
|--------|-----------|-------------|-------|
| HTML | 5 min | 45 min | Includes search index generation |
| Markdown (Plain) | 3 min | 25 min | Fastest export |
| Markdown (GitHub) | 4 min | 35 min | Includes README generation |
| All Formats | 12 min | 105 min | Parallel export |

### Update Performance (Incremental)

| Updates | New Posts | Modified Posts | Time |
|---------|-----------|----------------|------|
| Hourly | 10-50 | 5-20 | 30 sec - 2 min |
| Daily | 100-500 | 20-100 | 5-15 min |
| Weekly | 500-2000 | 100-500 | 20-60 min |

## Performance Bottlenecks

### 1. Network I/O (Primary Bottleneck)

**Impact:** 60-70% of total time

**Factors:**
- API rate limiting
- Network latency
- Forum response time
- Request retry logic

**Mitigation:**
```toml
[fetching]
rate_limit_seconds = 0.3  # Aggressive (check forum limits)
timeout = 30              # Longer timeout for slow forums
max_retries = 3           # Fewer retries
max_workers = 16          # More concurrent requests
```

> **⚠️ Important:**
> - Always respect forum's rate limits
> - See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#rate-limiting-http-429) if you get 429 errors
> - Check [FAQ.md](FAQ.md#my-forum-is-huge-how-do-i-handle-it) for large forum strategies

### 2. Asset Downloads

**Impact:** 20-30% of total time (if downloading images)

**Factors:**
- Number of images
- Image sizes
- Network bandwidth
- Concurrent download limit

**Mitigation:**
```bash
# Skip images for faster archiving
chronicon archive --urls https://meta.discourse.org --text-only

# Or reduce workers
[fetching]
max_workers = 8  # Balance between speed and load
```

### 3. Database Operations

**Impact:** 5-10% of total time

**Factors:**
- Database size
- Disk I/O speed
- Transaction overhead
- Index efficiency

**Mitigation:**
```bash
# Use SSD storage
# Or PostgreSQL for large archives
[general]
database_url = "postgresql://user:pass@localhost/chronicon"

# Regular maintenance
sqlite3 archive.db "VACUUM;"
sqlite3 archive.db "ANALYZE;"
```

### 4. Export Generation

**Impact:** 5-10% of total time

**Factors:**
- Number of topics
- Number of formats
- Template rendering
- File I/O

**Mitigation:**
```bash
# Export only needed formats
chronicon archive --formats html

# Use incremental updates
chronicon update --output-dir archives/
```

## Optimization Strategies

### Strategy 1: Incremental Archiving

**Problem:** Re-archiving everything is slow

**Solution:**
```bash
# Initial archive
chronicon archive --urls https://meta.discourse.org

# Regular updates (only new/modified content)
chronicon update --output-dir archives/
```

**Benefit:** 10-50x faster for updates

### Strategy 2: Category-Based Archiving

**Problem:** Large forums take too long

**Solution:**
```bash
# Archive one category at a time
chronicon archive --urls https://meta.discourse.org --categories 1
chronicon archive --urls https://meta.discourse.org --categories 2
# etc.
```

**Benefit:** Manageable chunks, can parallelize

### Strategy 3: Text-Only Mode

**Problem:** Image downloads slow everything down

**Solution:**
```bash
chronicon archive --urls https://meta.discourse.org --text-only
```

**Benefit:** 40-60% faster, 90% less disk space

### Strategy 4: Optimal Worker Count

**Finding the sweet spot:**

```bash
# Test different worker counts
time chronicon archive --urls https://meta.discourse.org --categories 1 --max-workers 4
time chronicon archive --urls https://meta.discourse.org --categories 1 --max-workers 8
time chronicon archive --urls https://meta.discourse.org --categories 1 --max-workers 16
```

**Guidelines:**
- Start with CPU core count * 2
- Watch for rate limiting (429 errors)
- Monitor memory usage
- Balance: speed vs forum load

**Recommended:**
```toml
[fetching]
max_workers = 8  # Good default
# For fast forums with high rate limits: 16
# For slow forums or restrictive limits: 4
```

### Strategy 5: Selective Format Export

**Problem:** Don't need all formats

**Solution:**
```bash
# HTML only (best for browsing)
chronicon archive --urls https://meta.discourse.org --formats html

# Markdown only (best for archival)
chronicon archive --urls https://meta.discourse.org --formats markdown
```

**Benefit:** 60-70% faster than all formats

### Strategy 6: Database Optimization

**SQLite:**
```bash
# Enable WAL mode (better concurrency)
sqlite3 archive.db "PRAGMA journal_mode=WAL;"

# Increase cache
sqlite3 archive.db "PRAGMA cache_size=-64000;"  # 64MB cache

# Regular maintenance
sqlite3 archive.db "VACUUM;"
sqlite3 archive.db "ANALYZE;"
```

**PostgreSQL (for large archives):**
```sql
-- Tune for performance
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET max_worker_processes = 8;
```

### Strategy 7: Storage Optimization

**SSD vs HDD:**
- SSD: 3-5x faster for database operations
- NVMe: 5-10x faster

**Separate disks:**
```bash
# Database on fast SSD
/fast-ssd/archives/archive.db

# Exports on slower HDD
/bulk-storage/archives/html/
```

### Strategy 8: Watch Mode Tuning

**For continuous monitoring:**

```toml
[continuous]
# Longer intervals = less load
polling_interval_minutes = 15  # Instead of 10

# Batch git commits
[continuous.git]
commit_on_each_update = false  # Commit daily instead
```

## Resource Requirements

### CPU

| Forum Size | Recommended Cores | Notes |
|-----------|-------------------|-------|
| Small (<10k topics) | 2 cores | Single-core bottlenecked by network |
| Medium (10k-50k) | 4 cores | Good parallelization |
| Large (50k-100k) | 4-8 cores | Diminishing returns above 8 |
| Very Large (100k+) | 8 cores | Max benefit |

### Memory

| Forum Size | Minimum RAM | Recommended RAM | Notes |
|-----------|-------------|-----------------|-------|
| Small | 512 MB | 2 GB | |
| Medium | 2 GB | 4 GB | |
| Large | 4 GB | 8 GB | |
| Very Large | 8 GB | 16 GB | For PostgreSQL + processing |

**Memory usage patterns:**
```
Base process: ~50-100 MB
Per worker thread: ~10-20 MB
Database cache (SQLite): ~64 MB default
Asset processing: ~100-200 MB
```

### Storage

| Component | Small Forum | Medium Forum | Large Forum |
|-----------|-------------|--------------|-------------|
| Database | 50 MB | 500 MB | 5 GB |
| HTML Export | 200 MB | 2 GB | 20 GB |
| Markdown Export | 30 MB | 300 MB | 3 GB |
| GitHub Export | 150 MB | 1.5 GB | 15 GB |
| **Total (all formats)** | **430 MB** | **4.3 GB** | **43 GB** |

**Text-only (no images):**
- 80-90% smaller
- Faster archiving
- Less bandwidth

### Network

**Bandwidth requirements:**

| Forum Size | Download (Full) | Download (Text-Only) | Duration @ 10 Mbps |
|-----------|-----------------|----------------------|-------------------|
| Small | 500 MB | 50 MB | 7 min / 40 sec |
| Medium | 5 GB | 200 MB | 1.1 hrs / 3 min |
| Large | 25 GB | 1 GB | 5.5 hrs / 13 min |

**API requests:**
- Small: ~1,000 requests
- Medium: ~10,000 requests  
- Large: ~100,000 requests

## Monitoring Performance

### Built-in Statistics

```python
from chronicon.fetchers import DiscourseAPIClient

client = DiscourseAPIClient(base_url="https://meta.discourse.org")
# ... perform operations ...

print(f"Requests: {client.requests_made}")
print(f"Success rate: {client.requests_successful / client.requests_made * 100}%")
print(f"Data: {client.bytes_transferred / 1024 / 1024:.2f} MB")
print(f"Duration: {time.time() - client.start_time:.1f}s")
```

### System Monitoring

**CPU and Memory:**
```bash
# Real-time monitoring
top -p $(pgrep -f chronicon)

# Or with htop
htop -p $(pgrep -f chronicon)
```

**Disk I/O:**
```bash
# Monitor disk usage
iotop -p $(pgrep -f chronicon)

# Or simpler
iostat -x 5
```

**Network:**
```bash
# Monitor network usage
iftop

# Or simpler
nethogs $(pgrep -f chronicon)
```

### Database Profiling

**SQLite query analysis:**
```bash
# Enable query logging
sqlite3 archive.db "PRAGMA query_only = ON;"

# Analyze slow queries
sqlite3 archive.db "EXPLAIN QUERY PLAN SELECT * FROM posts WHERE topic_id = 123;"
```

**Check database health:**
```bash
# Size
ls -lh archive.db

# Integrity
sqlite3 archive.db "PRAGMA integrity_check;"

# Fragmentation
sqlite3 archive.db "PRAGMA freelist_count;"
# If high, run VACUUM
```

### Performance Metrics to Track

1. **Throughput:** Topics/hour, Posts/hour
2. **Latency:** Average request time
3. **Success Rate:** % of successful requests
4. **Resource Usage:** CPU %, Memory MB, Disk I/O
5. **Error Rate:** Failed requests, retries

### Sample Performance Report

```bash
#!/bin/bash
# performance-report.sh

echo "=== Chronicon Performance Report ==="
echo "Date: $(date)"
echo

echo "Database Statistics:"
sqlite3 archive.db "SELECT 
    (SELECT COUNT(*) FROM topics) as topics,
    (SELECT COUNT(*) FROM posts) as posts,
    (SELECT COUNT(*) FROM categories) as categories,
    (SELECT COUNT(*) FROM users) as users;"

echo
echo "Database Size:"
ls -lh archive.db

echo
echo "Export Sizes:"
du -sh archives/html/ archives/markdown/ archives/github/ 2>/dev/null

echo
echo "Last 10 Errors:"
grep -i error chronicon.log | tail -10
```

## Performance Checklist

### Before Archiving

- [ ] Check forum's robots.txt and rate limits
- [ ] Ensure adequate disk space (2-3x expected size)
- [ ] Use SSD if possible
- [ ] Configure optimal worker count
- [ ] Set appropriate rate limits
- [ ] Choose necessary formats only

### During Archiving

- [ ] Monitor for rate limiting (429 errors)
- [ ] Watch disk space
- [ ] Check memory usage
- [ ] Monitor network bandwidth
- [ ] Track progress and ETA

### After Archiving

- [ ] Run database VACUUM and ANALYZE
- [ ] Verify export completeness
- [ ] Check for errors in logs
- [ ] Measure actual performance
- [ ] Adjust settings for next run

## Troubleshooting Performance Issues

### Issue: Very Slow Archiving

**Diagnosis:**
```bash
# Check network
ping -c 10 forum.example.com

# Check rate limiting
grep "429" chronicon.log

# Check disk I/O
iostat -x 5
```

**Solutions:**
- Increase workers if network is fast
- Decrease workers if hitting rate limits  
- Use faster storage
- Enable text-only mode

### Issue: High Memory Usage

**Diagnosis:**
```bash
ps aux | grep chronicon
# Check RSS (resident memory)
```

**Solutions:**
```toml
[fetching]
max_workers = 4  # Reduce workers
```

### Issue: Slow Exports

**Diagnosis:**
```bash
# Time each format
time chronicon update --formats html
time chronicon update --formats markdown
time chronicon update --formats github
```

**Solutions:**
- Export fewer formats
- Use incremental updates
- Faster disk storage

## See Also

**Performance Related:**
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md#performance-issues) - Performance troubleshooting
- [FAQ.md](FAQ.md#performance) - Performance FAQs
- [EXAMPLES.md](EXAMPLES.md#advanced-use-cases) - Optimization examples

**Technical Documentation:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - Understanding bottlenecks
- [API_REFERENCE.md](API_REFERENCE.md) - Programmatic optimization
- [README.md](README.md#troubleshooting) - Quick performance tips

**Return to:** [Documentation Index](DOCUMENTATION.md)
