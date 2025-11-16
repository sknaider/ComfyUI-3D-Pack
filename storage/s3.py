"""
AWS S3 Storage Backend Implementation

Provides integration with Amazon S3 for object storage.
"""

from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from . import StorageBackend, StorageConfig

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """AWS S3 storage backend implementation"""

    def __init__(self, config: StorageConfig):
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3 storage. "
                "Install it with: pip install boto3"
            )

        super().__init__(config)

        # Configure boto3 client
        boto_config = Config(
            region_name=config.region,
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )

        # Create S3 client
        client_kwargs = {
            'config': boto_config,
        }

        if config.endpoint:
            client_kwargs['endpoint_url'] = (
                f"{'https' if config.use_ssl else 'http'}://{config.endpoint}"
            )

        if config.access_key and config.secret_key:
            client_kwargs['aws_access_key_id'] = config.access_key
            client_kwargs['aws_secret_access_key'] = config.secret_key

        self.s3_client = boto3.client('s3', **client_kwargs)
        self.s3_resource = boto3.resource('s3', **client_kwargs)

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            self.logger.info(f"S3 bucket '{self.bucket}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    if self.config.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket,
                            CreateBucketConfiguration={'LocationConstraint': self.config.region}
                        )
                    self.logger.info(f"Created S3 bucket '{self.bucket}'")
                except ClientError as create_error:
                    self.logger.error(f"Failed to create bucket: {create_error}")
            else:
                self.logger.error(f"Error checking bucket: {e}")

    def upload_file(self, local_path: str, remote_path: str,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to S3"""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            self.s3_client.upload_file(
                local_path,
                self.bucket,
                remote_path,
                ExtraArgs=extra_args
            )
            self.logger.debug(f"Uploaded {local_path} to s3://{self.bucket}/{remote_path}")
            return True
        except (ClientError, FileNotFoundError) as e:
            self.logger.error(f"Failed to upload {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from S3"""
        try:
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            self.s3_client.download_file(
                self.bucket,
                remote_path,
                local_path
            )
            self.logger.debug(f"Downloaded s3://{self.bucket}/{remote_path} to {local_path}")
            return True
        except ClientError as e:
            self.logger.error(f"Failed to download {remote_path}: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=remote_path
            )
            self.logger.debug(f"Deleted s3://{self.bucket}/{remote_path}")
            return True
        except ClientError as e:
            self.logger.error(f"Failed to delete {remote_path}: {e}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """List files in S3"""
        try:
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')

            params = {
                'Bucket': self.bucket,
                'Prefix': prefix,
            }
            if not recursive:
                params['Delimiter'] = '/'

            for page in paginator.paginate(**params):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append(obj['Key'])

            return files
        except ClientError as e:
            self.logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=remote_path)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            self.logger.error(f"Error checking if file exists: {e}")
            return False

    def get_file_metadata(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file in S3"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket,
                Key=remote_path
            )
            return {
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
            }
        except ClientError as e:
            self.logger.error(f"Failed to get metadata for {remote_path}: {e}")
            return None

    def get_presigned_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for temporary access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': remote_path
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            self.logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def upload_stream(self, stream: BinaryIO, remote_path: str,
                     metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload data from a stream to S3"""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            self.s3_client.upload_fileobj(
                stream,
                self.bucket,
                remote_path,
                ExtraArgs=extra_args
            )
            self.logger.debug(f"Uploaded stream to s3://{self.bucket}/{remote_path}")
            return True
        except ClientError as e:
            self.logger.error(f"Failed to upload stream: {e}")
            return False

    def copy_file(self, source_path: str, dest_path: str,
                 source_bucket: Optional[str] = None) -> bool:
        """
        Copy a file within S3 or from another bucket

        Args:
            source_path: Source object key
            dest_path: Destination object key
            source_bucket: Source bucket (defaults to same bucket)

        Returns:
            True if successful, False otherwise
        """
        try:
            source_bucket = source_bucket or self.bucket
            copy_source = {
                'Bucket': source_bucket,
                'Key': source_path
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=dest_path
            )
            self.logger.debug(
                f"Copied s3://{source_bucket}/{source_path} to "
                f"s3://{self.bucket}/{dest_path}"
            )
            return True
        except ClientError as e:
            self.logger.error(f"Failed to copy file: {e}")
            return False

    def set_object_acl(self, remote_path: str, acl: str = 'private') -> bool:
        """
        Set ACL for an object

        Args:
            remote_path: Object key
            acl: ACL type (private, public-read, public-read-write, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.put_object_acl(
                Bucket=self.bucket,
                Key=remote_path,
                ACL=acl
            )
            self.logger.debug(f"Set ACL '{acl}' for s3://{self.bucket}/{remote_path}")
            return True
        except ClientError as e:
            self.logger.error(f"Failed to set ACL: {e}")
            return False
