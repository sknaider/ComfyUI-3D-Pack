"""
Object Storage Abstraction Layer for ComfyUI-3D-Pack

This module provides a unified interface for various cloud object storage providers
including AWS S3, MinIO, Google Cloud Storage, and Azure Blob Storage.

Usage:
    from storage import get_storage_backend

    storage = get_storage_backend('s3', endpoint='s3.amazonaws.com', bucket='my-bucket')
    storage.upload_file('local/path.txt', 'remote/path.txt')
    storage.download_file('remote/path.txt', 'local/path.txt')
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """Configuration for object storage backend"""
    backend_type: str  # s3, minio, gcs, azure
    endpoint: Optional[str] = None
    bucket: str = "comfyui-3d-pack"
    region: str = "us-east-1"
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    use_ssl: bool = True
    # Provider-specific options
    extra_config: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_config is None:
            self.extra_config = {}


class StorageBackend(ABC):
    """Abstract base class for object storage backends"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self.bucket = config.bucket
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload a file to object storage

        Args:
            local_path: Path to local file
            remote_path: Path in object storage
            metadata: Optional metadata to attach to object

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a file from object storage

        Args:
            remote_path: Path in object storage
            local_path: Path to save file locally

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from object storage

        Args:
            remote_path: Path in object storage

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def list_files(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """
        List files in object storage

        Args:
            prefix: Optional prefix to filter files
            recursive: List files recursively

        Returns:
            List of file paths
        """
        pass

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in object storage

        Args:
            remote_path: Path in object storage

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_file_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file

        Args:
            remote_path: Path in object storage

        Returns:
            Dictionary of metadata or None if file doesn't exist
        """
        pass

    @abstractmethod
    def get_presigned_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for temporary access

        Args:
            remote_path: Path in object storage
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL or None if operation failed
        """
        pass

    @abstractmethod
    def upload_stream(self, stream: BinaryIO, remote_path: str,
                     metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload data from a stream/file-like object

        Args:
            stream: Binary stream to upload
            remote_path: Path in object storage
            metadata: Optional metadata to attach

        Returns:
            True if successful, False otherwise
        """
        pass

    def sync_directory(self, local_dir: str, remote_prefix: str,
                      delete: bool = False) -> Dict[str, int]:
        """
        Sync a local directory to object storage

        Args:
            local_dir: Local directory path
            remote_prefix: Remote prefix/directory
            delete: Delete remote files not present locally

        Returns:
            Dictionary with counts: {'uploaded': N, 'deleted': N, 'skipped': N}
        """
        local_path = Path(local_dir)
        if not local_path.exists():
            raise ValueError(f"Local directory does not exist: {local_dir}")

        stats = {'uploaded': 0, 'deleted': 0, 'skipped': 0}

        # Upload local files
        for file_path in local_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_path)
                remote_path = f"{remote_prefix}/{relative_path}".replace('\\', '/')

                if self.upload_file(str(file_path), remote_path):
                    stats['uploaded'] += 1
                    self.logger.info(f"Uploaded {file_path} -> {remote_path}")
                else:
                    stats['skipped'] += 1
                    self.logger.warning(f"Failed to upload {file_path}")

        # Delete remote files if requested
        if delete:
            remote_files = set(self.list_files(prefix=remote_prefix))
            local_files = set(
                f"{remote_prefix}/{p.relative_to(local_path)}".replace('\\', '/')
                for p in local_path.rglob('*') if p.is_file()
            )

            for remote_file in remote_files - local_files:
                if self.delete_file(remote_file):
                    stats['deleted'] += 1
                    self.logger.info(f"Deleted {remote_file}")

        return stats


def get_storage_backend(backend_type: str = None, **kwargs) -> StorageBackend:
    """
    Factory function to get appropriate storage backend

    Args:
        backend_type: Type of backend (s3, minio, gcs, azure)
        **kwargs: Configuration parameters

    Returns:
        StorageBackend instance

    Example:
        storage = get_storage_backend(
            backend_type='s3',
            bucket='my-bucket',
            region='us-west-2',
            access_key='...',
            secret_key='...'
        )
    """
    # Import here to avoid circular dependencies
    if backend_type == 's3':
        from .s3 import S3Storage
        config = StorageConfig(backend_type='s3', **kwargs)
        return S3Storage(config)
    elif backend_type == 'minio':
        from .minio import MinIOStorage
        config = StorageConfig(backend_type='minio', **kwargs)
        return MinIOStorage(config)
    elif backend_type == 'gcs':
        from .gcs import GCSStorage
        config = StorageConfig(backend_type='gcs', **kwargs)
        return GCSStorage(config)
    elif backend_type == 'azure':
        from .azure import AzureStorage
        config = StorageConfig(backend_type='azure', **kwargs)
        return AzureStorage(config)
    else:
        raise ValueError(
            f"Unknown storage backend: {backend_type}. "
            f"Supported: s3, minio, gcs, azure"
        )


__all__ = [
    'StorageBackend',
    'StorageConfig',
    'get_storage_backend',
]
