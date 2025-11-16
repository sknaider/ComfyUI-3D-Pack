"""
Azure Blob Storage Backend Implementation

Provides integration with Microsoft Azure Blob Storage.
"""

from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path
from datetime import datetime, timedelta

try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
    from azure.core.exceptions import ResourceNotFoundError, AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from . import StorageBackend, StorageConfig

logger = logging.getLogger(__name__)


class AzureStorage(StorageBackend):
    """Azure Blob Storage backend implementation"""

    def __init__(self, config: StorageConfig):
        if not AZURE_AVAILABLE:
            raise ImportError(
                "azure-storage-blob is required for Azure storage. "
                "Install it with: pip install azure-storage-blob"
            )

        super().__init__(config)

        # Azure uses container instead of bucket
        self.container = self.bucket

        # Build connection string or use account URL
        connection_string = config.extra_config.get('connection_string')
        account_name = config.extra_config.get('account_name')

        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
        elif config.endpoint and config.access_key:
            # Use account URL and key
            account_url = f"https://{config.endpoint}"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=config.access_key
            )
        elif account_name and config.access_key:
            # Build URL from account name
            account_url = f"https://{account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=config.access_key
            )
        else:
            raise ValueError(
                "Azure storage requires either connection_string or "
                "(endpoint/account_name + access_key)"
            )

        # Store account key for SAS generation
        self.account_key = config.access_key
        self.account_name = account_name or config.extra_config.get('account_name')

        # Ensure container exists
        self._ensure_container_exists()

    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            self.container_client = self.blob_service_client.get_container_client(
                self.container
            )
            if not self.container_client.exists():
                self.container_client.create_container()
                self.logger.info(f"Created Azure container '{self.container}'")
            else:
                self.logger.info(f"Azure container '{self.container}' exists")
        except AzureError as e:
            self.logger.error(f"Error with container: {e}")

    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )

            with open(local_path, 'rb') as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    metadata=metadata
                )

            self.logger.debug(
                f"Uploaded {local_path} to azure://{self.container}/{remote_path}"
            )
            return True
        except (AzureError, FileNotFoundError) as e:
            self.logger.error(f"Failed to upload {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from Azure Blob Storage"""
        try:
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )

            with open(local_path, 'wb') as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())

            self.logger.debug(
                f"Downloaded azure://{self.container}/{remote_path} to {local_path}"
            )
            return True
        except AzureError as e:
            self.logger.error(f"Failed to download {remote_path}: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )
            blob_client.delete_blob()
            self.logger.debug(f"Deleted azure://{self.container}/{remote_path}")
            return True
        except AzureError as e:
            self.logger.error(f"Failed to delete {remote_path}: {e}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """List files in Azure Blob Storage"""
        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix)

            if recursive:
                return [blob.name for blob in blobs]
            else:
                # Non-recursive: only return blobs at the current level
                files = set()
                for blob in blobs:
                    relative_path = blob.name[len(prefix):] if prefix else blob.name
                    if '/' in relative_path:
                        # This is in a subdirectory, skip it
                        continue
                    files.add(blob.name)
                return list(files)
        except AzureError as e:
            self.logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )
            return blob_client.exists()
        except AzureError as e:
            self.logger.error(f"Error checking if file exists: {e}")
            return False

    def get_file_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file in Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )
            properties = blob_client.get_blob_properties()

            return {
                'size': properties.size,
                'last_modified': properties.last_modified,
                'content_type': properties.content_settings.content_type,
                'etag': properties.etag,
                'metadata': properties.metadata or {},
                'content_md5': properties.content_settings.content_md5,
            }
        except AzureError as e:
            self.logger.error(f"Failed to get metadata for {remote_path}: {e}")
            return None

    def get_presigned_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """Generate a SAS URL for temporary access"""
        try:
            if not self.account_key or not self.account_name:
                self.logger.error("Account key and name required for SAS generation")
                return None

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container,
                blob_name=remote_path,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expiration)
            )

            # Construct full URL with SAS token
            url = f"{blob_client.url}?{sas_token}"
            return url
        except AzureError as e:
            self.logger.error(f"Failed to generate SAS URL: {e}")
            return None

    def upload_stream(self, stream: BinaryIO, remote_path: str,
                     metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload data from a stream to Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )

            blob_client.upload_blob(
                stream,
                overwrite=True,
                metadata=metadata
            )

            self.logger.debug(
                f"Uploaded stream to azure://{self.container}/{remote_path}"
            )
            return True
        except AzureError as e:
            self.logger.error(f"Failed to upload stream: {e}")
            return False

    def copy_file(self, source_path: str, dest_path: str,
                 source_container: Optional[str] = None) -> bool:
        """
        Copy a file within Azure or from another container

        Args:
            source_path: Source blob name
            dest_path: Destination blob name
            source_container: Source container (defaults to same container)

        Returns:
            True if successful, False otherwise
        """
        try:
            source_container = source_container or self.container

            source_blob_client = self.blob_service_client.get_blob_client(
                container=source_container,
                blob=source_path
            )
            dest_blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=dest_path
            )

            # Start copy operation
            dest_blob_client.start_copy_from_url(source_blob_client.url)

            self.logger.debug(
                f"Copied azure://{source_container}/{source_path} to "
                f"azure://{self.container}/{dest_path}"
            )
            return True
        except AzureError as e:
            self.logger.error(f"Failed to copy file: {e}")
            return False

    def set_blob_tier(self, remote_path: str, tier: str = 'Hot') -> bool:
        """
        Set access tier for a blob (Hot, Cool, Archive)

        Args:
            remote_path: Blob name
            tier: Access tier (Hot, Cool, Archive)

        Returns:
            True if successful, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container,
                blob=remote_path
            )
            blob_client.set_standard_blob_tier(tier)
            self.logger.debug(f"Set tier '{tier}' for azure://{self.container}/{remote_path}")
            return True
        except AzureError as e:
            self.logger.error(f"Failed to set blob tier: {e}")
            return False

    def set_container_public_access(self, public_access: str = 'off') -> bool:
        """
        Set public access level for container

        Args:
            public_access: Access level (off, blob, container)

        Returns:
            True if successful, False otherwise
        """
        try:
            from azure.storage.blob import PublicAccess

            access_map = {
                'off': None,
                'blob': PublicAccess.Blob,
                'container': PublicAccess.Container
            }

            if public_access not in access_map:
                self.logger.error(f"Invalid public access level: {public_access}")
                return False

            self.container_client.set_container_access_policy(
                public_access=access_map[public_access]
            )
            self.logger.debug(f"Set public access '{public_access}' for container '{self.container}'")
            return True
        except AzureError as e:
            self.logger.error(f"Failed to set public access: {e}")
            return False

    def enable_versioning(self) -> bool:
        """
        Enable versioning for the storage account

        Note: This requires account-level permissions

        Returns:
            True if successful, False otherwise
        """
        try:
            self.blob_service_client.set_service_properties(
                versioning_enabled=True
            )
            self.logger.info("Enabled versioning for storage account")
            return True
        except AzureError as e:
            self.logger.error(f"Failed to enable versioning: {e}")
            return False
