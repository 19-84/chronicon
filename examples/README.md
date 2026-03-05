# Examples

## Demo Archive

A live demo archive of meta.discourse.org (Theme category) is hosted at:

- **Live site:** https://online-archives.github.io/chronicon-archive-example/
- **Source repo:** https://github.com/online-archives/chronicon-archive-example

## Generating Your Own Archive

```bash
# Archive a category from meta.discourse.org
chronicon archive \
  --urls https://meta.discourse.org \
  --categories 61 \
  --output-dir ./my-archive \
  --formats html,markdown-github \
  --search-backend static

# Export with canonical URLs for GitHub Pages
# Add to .chronicon.toml:
# [export]
# canonical_base_url = "https://yourusername.github.io/your-repo"
```

## Docker Examples

See `examples/docker/` for production-ready Docker deployment configurations:

- `docker-compose.yml` — SQLite-based deployment
- `docker-compose.postgres.yml` — PostgreSQL-based deployment with API server
