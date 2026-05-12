"""
Tests for the security utilities.
"""

import pytest
from datetime import timedelta
from jose import jwt

from app.core.security import TokenEncryptor, JWTValidator, SecurityManager


class TestTokenEncryptor:
    """Test cases for TokenEncryptor."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        key = "test-encryption-key-123456789012"
        encryptor = TokenEncryptor(key)

        plaintext = "my-secret-token-12345"
        encrypted = encryptor.encrypt(plaintext)

        assert encrypted != plaintext
        assert encryptor.decrypt(encrypted) == plaintext

    def test_different_encryptions_for_same_plaintext(self):
        """Test that same plaintext produces different ciphertext (due to IV)."""
        key = "test-encryption-key-123456789012"
        encryptor = TokenEncryptor(key)

        plaintext = "same-text"
        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        # Fernet includes timestamp and IV, so same text produces different output
        assert encrypted1 != encrypted2

    def test_decrypt_invalid_token_returns_none(self):
        """Test that decrypting invalid data returns None."""
        key = "test-encryption-key-123456789012"
        encryptor = TokenEncryptor(key)

        result = encryptor.decrypt("invalid-ciphertext")
        assert result is None

    def test_generate_key_produces_valid_key(self):
        """Test that generate_key produces a valid key."""
        key = TokenEncryptor.generate_key()

        # Should be able to create encryptor with generated key
        encryptor = TokenEncryptor(key)
        encrypted = encryptor.encrypt("test")
        assert encryptor.decrypt(encrypted) == "test"


class TestJWTValidator:
    """Test cases for JWTValidator."""

    def test_create_and_verify_token(self):
        """Test token creation and verification."""
        secret = "test-secret-key-1234567890123456"
        validator = JWTValidator(secret)

        token = validator.create_token(
            subject="user123",
            expires_delta=timedelta(hours=1),
        )

        payload = validator.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"

    def test_verify_invalid_token_returns_none(self):
        """Test that invalid token returns None."""
        secret = "test-secret-key-1234567890123456"
        validator = JWTValidator(secret)

        result = validator.verify_token("invalid.token.here")
        assert result is None

    def test_verify_expired_token_returns_none(self):
        """Test that expired token returns None."""
        secret = "test-secret-key-1234567890123456"
        validator = JWTValidator(secret)

        token = validator.create_token(
            subject="user123",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        result = validator.verify_token(token)
        assert result is None

    def test_create_token_with_additional_claims(self):
        """Test token creation with extra claims."""
        secret = "test-secret-key-1234567890123456"
        validator = JWTValidator(secret)

        token = validator.create_token(
            subject="user123",
            additional_claims={"role": "admin", "workspace": "ws1"},
        )

        payload = validator.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["workspace"] == "ws1"

    def test_get_subject(self):
        """Test extracting subject from token."""
        secret = "test-secret-key-1234567890123456"
        validator = JWTValidator(secret)

        token = validator.create_token(subject="user456")
        subject = validator.get_subject(token)

        assert subject == "user456"

    def test_get_subject_invalid_token(self):
        """Test that invalid token returns None for subject."""
        secret = "test-secret-key-1234567890123456"
        validator = JWTValidator(secret)

        subject = validator.get_subject("invalid.token")
        assert subject is None


class TestSecurityManager:
    """Test cases for SecurityManager with mocked settings."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for SecurityManager."""
        from unittest.mock import MagicMock
        settings = MagicMock()
        settings.encryption_key = "test-key-12345678901234567890"
        settings.jwt_secret = "test-jwt-secret-1234567890123456"
        return settings

    def test_encrypt_and_decrypt_token(self, mock_settings):
        """Test token encryption and decryption via SecurityManager."""
        with pytest.mock.patch("app.core.security.get_settings", return_value=mock_settings):
            manager = SecurityManager()

            original = "github-oauth-token-123456"
            encrypted = manager.encrypt_token(original)
            decrypted = manager.decrypt_token(encrypted)

            assert encrypted != original
            assert decrypted == original

    def test_create_and_verify_api_token(self, mock_settings):
        """Test API token creation and verification."""
        with pytest.mock.patch("app.core.security.get_settings", return_value=mock_settings):
            manager = SecurityManager()

            token = manager.create_api_token("user789", expires_hours=2)
            user_id = manager.verify_api_token(token)

            assert user_id == "user789"

    def test_validate_bearer_token_valid(self, mock_settings):
        """Test valid Bearer token validation."""
        with pytest.mock.patch("app.core.security.get_settings", return_value=mock_settings):
            manager = SecurityManager()

            token = manager.create_api_token("user123")
            user_id = manager.validate_bearer_token(f"Bearer {token}")

            assert user_id == "user123"

    def test_validate_bearer_token_invalid_format(self, mock_settings):
        """Test invalid format returns None."""
        with pytest.mock.patch("app.core.security.get_settings", return_value=mock_settings):
            manager = SecurityManager()

            assert manager.validate_bearer_token("InvalidFormat") is None
            assert manager.validate_bearer_token("Basic token") is None
            assert manager.validate_bearer_token("") is None

    def test_validate_bearer_token_invalid_token(self, mock_settings):
        """Test invalid token returns None."""
        with pytest.mock.patch("app.core.security.get_settings", return_value=mock_settings):
            manager = SecurityManager()

            result = manager.validate_bearer_token("Bearer invalid.token.here")
            assert result is None