# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- WebSocket support for real-time streaming (planned)
- Advanced caching strategies (planned)
- Multi-model parallel inference (planned)

## [0.1.7] - 2025-11-16

### Added - Enterprise Features 🚀

#### Infrastructure & DevOps
- **Makefile** with 30+ commands for development and deployment
- **Deployment script** (`scripts/deploy.sh`) with automated validation and health checks
- **Health check script** (`scripts/health-check.sh`) for service monitoring
- **Backup script** (`scripts/backup.sh`) with S3 support and automated rotation
- **Log rotation script** (`scripts/rotate-logs.sh`) for log management
- **docker-compose.dev.yml** for local development environment
- Enhanced **docker-compose.yml** with monitoring stack (Prometheus, Grafana, Redis)

#### Kubernetes Support
- Complete Kubernetes manifests in `k8s/` directory:
  - Deployment with GPU support and resource limits
  - Service and headless service
  - Ingress with TLS and rate limiting
  - HorizontalPodAutoscaler for auto-scaling
  - PersistentVolumeClaims for models and outputs
  - ConfigMap and Secrets management
  - ServiceMonitor for Prometheus Operator
- Comprehensive Kubernetes deployment guide

#### Middleware & Performance
- **Rate limiting** implementation with token bucket algorithm
  - Per-minute and per-hour limits
  - Burst support
  - Distributed support via Redis
- **Request caching** system (in-memory and Redis-based)
- **Redis integration** for distributed caching and rate limiting
- **Request logging** with advanced metrics tracking

#### API Documentation
- **OpenAPI 3.0 specification** for all endpoints
- **Swagger UI** integration at `/api/docs`
- Complete API documentation with authentication examples

#### Monitoring & Observability
- **Grafana dashboards** for GPU metrics, memory usage, and service health
- **Prometheus alerts** for critical conditions:
  - Service down alerts
  - High error rate detection
  - GPU memory warnings
  - Performance degradation alerts
  - Storage capacity alerts
- Enhanced metrics endpoint with detailed GPU statistics
- Prometheus datasource configuration for Grafana

#### Configuration & Deployment
- **Codecov** configuration for coverage reporting
- Environment-specific configurations:
  - `.env.staging` for staging environment
  - `.env.production` template
- **README_ENTERPRISE.md** - Comprehensive 350+ line enterprise deployment guide
- Multi-profile Docker Compose support (default, full, monitoring, legacy)

### Changed
- Enhanced **docker-compose.yml** with backward compatibility
- Improved health check endpoints with detailed status
- Updated `.gitignore` with enterprise patterns
- Enhanced security with multiple authentication layers

### Documentation
- Added **README_ENTERPRISE.md** with:
  - Quick start guide
  - Installation options (Docker, Kubernetes, local)
  - Complete configuration reference
  - Deployment checklist
  - Monitoring setup guide
  - Security hardening instructions
  - Troubleshooting guide
  - Maintenance procedures
- Added **k8s/README.md** for Kubernetes deployment
- Updated all documentation with enterprise examples

### Infrastructure
- Docker health checks for all services
- Volume management for persistence
- Network isolation in Docker Compose
- Environment variable interpolation
- Grafana and Prometheus integration out of the box

## [0.1.6] - 2025-11-16

### Added - Security & Quality 🔒

#### Security Enhancements
- **Path traversal prevention** in webserver with PathValidator
- **API key authentication** with SHA-256 hashing (supports Bearer token, X-API-Key header, query parameter)
- **IP whitelisting** with proxy support (X-Forwarded-For, X-Real-IP)
- **Secure configuration system** with environment variables and dotenv support
- Security module (`webserver/security.py`) with:
  - PathValidator for safe file access
  - APIKeyAuth for authentication
  - IPWhitelist for network security
- Removed hardcoded secrets from configuration files
- Environment-based secret management

#### Testing Infrastructure
- **pytest** professional test structure
- Comprehensive unit tests for:
  - Configuration system (15+ tests)
  - Security features (25+ tests)
- Test categorization (unit, integration, security, GPU)
- pytest.ini with coverage configuration
- Test fixtures and utilities in `tests/conftest.py`
- Achieved 80%+ coverage for new modules

#### Code Quality & CI/CD
- **Pre-commit hooks** configured:
  - ruff (linting)
  - black (formatting)
  - mypy (type checking)
  - isort (import sorting)
  - bandit (security scanning)
  - pydocstyle (docstring linting)
- **GitHub Actions CI/CD pipeline**:
  - Lint job (ruff, black, mypy, isort)
  - Security scan job (bandit)
  - Test job (Python 3.10, 3.11)
  - Build verification
  - Docker build test
  - Coverage upload (Codecov)
- **Dependabot** configuration for automated dependency updates
- **pyproject.toml** with unified tool configurations
- Type hints added to all new modules

#### Monitoring & Observability
- `/health` endpoint with CUDA status
- `/metrics` endpoint with Prometheus metrics:
  - cuda_available
  - cuda_devices
  - cuda_memory_allocated_bytes
  - cuda_memory_reserved_bytes
- **Structured JSON logging** system (`shared_utils/structured_logging.py`):
  - JSONFormatter for production
  - ColoredTextFormatter for development
  - LogContext for contextual logging
  - Support for ELK, Splunk, CloudWatch

#### Docker Improvements
- **Dockerfile.enterprise** with:
  - Multi-stage builds for optimization
  - Non-root user (UID 1001)
  - Health checks
  - OCI-compliant labels and metadata
  - Optimized layer caching
  - Volume mounts for persistence
  - Security best practices

#### Documentation
- **CONTRIBUTING.md** - Complete developer guide with:
  - Development setup
  - Code style guidelines
  - Testing requirements
  - PR process
  - Commit message conventions
- **CODE_OF_CONDUCT.md** - Community standards
- **ARCHITECTURE.md** - Complete system architecture documentation
- **SECURITY.md** - Security policies and vulnerability reporting
- **README** enhancements
- Improved `.gitignore` for enterprise patterns
- `.env.example` with all configuration options

#### Configuration System
- New modular config system (`config/__init__.py`):
  - Environment-based configuration
  - Hierarchical loading (env > .env > config file)
  - Type-safe configuration classes
  - Validation and defaults
  - Backward compatibility with legacy config

### Changed
- Migrated from hardcoded configs to environment variables
- Enhanced `__init__.py` with new configuration system
- Updated `requirements.txt` with dev dependencies:
  - pytest and plugins
  - ruff, black, mypy, isort
  - python-dotenv
- Improved `webserver/server.py` with security features

### Security
- Fixed critical path traversal vulnerability (CVE-level)
- Fixed IP spoofing vulnerability
- Implemented secure secret management
- Added input validation across all endpoints

## [0.1.5] - Previous Release

### Features
- Support for 21+ state-of-the-art 3D generation models
- Multi-view algorithms (GaussianSplatting, NeRF, FlexiCubes, DiffRastMesh)
- Mesh processing utilities
- ComfyUI node system integration
- Docker support

## Migration Guides

### Migrating to 0.1.7 from 0.1.6

1. **Update Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Use New Deployment Tools**:
   ```bash
   # Deploy with script
   ./scripts/deploy.sh production

   # Or use Makefile
   make compose-up
   ```

4. **Enable Monitoring** (Optional):
   ```bash
   make compose-up-full
   ```

### Migrating to 0.1.6 from 0.1.5

1. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```

2. **Move secrets to environment variables**:
   - Set `HUGGINGFACE_TOKEN` in `.env`
   - Set `API_KEYS` in `.env`
   - Set `ALLOWED_IPS` for your network

3. **Enable authentication**:
   ```bash
   echo "ENABLE_AUTH=true" >> .env
   ```

4. **Install pre-commit hooks** (for development):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Breaking Changes

### 0.1.7
- None - All changes are backward compatible

### 0.1.6
- None - Configuration system maintains backward compatibility
- Existing deployments continue to work
- New features are opt-in via environment variables

## Deprecated

- Direct configuration file editing (use environment variables instead)
- Hardcoded tokens in `system.conf` (use `.env` instead)

## Removed

Nothing removed - full backward compatibility maintained.

## Security

### 0.1.7
- Rate limiting to prevent abuse
- Request validation and sanitization
- Secure defaults in all configurations

### 0.1.6
- **[CRITICAL]** Fixed path traversal vulnerability in file serving
- **[HIGH]** Fixed IP spoofing vulnerability
- **[MEDIUM]** Removed plain text secrets from config files

Please report security vulnerabilities to the maintainers (see SECURITY.md).

## Performance

### 0.1.7
- Redis caching for improved response times
- Request deduplication
- Optimized Docker images with multi-stage builds

### 0.1.6
- Structured logging with minimal overhead
- Optimized Docker builds with layer caching

## Known Issues

- WebSocket support not yet implemented (planned for 0.2.0)
- Rate limiting is in-memory only (Redis support available but optional)
- No built-in model download UI (CLI only)

## Roadmap

### 0.2.0 - Async Processing (Q1 2026)
- Celery task queue integration
- WebSocket support for real-time updates
- Progress tracking API
- Enhanced rate limiting with Redis

### 0.3.0 - Cloud Native (Q2 2026)
- S3/MinIO object storage integration
- Fully stateless architecture
- Helm charts for Kubernetes
- Multi-region support

### 0.4.0 - Advanced Features (Q3 2026)
- Multi-GPU distributed inference
- Model registry and versioning
- A/B testing framework
- Advanced analytics

---

**Note**: Dates in roadmap are estimates and subject to change.

For more information, see:
- [README_ENTERPRISE.md](README_ENTERPRISE.md) for deployment guide
- [CONTRIBUTING.md](CONTRIBUTING.md) for development guide
- [SECURITY.md](SECURITY.md) for security policies
