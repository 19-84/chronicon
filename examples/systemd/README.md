# Systemd Service for Chronicon Watch

This directory contains a systemd service file for running Chronicon watch mode as a system service.

## Installation

1. **Create chronicon user** (optional but recommended):
   ```bash
   sudo useradd -r -s /bin/false -d /var/lib/chronicon chronicon
   sudo mkdir -p /var/lib/chronicon/archives
   sudo chown -R chronicon:chronicon /var/lib/chronicon
   ```

2. **Install Chronicon**:
   ```bash
   # Using uv
   uv tool install chronicon

   # Or using pip
   pip install chronicon
   ```

3. **Create initial archive**:
   ```bash
   sudo -u chronicon chronicon archive \
     --urls https://discourse.example.com \
     --output-dir /var/lib/chronicon/archives
   ```

4. **Install service file**:
   ```bash
   sudo cp chronicon-watch.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

5. **Configure** (optional):
   Create `/var/lib/chronicon/.chronicon.toml` with your settings:
   ```toml
   [continuous]
   polling_interval_minutes = 10
   max_consecutive_errors = 5

   [continuous.git]
   enabled = true
   auto_commit = true
   push_to_remote = true
   remote_name = "origin"
   branch = "main"
   ```

6. **Enable and start**:
   ```bash
   sudo systemctl enable chronicon-watch
   sudo systemctl start chronicon-watch
   ```

## Management

### Check status
```bash
sudo systemctl status chronicon-watch
```

### View logs
```bash
# Follow live logs
sudo journalctl -u chronicon-watch -f

# Recent logs
sudo journalctl -u chronicon-watch -n 100

# Logs since last boot
sudo journalctl -u chronicon-watch -b
```

### Stop service
```bash
sudo systemctl stop chronicon-watch
```

### Restart service
```bash
sudo systemctl restart chronicon-watch
```

### Disable service
```bash
sudo systemctl disable chronicon-watch
```

## Customization

Edit the service file to customize:

- **User/Group**: Change `User` and `Group` to run as different user
- **Working Directory**: Change `WorkingDirectory` to your archive location
- **Memory Limit**: Adjust `MemoryMax` based on your forum size
- **CPU Limit**: Adjust `CPUQuota` (200% = 2 cores)
- **Restart Policy**: Modify `RestartSec` to change restart delay

## Monitoring

The service can be monitored using:

1. **systemd status**:
   ```bash
   sudo systemctl status chronicon-watch
   ```

2. **Chronicon status command**:
   ```bash
   sudo -u chronicon chronicon watch status --output-dir /var/lib/chronicon/archives
   ```

3. **Health check endpoint** (if enabled):
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:8080/metrics
   ```

## Troubleshooting

### Service won't start
- Check logs: `sudo journalctl -u chronicon-watch -n 50`
- Verify permissions: `ls -la /var/lib/chronicon`
- Test command manually: `sudo -u chronicon chronicon watch --output-dir /var/lib/chronicon/archives`

### Service keeps restarting
- Check for errors: `sudo journalctl -u chronicon-watch | grep -i error`
- Verify archive database exists: `ls -la /var/lib/chronicon/archives/archive.db`
- Check network connectivity to Discourse forum

### High resource usage
- Reduce polling frequency in config
- Disable text formats you don't need
- Adjust `MemoryMax` and `CPUQuota` in service file
