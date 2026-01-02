# Deployment Guide

Complete guide for deploying the F1 Race Strategy Workbench to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Local Deployment](#local-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Monitoring](#monitoring)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Disk | 10 GB | 50 GB |

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Runtime |
| Node.js | 18+ | Frontend build |
| Docker | 24+ | Containerization |
| PostgreSQL | 15+ | Database (optional) |
| Redis | 7+ | Caching (optional) |

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RSW_ENV` | Yes | `development` | Environment (development/staging/production) |
| `RSW_PORT` | No | `8000` | Server port |
| `RSW_HOST` | No | `0.0.0.0` | Server host |
| `RSW_LOG_LEVEL` | No | `INFO` | Logging level |
| `RSW_DEBUG` | No | `false` | Debug mode |
| `RSW_WORKERS` | No | `4` | Uvicorn workers |

### Optional Services

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string |
| `OPENF1_BASE_URL` | `https://api.openf1.org/v1` | OpenF1 API URL |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `RSW_AUTH_ENABLED` | `false` | Enable authentication |
| `JWT_SECRET` | - | JWT signing secret (required if auth enabled) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `60` | Token expiration |

### Example .env File

```env
# Environment
RSW_ENV=production
RSW_PORT=8000
RSW_LOG_LEVEL=INFO

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost:5432/rsw
REDIS_URL=redis://localhost:6379/0

# Authentication
RSW_AUTH_ENABLED=true
JWT_SECRET=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# OpenF1
OPENF1_BASE_URL=https://api.openf1.org/v1
```

---

## Local Deployment

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python run.py --prod
```

### Production Server

```bash
# Using Uvicorn directly
uvicorn rsw.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --access-log \
  --proxy-headers
```

### With Gunicorn

```bash
gunicorn rsw.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile -
```

### Systemd Service

`/etc/systemd/system/rsw.service`:
```ini
[Unit]
Description=Race Strategy Workbench
After=network.target

[Service]
User=rsw
Group=rsw
WorkingDirectory=/opt/rsw
Environment="PATH=/opt/rsw/.venv/bin"
EnvironmentFile=/opt/rsw/.env
ExecStart=/opt/rsw/.venv/bin/uvicorn rsw.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable rsw
sudo systemctl start rsw
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY run.py .

# Environment
ENV PYTHONPATH=/app/src
ENV RSW_ENV=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

# Run
CMD ["uvicorn", "rsw.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

`docker-compose.yml`:
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - RSW_ENV=production
      - DATABASE_URL=postgresql://rsw:password@db:5432/rsw
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=rsw
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=rsw
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Build and Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

---

## Kubernetes Deployment

### Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rsw
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rsw-api
  namespace: rsw
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rsw-api
  template:
    metadata:
      labels:
        app: rsw-api
    spec:
      containers:
        - name: rsw-api
          image: rsw:latest
          ports:
            - containerPort: 8000
          env:
            - name: RSW_ENV
              value: "production"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: rsw-secrets
                  key: database-url
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

### Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: rsw-api
  namespace: rsw
spec:
  selector:
    app: rsw-api
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rsw-ingress
  namespace: rsw
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.racestrategy.dev
      secretName: rsw-tls
  rules:
    - host: api.racestrategy.dev
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: rsw-api
                port:
                  number: 80
```

### Deploy

```bash
kubectl apply -f k8s/
```

---

## Cloud Deployment

### AWS (ECS)

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO
docker build -t rsw .
docker tag rsw:latest $ECR_REPO/rsw:latest
docker push $ECR_REPO/rsw:latest

# Deploy with Copilot
copilot deploy
```

### Google Cloud (Cloud Run)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/rsw

# Deploy
gcloud run deploy rsw \
  --image gcr.io/$PROJECT_ID/rsw \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --allow-unauthenticated
```

### Azure (Container Apps)

```bash
# Build and push to ACR
az acr build --registry $ACR_NAME --image rsw:latest .

# Deploy
az containerapp create \
  --name rsw \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT \
  --image $ACR_NAME.azurecr.io/rsw:latest \
  --target-port 8000 \
  --ingress external
```

---

## Monitoring

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Full health check |
| `GET /health/live` | Liveness probe |
| `GET /health/ready` | Readiness probe |

### Prometheus Metrics

Expose at `/metrics`:
- `http_requests_total` — Request count
- `http_request_duration_seconds` — Request latency
- `http_requests_in_progress` — Active requests
- `websocket_connections` — Active WebSocket connections

### Grafana Dashboard

Import dashboard ID: `12345` (example)

### Logging

Structured JSON logging:
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "level": "INFO",
  "logger": "rsw.api",
  "message": "Request completed",
  "request_id": "req_123",
  "method": "GET",
  "path": "/api/sessions",
  "status_code": 200,
  "duration_ms": 45
}
```

---

## Security

### SSL/TLS

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.racestrategy.dev;

    ssl_certificate /etc/ssl/certs/rsw.crt;
    ssl_certificate_key /etc/ssl/private/rsw.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Security Headers

```python
# Automatically added by FastAPI middleware
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### Rate Limiting

```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://localhost:8000;
}
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### Database Connection Failed

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check logs
docker-compose logs db
```

#### High Memory Usage

```bash
# Check memory
docker stats

# Reduce workers
uvicorn rsw.main:app --workers 2
```

### Log Locations

| Component | Location |
|-----------|----------|
| Application | stdout/stderr |
| Nginx | `/var/log/nginx/` |
| PostgreSQL | `/var/log/postgresql/` |
| Systemd | `journalctl -u rsw` |

---

## Next Steps

- [Monitoring Setup](MONITORING.md) — Detailed monitoring guide
- [Disaster Recovery](DISASTER_RECOVERY.md) — Backup and restore
- [Scaling Guide](SCALING.md) — Horizontal scaling

---
**Next:** [[Troubleshooting]]
