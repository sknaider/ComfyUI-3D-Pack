"""
Security utilities for web server
Provides authentication, path validation, and request security
"""

import os
import secrets
import hashlib
from pathlib import Path
from typing import List, Optional, Set
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class PathValidator:
    """Validates and sanitizes file paths to prevent directory traversal"""

    def __init__(self, allowed_directories: List[Path]):
        """
        Initialize path validator

        Args:
            allowed_directories: List of allowed base directories
        """
        self.allowed_directories = [Path(d).resolve() for d in allowed_directories]
        logger.info(f"Path validator initialized with {len(self.allowed_directories)} allowed directories")

    def validate_path(self, filepath: str) -> Optional[Path]:
        """
        Validate that a file path is safe and within allowed directories

        Args:
            filepath: Path to validate

        Returns:
            Resolved Path if valid, None if invalid

        Security checks:
        - Resolves symlinks and relative paths
        - Ensures path is within allowed directories
        - Checks file exists
        - Prevents directory traversal attacks
        """
        try:
            # Convert to Path and resolve (follows symlinks, removes ..)
            requested_path = Path(filepath).resolve()

            # Check if path exists
            if not requested_path.exists():
                logger.warning(f"Path does not exist: {requested_path}")
                return None

            # Check if path is a file (not directory)
            if not requested_path.is_file():
                logger.warning(f"Path is not a file: {requested_path}")
                return None

            # Verify path is within allowed directories
            for allowed_dir in self.allowed_directories:
                try:
                    # This will raise ValueError if not relative to allowed_dir
                    requested_path.relative_to(allowed_dir)
                    logger.debug(f"Path validated: {requested_path}")
                    return requested_path
                except ValueError:
                    continue

            # Path not in any allowed directory
            logger.warning(
                f"Path traversal attempt detected: {filepath} -> {requested_path}"
            )
            return None

        except (OSError, RuntimeError) as e:
            logger.error(f"Error validating path {filepath}: {e}")
            return None


class APIKeyAuth:
    """Simple API key authentication"""

    def __init__(self, api_keys: List[str]):
        """
        Initialize API key authentication

        Args:
            api_keys: List of valid API keys
        """
        # Store hashed keys for security
        self.valid_key_hashes: Set[str] = set()
        for key in api_keys:
            if key and len(key) > 0:
                self.valid_key_hashes.add(self._hash_key(key))

        logger.info(f"API key auth initialized with {len(self.valid_key_hashes)} keys")

    def _hash_key(self, key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(key.encode()).hexdigest()

    def validate_key(self, key: Optional[str]) -> bool:
        """
        Validate an API key

        Args:
            key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not key:
            return False

        key_hash = self._hash_key(key)
        return key_hash in self.valid_key_hashes

    def validate_request(self, request) -> bool:
        """
        Validate API key from request

        Checks in order:
        1. Authorization header (Bearer token)
        2. X-API-Key header
        3. api_key query parameter

        Args:
            request: aiohttp request object

        Returns:
            True if valid, False otherwise
        """
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if self.validate_key(token):
                return True

        # Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key", "")
        if self.validate_key(api_key_header):
            return True

        # Check query parameter
        api_key_param = request.rel_url.query.get("api_key", "")
        if self.validate_key(api_key_param):
            return True

        return False


class IPWhitelist:
    """IP address whitelist for access control"""

    def __init__(self, allowed_ips: List[str]):
        """
        Initialize IP whitelist

        Args:
            allowed_ips: List of allowed IP addresses
        """
        self.allowed_ips = set(allowed_ips)
        logger.info(f"IP whitelist initialized with {len(self.allowed_ips)} IPs")

    def is_allowed(self, ip: str) -> bool:
        """
        Check if IP is in whitelist

        Args:
            ip: IP address to check

        Returns:
            True if allowed, False otherwise
        """
        # Handle common cases
        if ip in self.allowed_ips:
            return True

        # Handle Docker/proxy scenarios
        if "127.0.0.1" in self.allowed_ips and ip.startswith("127."):
            return True

        if "172.17.0.0" in self.allowed_ips and ip.startswith("172.17."):
            return True

        return False

    def validate_request(self, request) -> bool:
        """
        Validate IP from request

        Handles X-Forwarded-For and X-Real-IP headers for proxy scenarios

        Args:
            request: aiohttp request object

        Returns:
            True if allowed, False otherwise
        """
        # Try to get real IP from headers (for proxy scenarios)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip and self.is_allowed(real_ip):
            return True

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in chain
            first_ip = forwarded_for.split(",")[0].strip()
            if self.is_allowed(first_ip):
                return True

        # Fall back to direct connection IP
        remote_ip = request.remote
        return self.is_allowed(remote_ip)


def generate_api_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure API key

    Args:
        length: Length of the key in bytes

    Returns:
        Hex-encoded API key
    """
    return secrets.token_hex(length)


# Example usage:
if __name__ == "__main__":
    # Generate a new API key
    new_key = generate_api_key()
    print(f"Generated API Key: {new_key}")
    print(f"Add this to your .env file: API_KEYS={new_key}")
