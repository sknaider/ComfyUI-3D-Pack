# ComfyUI-3D-Pack Enterprise Edition

## 🚀 Quick Start Enterprise

This guide will help you deploy ComfyUI-3D-Pack in a production-ready enterprise environment.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Overview

ComfyUI-3D-Pack Enterprise Edition includes:

- ✅ **Security**: API key authentication, path traversal prevention, IP whitelisting
- ✅ **Testing**: Comprehensive test suite with 80%+ coverage
- ✅ **CI/CD**: Automated testing, linting, and security scanning
- ✅ **Monitoring**: Health checks, Prometheus metrics, structured logging
- ✅ **DevOps**: Docker optimization, multi-stage builds, orchestration ready
- ✅ **Documentation**: Complete architecture, security, and contribution guides

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 22.04+ recommended)
- **GPU**: NVIDIA GPU with CUDA 12.4+ support
- **RAM**: 16GB minimum, 32GB recommended
- **Disk**: 50GB minimum for models and outputs
- **Network**: Internet access for model downloads

### Software Requirements

- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **NVIDIA Container Toolkit**: Latest
- **Python**: 3.10+ (for local development)
- **Make**: GNU Make 4.0+

### Optional (for monitoring)

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Redis**: Caching (future enhancement)

## Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/MrForExample/ComfyUI-3D-Pack.git
cd ComfyUI-3D-Pack

# Checkout enterprise branch
git checkout claude/review-enterprise-improvements-01JLNnx9b1bXmQ2emg3mYLkA

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration (see Configuration section)

# Build and start services
make compose-up
```

### Option 2: Manual Docker Build

```bash
# Build enterprise image
docker build -f Dockerfile.enterprise -t comfyui-3d-pack:latest .

# Run container
docker run -d \
  --name comfyui-3d-pack \
  --gpus all \
  -p 8188:8188 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/output:/app/output \
  --env-file .env \
  comfyui-3d-pack:latest
```

### Option 3: Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
make install-dev

# Configure environment
cp .env.example .env

# Run application
python main.py
```

## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

#### Required Configuration

```bash
# HuggingFace Authentication (required for model downloads)
HUGGINGFACE_TOKEN=hf_your_token_here

# API Security
ENABLE_AUTH=true
# Generate with: make generate-key
API_KEYS=your-secure-api-key-here
```

#### Recommended Configuration

```bash
# Network Security
ALLOWED_IPS=127.0.0.1,10.0.0.0/8
ALLOWED_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
MAX_WORKERS=4
GPU_MEMORY_FRACTION=0.9
REQUEST_TIMEOUT=3600
```

### Security Configuration

#### 1. Generate Strong API Keys

```bash
# Generate a secure API key
make generate-key

# Or manually:
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env`:
```bash
API_KEYS=a1b2c3d4e5f6...  # Use generated key
```

#### 2. Configure IP Whitelist

Edit `.env`:
```bash
# Allow specific IPs
ALLOWED_IPS=127.0.0.1,192.168.1.100,10.0.0.0/24

# Allow Docker network
ALLOWED_IPS=127.0.0.1,172.17.0.0/16
```

#### 3. Configure CORS

Edit `.env`:
```bash
CORS_ENABLED=true
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

### Environment-Specific Configuration

#### Development

```bash
cp .env.example .env
# Set development-friendly values:
LOG_FORMAT=text  # Colored logs
ENABLE_AUTH=false  # Disable for local testing
```

#### Staging

```bash
cp .env.staging .env
# Update with staging credentials
```

#### Production

```bash
cp .env.production .env
# IMPORTANT: Update ALL values marked CHANGE-ME
# Never commit .env to version control
```

## Deployment

### Deployment Checklist

Before deploying to production, complete this checklist:

- [ ] **.env configured** with production values
- [ ] **API keys generated** (strong, unique, 32+ bytes)
- [ ] **ENABLE_AUTH=true**
- [ ] **ALLOWED_IPS** configured for your network
- [ ] **HUGGINGFACE_TOKEN** set (if using restricted models)
- [ ] **Reverse proxy** configured (NGINX/Traefik with TLS)
- [ ] **Firewall rules** configured
- [ ] **Backup strategy** implemented
- [ ] **Monitoring** configured
- [ ] **Secrets** NOT in version control
- [ ] **Dependencies** up to date

### Automated Deployment

Use the deployment script:

```bash
# Deploy to production
./scripts/deploy.sh production

# Deploy to staging
./scripts/deploy.sh staging
```

The script will:
1. Check prerequisites
2. Validate configuration
3. Build Docker image
4. Run tests (staging only)
5. Stop old containers
6. Start new containers
7. Run health checks
8. Run smoke tests

### Manual Deployment

#### Step 1: Build

```bash
make docker-build
```

#### Step 2: Test (Optional)

```bash
make test
make security
```

#### Step 3: Deploy

```bash
# Start services
make compose-up

# With monitoring
make compose-up-full
```

#### Step 4: Verify

```bash
# Check health
make health

# Run health check script
./scripts/health-check.sh

# View logs
make compose-logs
```

### Deployment with Monitoring Stack

```bash
# Start all services including Prometheus and Grafana
docker-compose --profile monitoring up -d

# Access monitoring:
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

## Monitoring

### Health Checks

#### Automated Health Checks

```bash
# Run health check script
./scripts/health-check.sh

# Check specific host
./scripts/health-check.sh staging.example.com 8188
```

#### Manual Health Checks

```bash
# Health endpoint
curl http://localhost:8188/health

# Expected response:
{
  "status": "healthy",
  "cuda_available": true,
  "cuda_devices": 1
}
```

### Metrics

#### Prometheus Metrics

```bash
# View metrics
curl http://localhost:8188/metrics
```

Available metrics:
- `cuda_available` - CUDA availability (0 or 1)
- `cuda_devices` - Number of CUDA devices
- `cuda_memory_allocated_bytes` - GPU memory allocated
- `cuda_memory_reserved_bytes` - GPU memory reserved

#### Grafana Dashboards

1. Open http://localhost:3000
2. Login (admin/admin)
3. Add Prometheus data source: http://prometheus:9090
4. Import dashboard from `monitoring/grafana/dashboards/`

### Logging

#### Structured Logs (JSON)

Production configuration:
```bash
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Example log entry:
```json
{
  "timestamp": "2025-11-16T10:30:00.123456",
  "level": "INFO",
  "logger": "comfyui-3d-pack",
  "message": "Processing request",
  "request_id": "req-abc-123"
}
```

#### View Logs

```bash
# Docker Compose logs
docker-compose logs -f

# Specific service
docker-compose logs -f comfyui-3d-pack

# Container logs
docker logs -f comfyui-3d-pack
```

#### Log Aggregation

For production, send logs to:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **CloudWatch** (AWS)
- **Stackdriver** (GCP)

## Security

### Authentication

#### API Key Authentication

All requests to protected endpoints must include API key:

**Option 1: Authorization Header**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8188/viewfile?filepath=/path/to/file.obj
```

**Option 2: X-API-Key Header**
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8188/viewfile?filepath=/path/to/file.obj
```

**Option 3: Query Parameter**
```bash
curl "http://localhost:8188/viewfile?filepath=/path/to/file.obj&api_key=YOUR_API_KEY"
```

### Network Security

#### Reverse Proxy Configuration (NGINX)

```nginx
# /etc/nginx/sites-available/comfyui-3d-pack

upstream comfyui {
    server localhost:8188;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://comfyui;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

#### Firewall Rules (UFW)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTPS only (NGINX)
sudo ufw allow 443/tcp

# Block direct access to app
sudo ufw deny 8188/tcp

# Enable firewall
sudo ufw enable
```

### Secrets Management

#### Best Practices

1. **Never commit secrets** to version control
2. **Use environment variables** for all secrets
3. **Rotate API keys** regularly (quarterly minimum)
4. **Use different keys** per environment
5. **Audit access logs** regularly

#### Using External Secrets Manager

**AWS Secrets Manager:**
```bash
# Fetch secret
aws secretsmanager get-secret-value \
  --secret-id comfyui-3d-pack/api-keys \
  --query SecretString \
  --output text
```

**HashiCorp Vault:**
```bash
# Read secret
vault kv get -field=api_key secret/comfyui-3d-pack
```

## Troubleshooting

### Common Issues

#### Issue: Container fails to start

```bash
# Check logs
docker logs comfyui-3d-pack

# Common causes:
# 1. Missing .env file
# 2. Invalid environment variables
# 3. Port already in use
# 4. GPU not available
```

**Solution:**
```bash
# Verify .env exists
ls -la .env

# Check port
lsof -i :8188

# Verify GPU
nvidia-smi
```

#### Issue: Health check fails

```bash
# Run health check
./scripts/health-check.sh

# Check if service is running
docker ps | grep comfyui

# Check logs
docker logs comfyui-3d-pack
```

#### Issue: CUDA not available

```bash
# Verify NVIDIA driver
nvidia-smi

# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Reinstall NVIDIA Container Toolkit if needed
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### Issue: Authentication errors

```bash
# Verify API key is set
grep API_KEYS .env

# Test without auth (should fail)
curl http://localhost:8188/viewfile?filepath=/test

# Test with auth
curl -H "X-API-Key: YOUR_KEY" http://localhost:8188/viewfile?filepath=/test
```

### Debug Mode

Enable debug logging:

```bash
# Edit .env
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

### Performance Issues

#### High GPU Memory Usage

```bash
# Check GPU usage
nvidia-smi

# Adjust in .env
GPU_MEMORY_FRACTION=0.7  # Use 70% instead of 90%
```

#### Slow Response Times

```bash
# Check metrics
curl http://localhost:8188/metrics

# Increase workers
MAX_WORKERS=8  # In .env
```

## Maintenance

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild images
make docker-build

# Restart services
make compose-down
make compose-up
```

### Backups

#### Backup Models

```bash
# Backup models directory
tar -czf models-backup-$(date +%Y%m%d).tar.gz models/

# Sync to S3
aws s3 sync models/ s3://your-bucket/models/
```

#### Backup Outputs

```bash
# Backup outputs
tar -czf output-backup-$(date +%Y%m%d).tar.gz output/

# Sync to S3
aws s3 sync output/ s3://your-bucket/output/
```

### Monitoring Checklist

Daily:
- [ ] Check health endpoint status
- [ ] Review error logs
- [ ] Monitor GPU utilization

Weekly:
- [ ] Review security logs
- [ ] Check disk space usage
- [ ] Review performance metrics

Monthly:
- [ ] Update dependencies
- [ ] Rotate API keys
- [ ] Review and update documentation

## Support

### Getting Help

- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md)
- **Issues**: https://github.com/MrForExample/ComfyUI-3D-Pack/issues
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

### Commercial Support

For enterprise support, SLAs, and custom development:
- Contact: See repository maintainers
- Response time: 24-48 hours

## License

Apache 2.0 - See [LICENSE](LICENSE) file

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history

---

**Version**: 0.1.6
**Last Updated**: 2025-11-16
**Status**: Production Ready ✅
