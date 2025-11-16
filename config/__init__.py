"""
Enterprise Configuration Management
Provides secure, environment-aware configuration loading
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging

# Try to import python-dotenv, fallback gracefully
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logging.warning("python-dotenv not available, falling back to environment variables only")

from pyhocon import ConfigFactory

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    api_keys: List[str] = field(default_factory=list)
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:8188"])
    allowed_ips: List[str] = field(default_factory=lambda: ["127.0.0.1"])
    enable_auth: bool = True
    cors_enabled: bool = True


@dataclass
class StorageConfig:
    """Storage paths configuration"""
    models_base_path: Path = Path("/tmp/models")
    output_base_path: Path = Path("/tmp/output")


@dataclass
class CloudStorageConfig:
    """Cloud object storage configuration"""
    enabled: bool = False
    backend_type: str = "s3"  # s3, minio, gcs, azure
    endpoint: Optional[str] = None
    bucket: str = "comfyui-3d-pack"
    region: str = "us-east-1"
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    use_ssl: bool = True
    # Provider-specific options
    connection_string: Optional[str] = None  # Azure
    project_id: Optional[str] = None  # GCS
    credentials_path: Optional[str] = None  # GCS


@dataclass
class PerformanceConfig:
    """Performance tuning configuration"""
    max_workers: int = 4
    gpu_memory_fraction: float = 0.8
    request_timeout: int = 3600


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"  # json or text


@dataclass
class AppConfig:
    """Main application configuration"""
    huggingface_token: Optional[str] = None
    security: SecurityConfig = field(default_factory=SecurityConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    cloud_storage: CloudStorageConfig = field(default_factory=CloudStorageConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Legacy compatibility
    web_clients_ip: List[str] = field(default_factory=lambda: ["127.0.0.1"])


class ConfigLoader:
    """Loads configuration from multiple sources with priority: ENV > .env > config file"""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.env_file = root_path / ".env"
        self.config_file = root_path / "Configs" / "system.conf"

    def load(self) -> AppConfig:
        """Load configuration from all sources"""
        # Load .env file if available
        if DOTENV_AVAILABLE and self.env_file.exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment from {self.env_file}")

        # Load legacy config file
        legacy_config = self._load_legacy_config()

        # Build configuration with priority: ENV > legacy config
        config = AppConfig(
            huggingface_token=self._get_env_or_legacy(
                "HUGGINGFACE_TOKEN",
                legacy_config.get("huggingface.token", "")
            ),
            security=SecurityConfig(
                api_keys=self._parse_list(os.getenv("API_KEYS", "")),
                allowed_origins=self._parse_list(
                    os.getenv("ALLOWED_ORIGINS", "http://localhost:8188")
                ),
                allowed_ips=self._parse_list(
                    os.getenv("ALLOWED_IPS") or
                    ",".join(str(ip) for ip in legacy_config.get("web.clients_ip", ["127.0.0.1"]))
                ),
                enable_auth=os.getenv("ENABLE_AUTH", "true").lower() == "true",
                cors_enabled=os.getenv("CORS_ENABLED", "true").lower() == "true",
            ),
            storage=StorageConfig(
                models_base_path=Path(os.getenv("MODELS_BASE_PATH", "/tmp/models")),
                output_base_path=Path(os.getenv("OUTPUT_BASE_PATH", "/tmp/output")),
            ),
            cloud_storage=CloudStorageConfig(
                enabled=os.getenv("CLOUD_STORAGE_ENABLED", "false").lower() == "true",
                backend_type=os.getenv("CLOUD_STORAGE_TYPE", "s3"),
                endpoint=os.getenv("CLOUD_STORAGE_ENDPOINT"),
                bucket=os.getenv("CLOUD_STORAGE_BUCKET", "comfyui-3d-pack"),
                region=os.getenv("CLOUD_STORAGE_REGION", "us-east-1"),
                access_key=os.getenv("CLOUD_STORAGE_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID"),
                secret_key=os.getenv("CLOUD_STORAGE_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
                use_ssl=os.getenv("CLOUD_STORAGE_USE_SSL", "true").lower() == "true",
                connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
                project_id=os.getenv("GCP_PROJECT_ID"),
                credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            ),
            performance=PerformanceConfig(
                max_workers=int(os.getenv("MAX_WORKERS", "4")),
                gpu_memory_fraction=float(os.getenv("GPU_MEMORY_FRACTION", "0.8")),
                request_timeout=int(os.getenv("REQUEST_TIMEOUT", "3600")),
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json"),
            ),
            # Legacy compatibility
            web_clients_ip=self._parse_list(
                os.getenv("ALLOWED_IPS") or
                ",".join(str(ip) for ip in legacy_config.get("web.clients_ip", ["127.0.0.1"]))
            ),
        )

        # Validate configuration
        self._validate_config(config)

        return config

    def _load_legacy_config(self) -> Dict[str, Any]:
        """Load legacy HOCON configuration file"""
        if not self.config_file.exists():
            logger.warning(f"Legacy config file not found: {self.config_file}")
            return {}

        try:
            with open(self.config_file) as f:
                conf_text = f.read()
            return ConfigFactory.parse_string(conf_text)
        except Exception as e:
            logger.error(f"Failed to load legacy config: {e}")
            return {}

    def _get_env_or_legacy(self, env_key: str, legacy_value: Any) -> Any:
        """Get value from environment or fall back to legacy config"""
        env_value = os.getenv(env_key)
        if env_value is not None and env_value != "":
            return env_value
        return legacy_value if legacy_value else None

    def _parse_list(self, value: str) -> List[str]:
        """Parse comma-separated list from string"""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _validate_config(self, config: AppConfig) -> None:
        """Validate configuration values"""
        # Warn if using default/insecure values
        if config.security.enable_auth and not config.security.api_keys:
            logger.warning(
                "Authentication is enabled but no API keys are configured. "
                "Set API_KEYS environment variable."
            )

        if config.huggingface_token and len(config.huggingface_token) < 10:
            logger.warning("HuggingFace token appears to be invalid (too short)")

        # Ensure storage paths exist
        config.storage.models_base_path.mkdir(parents=True, exist_ok=True)
        config.storage.output_base_path.mkdir(parents=True, exist_ok=True)

        logger.info("Configuration validated successfully")


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config(root_path: Optional[Path] = None) -> AppConfig:
    """Get or create global configuration instance"""
    global _config

    if _config is None:
        if root_path is None:
            # Try to determine root path automatically
            root_path = Path(__file__).parent.parent

        loader = ConfigLoader(root_path)
        _config = loader.load()

    return _config


def reload_config(root_path: Path) -> AppConfig:
    """Force reload configuration"""
    global _config
    loader = ConfigLoader(root_path)
    _config = loader.load()
    return _config
