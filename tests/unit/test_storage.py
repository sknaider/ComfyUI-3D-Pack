"""
Unit tests for object storage backends

Tests the abstraction layer and individual storage implementations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from io import BytesIO

from storage import StorageConfig, get_storage_backend


class TestStorageConfig:
    """Test StorageConfig dataclass"""

    def test_storage_config_defaults(self):
        """Test default values"""
        config = StorageConfig(backend_type='s3')

        assert config.backend_type == 's3'
        assert config.bucket == 'comfyui-3d-pack'
        assert config.region == 'us-east-1'
        assert config.use_ssl is True
        assert config.extra_config == {}

    def test_storage_config_custom(self):
        """Test custom values"""
        config = StorageConfig(
            backend_type='minio',
            endpoint='minio.local:9000',
            bucket='my-bucket',
            region='us-west-1',
            access_key='test-key',
            secret_key='test-secret',
            use_ssl=False
        )

        assert config.backend_type == 'minio'
        assert config.endpoint == 'minio.local:9000'
        assert config.bucket == 'my-bucket'
        assert config.use_ssl is False


class TestStorageFactory:
    """Test storage backend factory"""

    @patch('storage.s3.boto3')
    def test_get_s3_backend(self, mock_boto3):
        """Test creating S3 backend"""
        backend = get_storage_backend(
            backend_type='s3',
            bucket='test-bucket',
            access_key='key',
            secret_key='secret'
        )

        from storage.s3 import S3Storage
        assert isinstance(backend, S3Storage)
        assert backend.bucket == 'test-bucket'

    @patch('storage.minio.Minio')
    def test_get_minio_backend(self, mock_minio):
        """Test creating MinIO backend"""
        backend = get_storage_backend(
            backend_type='minio',
            endpoint='localhost:9000',
            bucket='test-bucket'
        )

        from storage.minio import MinIOStorage
        assert isinstance(backend, MinIOStorage)

    def test_invalid_backend_type(self):
        """Test error on invalid backend type"""
        with pytest.raises(ValueError, match="Unknown storage backend"):
            get_storage_backend(backend_type='invalid')


@patch('storage.s3.boto3')
class TestS3Storage:
    """Test S3 storage backend"""

    def test_upload_file(self, mock_boto3):
        """Test file upload"""
        from storage.s3 import S3Storage

        config = StorageConfig(
            backend_type='s3',
            bucket='test-bucket',
            access_key='key',
            secret_key='secret'
        )
        storage = S3Storage(config)

        # Mock successful upload
        storage.s3_client.upload_file = Mock()

        result = storage.upload_file('/local/file.txt', 'remote/file.txt')

        assert result is True
        storage.s3_client.upload_file.assert_called_once()

    def test_download_file(self, mock_boto3):
        """Test file download"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        # Mock successful download
        storage.s3_client.download_file = Mock()

        with patch('pathlib.Path.mkdir'):
            result = storage.download_file('remote/file.txt', '/local/file.txt')

        assert result is True
        storage.s3_client.download_file.assert_called_once()

    def test_delete_file(self, mock_boto3):
        """Test file deletion"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        storage.s3_client.delete_object = Mock()

        result = storage.delete_file('remote/file.txt')

        assert result is True
        storage.s3_client.delete_object.assert_called_once()

    def test_file_exists_true(self, mock_boto3):
        """Test checking if file exists (true case)"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        storage.s3_client.head_object = Mock()

        result = storage.file_exists('remote/file.txt')

        assert result is True

    def test_file_exists_false(self, mock_boto3):
        """Test checking if file exists (false case)"""
        from storage.s3 import S3Storage
        from botocore.exceptions import ClientError

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        # Mock 404 error
        error_response = {'Error': {'Code': '404'}}
        storage.s3_client.head_object = Mock(
            side_effect=ClientError(error_response, 'HeadObject')
        )

        result = storage.file_exists('remote/file.txt')

        assert result is False

    def test_list_files(self, mock_boto3):
        """Test listing files"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        # Mock paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'file1.txt'},
                    {'Key': 'file2.txt'},
                ]
            }
        ]
        storage.s3_client.get_paginator = Mock(return_value=mock_paginator)

        files = storage.list_files(prefix='test/')

        assert len(files) == 2
        assert 'file1.txt' in files
        assert 'file2.txt' in files

    def test_get_file_metadata(self, mock_boto3):
        """Test getting file metadata"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        # Mock metadata response
        storage.s3_client.head_object = Mock(return_value={
            'ContentLength': 1024,
            'LastModified': '2024-01-01',
            'ContentType': 'text/plain',
            'ETag': '"abc123"',
            'Metadata': {'custom': 'value'}
        })

        metadata = storage.get_file_metadata('remote/file.txt')

        assert metadata is not None
        assert metadata['size'] == 1024
        assert metadata['content_type'] == 'text/plain'
        assert metadata['etag'] == 'abc123'

    def test_get_presigned_url(self, mock_boto3):
        """Test generating presigned URL"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        storage.s3_client.generate_presigned_url = Mock(
            return_value='https://example.com/presigned-url'
        )

        url = storage.get_presigned_url('remote/file.txt', expiration=3600)

        assert url == 'https://example.com/presigned-url'

    def test_upload_stream(self, mock_boto3):
        """Test uploading from stream"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        storage.s3_client.upload_fileobj = Mock()

        stream = BytesIO(b'test data')
        result = storage.upload_stream(stream, 'remote/file.txt')

        assert result is True
        storage.s3_client.upload_fileobj.assert_called_once()


@patch('storage.minio.Minio')
class TestMinIOStorage:
    """Test MinIO storage backend"""

    def test_init_requires_endpoint(self, mock_minio):
        """Test that MinIO requires endpoint"""
        from storage.minio import MinIOStorage

        config = StorageConfig(backend_type='minio')

        with pytest.raises(ValueError, match="MinIO endpoint is required"):
            MinIOStorage(config)

    def test_upload_file(self, mock_minio):
        """Test file upload"""
        from storage.minio import MinIOStorage

        config = StorageConfig(
            backend_type='minio',
            endpoint='localhost:9000',
            bucket='test-bucket'
        )

        with patch('pathlib.Path.exists', return_value=True):
            storage = MinIOStorage(config)
            storage.client.fput_object = Mock()

            result = storage.upload_file('/local/file.txt', 'remote/file.txt')

            assert result is True

    def test_list_files(self, mock_minio):
        """Test listing files"""
        from storage.minio import MinIOStorage

        config = StorageConfig(
            backend_type='minio',
            endpoint='localhost:9000',
            bucket='test-bucket'
        )
        storage = MinIOStorage(config)

        # Mock objects
        mock_obj1 = Mock()
        mock_obj1.object_name = 'file1.txt'
        mock_obj2 = Mock()
        mock_obj2.object_name = 'file2.txt'

        storage.client.list_objects = Mock(return_value=[mock_obj1, mock_obj2])

        files = storage.list_files()

        assert len(files) == 2
        assert 'file1.txt' in files


@patch('storage.gcs.storage')
class TestGCSStorage:
    """Test Google Cloud Storage backend"""

    def test_upload_file(self, mock_gcs):
        """Test file upload"""
        from storage.gcs import GCSStorage

        config = StorageConfig(backend_type='gcs', bucket='test-bucket')

        # Mock GCS client
        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()

        mock_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        with patch('storage.gcs.storage.Client', return_value=mock_client):
            storage = GCSStorage(config)
            result = storage.upload_file('/local/file.txt', 'remote/file.txt')

            # upload_from_filename should be called
            mock_blob.upload_from_filename.assert_called_once()


@patch('storage.azure.BlobServiceClient')
class TestAzureStorage:
    """Test Azure Blob Storage backend"""

    def test_init_with_connection_string(self, mock_azure):
        """Test initialization with connection string"""
        from storage.azure import AzureStorage

        config = StorageConfig(
            backend_type='azure',
            bucket='test-container',
            extra_config={'connection_string': 'test-connection-string'}
        )

        # Mock container exists
        mock_container = Mock()
        mock_container.exists.return_value = True
        mock_azure.return_value.get_container_client.return_value = mock_container

        storage = AzureStorage(config)

        assert storage.container == 'test-container'

    def test_upload_file(self, mock_azure):
        """Test file upload"""
        from storage.azure import AzureStorage

        config = StorageConfig(
            backend_type='azure',
            bucket='test-container',
            extra_config={'connection_string': 'test'}
        )

        # Mock container and blob
        mock_container = Mock()
        mock_container.exists.return_value = True
        mock_blob = Mock()

        mock_service = mock_azure.return_value
        mock_service.get_container_client.return_value = mock_container
        mock_service.get_blob_client.return_value = mock_blob

        with patch('builtins.open', mock_open(read_data=b'test data')):
            storage = AzureStorage(config)
            result = storage.upload_file('/local/file.txt', 'remote/file.txt')

            mock_blob.upload_blob.assert_called_once()


class TestStorageBackendAbstract:
    """Test abstract StorageBackend methods"""

    @patch('storage.s3.boto3')
    def test_sync_directory(self, mock_boto3):
        """Test directory sync functionality"""
        from storage.s3 import S3Storage

        config = StorageConfig(backend_type='s3', bucket='test-bucket')
        storage = S3Storage(config)

        # Mock file operations
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob') as mock_rglob, \
             patch.object(storage, 'upload_file', return_value=True), \
             patch.object(storage, 'list_files', return_value=[]):

            # Mock two files in directory
            mock_file1 = Mock(spec=Path)
            mock_file1.is_file.return_value = True
            mock_file1.relative_to.return_value = Path('file1.txt')

            mock_file2 = Mock(spec=Path)
            mock_file2.is_file.return_value = True
            mock_file2.relative_to.return_value = Path('file2.txt')

            mock_rglob.return_value = [mock_file1, mock_file2]

            stats = storage.sync_directory('/local/dir', 'remote/prefix')

            assert stats['uploaded'] == 2
            assert stats['deleted'] == 0
