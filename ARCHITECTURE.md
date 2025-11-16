# ComfyUI-3D-Pack Architecture

## Overview

ComfyUI-3D-Pack is an enterprise-grade extension for ComfyUI that provides comprehensive 3D generation capabilities. This document describes the system architecture, design decisions, and implementation patterns.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ComfyUI-3D-Pack                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Web API    │  │  Node System │  │  3D Models   │     │
│  │   Server     │──│   (nodes.py) │──│  Generation  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │            │
│         ▼                  ▼                  ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Security &  │  │ Mesh         │  │ Multi-View   │     │
│  │  Auth        │  │ Processing   │  │ Algorithms   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │            │
│         ▼                  ▼                  ▼            │
│  ┌──────────────────────────────────────────────────┐     │
│  │         Configuration & Logging System           │     │
│  └──────────────────────────────────────────────────┘     │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            ▼
                   ┌────────────────┐
                   │  External Deps │
                   │ PyTorch, CUDA  │
                   │ HuggingFace    │
                   └────────────────┘
```

## Core Components

### 1. Configuration Management (`config/`)

**Purpose**: Centralized, secure configuration management

**Key Features**:
- Environment-based configuration (.env support)
- Hierarchical configuration (env vars > .env > config file)
- Type-safe configuration classes
- Validation and defaults

**Files**:
- `config/__init__.py` - Main configuration loader
- `.env.example` - Example environment variables
- `Configs/system.conf` - Legacy HOCON configuration

**Usage**:
```python
from config import get_config

config = get_config()
hf_token = config.huggingface_token
api_keys = config.security.api_keys
```

### 2. Web Server (`webserver/`)

**Purpose**: HTTP API for file serving and health checks

**Security Features**:
- Path traversal prevention
- API key authentication
- IP whitelisting
- Request validation

**Endpoints**:
- `GET /viewfile` - Serve 3D files (secured)
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

**Files**:
- `webserver/server.py` - Main server implementation
- `webserver/security.py` - Security utilities

### 3. 3D Model Generation (`Gen_3D_Modules/`)

**Purpose**: Integration of 21+ state-of-the-art 3D generation models

**Supported Models**:
- **Hunyuan3D** (v1, v2, v2.1) - Tencent's latest models
- **TRELLIS** - Microsoft Research
- **TripoSR** - Stable diffusion for 3D
- **StableFast3D** - Stability AI
- **InstantMesh** - Fast mesh generation
- **CRM** (v1, v2, v3) - Convolutional Reconstruction
- **Wonder3D** - Multi-view generation
- **Era3D** - Evolution of Wonder3D
- **Unique3D** - High-quality texturing
- **CharacterGen** - Character-specific generation
- **Craftsman** - General 3D object generation
- **LGM** - Large Gaussian Model
- **TriplaneGaussian** - 3D Gaussian Splatting
- **PartCrafter** - Part-based generation
- **MV_Adapter** - Multi-view adaptation
- **Stable3DGen** - Generalized 3D generation

Each module follows a plugin architecture with:
- Model loading and initialization
- Inference pipeline
- Post-processing
- Resource management (GPU memory)

### 4. Multi-View Algorithms (`MVs_Algorithms/`)

**Purpose**: Reconstruction algorithms for multi-view synthesis

**Algorithms**:
- **GaussianSplatting** - 3D Gaussian Splatting for real-time rendering
- **NeRF** - Neural Radiance Fields (Instant-NGP)
- **FlexiCubes** - Flexible isosurface extraction
- **DiffRastMesh** - Differentiable rasterization

**Common Pipeline**:
1. Multi-view image input
2. Camera pose estimation
3. 3D reconstruction
4. Mesh extraction
5. Texture optimization

### 5. Mesh Processing (`mesh_processer/`)

**Purpose**: Utilities for mesh manipulation

**Operations**:
- Loading (PLY, OBJ, GLB)
- Cleaning and repair
- Decimation and simplification
- Normal computation
- UV unwrapping
- Texture baking
- Format conversion

**Key File**:
- `mesh_processer/mesh.py` - Main Mesh class
- `mesh_processer/mesh_utils.py` - Utility functions

### 6. Node System (`nodes.py`)

**Purpose**: ComfyUI node definitions for workflow building

**Current State**:
- ⚠️ **Monolithic** - 6,000 lines in single file
- 213 node class definitions
- Tightly coupled with model implementations

**Enterprise Refactoring Plan** (Future):
```
nodes/
├── __init__.py
├── base.py              # Base node classes
├── loaders/             # Model loading nodes
│   ├── mesh_loaders.py
│   └── model_loaders.py
├── generators/          # 3D generation nodes
│   ├── text_to_3d.py
│   └── image_to_3d.py
├── processors/          # Processing nodes
│   ├── mesh_ops.py
│   └── texture_ops.py
└── outputs/             # Output nodes
    └── exporters.py
```

### 7. Shared Utilities (`shared_utils/`)

**Purpose**: Common utilities and helpers

**Modules**:
- `log_utils.py` - Custom logging (legacy colored output)
- `structured_logging.py` - **NEW**: JSON logging for production
- Additional utilities as needed

## Security Architecture

### Authentication Flow

```
Request → IP Whitelist Check → API Key Validation → Path Validation → Response
            ↓ (fail)              ↓ (fail)            ↓ (fail)
          403 Forbidden         401 Unauthorized    403 Forbidden
```

### Security Layers

1. **Network Security**
   - IP whitelisting
   - CORS configuration
   - Rate limiting (TODO)

2. **Authentication**
   - API key-based auth
   - Bearer token support
   - Key hashing (SHA-256)

3. **Authorization**
   - Path-based access control
   - File type restrictions
   - Directory traversal prevention

4. **Data Security**
   - Environment variable secrets
   - Encrypted model downloads (TODO)
   - Audit logging

## Configuration Hierarchy

```
Priority (highest to lowest):
1. Environment Variables
2. .env file
3. Configs/system.conf (legacy)
4. Default values in code
```

## Logging Architecture

### Structured Logging

**Format**: JSON for production, colored text for development

**Log Levels**:
- DEBUG - Detailed debugging information
- INFO - General informational messages
- WARNING - Warning messages
- ERROR - Error messages
- CRITICAL - Critical errors

**Log Fields** (JSON format):
```json
{
  "timestamp": "2025-11-16T10:30:00.123456",
  "level": "INFO",
  "logger": "comfyui-3d-pack",
  "message": "Processing request",
  "function": "process_mesh",
  "line": 123,
  "file": "mesh.py",
  "request_id": "req-abc-123",
  "user_id": "user-456"
}
```

**Log Aggregation**:
- stdout → Container logs → CloudWatch/ELK/Splunk
- File logs in `/var/log/comfyui-3d-pack/` (optional)

## Testing Strategy

### Test Structure

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_config.py
│   ├── test_security.py
│   └── test_mesh.py
├── integration/       # Component interaction tests
│   ├── test_pipelines.py
│   └── test_api.py
└── fixtures/          # Shared test data
    └── sample_models/
```

### Test Categories

1. **Unit Tests** - Individual functions/classes
   - Markers: `@pytest.mark.unit`
   - Fast execution (< 1s per test)
   - No external dependencies

2. **Integration Tests** - Component interactions
   - Markers: `@pytest.mark.integration`
   - Moderate execution time
   - May use mocked models

3. **Security Tests** - Security features
   - Markers: `@pytest.mark.security`
   - Path traversal attempts
   - Authentication bypass attempts
   - Input validation

4. **GPU Tests** - GPU-dependent tests
   - Markers: `@pytest.mark.requires_gpu`
   - Run only on GPU-enabled CI

## Deployment Architecture

### Docker Deployment

```
┌─────────────────────────┐
│   Load Balancer         │
│   (NGINX/ALB)           │
└───────────┬─────────────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼────┐      ┌───▼────┐
│Instance│      │Instance│
│   1    │      │   2    │
└────┬───┘      └───┬────┘
     │              │
     └───────┬──────┘
             │
    ┌────────▼─────────┐
    │  Shared Storage  │
    │  (S3/EFS)        │
    │  - Models        │
    │  - Output        │
    └──────────────────┘
```

### Kubernetes Deployment (Future)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: comfyui-3d-pack
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: comfyui-3d-pack:latest
        resources:
          limits:
            nvidia.com/gpu: 1
        env:
        - name: LOG_FORMAT
          value: "json"
```

## Scalability Considerations

### Current Limitations

1. **Stateful** - Session-based processing
2. **No queue system** - Sequential processing
3. **Local storage** - Not cloud-native
4. **Single instance** - No horizontal scaling

### Enterprise Roadmap

1. **Phase 1** - Current (v0.1.6)
   - ✅ Security hardening
   - ✅ Structured logging
   - ✅ Health checks
   - ✅ Testing infrastructure

2. **Phase 2** - Async Processing (v0.2.0)
   - Task queue (Celery/RQ)
   - Result storage (Redis)
   - Progress tracking

3. **Phase 3** - Cloud Native (v0.3.0)
   - S3/MinIO integration
   - Stateless architecture
   - Kubernetes deployment

4. **Phase 4** - Distributed (v0.4.0)
   - Multi-GPU support
   - Distributed inference
   - Auto-scaling

## Performance Optimization

### GPU Memory Management

```python
# Pattern: Lazy loading + offloading
@offload_decorator
def load_model(model_name):
    model = load_heavy_model(model_name)
    return model

# After use
torch.cuda.empty_cache()
gc.collect()
```

### Caching Strategy

1. **Model caching** - Keep frequently used models in memory
2. **Result caching** - Cache expensive operations
3. **Asset caching** - CDN for static models

### Profiling

```bash
# CPU profiling
python -m cProfile -o profile.stats main.py

# GPU profiling
nvprof python main.py

# Memory profiling
python -m memory_profiler main.py
```

## Monitoring & Observability

### Metrics (Prometheus)

- `cuda_available` - CUDA availability
- `cuda_devices` - Number of GPUs
- `cuda_memory_allocated_bytes` - GPU memory usage
- `request_duration_seconds` - Request latency
- `active_models` - Loaded models count

### Dashboards (Grafana)

- System health
- GPU utilization
- Request rate/latency
- Error rate
- Model performance

### Alerts

- GPU OOM
- High error rate
- Slow requests
- Service down

## Development Guidelines

### Adding New Models

1. Create module in `Gen_3D_Modules/ModelName/`
2. Implement standard interface
3. Add configuration
4. Write tests
5. Update documentation
6. Create example workflow

### Code Quality Standards

- **Line length**: 120 characters
- **Type hints**: Required for public APIs
- **Docstrings**: Google style
- **Test coverage**: ≥ 80%
- **Linting**: Ruff + Black
- **Type checking**: mypy

### Versioning

- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Breaking changes**: Increment MAJOR
- **New features**: Increment MINOR
- **Bug fixes**: Increment PATCH

## References

- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- [NeRF](https://www.matthewtancik.com/nerf)
