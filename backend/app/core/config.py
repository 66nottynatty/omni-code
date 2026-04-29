from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://omnicode:omnicode@localhost:5432/omnicode"
    redis_url: str = "redis://localhost:6379"
    github_client_id: str = ""
    github_client_secret: str = ""
    
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
