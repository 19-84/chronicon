# Docker Deployment for Chronicon Watch

This directory contains Docker and Docker Compose files for running Chronicon watch mode in a container.

## Quick Start

### Using Docker Compose (Recommended)

1. **Create initial archive** (first time only):
   ```bash
   docker run --rm -v ./archives:/archives \
     chronicon archive \
     --urls https://discourse.example.com \
     --output-dir /archives
   ```

2. **Create configuration file** (optional):
   ```bash
   mkdir -p config
   cp ../../.chronicon.toml.example config/.chronicon.toml
   # Edit config/chronicon.toml with your settings
   ```

3. **Start watch mode**:
   ```bash
   docker-compose up -d
   ```

4. **Check status**:
   ```bash
   # View logs
   docker-compose logs -f

   # Check health
   curl http://localhost:8080/health

   # View metrics
   curl http://localhost:8080/metrics
   ```

### Using Docker (without Compose)

1. **Build image**:
   ```bash
   docker build -f Dockerfile.watch -t chronicon-watch:latest ../..
   ```

2. **Run container**:
   ```bash
   docker run -d \
     --name chronicon-watch \
     --restart unless-stopped \
     -v ./archives:/archives \
     -p 8080:8080 \
     chronicon-watch:latest
   ```

## Configuration

### Environment Variables

You can override configuration via environment variables:

```bash
docker run -d \
  -e CHRONICON_OUTPUT_DIR=/archives \
  -e TZ=America/New_York \
  -v ./archives:/archives \
  chronicon-watch:latest
```

### Configuration File

Mount a configuration file:

```bash
docker run -d \
  -v ./config/.chronicon.toml:/home/chronicon/.chronicon.toml:ro \
  -v ./archives:/archives \
  chronicon-watch:latest
```

Example config file (`config/.chronicon.toml`):
```toml
[continuous]
polling_interval_minutes = 10
max_consecutive_errors = 5

[continuous.git]
enabled = false
auto_commit = true
push_to_remote = false
```

## Git Integration

To enable git auto-commit and push:

1. **Initialize git repository in archives**:
   ```bash
   cd archives
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin git@github.com:your-org/your-repo.git
   ```

2. **Mount SSH key** (for push to remote):
   ```bash
   # Copy your SSH key
   mkdir -p config/ssh
   cp ~/.ssh/id_rsa config/ssh/
   cp ~/.ssh/id_rsa.pub config/ssh/
   chmod 600 config/ssh/id_rsa

   # Update docker-compose.yml to mount SSH directory
   volumes:
     - ./config/ssh:/home/chronicon/.ssh:ro
   ```

3. **Enable git in configuration**:
   ```toml
   [continuous.git]
   enabled = true
   auto_commit = true
   push_to_remote = true
   remote_name = "origin"
   branch = "main"
   ```

## Monitoring

### Health Checks

The container includes health checks on port 8080:

- **`GET /health`** - Returns health status (200 if healthy, 503 if unhealthy)
- **`GET /metrics`** - Returns detailed metrics (JSON)
- **`GET /`** - HTML page with endpoint documentation

```bash
# Check health
curl http://localhost:8080/health | jq

# Get metrics
curl http://localhost:8080/metrics | jq
```

### Docker Healthcheck

Docker will automatically monitor container health:

```bash
# Check container health status
docker ps

# View health check logs
docker inspect chronicon-watch | jq '.[0].State.Health'
```

### Logging

View container logs:

```bash
# Follow logs
docker-compose logs -f chronicon-watch

# Last 100 lines
docker-compose logs --tail=100 chronicon-watch

# Since timestamp
docker-compose logs --since=2023-10-14T12:00:00 chronicon-watch
```

## Management

### Stop container
```bash
docker-compose stop
```

### Restart container
```bash
docker-compose restart
```

### Update to latest version
```bash
docker-compose pull
docker-compose up -d
```

### Remove container
```bash
docker-compose down
```

### Clean up (removes volumes)
```bash
docker-compose down -v
```

## Kubernetes Deployment

Example Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronicon-watch
spec:
  replicas: 1
  selector:
    matchLabels:
      app: chronicon-watch
  template:
    metadata:
      labels:
        app: chronicon-watch
    spec:
      containers:
      - name: chronicon-watch
        image: chronicon-watch:latest
        ports:
        - containerPort: 8080
          name: health
        volumeMounts:
        - name: archives
          mountPath: /archives
        - name: config
          mountPath: /home/chronicon/.chronicon.toml
          subPath: .chronicon.toml
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 60
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "500m"
            memory: "512Mi"
      volumes:
      - name: archives
        persistentVolumeClaim:
          claimName: chronicon-archives
      - name: config
        configMap:
          name: chronicon-config
```

## Troubleshooting

### Container exits immediately
- Check logs: `docker-compose logs chronicon-watch`
- Verify archive database exists: `ls -la archives/archive.db`
- Ensure initial archive was created

### Health check failing
- Check endpoint: `curl http://localhost:8080/health`
- View container status: `docker ps`
- Check logs for errors: `docker-compose logs --tail=50 chronicon-watch`

### Git push failing
- Verify SSH key is mounted and has correct permissions
- Test git connection: `docker-compose exec chronicon-watch ssh -T git@github.com`
- Check git configuration in archives directory

### High resource usage
- Reduce polling frequency in configuration
- Adjust resource limits in docker-compose.yml
- Monitor with: `docker stats chronicon-watch`

## Security Considerations

1. **Non-root user**: Container runs as non-root user `chronicon` (UID 1000)
2. **Read-only config**: Mount configuration as read-only (`:ro`)
3. **SSH key permissions**: Ensure SSH keys are properly secured (chmod 600)
4. **Network isolation**: Consider using Docker networks for isolation
5. **Resource limits**: Set appropriate CPU and memory limits
6. **Health monitoring**: Use health checks to detect issues early
