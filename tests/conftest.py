"""
Pytest configuration and shared fixtures
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import pytest
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing"""
    return {
        'huggingface': {
            'token': 'test-token-123'
        },
        'web': {
            'clients_ip': ['127.0.0.1', '0.0.0.0']
        }
    }


@pytest.fixture
def env_vars(monkeypatch):
    """Set up test environment variables"""
    test_vars = {
        'HUGGINGFACE_TOKEN': 'test-hf-token',
        'API_KEYS': 'test-key-1,test-key-2',
        'ALLOWED_IPS': '127.0.0.1,10.0.0.1',
        'LOG_LEVEL': 'DEBUG',
        'ENABLE_AUTH': 'true',
    }
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    return test_vars


@pytest.fixture
def mock_torch(monkeypatch):
    """Mock torch for tests that don't need real GPU"""
    class MockCUDA:
        @staticmethod
        def is_available():
            return False

        @staticmethod
        def device_count():
            return 0

    class MockTorch:
        cuda = MockCUDA()
        device = lambda x: x

    monkeypatch.setattr('torch.cuda', MockCUDA())
    return MockTorch


@pytest.fixture
def sample_ply_content() -> bytes:
    """Sample PLY file content for testing"""
    return b"""ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
end_header
0 0 0
1 0 0
0 1 0
"""


@pytest.fixture
def sample_obj_content() -> str:
    """Sample OBJ file content for testing"""
    return """# Sample OBJ file
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
f 1 2 3
"""


@pytest.fixture
def create_test_file(temp_dir):
    """Factory fixture to create test files"""
    def _create_file(filename: str, content: str = "test content") -> Path:
        filepath = temp_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        return filepath
    return _create_file


@pytest.fixture
def api_keys():
    """Sample API keys for testing"""
    return ['test-api-key-1', 'test-api-key-2', 'secret-key-123']


@pytest.fixture
def allowed_ips():
    """Sample allowed IPs for testing"""
    return ['127.0.0.1', '192.168.1.1', '10.0.0.1']


def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Set test environment marker
    os.environ['TESTING'] = '1'


def pytest_unconfigure(config):
    """Clean up after all tests"""
    # Remove test environment marker
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
