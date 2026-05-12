# DevOps & CI/CD Specialist

## CI/CD Pipeline Design

### Pipeline Stages
```
┌─────────────────────────────────────────────────────────────┐
│                     CI/CD Pipeline                          │
├─────────┬─────────┬─────────┬─────────┬─────────┬───────────┤
│  Build  │  Test   │   Sec   │  Deploy │ Verify  │  Monitor  │
│         │         │  Scan   │         │         │           │
├─────────┼─────────┼─────────┼─────────┼─────────┼───────────┤
│Compile  │ Unit    │ SAST    │ Dev     │Smoke    │Metrics    │
│Package  │Integra  │ SCA     │ Staging │E2E      │Logs       │
│Artifact │Coverage │ Secrets │ Prod    │Health   │Alerts     │
│         │Perf     │ DAST*   │Rollback │         │Dashboards │
└─────────┴─────────┴─────────┴─────────┴─────────┴───────────┘
* DAST: Dynamic Application Security Testing
```

### GitHub Actions Example
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Lint with Ruff
        run: |
          pip install ruff
          ruff check .
      
      - name: Type check with mypy
        run: |
          pip install mypy
          mypy app/
      
      - name: Security audit
        run: |
          pip install safety bandit
          safety check || true
          bandit -r app/

  test:
    name: Test Suite
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest tests/ \
            --cov=app \
            --cov-report=xml \
            --cov-fail-under=80 \
            -v

  build:
    name: Build & Push
    runs-on: ubuntu-latest
    needs: [quality, test]
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            PYTHON_VERSION=${{ env.PYTHON_VERSION }}

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build
    environment:
      name: staging
      url: https://staging.example.com
    
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/api \
            api=ghcr.io/${{ github.repository }}:${{ github.sha }} \
            -n staging
      
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/api \
            -n staging \
            --timeout=300s

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com
    
    steps:
      - name: Blue-Green Deploy
        run: |
          # Deploy to new green deployment
          kubectl apply -f k8s/green.yaml
          
          # Wait for health checks
          kubectl rollout status deployment/api-green -n production
          
          # Switch traffic
          kubectl patch service/api \
            -p '{"spec":{"selector":{"version":"green"}}}' \
            -n production
          
          # Monitor for errors (5 minutes)
          sleep 300
          
          # Delete old blue deployment
          kubectl delete deployment/api-blue -n production
```

## Docker Best Practices

### Multi-stage Dockerfile
```dockerfile
# syntax=docker/dockerfile:1

# ---- Build Stage ----
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/opt/venv -r requirements.txt


# ---- Production Stage ----
FROM python:3.11-slim AS production

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup . .

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Development
```yaml
# docker-compose.yml
version: '3.9'

services:
  api:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://postgres:dev@db:5432/app
      - REDIS_URL=redis://redis:6379
      - DEBUG=1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

## Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels:
    app: api
    version: v2
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: api
        version: v2
    spec:
      serviceAccountName: api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: ghcr.io/example/api:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: api-secrets
                  key: database-url
          envFrom:
            - configMapRef:
                name: api-config
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            failureThreshold: 30
            periodSeconds: 10
```

## Monitoring & Observability

### Key Metrics to Track
- **RED Metrics**: Rate, Errors, Duration
- **USE Metrics**: Utilization, Saturation, Errors
- **Business Metrics**: Conversion, Revenue, Engagement

### Prometheus Metrics Example
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'api_request_duration_seconds',
    'API request latency',
    ['method', 'endpoint'],
    buckets=[.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)

# Business metrics
ACTIVE_USERS = Gauge(
    'active_users',
    'Number of active users'
)

ORDERS_COMPLETED = Counter(
    'orders_completed_total',
    'Total completed orders',
    ['payment_method']
)

# Usage in code
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```
