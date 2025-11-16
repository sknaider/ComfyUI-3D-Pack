"""
OpenAPI/Swagger documentation for ComfyUI-3D-Pack API
"""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "ComfyUI-3D-Pack API",
        "version": "0.1.7",
        "description": "Enterprise-grade 3D generation API with 21+ state-of-the-art models",
        "contact": {
            "name": "ComfyUI-3D-Pack Team",
            "url": "https://github.com/MrForExample/ComfyUI-3D-Pack",
        },
        "license": {
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
    },
    "servers": [
        {"url": "http://localhost:8188", "description": "Local development"},
        {"url": "https://api.example.com", "description": "Production"},
    ],
    "tags": [
        {"name": "health", "description": "Health check and monitoring endpoints"},
        {"name": "files", "description": "File serving endpoints"},
        {"name": "metrics", "description": "Prometheus metrics"},
    ],
    "paths": {
        "/health": {
            "get": {
                "tags": ["health"],
                "summary": "Health check endpoint",
                "description": "Returns the health status of the service including CUDA availability",
                "operationId": "getHealth",
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthStatus"},
                                "example": {
                                    "status": "healthy",
                                    "cuda_available": True,
                                    "cuda_devices": 1,
                                },
                            }
                        },
                    }
                },
            }
        },
        "/metrics": {
            "get": {
                "tags": ["metrics"],
                "summary": "Prometheus metrics endpoint",
                "description": "Returns metrics in Prometheus format",
                "operationId": "getMetrics",
                "responses": {
                    "200": {
                        "description": "Metrics in Prometheus format",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"},
                                "example": "# HELP cuda_available CUDA availability\n# TYPE cuda_available gauge\ncuda_available 1\n",
                            }
                        },
                    }
                },
            }
        },
        "/viewfile": {
            "get": {
                "tags": ["files"],
                "summary": "View 3D file",
                "description": "Serve 3D files with security checks",
                "operationId": "viewFile",
                "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "filepath",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Path to the 3D file",
                        "example": "/app/output/model.obj",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "File served successfully",
                        "content": {
                            "application/octet-stream": {
                                "schema": {"type": "string", "format": "binary"}
                            }
                        },
                    },
                    "400": {
                        "description": "Missing or invalid filepath",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"},
                                "example": "Missing filepath parameter",
                            }
                        },
                    },
                    "401": {
                        "description": "Authentication required",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"},
                                "example": "Authentication required. Provide API key via Authorization header or X-API-Key header",
                            }
                        },
                    },
                    "403": {
                        "description": "Access denied",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"},
                                "example": "Access denied: Invalid path",
                            }
                        },
                    },
                    "404": {
                        "description": "File not found",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"},
                                "example": "File not found",
                            }
                        },
                    },
                },
            }
        },
    },
    "components": {
        "schemas": {
            "HealthStatus": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["healthy", "unhealthy"],
                        "description": "Overall service status",
                    },
                    "cuda_available": {
                        "type": "boolean",
                        "description": "Whether CUDA is available",
                    },
                    "cuda_devices": {
                        "type": "integer",
                        "description": "Number of CUDA devices",
                    },
                },
                "required": ["status", "cuda_available", "cuda_devices"],
            }
        },
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for authentication",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key",
                "description": "Bearer token authentication",
            },
        },
    },
}


def get_openapi_html() -> str:
    """Generate Swagger UI HTML"""
    import json

    spec_json = json.dumps(OPENAPI_SPEC, indent=2)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI-3D-Pack API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                spec: {spec_json},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
            window.ui = ui;
        }};
    </script>
</body>
</html>
"""
