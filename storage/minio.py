"""
MinIO Storage Backend Implementation

Provides integration with MinIO, an S3-compatible object storage server.
"""

from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path
from datetime import timedelta

try:
    from minio import Minio
    from minio.error import S3Error
    from urllib3.exceptions import MaxRetryError
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

from . import StorageBackend, StorageConfig

logger = logging.getLogger(__name__)


class MinIOStorage(StorageBackend):
    """MinIO storage backend implementation"""

    def __init__(self, config: StorageConfig):
        if not MINIO_AVAILABLE:
            raise ImportError(
                "minio is required for MinIO storage. "
                "Install it with: pip install minio"
            )

        super().__init__(config)

        if not config.endpoint:
            raise ValueError("MinIO endpoint is required")

        # Create MinIO client
        self.client = Minio(
            config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.use_ssl,
            region=config.region
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket, location=self.config.region)
                self.logger.info(f"Created MinIO bucket '{self.bucket}'")
            else:
                self.logger.info(f"MinIO bucket '{self.bucket}' exists")
        except (S3Error, MaxRetryError) as e:
            self.logger.error(f"Error with bucket: {e}")

    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to MinIO"""
        try:
            file_path = Path(local_path)
            if not file_path.exists():
                self.logger.error(f"Local file does not exist: {local_path}")
                return False

            self.client.fput_object(
                self.bucket,
                remote_path,
                local_path,
                metadata=metadata
            )
            self.logger.debug(f"Uploaded {local_path} to minio://{self.bucket}/{remote_path}")
            return True
        except (S3Error, FileNotFoundError) as e:
            self.logger.error(f"Failed to upload {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from MinIO"""
        try:
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            self.client.fget_object(
                self.bucket,
                remote_path,
                local_path
            )
            self.logger.debug(f"Downloaded minio://{self.bucket}/{remote_path} to {local_path}")
            return True
        except S3Error as e:
            self.logger.error(f"Failed to download {remote_path}: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(self.bucket, remote_path)
            self.logger.debug(f"Deleted minio://{self.bucket}/{remote_path}")
            return True
        except S3Error as e:
            self.logger.error(f"Failed to delete {remote_path}: {e}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """List files in MinIO"""
        try:
            objects = self.client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=recursive
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            self.logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket, remote_path)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            self.logger.error(f"Error checking if file exists: {e}")
            return False

    def get_file_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file in MinIO"""
        try:
            stat = self.client.stat_object(self.bucket, remote_path)
            return {
                'size': stat.size,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type,
                'etag': stat.etag,
                'metadata': stat.metadata or {},
            }
        except S3Error as e:
            self.logger.error(f"Failed to get metadata for {remote_path}: {e}")
            return None

    def get_presigned_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for temporary access"""
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                remote_path,
                expires=timedelta(seconds=expiration)
            )
            return url
        except S3Error as e:
            self.logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def upload_stream(self, stream: BinaryIO, remote_path: str,
                     metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload data from a stream to MinIO"""
        try:
            # MinIO requires content length for streams
            # Read stream to get length
            data = stream.read()
            length = len(data)

            from io import BytesIO
            stream_with_length = BytesIO(data)

            self.client.put_object(
                self.bucket,
                remote_path,
                stream_with_length,
                length,
                metadata=metadata
            )
            self.logger.debug(f"Uploaded stream to minio://{self.bucket}/{remote_path}")
            return True
        except S3Error as e:
            self.logger.error(f"Failed to upload stream: {e}")
            return False

    def copy_file(self, source_path: str, dest_path: str,
                 source_bucket: Optional[str] = None) -> bool:
        """
        Copy a file within MinIO or from another bucket

        Args:
            source_path: Source object key
            dest_path: Destination object key
            source_bucket: Source bucket (defaults to same bucket)

        Returns:
            True if successful, False otherwise
        """
        try:
            from minio.commonconfig import CopySource

            source_bucket = source_bucket or self.bucket
            copy_source = CopySource(source_bucket, source_path)

            self.client.copy_object(
                self.bucket,
                dest_path,
                copy_source
            )
            self.logger.debug(
                f"Copied minio://{source_bucket}/{source_path} to "
                f"minio://{self.bucket}/{dest_path}"
            )
            return True
        except S3Error as e:
            self.logger.error(f"Failed to copy file: {e}")
            return False

    def get_bucket_policy(self) -> Optional[str]:
        """
        Get bucket policy

        Returns:
            Bucket policy as JSON string or None
        """
        try:
            policy = self.client.get_bucket_policy(self.bucket)
            return policy
        except S3Error as e:
            if e.code == 'NoSuchBucketPolicy':
                return None
            self.logger.error(f"Failed to get bucket policy: {e}")
            return None

    def set_bucket_policy(self, policy: str) -> bool:
        """
        Set bucket policy

        Args:
            policy: Bucket policy as JSON string

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.set_bucket_policy(self.bucket, policy)
            self.logger.debug(f"Set bucket policy for '{self.bucket}'")
            return True
        except S3Error as e:
            self.logger.error(f"Failed to set bucket policy: {e}")
            return False

    def enable_versioning(self) -> bool:
        """
        Enable versioning for the bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            from minio.commonconfig import ENABLED
            from minio.versioningconfig import VersioningConfig

            self.client.set_bucket_versioning(
                self.bucket,
                VersioningConfig(ENABLED)
            )
            self.logger.info(f"Enabled versioning for bucket '{self.bucket}'")
            return True
        except S3Error as e:
            self.logger.error(f"Failed to enable versioning: {e}")
            return False

    def set_bucket_tags(self, tags: Dict[str, str]) -> bool:
        """
        Set bucket tags

        Args:
            tags: Dictionary of tag key-value pairs

        Returns:
            True if successful, False otherwise
        """
        try:
            from minio.commonconfig import Tags

            tag_obj = Tags.new_bucket_tags()
            for key, value in tags.items():
                tag_obj[key] = value

            self.client.set_bucket_tags(self.bucket, tag_obj)
            self.logger.debug(f"Set bucket tags for '{self.bucket}'")
            return True
        except S3Error as e:
            self.logger.error(f"Failed to set bucket tags: {e}")
            return False
