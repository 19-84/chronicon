# Docker Security Hardening Guide for Chronicon

Comprehensive security hardening guide for deploying Chronicon in Docker containers.

## Table of Contents

- [Security Architecture](#security-architecture)
- [Threat Model](#threat-model)
- [Hardening Layers](#hardening-layers)
- [Security Checklist](#security-checklist)
- [Vulnerability Management](#vulnerability-management)
- [Incident Response](#incident-response)

## Security Architecture

### Defense in Depth

Chronicon containers implement multiple security layers:

```
┌─────────────────────────────────────────────┐
│ Layer 7: Monitoring & Alerting             │
│  - Health checks                            │
│  - Security scanning                        │
│  - Log aggregation                          │
├─────────────────────────────────────────────┤
│ Layer 6: Secrets Management                │
│  - Docker secrets                           │
│  - No secrets in images/logs                │
├─────────────────────────────────────────────┤
│ Layer 5: Network Isolation                 │
│  - Custom bridge network                    │
│  - Port restrictions                        │
│  - Localhost binding                        │
├─────────────────────────────────────────────┤
│ Layer 4: System Call Filtering             │
│  - Seccomp profile                          │
│  - AppArmor profile (optional)              │
├─────────────────────────────────────────────┤
│ Layer 3: Capability Restrictions            │
│  - Drop all capabilities                    │
│  - No privileged operations                 │
├─────────────────────────────────────────────┤
│ Layer 2: Filesystem Security                │
│  - Read-only root filesystem                │
│  - Minimal writable mounts                  │
│  - No setuid binaries                       │
├─────────────────────────────────────────────┤
│ Layer 1: Minimal Base                       │
│  - Alpine Linux (45MB)                      │
│  - Non-root user                            │
│  - No shell in production                   │
└─────────────────────────────────────────────┘
```

## Threat Model

### Assets to Protect

1. **Archive Data** - Forum posts, topics, user information
2. **Credentials** - SSH keys, API tokens (if any)
3. **System Resources** - CPU, memory, disk, network
4. **Host System** - Prevent container escape

### Threats

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Container Escape | Critical | Read-only FS, dropped capabilities, seccomp |
| Privilege Escalation | High | Non-root user, no-new-privileges |
| Resource Exhaustion | Medium | Resource limits, pids limit |
| Data Exfiltration | High | Network isolation, file permissions |
| Malicious Code Injection | High | Multi-stage build, verified base images |
| Supply Chain Attack | High | Image scanning, signed images |

## Hardening Layers

### Layer 1: Minimal Base (Alpine Linux)

**Configuration:**
```dockerfile
FROM alpine:3.19
RUN apk add --no-cache python3 git ca-certificates
```

**Security Benefits:**
- Minimal package count (~50 vs ~200)
- Smaller attack surface (45MB vs 130MB)
- Fewer CVEs to track
- Simpler update process

**Verification:**
```bash
# Check image size
docker images chronicon:alpine

# List installed packages
docker run --rm chronicon:alpine apk list -I

# Check for vulnerabilities
trivy image chronicon:alpine
```

### Layer 2: Filesystem Security

**Configuration:**
```yaml
read_only: true
tmpfs:
  - /tmp:noexec,nosuid,nodev,size=100m,mode=1777
  - /home/chronicon:noexec,nosuid,nodev,size=10m,mode=700
```

**Security Benefits:**
- Prevents malware persistence
- Blocks unauthorized modifications
- Limits tmp filesystem size
- Prevents execution from writable areas

**Verification:**
```bash
# Try to write to filesystem (should fail)
docker exec chronicon-test-watch touch /usr/bin/malware

# Check mount options
docker inspect chronicon-test-watch | jq '.[0].HostConfig.ReadonlyRootfs'
```

### Layer 3: Capability Restrictions

**Configuration:**
```yaml
cap_drop:
  - ALL
# Only add if absolutely needed:
# cap_add:
#   - NET_BIND_SERVICE  # For privileged ports <1024
```

**Security Benefits:**
- Prevents privileged operations
- Blocks raw socket creation
- Prevents device access
- Limits kernel interactions

**Verification:**
```bash
# Check capabilities
docker exec chronicon-test-watch capsh --print

# Should show no capabilities
```

### Layer 4: System Call Filtering (Seccomp)

**Configuration:**
```yaml
security_opt:
  - seccomp:seccomp.json
```

**Security Benefits:**
- Blocks dangerous syscalls (ptrace, mount, etc.)
- Allows only required operations
- Prevents kernel exploits
- Defense against 0-days

**Verification:**
```bash
# Check seccomp profile
docker inspect chronicon-test-watch | jq '.[0].HostConfig.SecurityOpt'

# Test blocked syscall
docker exec chronicon-test-watch strace ls  # Should fail
```

### Layer 5: Network Isolation

**Configuration:**
```yaml
networks:
  chronicon-prod:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"

ports:
  - "127.0.0.1:8080:8080"  # Localhost only
```

**Security Benefits:**
- Isolated from other containers
- No inter-container communication
- Limited external exposure
- Localhost binding prevents remote access

**Verification:**
```bash
# Check network isolation
docker network inspect chronicon-prod

# Check port binding
netstat -tlnp | grep 8080
```

### Layer 6: Secrets Management

**Configuration (Docker Secrets):**
```yaml
secrets:
  chronicon_ssh_key:
    file: ./secrets/id_rsa

services:
  chronicon-watch:
    secrets:
      - chronicon_ssh_key
```

**Security Benefits:**
- Secrets not in environment variables
- Secrets not in logs
- Secrets encrypted at rest
- Secrets only in memory

**Verification:**
```bash
# Check no secrets in env
docker exec chronicon-test-watch env | grep -i key

# Check no secrets in logs
docker logs chronicon-test-watch | grep -i secret
```

### Layer 7: Monitoring & Alerting

**Components:**
- Health check endpoint (HTTP)
- Status file monitoring
- Log aggregation
- Vulnerability scanning
- Audit logging

**Implementation:**
```bash
# Automated scanning (daily)
0 2 * * * trivy image chronicon:alpine --severity HIGH,CRITICAL

# Health monitoring
*/5 * * * * curl -f http://localhost:8080/health || alert-team

# Log monitoring
# Use: ELK, Loki, Splunk, etc.
```

## Security Checklist

### Pre-Deployment

- [ ] **Image Scanning**: Run `trivy image chronicon:alpine`
- [ ] **Secrets Review**: No secrets in images or environment
- [ ] **Configuration Review**: All settings appropriate for production
- [ ] **Network Configuration**: Isolated network, minimal exposure
- [ ] **Resource Limits**: CPU, memory, disk limits set
- [ ] **User Verification**: Running as non-root (UID 1000)
- [ ] **Filesystem**: Read-only root filesystem enabled
- [ ] **Capabilities**: All capabilities dropped
- [ ] **Seccomp**: Custom profile applied
- [ ] **Health Checks**: Configured and tested

### Post-Deployment

- [ ] **Monitor Health**: Health endpoint responding correctly
- [ ] **Check Logs**: No errors or security warnings
- [ ] **Verify Permissions**: All files have correct ownership
- [ ] **Test Failover**: Container restarts automatically on failure
- [ ] **Audit Access**: Review who has access to host system
- [ ] **Monitor Resources**: CPU/memory within expected ranges
- [ ] **Check Updates**: Base image and dependencies up to date
- [ ] **Backup Verification**: Backups working and tested

### Ongoing Maintenance

- [ ] **Weekly**: Review logs for anomalies
- [ ] **Monthly**: Scan images for new vulnerabilities
- [ ] **Monthly**: Update base images and dependencies
- [ ] **Quarterly**: Penetration testing
- [ ] **Quarterly**: Review and update security policies
- [ ] **Annually**: Full security audit

## Vulnerability Management

### Scanning Images

```bash
# Trivy (comprehensive)
trivy image chronicon:alpine --severity HIGH,CRITICAL

# Docker scan (requires Docker Hub login)
docker scan chronicon:alpine

# Grype (alternative)
grype chronicon:alpine
```

### Updating Images

```bash
# Rebuild with latest base
docker build --pull --no-cache -f Dockerfile.alpine -t chronicon:alpine .

# Verify improvements
trivy image chronicon:alpine
```

### Response Process

**High/Critical CVE Found:**
1. **Assess**: Determine if vulnerability affects Chronicon
2. **Mitigate**: Apply workaround if available
3. **Update**: Rebuild image with patched dependencies
4. **Test**: Run full test suite
5. **Deploy**: Rolling update to production
6. **Verify**: Rescan to confirm CVE resolved

## Incident Response

### Container Compromise Suspected

**1. Isolate:**
```bash
# Disconnect from network
docker network disconnect chronicon-prod chronicon-test-watch

# Stop container
docker stop chronicon-test-watch
```

**2. Investigate:**
```bash
# Export logs
docker logs chronicon-test-watch > incident-logs.txt

# Export container filesystem
docker export chronicon-test-watch > incident-filesystem.tar

# Check for modifications
docker diff chronicon-test-watch
```

**3. Remediate:**
```bash
# Remove compromised container
docker rm chronicon-test-watch

# Pull clean image
docker pull chronicon:alpine-watch

# Redeploy with security review
docker-compose -f docker-compose.prod.yml up -d
```

**4. Review:**
- Analyze logs for attack vector
- Review security configurations
- Update hardening as needed
- Document lessons learned

### Data Breach Response

**If archive data is compromised:**

1. **Contain**: Stop all containers
2. **Assess**: Determine extent of breach
3. **Notify**: Inform stakeholders
4. **Restore**: From known-good backup
5. **Harden**: Apply additional security measures
6. **Monitor**: Enhanced monitoring for period

## Compliance

### CIS Docker Benchmark

Chronicon Alpine containers align with CIS Docker Benchmark:

- ✅ 4.1: Create a user for container
- ✅ 5.1: Do not disable AppArmor
- ✅ 5.2: Verify SELinux security options
- ✅ 5.3: Restrict Linux kernel capabilities
- ✅ 5.4: Do not use privileged containers
- ✅ 5.5: Do not mount sensitive host dirs
- ✅ 5.6: Do not run SSH within containers
- ✅ 5.7: Do not map privileged ports
- ✅ 5.10: Limit memory usage
- ✅ 5.11: Set CPU priority appropriately
- ✅ 5.12: Mount container's root filesystem as read-only
- ✅ 5.25: Restrict container from acquiring additional privileges
- ✅ 5.28: Use PIDs cgroup limit

### NIST Guidelines

Aligned with NIST SP 800-190 (Application Container Security Guide):

- ✅ Image security and integrity
- ✅ Registry security (sign and scan images)
- ✅ Orchestrator security (resource limits)
- ✅ Container runtime security (seccomp, capabilities)
- ✅ Host OS security (minimal, updated)

## Advanced Hardening

### AppArmor Profile

Create custom AppArmor profile (Linux only):

```bash
# /etc/apparmor.d/chronicon
#include <tunables/global>

profile chronicon flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/python>

  /archives/** rw,
  /tmp/** rw,
  /home/chronicon/** rw,

  # Python
  /opt/venv/** r,
  /usr/bin/python3 ix,

  # Git
  /usr/bin/git ix,

  # Deny everything else
  /** deny,
}
```

```bash
# Load profile
sudo apparmor_parser -r /etc/apparmor.d/chronicon

# Enable in docker-compose
security_opt:
  - apparmor:chronicon
```

### User Namespace Remapping

Map container UID to unprivileged host UID:

```json
// /etc/docker/daemon.json
{
  "userns-remap": "default"
}
```

```bash
# Restart Docker
sudo systemctl restart docker

# Containers now run with remapped UIDs
```

### gVisor Runtime (Advanced)

Use gVisor for additional kernel isolation:

```bash
# Install gVisor
curl -fsSL https://gvisor.dev/archive.key | sudo apt-key add -
sudo apt-get install -y runsc

# Configure Docker
sudo runsc install
sudo systemctl restart docker

# Use in docker-compose
runtime: runsc
```

## Security Testing

### Automated Testing

```bash
# Security scan
docker scan chronicon:alpine

# Vulnerability scan
trivy image chronicon:alpine --severity HIGH,CRITICAL

# CIS Benchmark
docker-bench-security
```

### Manual Testing

```bash
# 1. Verify non-root user
docker exec chronicon-test-watch whoami
# Expected: chronicon

# 2. Verify no shell access
docker exec chronicon-test-watch sh
# Expected: Error (no shell)

# 3. Verify read-only filesystem
docker exec chronicon-test-watch touch /test
# Expected: Error (read-only)

# 4. Verify capabilities
docker exec chronicon-test-watch capsh --print
# Expected: No capabilities

# 5. Verify no privileged operations
docker exec chronicon-test-watch mount /dev/sda1 /mnt
# Expected: Error (operation not permitted)

# 6. Check for secrets
docker history chronicon:alpine | grep -i password
# Expected: No results

# 7. Verify resource limits
docker inspect chronicon-test-watch | jq '.[0].HostConfig.Memory'
# Expected: Limit configured
```

### Penetration Testing

```bash
# Test container escape attempts
# (Use in isolated environment only)

# 1. Try to access host filesystem
docker exec chronicon-test-watch ls /host

# 2. Try to modify system files
docker exec chronicon-test-watch chmod 777 /etc/passwd

# 3. Try to execute privileged operations
docker exec chronicon-test-watch chroot /

# 4. Try network access to other containers
docker exec chronicon-test-watch curl http://other-container

# All should fail
```

## Vulnerability Management

### Image Scanning Pipeline

```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -f examples/docker/Dockerfile.alpine -t chronicon:alpine .

      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: chronicon:alpine
          severity: HIGH,CRITICAL
          exit-code: 1

      - name: Scan with Grype
        uses: anchore/scan-action@v3
        with:
          image: chronicon:alpine
          severity-cutoff: high
```

### Update Schedule

| Component | Update Frequency | Method |
|-----------|------------------|--------|
| Alpine Base | Monthly | Rebuild image |
| Python | Monthly | Update in requirements |
| Dependencies | Weekly | `pip list --outdated` |
| Security Patches | Within 24h | Emergency rebuild |

### CVE Response

**Critical CVE (Score ≥9.0):**
- Response time: 4 hours
- Emergency patch and deployment
- Notify all users

**High CVE (Score 7.0-8.9):**
- Response time: 24 hours
- Scheduled patch and deployment
- Update security advisory

**Medium/Low CVE:**
- Response time: 1 week
- Include in next regular update
- Document in changelog

## Incident Response

### Preparation

**Before an Incident:**
1. Document incident response plan
2. Identify security contacts
3. Set up monitoring and alerting
4. Create backup/restore procedures
5. Test failover scenarios

**Response Team:**
- Security Lead: Primary responder
- DevOps: Infrastructure and deployment
- Developer: Code analysis and patches
- Management: Communications and decisions

### Detection

**Signs of Compromise:**
- Unexpected resource usage
- Failed health checks
- Unusual log entries
- Network anomalies
- File modifications in read-only areas

**Monitoring Tools:**
```bash
# Resource anomalies
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" --no-stream

# Log anomalies
docker logs chronicon-test-watch | grep -E "(error|fail|unauthorized|denied)"

# Network anomalies
docker exec chronicon-test-watch netstat -tuln
```

### Containment

**Immediate Actions:**
```bash
# 1. Isolate network
docker network disconnect chronicon-prod chronicon-watch

# 2. Pause container (preserves state for forensics)
docker pause chronicon-watch

# 3. Export logs
docker logs chronicon-watch > /secure/logs/incident-$(date +%Y%m%d-%H%M%S).log

# 4. Export filesystem
docker export chronicon-watch > /secure/forensics/container-$(date +%Y%m%d-%H%M%S).tar
```

### Eradication

**Remove Threat:**
```bash
# 1. Stop and remove container
docker stop chronicon-watch
docker rm chronicon-watch

# 2. Remove potentially compromised image
docker rmi chronicon:alpine-watch

# 3. Pull/rebuild clean image
docker build --pull --no-cache -f Dockerfile.alpine-watch -t chronicon:alpine-watch .

# 4. Scan new image
trivy image chronicon:alpine-watch
```

### Recovery

**Restore Operations:**
```bash
# 1. Verify clean image
docker scan chronicon:alpine-watch

# 2. Restore from backup (if needed)
docker run --rm \
  -v /backup/archives:/backup:ro \
  -v ./archives:/archives \
  chronicon:alpine \
  sh -c "cp -r /backup/* /archives/"

# 3. Redeploy with enhanced security
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify health
curl http://localhost:8080/health
```

### Lessons Learned

**Post-Incident Actions:**
1. Root cause analysis
2. Update security configurations
3. Enhance monitoring
4. Document incident
5. Train team on findings
6. Update incident response plan

## Security Maintenance

### Daily

```bash
# Check health
curl -f http://localhost:8080/health

# Review logs
docker logs --since=24h chronicon-watch | grep -i error
```

### Weekly

```bash
# Check resource usage
docker stats chronicon-watch --no-stream

# Review updates
docker pull alpine:3.19
docker images --filter dangling=true
```

### Monthly

```bash
# Scan for vulnerabilities
trivy image chronicon:alpine --severity HIGH,CRITICAL

# Update base image
docker build --pull -f Dockerfile.alpine -t chronicon:alpine .

# Review and rotate logs
docker-compose -f docker-compose.prod.yml logs --tail=1000 > archive-logs-$(date +%Y%m).log
```

### Quarterly

```bash
# Full security audit
docker-bench-security

# Penetration test
# (Use authorized testing tools)

# Review and update
# - Security policies
# - Incident response plan
# - Access controls
# - Secrets rotation
```

## Compliance Documentation

### Audit Trail

**Required Documentation:**
1. **Deployment History**: When, what, who
2. **Security Scans**: Results and remediations
3. **Incidents**: All security events
4. **Changes**: Configuration modifications
5. **Access**: Who has access to what

**Implementation:**
```bash
# Git commit all deployments
git log --grep="deploy" --format="%h %ad %s" > audit-deployments.log

# Save scan results
trivy image chronicon:alpine -f json > scans/scan-$(date +%Y%m%d).json

# Log all docker commands
export PROMPT_COMMAND='history -a; echo "$(date +"%Y-%m-%d %H:%M:%S") $(whoami) $(history 1)" >> /var/log/docker-commands.log'
```

## References

### Standards
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST SP 800-190](https://csrc.nist.gov/publications/detail/sp/800-190/final)
- [OWASP Container Security](https://owasp.org/www-project-docker-top-10/)

### Tools
- [Trivy](https://github.com/aquasecurity/trivy) - Vulnerability scanner
- [Docker Bench](https://github.com/docker/docker-bench-security) - Security audit
- [Grype](https://github.com/anchore/grype) - Vulnerability scanner
- [Clair](https://github.com/quay/clair) - Static analysis

### Documentation
- [Docker Security](https://docs.docker.com/engine/security/)
- [Alpine Security](https://alpinelinux.org/security/)
- [Seccomp](https://docs.docker.com/engine/security/seccomp/)

## Support

### Security Issues

**Report security vulnerabilities:**
- Email: security@example.com (private)
- PGP Key: [link to public key]
- Response time: 24 hours

**DO NOT** report security issues publicly on GitHub.

### Security Questions

For security-related questions:
- Documentation: This guide
- Community: GitHub Discussions (for non-sensitive topics)
- Professional: security@example.com

## Changelog

### 2025-11-12
- Initial security hardening guide
- Alpine-based containers with full security features
- Seccomp profile implementation
- Compliance documentation

---

**Last Updated**: 2025-11-12
**Security Level**: Maximum
**Compliance**: CIS Benchmark, NIST SP 800-190, OWASP Top 10
