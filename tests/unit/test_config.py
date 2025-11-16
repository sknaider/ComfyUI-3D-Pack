"""
Unit tests for config module
Tests configuration loading, validation, and environment variable handling
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from config import (
    ConfigLoader,
    AppConfig,
    SecurityConfig,
    get_config,
    reload_config
)


class TestSecurityConfig:
    """Tests for SecurityConfig dataclass"""

    def test_default_values(self):
        """Test default configuration values"""
        config = SecurityConfig()
        assert config.api_keys == []
        assert config.allowed_origins == ["http://localhost:8188"]
        assert config.allowed_ips == ["127.0.0.1"]
        assert config.enable_auth is True
        assert config.cors_enabled is True

    def test_custom_values(self):
        """Test custom configuration values"""
        config = SecurityConfig(
            api_keys=["key1", "key2"],
            allowed_origins=["https://example.com"],
            allowed_ips=["192.168.1.1"],
            enable_auth=False,
            cors_enabled=False
        )
        assert config.api_keys == ["key1", "key2"]
        assert config.allowed_origins == ["https://example.com"]
        assert config.allowed_ips == ["192.168.1.1"]
        assert config.enable_auth is False
        assert config.cors_enabled is False


class TestConfigLoader:
    """Tests for ConfigLoader class"""

    def test_parse_list_empty(self):
        """Test parsing empty list"""
        loader = ConfigLoader(Path("/tmp"))
        assert loader._parse_list("") == []
        assert loader._parse_list("   ") == []

    def test_parse_list_single(self):
        """Test parsing single item"""
        loader = ConfigLoader(Path("/tmp"))
        assert loader._parse_list("item1") == ["item1"]

    def test_parse_list_multiple(self):
        """Test parsing multiple items"""
        loader = ConfigLoader(Path("/tmp"))
        result = loader._parse_list("item1,item2,item3")
        assert result == ["item1", "item2", "item3"]

    def test_parse_list_with_spaces(self):
        """Test parsing list with extra spaces"""
        loader = ConfigLoader(Path("/tmp"))
        result = loader._parse_list("  item1  ,  item2  ,  item3  ")
        assert result == ["item1", "item2", "item3"]

    def test_get_env_or_legacy_env_priority(self, monkeypatch):
        """Test that environment variables take priority"""
        monkeypatch.setenv("TEST_VAR", "env_value")
        loader = ConfigLoader(Path("/tmp"))
        result = loader._get_env_or_legacy("TEST_VAR", "legacy_value")
        assert result == "env_value"

    def test_get_env_or_legacy_fallback(self):
        """Test fallback to legacy value"""
        loader = ConfigLoader(Path("/tmp"))
        result = loader._get_env_or_legacy("NONEXISTENT_VAR", "legacy_value")
        assert result == "legacy_value"

    @pytest.mark.unit
    def test_load_with_env_vars(self, temp_dir, monkeypatch):
        """Test loading config from environment variables"""
        # Set environment variables
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test-token")
        monkeypatch.setenv("API_KEYS", "key1,key2,key3")
        monkeypatch.setenv("ALLOWED_IPS", "127.0.0.1,10.0.0.1")
        monkeypatch.setenv("ENABLE_AUTH", "true")

        # Create minimal config file
        config_dir = temp_dir / "Configs"
        config_dir.mkdir()
        config_file = config_dir / "system.conf"
        config_file.write_text("web { clients_ip = [] }\nhuggingface { token = \"\" }")

        loader = ConfigLoader(temp_dir)
        config = loader.load()

        assert config.huggingface_token == "test-token"
        assert config.security.api_keys == ["key1", "key2", "key3"]
        assert "127.0.0.1" in config.security.allowed_ips
        assert "10.0.0.1" in config.security.allowed_ips
        assert config.security.enable_auth is True

    @pytest.mark.unit
    def test_load_missing_config_file(self, temp_dir, monkeypatch):
        """Test loading when config file is missing"""
        # Create Configs dir but no file
        config_dir = temp_dir / "Configs"
        config_dir.mkdir()

        loader = ConfigLoader(temp_dir)
        config = loader.load()

        # Should use defaults
        assert isinstance(config, AppConfig)

    @pytest.mark.unit
    def test_validate_config_warnings(self, temp_dir, monkeypatch, caplog):
        """Test configuration validation warnings"""
        # Enable auth but no API keys
        monkeypatch.setenv("ENABLE_AUTH", "true")
        monkeypatch.setenv("API_KEYS", "")

        config_dir = temp_dir / "Configs"
        config_dir.mkdir()
        config_file = config_dir / "system.conf"
        config_file.write_text("web { clients_ip = [] }\nhuggingface { token = \"\" }")

        loader = ConfigLoader(temp_dir)
        config = loader.load()

        # Should log warning about missing API keys
        assert "no API keys are configured" in caplog.text.lower()


class TestAppConfig:
    """Tests for AppConfig dataclass"""

    def test_default_app_config(self):
        """Test default AppConfig initialization"""
        config = AppConfig()
        assert config.huggingface_token is None
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.storage.models_base_path, Path)
        assert isinstance(config.storage.output_base_path, Path)

    def test_custom_app_config(self):
        """Test custom AppConfig initialization"""
        security = SecurityConfig(api_keys=["test-key"])
        config = AppConfig(
            huggingface_token="my-token",
            security=security
        )
        assert config.huggingface_token == "my-token"
        assert config.security.api_keys == ["test-key"]


class TestConfigGlobalFunctions:
    """Tests for global configuration functions"""

    def test_get_config(self, temp_dir, monkeypatch):
        """Test get_config function"""
        # Create minimal config
        config_dir = temp_dir / "Configs"
        config_dir.mkdir()
        config_file = config_dir / "system.conf"
        config_file.write_text("web { clients_ip = [127.0.0.1] }\nhuggingface { token = \"\" }")

        config = get_config(temp_dir)
        assert isinstance(config, AppConfig)

    def test_reload_config(self, temp_dir):
        """Test reload_config function"""
        # Create minimal config
        config_dir = temp_dir / "Configs"
        config_dir.mkdir()
        config_file = config_dir / "system.conf"
        config_file.write_text("web { clients_ip = [127.0.0.1] }\nhuggingface { token = \"\" }")

        # Load once
        config1 = get_config(temp_dir)

        # Reload
        config2 = reload_config(temp_dir)

        # Should return new instance
        assert isinstance(config2, AppConfig)
