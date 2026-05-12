"""
Application configuration with Pydantic validation and environment security.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with validation for required environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Security keys (required in production)
    encryption_key: str = Field(
        default="",
        description="32-byte URL-safe base64-encoded Fernet encryption key",
    )
    jwt_secret: str = Field(
        default="",
        description="Secret for JWT token signing (should match NEXTAUTH_SECRET)",
    )

    # Database
    database_url: str = Field(
        default="postgresql://omnicode:omnicode@localhost:5432/omnicode",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379")
    redis_cluster: bool = Field(default=False)

    # GitHub OAuth (required in production)
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")
    github_token: str = Field(default="")

    # OpenAI API
    openai_api_key: str = Field(default="")

    # DeepSeek API
    deepseek_api_key: str = Field(default="")

    # CORS configuration
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)

    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)

    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # NextAuth compatibility
    nextauth_url: str = Field(default="http://localhost:3000")

    @field_validator("encryption_key", mode="before")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if not v:
            # Generate a development key if not provided
            if os.getenv("ENVIRONMENT", "development") == "development":
                return "development-key-please-change-in-production"
            raise ValueError("ENCRYPTION_KEY must be set in production")
        if len(v) < 16:
            raise ValueError("ENCRYPTION_KEY must be at least 16 characters")
        return v

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v:
            # Use a development secret if not provided
            if os.getenv("ENVIRONMENT", "development") == "development":
                return "dev-jwt-secret-please-change-in-production"
            raise ValueError("JWT_SECRET must be set in production")
        if len(v) < 16:
            raise ValueError("JWT_SECRET must be at least 16 characters")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    def validate_production(self) -> List[str]:
        """Validate that all required production settings are present."""
        errors = []
        if self.is_production:
            if self.encryption_key == "development-key-please-change-in-production":
                errors.append("ENCRYPTION_KEY must be set in production")
            if self.jwt_secret == "dev-jwt-secret-please-change-in-production":
                errors.append("JWT_SECRET must be set in production")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()