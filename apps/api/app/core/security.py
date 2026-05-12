"""
Secure per-user GitHub token management with Fernet encryption.
Provides high-level API for token storage, retrieval, and validation.
"""

from cryptography.fernet import Fernet, InvalidToken
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict
import base64
import hashlib
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


class TokenEncryptor:
    """
    Handles Fernet encryption/decryption for sensitive tokens.
    
    Uses AES-128-CBC for symmetric encryption with URL-safe encoding.
    """

    def __init__(self, encryption_key: str):
        self._fernet = self._create_fernet(encryption_key)

    @staticmethod
    def _create_fernet(key: str) -> Fernet:
        """
        Create a Fernet instance from a key string.
        
        The key is hashed and padded to exactly 32 bytes,
        then base64-encoded for Fernet compatibility.
        """
        key_bytes = key.encode('utf-8')
        
        # Hash the key to get consistent 32 bytes
        hashed = hashlib.sha256(key_bytes).digest()
        
        # Pad to 32 bytes if needed (shouldn't happen with SHA256)
        if len(hashed) < 32:
            hashed = hashed.ljust(32, b'\0')
        
        # Create URL-safe base64 key
        padded_key = base64.urlsafe_b64encode(hashed[:32])
        return Fernet(padded_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string and return base64-encoded ciphertext.
        
        Args:
            plaintext: The token to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error("token_encrypt_failed", error=str(e))
            raise ValueError("Failed to encrypt token")

    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt base64-encoded ciphertext and return plaintext.
        
        Args:
            ciphertext: Base64-encoded encrypted token
            
        Returns:
            Decrypted token or None if decryption fails
        """
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.warning("token_decrypt_invalid")
            return None
        except Exception as e:
            logger.error("token_decrypt_failed", error=str(e))
            return None

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet-compatible encryption key."""
        return Fernet.generate_key().decode('utf-8')


class JWTValidator:
    """
    Handles JWT token validation for API requests.
    
    Supports standard JWT operations with configurable
    expiration and additional claims.
    """

    def __init__(self, secret: str, algorithm: str = "HS256"):
        self._secret = secret
        self._algorithm = algorithm

    def create_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict] = None,
    ) -> str:
        """
        Create a new JWT token.
        
        Args:
            subject: The token subject (typically user ID)
            expires_delta: Token validity duration (default: 24 hours)
            additional_claims: Extra claims to include
            
        Returns:
            Encoded JWT string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        now = datetime.utcnow()
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + expires_delta,
        }
        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: The JWT string to verify
            
        Returns:
            Payload dict if valid, None otherwise
        """
        try:
            return jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm]
            )
        except JWTError as e:
            logger.debug("jwt_verify_failed", error=str(e))
            return None

    def get_subject(self, token: str) -> Optional[str]:
        """Extract subject from a token."""
        payload = self.verify_token(token)
        return payload.get("sub") if payload else None

    def refresh_token(self, token: str, expires_delta: Optional[timedelta] = None) -> Optional[str]:
        """
        Refresh an existing valid token.
        
        Args:
            token: The current JWT string
            expires_delta: New expiration duration
            
        Returns:
            New JWT string if valid, None otherwise
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        return self.create_token(
            subject=payload.get("sub"),
            expires_delta=expires_delta,
            additional_claims={k: v for k, v in payload.items() 
                              if k not in ("sub", "iat", "exp")}
        )


class TokenValidator:
    """
    Validates GitHub tokens by making API calls.
    """

    def __init__(self):
        pass

    def validate_github_token(self, token: str) -> Dict:
        """
        Validate a GitHub token and return user info.
        
        Args:
            token: GitHub personal access token
            
        Returns:
            Dict with validation result and user info
        """
        try:
            from github import Github
            
            g = Github(token)
            user = g.get_user()
            
            return {
                "valid": True,
                "username": user.login,
                "user_id": user.id,
                "avatar_url": user.avatar_url
            }
        except Exception as e:
            logger.warning("github_token_invalid", error=str(e))
            return {
                "valid": False,
                "error": str(e)
            }


class SecurityManager:
    """
    High-level security operations combining encryption and JWT.
    
    Provides a unified API for token management across the application.
    """

    def __init__(self):
        settings = get_settings()
        self._token_encryptor = TokenEncryptor(settings.encryption_key)
        self._jwt_validator = JWTValidator(settings.jwt_secret)
        self._token_validator = TokenValidator()

    # ========== GitHub Token Operations ==========

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a sensitive token (e.g., GitHub access token).
        
        Args:
            token: The token to encrypt
            
        Returns:
            Encrypted token string
        """
        return self._token_encryptor.encrypt(token)

    def decrypt_token(self, encrypted_token: str) -> Optional[str]:
        """
        Decrypt a stored token.
        
        Args:
            encrypted_token: Encrypted token string
            
        Returns:
            Decrypted token or None
        """
        return self._token_encryptor.decrypt(encrypted_token)

    def validate_and_store_token(self, token: str) -> Dict:
        """
        Validate a GitHub token and return encrypted version.
        
        Args:
            token: GitHub personal access token
            
        Returns:
            Dict with validation result and encrypted token
        """
        validation = self._token_validator.validate_github_token(token)
        
        if validation.get("valid"):
            encrypted = self.encrypt_token(token)
            return {
                "valid": True,
                "encrypted_token": encrypted,
                "username": validation.get("username")
            }
        
        return {
            "valid": False,
            "error": validation.get("error", "Invalid token")
        }

    # ========== API Token Operations ==========

    def create_api_token(
        self,
        user_id: str,
        expires_hours: int = 24,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """
        Create a JWT API token for a user.
        
        Args:
            user_id: User identifier
            expires_hours: Token validity in hours
            additional_claims: Extra claims
            
        Returns:
            JWT string
        """
        return self._jwt_validator.create_token(
            subject=user_id,
            expires_delta=timedelta(hours=expires_hours),
            additional_claims=additional_claims
        )

    def verify_api_token(self, token: str) -> Optional[str]:
        """
        Verify an API token and return user_id.
        
        Args:
            token: JWT string
            
        Returns:
            User ID if valid, None otherwise
        """
        return self._jwt_validator.get_subject(token)

    def validate_bearer_token(self, authorization: Optional[str]) -> Optional[str]:
        """
        Extract and validate user from Authorization: Bearer header.
        
        Args:
            authorization: Full Authorization header value
            
        Returns:
            User ID if valid, None otherwise
        """
        if not authorization:
            return None

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return self.verify_api_token(parts[1])

    def refresh_api_token(self, token: str, expires_hours: int = 24) -> Optional[str]:
        """
        Refresh an API token.
        
        Args:
            token: Current JWT string
            expires_hours: New expiration
            
        Returns:
            New JWT string if valid, None otherwise
        """
        return self._jwt_validator.refresh_token(token, timedelta(hours=expires_hours))

    # ========== Token Generation ==========

    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new Fernet encryption key."""
        return TokenEncryptor.generate_key()

    @staticmethod
    def generate_jwt_secret() -> str:
        """Generate a secure random string for JWT signing."""
        import secrets
        return secrets.token_urlsafe(64)

    # ========== User Session Management ==========

    def create_session_token(
        self,
        user_id: int,
        workspace_id: Optional[int] = None,
        expires_hours: int = 24
    ) -> str:
        """
        Create a session token with optional workspace context.
        
        Args:
            user_id: User identifier
            workspace_id: Optional workspace ID
            expires_hours: Session duration
            
        Returns:
            JWT string
        """
        claims = {"type": "session"}
        if workspace_id:
            claims["workspace_id"] = workspace_id
        
        return self.create_api_token(
            user_id=str(user_id),
            expires_hours=expires_hours,
            additional_claims=claims
        )

    def verify_session_token(self, token: str) -> Optional[Dict]:
        """
        Verify a session token and extract claims.
        
        Args:
            token: JWT string
            
        Returns:
            Dict with user_id, workspace_id, etc. or None
        """
        payload = self._jwt_validator.verify_token(token)
        if not payload:
            return None
        
        return {
            "user_id": payload.get("sub"),
            "workspace_id": payload.get("workspace_id"),
            "token_type": payload.get("type"),
            "expires": payload.get("exp")
        }


# Global security manager instance
security_manager = SecurityManager()


def get_token_encryptor() -> TokenEncryptor:
    """Get the token encryptor instance."""
    return security_manager._token_encryptor


def get_jwt_validator() -> JWTValidator:
    """Get the JWT validator instance."""
    return security_manager._jwt_validator