"""
Unit tests for webserver security module
Tests path validation, API authentication, and IP whitelisting
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import hashlib

from webserver.security import (
    PathValidator,
    APIKeyAuth,
    IPWhitelist,
    generate_api_key
)


class TestPathValidator:
    """Tests for PathValidator class"""

    @pytest.mark.security
    def test_valid_path_in_allowed_directory(self, temp_dir, create_test_file):
        """Test validation of path within allowed directory"""
        # Create test file
        test_file = create_test_file("test.txt", "content")

        validator = PathValidator([temp_dir])
        result = validator.validate_path(str(test_file))

        assert result is not None
        assert result == test_file

    @pytest.mark.security
    def test_path_outside_allowed_directory(self, temp_dir, create_test_file):
        """Test rejection of path outside allowed directory"""
        # Create test file
        test_file = create_test_file("test.txt", "content")

        # Create validator with different directory
        other_dir = temp_dir / "other"
        other_dir.mkdir()
        validator = PathValidator([other_dir])

        result = validator.validate_path(str(test_file))
        assert result is None

    @pytest.mark.security
    def test_directory_traversal_attack(self, temp_dir, create_test_file):
        """Test prevention of directory traversal attacks"""
        # Create nested structure
        allowed_dir = temp_dir / "allowed"
        allowed_dir.mkdir()
        secret_file = temp_dir / "secret.txt"
        secret_file.write_text("secret data")

        validator = PathValidator([allowed_dir])

        # Try to access parent directory
        malicious_path = str(allowed_dir / ".." / "secret.txt")
        result = validator.validate_path(malicious_path)

        # Should be rejected
        assert result is None

    @pytest.mark.security
    def test_nonexistent_file(self, temp_dir):
        """Test rejection of non-existent file"""
        validator = PathValidator([temp_dir])
        result = validator.validate_path(str(temp_dir / "nonexistent.txt"))
        assert result is None

    @pytest.mark.security
    def test_directory_not_file(self, temp_dir):
        """Test rejection of directory (not a file)"""
        validator = PathValidator([temp_dir])
        result = validator.validate_path(str(temp_dir))
        assert result is None

    @pytest.mark.security
    def test_symlink_traversal(self, temp_dir, create_test_file):
        """Test handling of symlinks"""
        # Create file outside allowed directory
        secret_dir = temp_dir / "secret"
        secret_dir.mkdir()
        secret_file = secret_dir / "data.txt"
        secret_file.write_text("secret")

        # Create allowed directory with symlink
        allowed_dir = temp_dir / "allowed"
        allowed_dir.mkdir()
        symlink = allowed_dir / "link.txt"

        try:
            symlink.symlink_to(secret_file)
        except OSError:
            pytest.skip("Symlink creation not supported")

        validator = PathValidator([allowed_dir])

        # Validator should resolve symlink and check actual path
        # This should fail because secret_file is outside allowed_dir
        result = validator.validate_path(str(symlink))
        assert result is None


class TestAPIKeyAuth:
    """Tests for APIKeyAuth class"""

    @pytest.mark.security
    def test_valid_key(self, api_keys):
        """Test validation of valid API key"""
        auth = APIKeyAuth(api_keys)
        assert auth.validate_key(api_keys[0]) is True

    @pytest.mark.security
    def test_invalid_key(self, api_keys):
        """Test rejection of invalid API key"""
        auth = APIKeyAuth(api_keys)
        assert auth.validate_key("wrong-key") is False

    @pytest.mark.security
    def test_empty_key(self, api_keys):
        """Test rejection of empty key"""
        auth = APIKeyAuth(api_keys)
        assert auth.validate_key("") is False
        assert auth.validate_key(None) is False

    @pytest.mark.security
    def test_key_hashing(self, api_keys):
        """Test that keys are hashed for storage"""
        auth = APIKeyAuth(api_keys)

        # Keys should be hashed in storage
        for key in api_keys:
            assert key not in auth.valid_key_hashes
            # But hash should be present
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            assert key_hash in auth.valid_key_hashes

    @pytest.mark.security
    def test_validate_request_bearer_token(self, api_keys):
        """Test validation from Authorization Bearer header"""
        auth = APIKeyAuth(api_keys)

        # Mock request with Bearer token
        request = Mock()
        request.headers = {"Authorization": f"Bearer {api_keys[0]}"}
        request.rel_url.query = {}

        assert auth.validate_request(request) is True

    @pytest.mark.security
    def test_validate_request_api_key_header(self, api_keys):
        """Test validation from X-API-Key header"""
        auth = APIKeyAuth(api_keys)

        request = Mock()
        request.headers = {"X-API-Key": api_keys[1]}
        request.rel_url.query = {}

        assert auth.validate_request(request) is True

    @pytest.mark.security
    def test_validate_request_query_param(self, api_keys):
        """Test validation from query parameter"""
        auth = APIKeyAuth(api_keys)

        request = Mock()
        request.headers = {}
        request.rel_url.query = {"api_key": api_keys[2]}

        assert auth.validate_request(request) is True

    @pytest.mark.security
    def test_validate_request_no_key(self, api_keys):
        """Test rejection when no key provided"""
        auth = APIKeyAuth(api_keys)

        request = Mock()
        request.headers = {}
        request.rel_url.query = {}

        assert auth.validate_request(request) is False


class TestIPWhitelist:
    """Tests for IPWhitelist class"""

    @pytest.mark.security
    def test_allowed_ip(self, allowed_ips):
        """Test validation of allowed IP"""
        whitelist = IPWhitelist(allowed_ips)
        assert whitelist.is_allowed(allowed_ips[0]) is True

    @pytest.mark.security
    def test_disallowed_ip(self, allowed_ips):
        """Test rejection of non-whitelisted IP"""
        whitelist = IPWhitelist(allowed_ips)
        assert whitelist.is_allowed("192.168.99.99") is False

    @pytest.mark.security
    def test_localhost_variations(self):
        """Test localhost IP variations"""
        whitelist = IPWhitelist(["127.0.0.1"])

        # Should allow other 127.x.x.x addresses
        assert whitelist.is_allowed("127.0.0.1") is True
        assert whitelist.is_allowed("127.0.0.2") is True
        assert whitelist.is_allowed("127.1.1.1") is True

    @pytest.mark.security
    def test_docker_network(self):
        """Test Docker network IP range"""
        whitelist = IPWhitelist(["172.17.0.0"])

        # Should allow 172.17.x.x addresses
        assert whitelist.is_allowed("172.17.0.1") is True
        assert whitelist.is_allowed("172.17.0.255") is True
        assert whitelist.is_allowed("172.18.0.1") is False

    @pytest.mark.security
    def test_validate_request_direct_ip(self, allowed_ips):
        """Test validation from direct IP"""
        whitelist = IPWhitelist(allowed_ips)

        request = Mock()
        request.remote = allowed_ips[0]
        request.headers = {}

        assert whitelist.validate_request(request) is True

    @pytest.mark.security
    def test_validate_request_x_real_ip(self, allowed_ips):
        """Test validation from X-Real-IP header"""
        whitelist = IPWhitelist(allowed_ips)

        request = Mock()
        request.remote = "10.0.0.99"  # Different from allowed
        request.headers = {"X-Real-IP": allowed_ips[1]}

        assert whitelist.validate_request(request) is True

    @pytest.mark.security
    def test_validate_request_x_forwarded_for(self, allowed_ips):
        """Test validation from X-Forwarded-For header"""
        whitelist = IPWhitelist(allowed_ips)

        request = Mock()
        request.remote = "10.0.0.99"
        request.headers = {"X-Forwarded-For": f"{allowed_ips[2]}, 10.0.0.5"}

        assert whitelist.validate_request(request) is True

    @pytest.mark.security
    def test_validate_request_rejected(self, allowed_ips):
        """Test rejection of non-whitelisted IP"""
        whitelist = IPWhitelist(allowed_ips)

        request = Mock()
        request.remote = "192.168.99.99"
        request.headers = {}

        assert whitelist.validate_request(request) is False


class TestGenerateAPIKey:
    """Tests for generate_api_key function"""

    def test_generate_default_length(self):
        """Test generating API key with default length"""
        key = generate_api_key()
        assert isinstance(key, str)
        assert len(key) == 64  # 32 bytes = 64 hex characters

    def test_generate_custom_length(self):
        """Test generating API key with custom length"""
        key = generate_api_key(16)
        assert isinstance(key, str)
        assert len(key) == 32  # 16 bytes = 32 hex characters

    def test_generate_unique_keys(self):
        """Test that generated keys are unique"""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100  # All unique

    def test_generate_hex_format(self):
        """Test that generated keys are valid hex"""
        key = generate_api_key()
        # Should be valid hex string
        try:
            int(key, 16)
            valid_hex = True
        except ValueError:
            valid_hex = False
        assert valid_hex is True
