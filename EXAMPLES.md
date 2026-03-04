# Real-World Examples

**[Documentation Index](DOCUMENTATION.md)** > Examples

**Learn More:** [API Reference](API_REFERENCE.md) | [Watch Mode](WATCH_MODE.md) | [Performance](PERFORMANCE.md)

---

Practical examples and workflows for common Chronicon use cases.

## Table of Contents

- [Basic Workflows](#basic-workflows)
- [Production Deployments](#production-deployments)
- [Integration Examples](#integration-examples)
- [Advanced Use Cases](#advanced-use-cases)

## Basic Workflows

### Example 1: Archive a Public Forum

**Scenario:** Archive meta.discourse.org for offline reference

```bash
# One-time full archive
chronicon archive \
  --urls https://meta.discourse.org \
  --formats html,markdown \
  --output-dir ./meta-archive

# Browse offline
open ./meta-archive/html/index.html
```

### Example 2: Archive Specific Categories

**Scenario:** Only archive support and documentation categories

```bash
# Find category IDs
curl https://meta.discourse.org/categories.json | jq '.category_list.categories[] | {id, name}'

# Archive specific categories
chronicon archive \
  --urls https://meta.discourse.org \
  --categories 1,2,7 \
  --output-dir ./meta-support
```

### Example 3: Weekly Updates

**Scenario:** Archive weekly, keep archive up to date

```bash
#!/bin/bash
# weekly-update.sh

cd /path/to/archive

# Update existing archive
chronicon update --output-dir ./ --formats html,markdown

# Commit to git
cd html/
git add .
git commit -m "Weekly update: $(date +%Y-%m-%d)"
git push
```

**Cron schedule:**
```bash
# Every Sunday at 2 AM
0 2 * * 0 ~/weekly-update.sh
```

### Example 4: Text-Only Archive

**Scenario:** Minimize disk space, skip images

```bash
chronicon archive \
  --urls https://meta.discourse.org \
  --text-only \
  --formats markdown \
  --output-dir ./text-archive

# Result: 90% smaller, 50% faster
```

## Production Deployments

### Example 5: Kubernetes Deployment

**Scenario:** Enterprise deployment with monitoring

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronicon-watch
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: chronicon
        image: chronicon:alpine
        command: ["chronicon", "watch", "--output-dir", "/archives"]
        volumeMounts:
        - name: archives
          mountPath: /archives
        - name: config
          mountPath: /home/chronicon/.chronicon.toml
          subPath: .chronicon.toml
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 60
      volumes:
      - name: archives
        persistentVolumeClaim:
          claimName: chronicon-archives
      - name: config
        configMap:
          name: chronicon-config
---
# ConfigMap with configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: chronicon-config
data:
  .chronicon.toml: |
    [general]
    output_dir = "/archives"
    default_formats = ["html"]
    
    [continuous]
    polling_interval_minutes = 15
    
    [continuous.git]
    enabled = true
    auto_commit = true
    push_to_remote = true
```

Deploy:
```bash
kubectl apply -f deployment.yaml
kubectl port-forward service/chronicon-health 8080:8080
curl http://localhost:8080/metrics
```

> **📚 See also:**
> - [docs/deployment/kubernetes.md](docs/deployment/kubernetes.md) - Complete Kubernetes guide
> - [WATCH_MODE.md](WATCH_MODE.md#kubernetes) - Watch mode on Kubernetes
> - [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker--deployment-issues) - Deployment troubleshooting

### Example 6: Docker Compose with GitLab Auto-Push

**Scenario:** Continuous archiving with automatic GitLab Pages updates

```yaml
# docker-compose.yml
version: '3.8'

services:
  chronicon-watch:
    image: chronicon:alpine
    container_name: forum-archiver
    restart: unless-stopped
    volumes:
      - ./archives:/archives
      - ./config/.chronicon.toml:/home/chronicon/.chronicon.toml:ro
      - ./ssh:/home/chronicon/.ssh:ro
    environment:
      - TZ=America/New_York
    ports:
      - "127.0.0.1:8080:8080"
    command: watch --output-dir /archives
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/health"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 60s
```

Configuration (`.chronicon.toml`):
```toml
[general]
output_dir = "/archives"
default_formats = ["github"]

[continuous]
polling_interval_minutes = 30

[continuous.git]
enabled = true
auto_commit = true
commit_on_each_update = true
push_to_remote = true
remote_name = "origin"
branch = "main"
commit_message_template = "Update archive: {new_posts} new posts"

[[sites]]
url = "https://forum.example.com"
nickname = "main"
```

### Example 7: Systemd with Monitoring

**Scenario:** Production server with comprehensive monitoring

`/etc/systemd/system/chronicon-watch.service`:
```ini
[Unit]
Description=Chronicon Watch Daemon
After=network.target

[Service]
Type=simple
User=chronicon
WorkingDirectory=/var/lib/chronicon
ExecStart=/usr/local/bin/chronicon watch --output-dir /var/lib/chronicon/archives
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=2G
CPUQuota=100%

# Healthcheck
ExecStartPost=/usr/local/bin/check-chronicon-health.sh

[Install]
WantedBy=multi-user.target
```

Healthcheck script (`/usr/local/bin/check-chronicon-health.sh`):
```bash
#!/bin/bash
# Wait for service to start
sleep 60

# Check health endpoint
if ! curl -f http://localhost:8080/health; then
    echo "Chronicon health check failed" | systemd-cat -t chronicon-monitor -p err
    exit 1
fi
```

Monitoring with Prometheus:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'chronicon'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

## Integration Examples

### Example 8: Backup to S3

**Scenario:** Daily backups to AWS S3

```bash
#!/bin/bash
# backup-to-s3.sh

DATE=$(date +%Y%m%d)
ARCHIVE_DB="/var/lib/chronicon/archives/archive.db"
S3_BUCKET="s3://my-backups/chronicon/"

# Backup database
gzip -c "$ARCHIVE_DB" > "/tmp/archive-$DATE.db.gz"

# Upload to S3
aws s3 cp "/tmp/archive-$DATE.db.gz" "$S3_BUCKET"

# Cleanup local backup
rm "/tmp/archive-$DATE.db.gz"

# Keep only last 30 days on S3
aws s3 ls "$S3_BUCKET" | while read -r line; do
    createDate=$(echo "$line" | awk {'print $1" "$2'})
    createDate=$(date -d "$createDate" +%s)
    olderThan=$(date -d "30 days ago" +%s)
    if [[ $createDate -lt $olderThan ]]; then
        fileName=$(echo "$line" | awk {'print $4'})
        if [[ $fileName != "" ]]; then
            aws s3 rm "$S3_BUCKET$fileName"
        fi
    fi
done

echo "Backup complete: archive-$DATE.db.gz"
```

Cron:
```bash
0 4 * * * /usr/local/bin/backup-to-s3.sh
```

### Example 9: Slack Notifications

**Scenario:** Notify team when updates complete

```python
#!/usr/bin/env python3
# notify-slack.py

import json
import sys
from pathlib import Path
import requests

def send_slack_notification(message):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    payload = {"text": message}
    requests.post(webhook_url, json=payload)

def main():
    status_file = Path("archives/.chronicon-watch-status.json")
    
    if not status_file.exists():
        return
    
    status = json.loads(status_file.read_text())
    last_cycle = status.get("cycle_history", [{}])[-1]
    
    if last_cycle.get("success"):
        message = (
            f"✅ Archive updated successfully\n"
            f"• New posts: {last_cycle.get('new_posts', 0)}\n"
            f"• Modified: {last_cycle.get('modified_posts', 0)}\n"
            f"• Topics: {last_cycle.get('affected_topics', 0)}"
        )
        send_slack_notification(message)

if __name__ == "__main__":
    main()
```

Add to cron:
```bash
*/30 * * * * /usr/local/bin/notify-slack.py
```

### Example 10: Multi-Forum Aggregator

**Scenario:** Archive multiple forums to separate databases

```python
#!/usr/bin/env python3
# multi-forum-archiver.py

from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.fetchers import DiscourseAPIClient, TopicFetcher
from chronicon.exporters import MarkdownGitHubExporter

FORUMS = [
    {
        "name": "Meta Discourse",
        "url": "https://meta.discourse.org",
        "output": "./archives/meta",
        "categories": [1, 2, 7]
    },
    {
        "name": "Community Forum",
        "url": "https://community.example.com",
        "output": "./archives/community",
        "categories": None  # All categories
    }
]

def archive_forum(config):
    print(f"Archiving {config['name']}...")
    
    output_path = Path(config['output'])
    output_path.mkdir(parents=True, exist_ok=True)
    
    db = ArchiveDatabase(db_path=output_path / "archive.db")
    client = DiscourseAPIClient(base_url=config['url'], rate_limit=1.0)
    fetcher = TopicFetcher(client, db)
    
    # Fetch topics
    if config['categories']:
        for cat_id in config['categories']:
            topics = fetcher.fetch_category_topics(cat_id, limit=1000)
            for topic in topics:
                fetcher.fetch_topic_with_posts(topic.id)
    else:
        topics = fetcher.fetch_recent_topics(limit=1000)
        for topic in topics:
            fetcher.fetch_topic_with_posts(topic.id)
    
    # Export
    exporter = MarkdownGitHubExporter(db, output_dir=output_path / "github")
    exporter.export()
    
    db.close()
    print(f"✓ {config['name']} complete")

def main():
    for forum in FORUMS:
        try:
            archive_forum(forum)
        except Exception as e:
            print(f"✗ {forum['name']} failed: {e}")

if __name__ == "__main__":
    main()
```

## Advanced Use Cases

### Example 11: Custom Post Processing

**Scenario:** Anonymize usernames before export

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.exporters import HTMLStaticExporter
import hashlib

def anonymize_username(username):
    """Convert username to anonymous hash."""
    return f"user_{hashlib.md5(username.encode()).hexdigest()[:8]}"

def anonymize_archive(db_path):
    db = ArchiveDatabase(db_path=db_path)
    
    # Get all posts
    posts = []
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM posts")
    
    for row in cursor.fetchall():
        post_dict = dict(row)
        # Anonymize username
        post_dict['username'] = anonymize_username(post_dict['username'])
        # Update in database
        cursor.execute(
            "UPDATE posts SET username = ? WHERE id = ?",
            (post_dict['username'], post_dict['id'])
        )
    
    db.connection.commit()
    db.close()

# Usage
anonymize_archive(Path("./archives/archive.db"))

# Then export
db = ArchiveDatabase(db_path=Path("./archives/archive.db"))
exporter = HTMLStaticExporter(db, output_dir=Path("./archives/html-anon"))
exporter.export()
db.close()
```

### Example 12: Statistical Analysis

**Scenario:** Generate forum statistics report

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from collections import Counter
from datetime import datetime
import json

def generate_statistics(db_path):
    db = ArchiveDatabase(db_path=db_path)
    
    stats = {}
    
    # Basic counts
    stats['summary'] = db.get_statistics()
    
    # Get all posts for analysis
    cursor = db.connection.cursor()
    cursor.execute("SELECT username, created_at, like_count FROM posts")
    posts = cursor.fetchall()
    
    # Top contributors
    user_counts = Counter(post['username'] for post in posts)
    stats['top_contributors'] = [
        {"username": username, "posts": count}
        for username, count in user_counts.most_common(10)
    ]
    
    # Activity by month
    activity_by_month = Counter()
    for post in posts:
        month = datetime.fromisoformat(post['created_at']).strftime('%Y-%m')
        activity_by_month[month] += 1
    stats['activity_by_month'] = dict(activity_by_month)
    
    # Most liked posts
    cursor.execute("""
        SELECT p.id, t.title, p.username, p.like_count
        FROM posts p
        JOIN topics t ON p.topic_id = t.id
        ORDER BY p.like_count DESC
        LIMIT 10
    """)
    stats['most_liked_posts'] = [dict(row) for row in cursor.fetchall()]
    
    db.close()
    
    # Save report
    report_path = Path("./archives/statistics.json")
    report_path.write_text(json.dumps(stats, indent=2))
    
    print(f"Statistics saved to {report_path}")
    return stats

# Generate report
stats = generate_statistics(Path("./archives/archive.db"))
print(json.dumps(stats['summary'], indent=2))
```

### Example 13: Selective Re-Export

**Scenario:** Re-export only topics modified in last week

```python
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.exporters import HTMLStaticExporter
from datetime import datetime, timedelta

def export_recent_updates(db_path, days=7):
    db = ArchiveDatabase(db_path=db_path)
    
    # Get topics updated in last N days
    since = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = db.connection.cursor()
    cursor.execute(
        "SELECT id FROM topics WHERE updated_at >= ? ORDER BY updated_at DESC",
        (since,)
    )
    topic_ids = [row['id'] for row in cursor.fetchall()]
    
    print(f"Found {len(topic_ids)} topics updated in last {days} days")
    
    # Export only these topics
    exporter = HTMLStaticExporter(db, output_dir=Path("./archives/html"))
    exporter.export_topics(topic_ids)
    exporter.update_index()
    
    db.close()
    print("Export complete")

# Usage
export_recent_updates(Path("./archives/archive.db"), days=7)
```

### Example 14: Mirror to GitHub Pages

**Scenario:** Automatic GitHub Pages deployment

```bash
#!/bin/bash
# deploy-github-pages.sh

ARCHIVE_DIR="/var/lib/chronicon/archives"
GITHUB_REPO="git@github.com:your-org/forum-archive.git"
TEMP_DIR="/tmp/chronicon-deploy"

# Update archive
chronicon update --output-dir "$ARCHIVE_DIR" --formats github

# Clone GitHub Pages repo
rm -rf "$TEMP_DIR"
git clone "$GITHUB_REPO" "$TEMP_DIR"

# Copy new content
rsync -av --delete "$ARCHIVE_DIR/github/" "$TEMP_DIR/"

# Commit and push
cd "$TEMP_DIR"
git add .
git commit -m "Archive update: $(date +%Y-%m-%d)"
git push origin main

# Cleanup
rm -rf "$TEMP_DIR"

echo "Deployed to GitHub Pages"
```

### Example 15: Email Digest

**Scenario:** Weekly email with new topics

```python
#!/usr/bin/env python3
# email-digest.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from datetime import datetime, timedelta

def send_digest(db_path, recipient):
    db = ArchiveDatabase(db_path=db_path)
    
    # Get topics from last week
    since = (datetime.now() - timedelta(days=7)).isoformat()
    cursor = db.connection.cursor()
    cursor.execute("""
        SELECT t.id, t.title, t.slug, t.created_at, t.reply_count, t.like_count
        FROM topics t
        WHERE t.created_at >= ?
        ORDER BY t.created_at DESC
        LIMIT 20
    """, (since,))
    topics = cursor.fetchall()
    
    if not topics:
        print("No new topics this week")
        return
    
    # Build email
    html_content = "<h2>Weekly Forum Digest</h2><ul>"
    for topic in topics:
        html_content += f"""
        <li>
            <strong>{topic['title']}</strong><br>
            Replies: {topic['reply_count']} | Likes: {topic['like_count']}<br>
            <a href="https://forum.example.com/t/{topic['slug']}/{topic['id']}">View Topic</a>
        </li>
        """
    html_content += "</ul>"
    
    # Send email
    msg = MIMEMultipart()
    msg['From'] = "archive@example.com"
    msg['To'] = recipient
    msg['Subject'] = f"Forum Digest - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(html_content, 'html'))
    
    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login("username", "password")
        server.send_message(msg)
    
    db.close()
    print(f"Digest sent to {recipient}")

# Usage
send_digest(Path("./archives/archive.db"), "team@example.com")
```

## See Also

**More Examples:**
- [WATCH_MODE.md](WATCH_MODE.md#examples) - Watch mode examples
- [examples/docker/](examples/docker/) - Docker deployment examples
- [examples/systemd/](examples/systemd/) - Systemd service examples

**Technical Documentation:**
- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation
- [PERFORMANCE.md](PERFORMANCE.md) - Optimization strategies
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting examples

**Getting Started:**
- [README.md](README.md) - Installation and basic usage
- [FAQ.md](FAQ.md) - Common questions

**Return to:** [Documentation Index](DOCUMENTATION.md)
