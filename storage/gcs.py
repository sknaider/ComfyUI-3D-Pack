"""
Google Cloud Storage Backend Implementation

Provides integration with Google Cloud Storage (GCS).
"""

from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path
from datetime import timedelta

try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound, GoogleCloudError
    from google.oauth2 import service_account
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

from . import StorageBackend, StorageConfig

logger = logging.getLogger(__name__)


class GCSStorage(StorageBackend):
    """Google Cloud Storage backend implementation"""

    def __init__(self, config: StorageConfig):
        if not GCS_AVAILABLE:
            raise ImportError(
                "google-cloud-storage is required for GCS storage. "
                "Install it with: pip install google-cloud-storage"
            )

        super().__init__(config)

        # Initialize GCS client
        client_kwargs = {}

        # Use service account credentials if provided
        credentials_path = config.extra_config.get('credentials_path')
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            client_kwargs['credentials'] = credentials

        # Use project ID if provided
        project_id = config.extra_config.get('project_id')
        if project_id:
            client_kwargs['project'] = project_id

        self.client = storage.Client(**client_kwargs)

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.bucket_obj = self.client.get_bucket(self.bucket)
            self.logger.info(f"GCS bucket '{self.bucket}' exists")
        except NotFound:
            try:
                self.bucket_obj = self.client.create_bucket(
                    self.bucket,
                    location=self.config.region
                )
                self.logger.info(f"Created GCS bucket '{self.bucket}'")
            except GoogleCloudError as e:
                self.logger.error(f"Failed to create bucket: {e}")
                raise

    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to GCS"""
        try:
            blob = self.bucket_obj.blob(remote_path)

            if metadata:
                blob.metadata = metadata

            blob.upload_from_filename(local_path)
            self.logger.debug(f"Uploaded {local_path} to gs://{self.bucket}/{remote_path}")
            return True
        except (GoogleCloudError, FileNotFoundError) as e:
            self.logger.error(f"Failed to upload {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from GCS"""
        try:
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob = self.bucket_obj.blob(remote_path)
            blob.download_to_filename(local_path)
            self.logger.debug(f"Downloaded gs://{self.bucket}/{remote_path} to {local_path}")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to download {remote_path}: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from GCS"""
        try:
            blob = self.bucket_obj.blob(remote_path)
            blob.delete()
            self.logger.debug(f"Deleted gs://{self.bucket}/{remote_path}")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to delete {remote_path}: {e}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """List files in GCS"""
        try:
            delimiter = None if recursive else '/'
            blobs = self.client.list_blobs(
                self.bucket,
                prefix=prefix,
                delimiter=delimiter
            )
            return [blob.name for blob in blobs]
        except GoogleCloudError as e:
            self.logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in GCS"""
        try:
            blob = self.bucket_obj.blob(remote_path)
            return blob.exists()
        except GoogleCloudError as e:
            self.logger.error(f"Error checking if file exists: {e}")
            return False

    def get_file_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file in GCS"""
        try:
            blob = self.bucket_obj.blob(remote_path)
            blob.reload()  # Fetch metadata from GCS

            return {
                'size': blob.size,
                'last_modified': blob.updated,
                'content_type': blob.content_type,
                'etag': blob.etag,
                'metadata': blob.metadata or {},
                'md5_hash': blob.md5_hash,
                'crc32c': blob.crc32c,
            }
        except GoogleCloudError as e:
            self.logger.error(f"Failed to get metadata for {remote_path}: {e}")
            return None

    def get_presigned_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """Generate a signed URL for temporary access"""
        try:
            blob = self.bucket_obj.blob(remote_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="GET"
            )
            return url
        except GoogleCloudError as e:
            self.logger.error(f"Failed to generate signed URL: {e}")
            return None

    def upload_stream(self, stream: BinaryIO, remote_path: str,
                     metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload data from a stream to GCS"""
        try:
            blob = self.bucket_obj.blob(remote_path)

            if metadata:
                blob.metadata = metadata

            blob.upload_from_file(stream)
            self.logger.debug(f"Uploaded stream to gs://{self.bucket}/{remote_path}")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to upload stream: {e}")
            return False

    def copy_file(self, source_path: str, dest_path: str,
                 source_bucket: Optional[str] = None) -> bool:
        """
        Copy a file within GCS or from another bucket

        Args:
            source_path: Source blob name
            dest_path: Destination blob name
            source_bucket: Source bucket (defaults to same bucket)

        Returns:
            True if successful, False otherwise
        """
        try:
            if source_bucket:
                source_bucket_obj = self.client.bucket(source_bucket)
            else:
                source_bucket_obj = self.bucket_obj

            source_blob = source_bucket_obj.blob(source_path)
            dest_blob = self.bucket_obj.blob(dest_path)

            self.bucket_obj.copy_blob(source_blob, self.bucket_obj, dest_path)
            self.logger.debug(
                f"Copied gs://{source_bucket or self.bucket}/{source_path} to "
                f"gs://{self.bucket}/{dest_path}"
            )
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to copy file: {e}")
            return False

    def set_blob_acl(self, remote_path: str, acl: str = 'private') -> bool:
        """
        Set ACL for a blob

        Args:
            remote_path: Blob name
            acl: ACL type (private, public-read, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket_obj.blob(remote_path)

            if acl == 'public-read':
                blob.make_public()
            elif acl == 'private':
                blob.make_private()
            else:
                self.logger.warning(f"Unsupported ACL type: {acl}")
                return False

            self.logger.debug(f"Set ACL '{acl}' for gs://{self.bucket}/{remote_path}")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to set ACL: {e}")
            return False

    def enable_versioning(self) -> bool:
        """
        Enable versioning for the bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            self.bucket_obj.versioning_enabled = True
            self.bucket_obj.patch()
            self.logger.info(f"Enabled versioning for bucket '{self.bucket}'")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to enable versioning: {e}")
            return False

    def set_lifecycle_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Set lifecycle management policy for the bucket

        Args:
            policy: Lifecycle policy configuration

        Returns:
            True if successful, False otherwise

        Example:
            policy = {
                "rule": [
                    {
                        "action": {"type": "Delete"},
                        "condition": {"age": 30}
                    }
                ]
            }
        """
        try:
            self.bucket_obj.lifecycle_rules = policy.get('rule', [])
            self.bucket_obj.patch()
            self.logger.debug(f"Set lifecycle policy for bucket '{self.bucket}'")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to set lifecycle policy: {e}")
            return False

    def set_cors_policy(self, cors_config: List[Dict[str, Any]]) -> bool:
        """
        Set CORS policy for the bucket

        Args:
            cors_config: List of CORS configuration dictionaries

        Returns:
            True if successful, False otherwise

        Example:
            cors_config = [
                {
                    "origin": ["*"],
                    "method": ["GET", "POST"],
                    "responseHeader": ["Content-Type"],
                    "maxAgeSeconds": 3600
                }
            ]
        """
        try:
            self.bucket_obj.cors = cors_config
            self.bucket_obj.patch()
            self.logger.debug(f"Set CORS policy for bucket '{self.bucket}'")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to set CORS policy: {e}")
            return False
