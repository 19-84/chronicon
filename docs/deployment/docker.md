# Docker Deployment Guide

Chronicon provides official Docker images for easy deployment in containerized environments.

## Available Images

Docker images are available on GitHub Container Registry:

- **Standard**: `ghcr.io/yourusername/chronicon:latest`
- **Alpine**: `ghcr.io/yourusername/chronicon:alpine` (smaller, ~100MB less)

Both images support the same features and command-line interface.

## Quick Start

### One-time Archive

```bash
docker run --rm \
  -v $(pwd)/archives:/archives \
  ghcr.io/yourusername/chronicon:alpine \
  archive --urls https://meta.discourse.org --output-dir /archives
```

### With Configuration File

```bash
docker run --rm \
  -v $(pwd)/archives:/archives \
  -v $(pwd)/.chronicon.toml:/home/chronicon/.chronicon.toml:ro \
  ghcr.io/yourusername/chronicon:alpine \
  archive --output-dir /archives
```

## Environment Variables

### `CHRONICON_OUTPUT_DIR`

Override the default output directory (useful for container orchestration):

```bash
docker run --rm \
  -v $(pwd)/archives:/data \
  -e CHRONICON_OUTPUT_DIR=/data \
  ghcr.io/yourusername/chronicon:alpine \
  archive --urls https://meta.discourse.org
```

## Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  chronicon:
    image: ghcr.io/yourusername/chronicon:alpine
    volumes:
      - ./archives:/archives
      - ./config/.chronicon.toml:/home/chronicon/.chronicon.toml:ro
    environment:
      - CHRONICON_OUTPUT_DIR=/archives
    command: archive --output-dir /archives
```

Run with:

```bash
docker-compose up
```

## Watch Mode (Continuous Updates)

Run Chronicon in watch mode to automatically update archives on a schedule:

```yaml
version: '3.8'

services:
  chronicon-watch:
    image: ghcr.io/yourusername/chronicon:alpine
    volumes:
      - ./archives:/archives
      - ./config/.chronicon.toml:/home/chronicon/.chronicon.toml:ro
    environment:
      - CHRONICON_OUTPUT_DIR=/archives
    command: watch start --urls https://meta.discourse.org --output-dir /archives
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

The watch mode includes a health check server on port 8080 for monitoring.

## Volume Mounts

### Required Mounts

- **Output directory**: `-v /host/path:/archives`
  - Stores archive database and exported files
  - Should be persistent storage

### Optional Mounts

- **Configuration**: `-v /host/.chronicon.toml:/home/chronicon/.chronicon.toml:ro`
  - Mount as read-only (`:ro`) for security
  - Falls back to command-line args if not provided

## Multi-Site Archiving

Archive multiple forums in one container:

```yaml
version: '3.8'

services:
  chronicon-meta:
    image: ghcr.io/yourusername/chronicon:alpine
    volumes:
      - ./archives/meta:/archives
    command: archive --urls https://meta.discourse.org --output-dir /archives

  chronicon-community:
    image: ghcr.io/yourusername/chronicon:alpine
    volumes:
      - ./archives/community:/archives
    command: archive --urls https://community.example.com --output-dir /archives
```

## Resource Limits

Set resource limits for production deployments:

```yaml
services:
  chronicon:
    image: ghcr.io/yourusername/chronicon:alpine
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Permissions

The container runs as user `chronicon` (UID 1000) by default. Ensure mounted volumes have appropriate permissions:

```bash
# Create archives directory with correct permissions
mkdir -p archives
chown -R 1000:1000 archives
chmod 755 archives
```

## Building Custom Images

If you need a custom image with additional tools:

```dockerfile
FROM ghcr.io/yourusername/chronicon:alpine

# Add custom tools
RUN apk add --no-cache curl jq

# Copy custom scripts
COPY scripts/ /usr/local/bin/
```

Build and run:

```bash
docker build -t chronicon-custom .
docker run --rm -v $(pwd)/archives:/archives chronicon-custom archive --urls https://meta.discourse.org
```

## Troubleshooting

### Permission Denied Errors

If you see permission errors:

```bash
# Run container as your user
docker run --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/archives:/archives \
  ghcr.io/yourusername/chronicon:alpine \
  archive --urls https://meta.discourse.org --output-dir /archives
```

### Out of Memory

Increase container memory limits or reduce concurrent workers:

```bash
docker run --rm \
  --memory=4g \
  -v $(pwd)/archives:/archives \
  ghcr.io/yourusername/chronicon:alpine \
  archive --urls https://meta.discourse.org --output-dir /archives --workers 4
```

### Slow Downloads

Increase worker count for faster archiving:

```bash
docker run --rm \
  -v $(pwd)/archives:/archives \
  ghcr.io/yourusername/chronicon:alpine \
  archive --urls https://meta.discourse.org --output-dir /archives --workers 16
```

## Security Best Practices

1. **Read-only configuration**: Mount config files as read-only (`:ro`)
2. **Non-root user**: Container runs as non-root by default
3. **Network isolation**: Use Docker networks to isolate containers
4. **Resource limits**: Set CPU/memory limits to prevent resource exhaustion
5. **Regular updates**: Pull latest images regularly for security patches

## Next Steps

- See [Kubernetes Deployment](kubernetes.md) for orchestration at scale
- See [Environment Variables](environment-variables.md) for all configuration options
- Check [examples/docker](../../examples/docker/) for more examples
