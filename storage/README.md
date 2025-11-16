# Object Storage Module

Enterprise-grade cloud object storage abstraction layer for ComfyUI-3D-Pack.

## Overview

This module provides a unified interface for integrating with multiple cloud object storage providers:

- **AWS S3** - Amazon Simple Storage Service
- **MinIO** - Self-hosted S3-compatible storage
- **Google Cloud Storage (GCS)** - Google Cloud Platform storage
- **Azure Blob Storage** - Microsoft Azure storage

## Features

- **Unified API** - Same interface across all providers
- **Multi-cloud Support** - Easy switching between providers
- **Streaming** - Upload/download from streams
- **Metadata** - Attach custom metadata to objects
- **Presigned URLs** - Generate temporary access URLs
- **Directory Sync** - Sync entire directories
- **Error Handling** - Comprehensive error handling and logging

## Installation

Install the required dependencies for your cloud provider:

```bash
# AWS S3
pip install boto3>=1.28.0

# MinIO
pip install minio>=7.2.0

# Google Cloud Storage
pip install google-cloud-storage>=2.10.0

# Azure Blob Storage
pip install azure-storage-blob>=12.19.0

# Or install all providers
pip install boto3 minio google-cloud-storage azure-storage-blob
```

## Quick Start

### Basic Usage

```python
from storage import get_storage_backend

# Create storage backend
storage = get_storage_backend(
    backend_type='s3',
    bucket='my-bucket',
    region='us-east-1',
    access_key='your-access-key',
    secret_key='your-secret-key'
)

# Upload a file
storage.upload_file('local/model.safetensors', 'models/sd_v1.5.safetensors')

# Download a file
storage.download_file('models/sd_v1.5.safetensors', 'local/model.safetensors')

# List files
files = storage.list_files(prefix='models/')

# Check if file exists
if storage.file_exists('models/sd_v1.5.safetensors'):
    print("Model exists!")

# Delete a file
storage.delete_file('old/model.safetensors')
```

## Provider-Specific Setup

### AWS S3

```python
from storage import get_storage_backend

storage = get_storage_backend(
    backend_type='s3',
    bucket='comfyui-models',
    region='us-east-1',
    access_key=os.getenv('AWS_ACCESS_KEY_ID'),
    secret_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
```

**Environment Variables:**
```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
```

### MinIO

```python
storage = get_storage_backend(
    backend_type='minio',
    endpoint='minio.example.com:9000',  # or localhost:9000
    bucket='comfyui-outputs',
    access_key=os.getenv('MINIO_ACCESS_KEY'),
    secret_key=os.getenv('MINIO_SECRET_KEY'),
    use_ssl=True  # Set to False for local development
)
```

**Docker Compose for Local MinIO:**
```yaml
version: '3.8'
services:
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
volumes:
  minio-data:
```

### Google Cloud Storage

```python
storage = get_storage_backend(
    backend_type='gcs',
    bucket='comfyui-assets',
    region='us-central1',
    extra_config={
        'project_id': 'my-gcp-project',
        'credentials_path': '/path/to/service-account-key.json'
    }
)
```

**Authentication:**
1. Create a service account in GCP Console
2. Download the JSON key file
3. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Azure Blob Storage

```python
# Option 1: Using connection string
storage = get_storage_backend(
    backend_type='azure',
    bucket='comfyui-container',  # container name
    extra_config={
        'connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    }
)

# Option 2: Using account name and key
storage = get_storage_backend(
    backend_type='azure',
    bucket='comfyui-container',
    extra_config={
        'account_name': 'mystorageaccount'
    },
    access_key=os.getenv('AZURE_STORAGE_KEY')
)
```

**Environment Variables:**
```bash
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
# OR
AZURE_STORAGE_ACCOUNT=mystorageaccount
AZURE_STORAGE_KEY=your-access-key
```

## Advanced Usage

### Uploading with Metadata

```python
storage.upload_file(
    local_path='models/checkpoint.safetensors',
    remote_path='models/sd_v2.safetensors',
    metadata={
        'version': '2.0',
        'model_type': 'stable-diffusion',
        'created_by': 'training-pipeline'
    }
)
```

### Streaming Uploads

```python
from io import BytesIO

# Upload from in-memory data
data = BytesIO(b"Training configuration data")
storage.upload_stream(
    stream=data,
    remote_path='configs/training.json',
    metadata={'format': 'json'}
)
```

### Generating Presigned URLs

```python
# Generate temporary URL (valid for 1 hour)
url = storage.get_presigned_url(
    remote_path='models/sd_v1.5.safetensors',
    expiration=3600
)

print(f"Download URL: {url}")
# Users can download without authentication for 1 hour
```

### Directory Synchronization

```python
# Sync local directory to cloud storage
stats = storage.sync_directory(
    local_dir='output/renders',
    remote_prefix='production/renders',
    delete=True  # Delete remote files not present locally
)

print(f"Uploaded: {stats['uploaded']}")
print(f"Deleted: {stats['deleted']}")
print(f"Skipped: {stats['skipped']}")
```

### Getting File Metadata

```python
metadata = storage.get_file_metadata('models/sd_v1.5.safetensors')

print(f"Size: {metadata['size'] / 1024 / 1024:.2f} MB")
print(f"Last Modified: {metadata['last_modified']}")
print(f"Content Type: {metadata['content_type']}")
print(f"Custom Metadata: {metadata['metadata']}")
```

### Copying Files

```python
# Copy within same storage
storage.copy_file(
    source_path='models/sd_v1.5.safetensors',
    dest_path='backups/sd_v1.5_backup.safetensors'
)

# Copy from another bucket (S3/Azure)
storage.copy_file(
    source_path='model.safetensors',
    dest_path='models/imported_model.safetensors',
    source_bucket='external-bucket'
)
```

## Configuration Integration

### Using with AppConfig

```python
from config import get_config
from storage import get_storage_backend

# Load configuration
config = get_config()

# Create storage backend from config
if config.cloud_storage.enabled:
    storage = get_storage_backend(
        backend_type=config.cloud_storage.backend_type,
        endpoint=config.cloud_storage.endpoint,
        bucket=config.cloud_storage.bucket,
        region=config.cloud_storage.region,
        access_key=config.cloud_storage.access_key,
        secret_key=config.cloud_storage.secret_key,
        use_ssl=config.cloud_storage.use_ssl
    )
else:
    print("Cloud storage is disabled")
```

### Environment Variables

Configure cloud storage via environment variables:

```bash
# Enable cloud storage
CLOUD_STORAGE_ENABLED=true

# Provider configuration
CLOUD_STORAGE_TYPE=s3  # s3, minio, gcs, azure
CLOUD_STORAGE_BUCKET=comfyui-3d-pack
CLOUD_STORAGE_REGION=us-east-1

# Credentials (varies by provider)
CLOUD_STORAGE_ACCESS_KEY=your-access-key
CLOUD_STORAGE_SECRET_KEY=your-secret-key

# Or use provider-specific env vars
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcs-key.json
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
```

## Use Cases

### Model Storage and Distribution

```python
# Upload trained models
storage.upload_file(
    'checkpoints/trained_model.safetensors',
    'models/production/v1.0.safetensors',
    metadata={'version': '1.0', 'accuracy': '95.2%'}
)

# Download models on inference nodes
if not Path('cache/model.safetensors').exists():
    storage.download_file(
        'models/production/v1.0.safetensors',
        'cache/model.safetensors'
    )
```

### Output Management

```python
# Upload rendered outputs
for output_file in Path('output/batch_001').glob('*.png'):
    remote_path = f"renders/{datetime.now():%Y/%m/%d}/{output_file.name}"
    storage.upload_file(str(output_file), remote_path)

# Generate shareable links
url = storage.get_presigned_url('renders/2024/01/15/image001.png', expiration=86400)
```

### Multi-Region Deployment

```python
# Primary region (US)
us_storage = get_storage_backend(
    backend_type='s3',
    bucket='comfyui-us',
    region='us-east-1'
)

# Secondary region (EU)
eu_storage = get_storage_backend(
    backend_type='s3',
    bucket='comfyui-eu',
    region='eu-west-1'
)

# Replicate critical files
for file in us_storage.list_files(prefix='critical/'):
    temp_path = f'/tmp/{Path(file).name}'
    us_storage.download_file(file, temp_path)
    eu_storage.upload_file(temp_path, file)
```

## Error Handling

```python
from storage import get_storage_backend
from pathlib import Path

try:
    storage = get_storage_backend(
        backend_type='s3',
        bucket='my-bucket'
    )

    # Check before operations
    if storage.file_exists('models/checkpoint.safetensors'):
        storage.download_file('models/checkpoint.safetensors', 'local.safetensors')
    else:
        print("⚠ Model not found in storage")

    # Verify upload success
    if storage.upload_file('local.safetensors', 'backup/model.safetensors'):
        print("✓ Upload successful")
    else:
        print("✗ Upload failed - check logs")

except ImportError as e:
    print(f"Missing required library: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Use Streaming for Large Files** - Avoid loading entire files into memory
2. **Batch Operations** - Upload/download multiple files in parallel
3. **Presigned URLs** - Let clients download directly from storage
4. **Metadata** - Store searchable information with objects
5. **Lifecycle Policies** - Auto-delete or archive old files
6. **CDN Integration** - Use CloudFront (S3) or CDN for frequently accessed files

## Testing

Run the storage tests:

```bash
# Run all storage tests
pytest tests/unit/test_storage.py -v

# Run specific provider tests
pytest tests/unit/test_storage.py::TestS3Storage -v
pytest tests/unit/test_storage.py::TestMinIOStorage -v
pytest tests/unit/test_storage.py::TestGCSStorage -v
pytest tests/unit/test_storage.py::TestAzureStorage -v
```

## Security Best Practices

1. **Never commit credentials** - Use environment variables or secrets management
2. **Use IAM roles** - When possible (EC2, EKS, GKE, AKS)
3. **Enable encryption** - Server-side encryption for stored objects
4. **Bucket policies** - Restrict access with least privilege
5. **Audit logging** - Enable CloudTrail (AWS) or equivalent
6. **Versioning** - Enable versioning for critical data
7. **Presigned URL expiration** - Keep expiration times short

## Troubleshooting

### Connection Issues

```python
# Test connectivity
try:
    files = storage.list_files()
    print(f"✓ Connection successful - {len(files)} files found")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Permission Errors

Ensure your credentials have the following permissions:
- `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` (S3)
- `storage.objects.create`, `storage.objects.get`, `storage.objects.delete` (GCS)
- `Storage Blob Data Contributor` role (Azure)

### Debugging

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('storage')
logger.setLevel(logging.DEBUG)
```

## Examples

See `examples/object_storage_example.py` for complete working examples.

## API Reference

### StorageBackend Methods

All storage backends implement these methods:

- `upload_file(local_path, remote_path, metadata=None)` - Upload a file
- `download_file(remote_path, local_path)` - Download a file
- `delete_file(remote_path)` - Delete a file
- `list_files(prefix="", recursive=True)` - List files
- `file_exists(remote_path)` - Check if file exists
- `get_file_metadata(remote_path)` - Get file metadata
- `get_presigned_url(remote_path, expiration=3600)` - Generate presigned URL
- `upload_stream(stream, remote_path, metadata=None)` - Upload from stream
- `sync_directory(local_dir, remote_prefix, delete=False)` - Sync directory

## License

Apache 2.0 License
