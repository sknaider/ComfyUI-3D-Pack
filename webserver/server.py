import server
import os
from pathlib import Path
from typing import Optional
import logging

from ..shared_utils.log_utils import cstr
from .security import PathValidator, APIKeyAuth, IPWhitelist

web = server.web
logger = logging.getLogger(__name__)

SUPPORTED_VIEW_EXTENSIONS = (
    '.png',
    '.jpg',
    '.jpeg',
    '.mtl',
    '.obj',
    '.glb',
    '.ply',
    '.splat'
)

# Global security components
web_conf = None
path_validator: Optional[PathValidator] = None
api_key_auth: Optional[APIKeyAuth] = None
ip_whitelist: Optional[IPWhitelist] = None
auth_enabled: bool = False


def set_web_conf(new_web_conf):
    """
    Configure web server security

    Args:
        new_web_conf: Configuration dictionary with security settings
    """
    global web_conf, path_validator, api_key_auth, ip_whitelist, auth_enabled

    web_conf = new_web_conf

    # Initialize path validator with allowed directories
    allowed_dirs = []
    if 'allowed_directories' in new_web_conf:
        allowed_dirs = new_web_conf['allowed_directories']
    else:
        # Default: allow output directory only
        output_dir = new_web_conf.get('output_directory', '/tmp/output')
        allowed_dirs = [output_dir]

    path_validator = PathValidator(allowed_dirs)

    # Initialize API key authentication if keys are provided
    api_keys = new_web_conf.get('api_keys', [])
    if api_keys:
        api_key_auth = APIKeyAuth(api_keys)
        auth_enabled = new_web_conf.get('enable_auth', True)
    else:
        api_key_auth = None
        auth_enabled = False

    # Initialize IP whitelist
    allowed_ips = new_web_conf.get('clients_ip', ['127.0.0.1'])
    ip_whitelist = IPWhitelist(allowed_ips)

    logger.info(f"Web server configured - Auth enabled: {auth_enabled}")


@server.PromptServer.instance.routes.get("/viewfile")
async def view_file(request):
    """
    Serve files with proper security checks

    Security features:
    - API key authentication (if enabled)
    - IP whitelist validation
    - Path traversal prevention
    - File extension validation
    """
    query = request.rel_url.query

    # Security check 1: IP whitelist
    if ip_whitelist and not ip_whitelist.validate_request(request):
        logger.warning(f"Access denied from IP: {request.remote}")
        return web.Response(status=403, text="Access denied: IP not allowed")

    # Security check 2: API key authentication (if enabled)
    if auth_enabled and api_key_auth:
        if not api_key_auth.validate_request(request):
            logger.warning(f"Invalid API key from IP: {request.remote}")
            return web.Response(
                status=401,
                text="Authentication required. Provide API key via Authorization header or X-API-Key header"
            )

    # Security check 3: Validate filepath parameter exists
    if "filepath" not in query:
        return web.Response(status=400, text="Missing filepath parameter")

    filepath = query["filepath"]
    cstr(f"[Server Query view_file] Request for file {filepath}").msg.print()

    # Security check 4: Validate file extension
    if not filepath.lower().endswith(SUPPORTED_VIEW_EXTENSIONS):
        logger.warning(f"Unsupported file extension: {filepath}")
        return web.Response(status=400, text="Unsupported file extension")

    # Security check 5: Validate path (prevent directory traversal)
    if path_validator:
        validated_path = path_validator.validate_path(filepath)
        if validated_path is None:
            logger.warning(f"Path validation failed for: {filepath}")
            return web.Response(status=403, text="Access denied: Invalid path")

        # Serve the validated file
        return web.FileResponse(validated_path)
    else:
        # Fallback: basic validation without path validator
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return web.FileResponse(filepath)

    return web.Response(status=404, text="File not found")


@server.PromptServer.instance.routes.get("/health")
async def health_check(request):
    """
    Health check endpoint for monitoring and load balancers

    Returns:
        JSON response with health status
    """
    import torch

    health_status = {
        "status": "healthy",
        "cuda_available": torch.cuda.is_available(),
        "cuda_devices": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }

    return web.json_response(health_status)


@server.PromptServer.instance.routes.get("/metrics")
async def metrics(request):
    """
    Prometheus-compatible metrics endpoint

    Returns:
        Text response with Prometheus metrics
    """
    import torch

    metrics_text = f"""# HELP cuda_available CUDA availability
# TYPE cuda_available gauge
cuda_available {1 if torch.cuda.is_available() else 0}

# HELP cuda_devices Number of CUDA devices
# TYPE cuda_devices gauge
cuda_devices {torch.cuda.device_count() if torch.cuda.is_available() else 0}
"""

    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            memory_allocated = torch.cuda.memory_allocated(i)
            memory_reserved = torch.cuda.memory_reserved(i)
            metrics_text += f"""
# HELP cuda_memory_allocated_bytes GPU memory allocated on device {i}
# TYPE cuda_memory_allocated_bytes gauge
cuda_memory_allocated_bytes{{device="{i}"}} {memory_allocated}

# HELP cuda_memory_reserved_bytes GPU memory reserved on device {i}
# TYPE cuda_memory_reserved_bytes gauge
cuda_memory_reserved_bytes{{device="{i}"}} {memory_reserved}
"""

    return web.Response(text=metrics_text, content_type="text/plain")
