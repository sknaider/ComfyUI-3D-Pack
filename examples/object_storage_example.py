"""
Object Storage Integration Examples

This file demonstrates how to use the object storage abstraction layer
with different cloud providers (S3, MinIO, GCS, Azure).
"""

import os
from pathlib import Path
from storage import get_storage_backend, StorageConfig


def example_s3_storage():
    """Example: Using AWS S3"""
    print("\n=== AWS S3 Example ===")

    # Initialize S3 storage
    storage = get_storage_backend(
        backend_type='s3',
        bucket='comfyui-models',
        region='us-east-1',
        access_key=os.getenv('AWS_ACCESS_KEY_ID'),
        secret_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    # Upload a file
    success = storage.upload_file(
        local_path='models/checkpoints/model.safetensors',
        remote_path='checkpoints/stable-diffusion/model.safetensors',
        metadata={'version': '1.0', 'type': 'checkpoint'}
    )
    print(f"Upload successful: {success}")

    # Download a file
    success = storage.download_file(
        remote_path='checkpoints/stable-diffusion/model.safetensors',
        local_path='local/model.safetensors'
    )
    print(f"Download successful: {success}")

    # List files
    files = storage.list_files(prefix='checkpoints/')
    print(f"Found {len(files)} files in checkpoints/")

    # Get presigned URL for sharing
    url = storage.get_presigned_url(
        remote_path='checkpoints/stable-diffusion/model.safetensors',
        expiration=3600  # 1 hour
    )
    print(f"Presigned URL: {url}")


def example_minio_storage():
    """Example: Using MinIO (self-hosted S3-compatible)"""
    print("\n=== MinIO Example ===")

    # Initialize MinIO storage
    storage = get_storage_backend(
        backend_type='minio',
        endpoint='minio.example.com:9000',  # or 'localhost:9000' for local
        bucket='comfyui-outputs',
        access_key=os.getenv('MINIO_ACCESS_KEY'),
        secret_key=os.getenv('MINIO_SECRET_KEY'),
        use_ssl=True
    )

    # Upload rendered output
    success = storage.upload_file(
        local_path='output/render_001.png',
        remote_path='renders/2024/01/render_001.png'
    )
    print(f"Upload successful: {success}")

    # Sync entire directory
    stats = storage.sync_directory(
        local_dir='output/batch_001',
        remote_prefix='renders/batch_001',
        delete=False  # Don't delete remote files
    )
    print(f"Synced directory: {stats}")


def example_gcs_storage():
    """Example: Using Google Cloud Storage"""
    print("\n=== Google Cloud Storage Example ===")

    # Initialize GCS storage
    storage = get_storage_backend(
        backend_type='gcs',
        bucket='comfyui-assets',
        region='us-central1',
        extra_config={
            'project_id': 'my-gcp-project',
            'credentials_path': '/path/to/service-account-key.json'
        }
    )

    # Upload with metadata
    from io import BytesIO

    data = BytesIO(b"Training data content")
    success = storage.upload_stream(
        stream=data,
        remote_path='training/data.bin',
        metadata={'format': 'binary', 'version': '2.0'}
    )
    print(f"Stream upload successful: {success}")

    # Check if file exists
    exists = storage.file_exists('training/data.bin')
    print(f"File exists: {exists}")

    # Get metadata
    metadata = storage.get_file_metadata('training/data.bin')
    print(f"File metadata: {metadata}")


def example_azure_storage():
    """Example: Using Azure Blob Storage"""
    print("\n=== Azure Blob Storage Example ===")

    # Initialize Azure storage
    storage = get_storage_backend(
        backend_type='azure',
        bucket='comfyui-container',  # container name in Azure
        extra_config={
            'connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            # OR use account_name and access_key:
            # 'account_name': 'mystorageaccount',
        },
        access_key=os.getenv('AZURE_STORAGE_KEY')  # if not using connection_string
    )

    # Upload file
    success = storage.upload_file(
        local_path='assets/texture.png',
        remote_path='textures/material_001.png'
    )
    print(f"Upload successful: {success}")

    # List all textures
    textures = storage.list_files(prefix='textures/')
    print(f"Found {len(textures)} textures")

    # Delete old file
    success = storage.delete_file('textures/old_material.png')
    print(f"Delete successful: {success}")


def example_multi_cloud_sync():
    """Example: Sync between different cloud providers"""
    print("\n=== Multi-Cloud Sync Example ===")

    # Primary storage (S3)
    primary = get_storage_backend(
        backend_type='s3',
        bucket='primary-bucket',
        region='us-east-1'
    )

    # Backup storage (GCS)
    backup = get_storage_backend(
        backend_type='gcs',
        bucket='backup-bucket',
        region='us-central1'
    )

    # Sync specific files from primary to backup
    files_to_backup = primary.list_files(prefix='critical/')

    for file_path in files_to_backup:
        # Download from primary
        temp_file = f'/tmp/{Path(file_path).name}'
        if primary.download_file(file_path, temp_file):
            # Upload to backup
            backup.upload_file(temp_file, file_path)
            print(f"Backed up: {file_path}")

            # Clean up temp file
            Path(temp_file).unlink()


def example_config_based_storage():
    """Example: Using configuration object"""
    print("\n=== Config-Based Storage Example ===")

    # Create configuration
    config = StorageConfig(
        backend_type='s3',
        bucket='my-bucket',
        region='eu-west-1',
        access_key=os.getenv('AWS_ACCESS_KEY_ID'),
        secret_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        use_ssl=True,
        extra_config={
            'max_retries': 3,
            'timeout': 300
        }
    )

    # Create storage backend from config
    from storage.s3 import S3Storage
    storage = S3Storage(config)

    # Use storage
    files = storage.list_files()
    print(f"Total files: {len(files)}")


def example_model_storage_workflow():
    """Example: Complete workflow for model storage and retrieval"""
    print("\n=== Model Storage Workflow ===")

    # Initialize storage
    storage = get_storage_backend(
        backend_type='minio',
        endpoint='localhost:9000',
        bucket='comfyui-models',
        access_key='minioadmin',
        secret_key='minioadmin',
        use_ssl=False
    )

    # 1. Upload new model
    model_path = 'models/checkpoints/sd_v1.5.safetensors'
    remote_path = 'stable-diffusion/v1.5/model.safetensors'

    print("Uploading model...")
    if storage.upload_file(model_path, remote_path, metadata={
        'model_type': 'stable-diffusion',
        'version': '1.5',
        'format': 'safetensors'
    }):
        print("✓ Model uploaded successfully")

    # 2. Check if model exists before downloading
    if storage.file_exists(remote_path):
        print("✓ Model exists in storage")

        # 3. Get model information
        metadata = storage.get_file_metadata(remote_path)
        print(f"Model size: {metadata['size'] / 1024 / 1024:.2f} MB")
        print(f"Model metadata: {metadata['metadata']}")

        # 4. Download model if needed
        local_cache = 'cache/models/sd_v1.5.safetensors'
        if not Path(local_cache).exists():
            print("Downloading model to cache...")
            storage.download_file(remote_path, local_cache)
            print("✓ Model cached locally")
        else:
            print("✓ Model already in cache")

    # 5. List all available models
    all_models = storage.list_files(prefix='stable-diffusion/')
    print(f"\nAvailable models: {len(all_models)}")
    for model in all_models[:5]:  # Show first 5
        print(f"  - {model}")


def example_error_handling():
    """Example: Proper error handling"""
    print("\n=== Error Handling Example ===")

    try:
        storage = get_storage_backend(
            backend_type='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        # Try to download non-existent file
        if storage.file_exists('nonexistent.txt'):
            storage.download_file('nonexistent.txt', 'local.txt')
        else:
            print("⚠ File does not exist in storage")

        # Try to upload file with error handling
        file_path = 'important_data.bin'
        if Path(file_path).exists():
            success = storage.upload_file(file_path, 'backups/data.bin')
            if success:
                print("✓ Upload successful")
            else:
                print("✗ Upload failed - check logs")
        else:
            print(f"⚠ Local file not found: {file_path}")

    except ImportError as e:
        print(f"✗ Missing required library: {e}")
        print("Install with: pip install boto3 minio google-cloud-storage azure-storage-blob")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


if __name__ == '__main__':
    """
    Run examples based on available credentials.
    Set environment variables:
        - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY for S3
        - MINIO_ACCESS_KEY, MINIO_SECRET_KEY for MinIO
        - GOOGLE_APPLICATION_CREDENTIALS for GCS
        - AZURE_STORAGE_CONNECTION_STRING for Azure
    """

    print("ComfyUI-3D-Pack Object Storage Examples")
    print("=" * 50)

    # Run examples (comment out unavailable providers)
    try:
        if os.getenv('AWS_ACCESS_KEY_ID'):
            example_s3_storage()
    except Exception as e:
        print(f"S3 example failed: {e}")

    try:
        if os.getenv('MINIO_ACCESS_KEY'):
            example_minio_storage()
            example_model_storage_workflow()
    except Exception as e:
        print(f"MinIO example failed: {e}")

    try:
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            example_gcs_storage()
    except Exception as e:
        print(f"GCS example failed: {e}")

    try:
        if os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
            example_azure_storage()
    except Exception as e:
        print(f"Azure example failed: {e}")

    # Always run these examples
    try:
        example_config_based_storage()
        example_error_handling()
    except Exception as e:
        print(f"Example failed: {e}")

    print("\n" + "=" * 50)
    print("Examples completed!")
