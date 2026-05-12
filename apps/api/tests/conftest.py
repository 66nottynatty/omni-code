"""
Pytest configuration and fixtures for backend tests.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fakeredis

os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-123456789012"
os.environ["JWT_SECRET"] = "test-jwt-secret-1234567890123456"


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="session")
def Base():
    """Import Base from models."""
    from app.database.models import Base
    return Base


@pytest.fixture(scope="function")
def tables(Base, engine):
    """Create all tables and drop them after test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine, tables):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_redis():
    """Create a fake Redis client for testing."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    return fake_redis


@pytest.fixture
def client(db_session, mock_redis):
    """Create a test client with mocked dependencies."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.environment = "test"
    mock_settings.debug = True
    mock_settings.redis_url = "redis://localhost:6379"
    mock_settings.database_url = "sqlite:///:memory:"
    mock_settings.cors_origins = ["http://localhost:3000"]
    mock_settings.cors_allow_credentials = True
    mock_settings.rate_limit_per_minute = 100
    mock_settings.encryption_key = "test-encryption-key-123456789012"
    mock_settings.jwt_secret = "test-jwt-secret-1234567890123456"
    mock_settings.is_production = False

    with patch("app.core.config.get_settings", return_value=mock_settings):
        with patch("app.database.session.get_settings", return_value=mock_settings):
            with patch("redis.from_url", return_value=mock_redis):
                # Import app after patching
                from main import app
                from app.database.session import get_db

                def override_get_db():
                    try:
                        yield db_session
                    finally:
                        pass

                app.dependency_overrides[get_db] = override_get_db

                with TestClient(app) as test_client:
                    yield test_client

                app.dependency_overrides.clear()


@pytest.fixture
def auth_token():
    """Generate a valid JWT token for testing."""
    from app.core.security import JWTValidator

    validator = JWTValidator("test-jwt-secret-1234567890123456")
    return validator.create_token(subject="test_user_123", expires_delta=None)


@pytest.fixture
def auth_headers(auth_token):
    """Return headers with valid auth token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_task_data():
    """Sample task creation data."""
    return {
        "workspace_id": 1,
        "task_type": "agent_run",
        "payload": {"repo": "test/repo", "instruction": "test instruction"}
    }


@pytest.fixture
def sample_user(db_session):
    """Create a sample user in the database."""
    from app.database.models import User

    user = User(
        github_id="12345",
        username="testuser",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_workspace(db_session, sample_user):
    """Create a sample workspace in the database."""
    from app.database.models import Workspace

    workspace = Workspace(
        owner="testuser",
        repo="test-repo",
        branch="main"
    )
    db_session.add(workspace)
    db_session.commit()
    db_session.refresh(workspace)
    return workspace


@pytest.fixture
def sample_task(db_session, sample_workspace):
    """Create a sample background task in the database."""
    from app.database.models import BackgroundTask

    task = BackgroundTask(
        workspace_id=sample_workspace.id,
        task_type="agent_run",
        payload={"instruction": "test"},
        status="pending"
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task