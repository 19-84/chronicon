# Kubernetes Deployment Guide

Deploy Chronicon on Kubernetes for scalable, production-grade forum archiving.

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured
- Persistent storage provisioner

## Quick Deploy

### One-Time Archive Job

Create `chronicon-job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: chronicon-archive
spec:
  template:
    spec:
      containers:
      - name: chronicon
        image: ghcr.io/yourusername/chronicon:alpine
        args:
          - archive
          - --urls
          - https://meta.discourse.org
          - --output-dir
          - /archives
        volumeMounts:
        - name: archives
          mountPath: /archives
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
      restartPolicy: Never
      volumes:
      - name: archives
        persistentVolumeClaim:
          claimName: chronicon-archives
  backoffLimit: 3
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: chronicon-archives
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

Deploy:

```bash
kubectl apply -f chronicon-job.yaml
kubectl logs -f job/chronicon-archive
```

## Scheduled Archiving with CronJob

For automatic periodic updates, use a CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: chronicon-daily
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: chronicon
            image: ghcr.io/yourusername/chronicon:alpine
            args:
              - update
              - --output-dir
              - /archives
            volumeMounts:
            - name: archives
              mountPath: /archives
            - name: config
              mountPath: /home/chronicon/.chronicon.toml
              subPath: .chronicon.toml
              readOnly: true
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "2Gi"
                cpu: "1000m"
          restartPolicy: OnFailure
          volumes:
          - name: archives
            persistentVolumeClaim:
              claimName: chronicon-archives
          - name: config
            configMap:
              name: chronicon-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: chronicon-config
data:
  .chronicon.toml: |
    [general]
    output_dir = "/archives"
    default_formats = ["html", "markdown"]

    [fetching]
    rate_limit_seconds = 0.5
    max_workers = 8

    [[sites]]
    url = "https://meta.discourse.org"
    nickname = "meta"
```

## Watch Mode Deployment

For continuous monitoring and updates:

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
      - name: chronicon
        image: ghcr.io/yourusername/chronicon:alpine
        args:
          - watch
          - start
          - --urls
          - https://meta.discourse.org
          - --output-dir
          - /archives
          - --interval
          - "3600"  # Check every hour
        ports:
        - containerPort: 8080
          name: health
        volumeMounts:
        - name: archives
          mountPath: /archives
        - name: config
          mountPath: /home/chronicon/.chronicon.toml
          subPath: .chronicon.toml
          readOnly: true
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
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: archives
        persistentVolumeClaim:
          claimName: chronicon-archives
      - name: config
        configMap:
          name: chronicon-config
---
apiVersion: v1
kind: Service
metadata:
  name: chronicon-health
spec:
  selector:
    app: chronicon-watch
  ports:
  - port: 8080
    targetPort: 8080
    name: health
```

### Monitoring Watch Mode

Check daemon status:

```bash
# View health endpoint
kubectl port-forward service/chronicon-health 8080:8080
curl http://localhost:8080/health

# View detailed metrics
curl http://localhost:8080/metrics

# Check logs
kubectl logs -f deployment/chronicon-watch
```

## Production Deployment with Ingress

Expose the HTML archive via Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: chronicon-archive
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: forums.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: chronicon-web
            port:
              number: 80
---
apiVersion: v1
kind: Service
metadata:
  name: chronicon-web
spec:
  selector:
    app: nginx-archive
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-archive
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx-archive
  template:
    metadata:
      labels:
        app: nginx-archive
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        volumeMounts:
        - name: archives
          mountPath: /usr/share/nginx/html
          subPath: html
          readOnly: true
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
      volumes:
      - name: archives
        persistentVolumeClaim:
          claimName: chronicon-archives
```

## StatefulSet for Multiple Sites

For managing multiple persistent archives:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: chronicon-sites
spec:
  serviceName: chronicon
  replicas: 3
  selector:
    matchLabels:
      app: chronicon
  template:
    metadata:
      labels:
        app: chronicon
    spec:
      containers:
      - name: chronicon
        image: ghcr.io/yourusername/chronicon:alpine
        args:
          - watch
          - start
          - --interval
          - "3600"
        volumeMounts:
        - name: archives
          mountPath: /archives
        - name: config
          mountPath: /home/chronicon/.chronicon.toml
          subPath: .chronicon.toml
          readOnly: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: config
        configMap:
          name: chronicon-config
  volumeClaimTemplates:
  - metadata:
      name: archives
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

## Backup Strategy

Set up automated backups of your archives:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: chronicon-backup
spec:
  schedule: "0 3 * * *"  # Daily at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: alpine:latest
            command:
            - sh
            - -c
            - |
              apk add --no-cache tar gzip
              cd /archives
              tar czf /backups/archive-$(date +%Y%m%d).tar.gz .
              # Keep only last 7 days
              find /backups -name "archive-*.tar.gz" -mtime +7 -delete
            volumeMounts:
            - name: archives
              mountPath: /archives
              readOnly: true
            - name: backups
              mountPath: /backups
          restartPolicy: OnFailure
          volumes:
          - name: archives
            persistentVolumeClaim:
              claimName: chronicon-archives
          - name: backups
            persistentVolumeClaim:
              claimName: chronicon-backups
```

## Monitoring and Observability

### Prometheus Metrics

Chronicon watch mode exposes metrics at `/metrics`:

```yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: chronicon-watch
spec:
  selector:
    matchLabels:
      app: chronicon-watch
  endpoints:
  - port: health
    path: /metrics
    interval: 30s
```

### Log Aggregation

Configure log shipping to your logging system:

```yaml
spec:
  template:
    spec:
      containers:
      - name: chronicon
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: LOG_FORMAT
          value: "json"  # For structured logging
```

## Scaling Considerations

- **CPU**: 1-2 cores recommended for concurrent operations
- **Memory**: 512MB-2GB depending on forum size and worker count
- **Storage**:
  - Small forums (<1000 topics): 1-5GB
  - Medium forums (1000-10000 topics): 5-20GB
  - Large forums (10000+ topics): 20GB+
- **Network**: Rate limiting respects forum server limits

## Security Hardening

```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: chronicon
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app=chronicon-watch
kubectl describe pod <pod-name>
kubectl logs -f <pod-name>
```

### Check PVC status

```bash
kubectl get pvc
kubectl describe pvc chronicon-archives
```

### Access container shell

```bash
kubectl exec -it <pod-name> -- sh
```

### View watch daemon status

```bash
kubectl port-forward deployment/chronicon-watch 8080:8080
curl http://localhost:8080/metrics | jq
```

## Additional Resources

For more Kubernetes deployment patterns:
- See the manifests above as starting templates
- Customize resource limits based on your forum size
- Review the Docker deployment guide for container best practices
- Consider using Helm charts for complex multi-site deployments
