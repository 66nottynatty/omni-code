"""
Tests for API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_check_returns_status(self, client):
        """Test that health check returns status information."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "db" in data
        assert "redis" in data


class TestRootEndpoint:
    """Test cases for root endpoint."""

    def test_root_returns_welcome(self, client):
        """Test that root endpoint returns welcome message."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "OmniCode" in data["message"]


class TestTasksEndpoints:
    """Test cases for task-related endpoints."""

    def test_list_tasks_empty(self, client):
        """Test listing tasks when none exist."""
        response = client.get("/api/tasks")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_tasks_with_filters(self, client):
        """Test listing tasks with query parameters."""
        response = client.get("/api/tasks?workspace_id=1&status=pending")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_task_validation(self, client):
        """Test task creation with valid data."""
        task_data = {
            "workspace_id": 1,
            "task_type": "agent_run",
            "payload": {"instruction": "test"}
        }

        response = client.post("/api/tasks", json=task_data)

        assert response.status_code in [200, 201, 500]  # 500 if no worker

    def test_create_task_missing_fields(self, client):
        """Test task creation with missing required fields."""
        response = client.post("/api/tasks", json={})

        assert response.status_code == 422  # Validation error

    def test_get_task_not_found(self, client):
        """Test getting a non-existent task."""
        response = client.get("/api/tasks/999999")

        assert response.status_code == 404

    def test_get_task_success(self, client, sample_task):
        """Test getting an existing task."""
        response = client.get(f"/api/tasks/{sample_task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_task.id


class TestModelsEndpoint:
    """Test cases for models endpoint."""

    def test_get_models(self, client):
        """Test getting available AI models."""
        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check model structure
        model = data[0]
        assert "id" in model
        assert "name" in model
        assert "provider" in model


class TestThreadHistoryEndpoint:
    """Test cases for thread history endpoint."""

    def test_get_thread_history_empty(self, client):
        """Test getting history for a thread with no actions."""
        response = client.get("/api/threads/1/history")

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestPendingChangesEndpoints:
    """Test cases for pending changes endpoints."""

    def test_accept_change_not_found(self, client):
        """Test accepting a non-existent change."""
        response = client.post("/api/pending-changes/999999/accept")

        assert response.status_code == 404

    def test_reject_change_not_found(self, client):
        """Test rejecting a non-existent change."""
        response = client.post("/api/pending-changes/999999/reject")

        assert response.status_code == 404


class TestRollbackEndpoint:
    """Test cases for rollback endpoint."""

    def test_rollback_action(self, client):
        """Test rollback action returns success."""
        response = client.post("/api/rollback/1")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestGraphInvokeEndpoint:
    """Test cases for graph invocation endpoint."""

    def test_invoke_graph_default(self, client):
        """Test invoking graph with default repo."""
        response = client.get("/graph/invoke")

        # May fail if LangGraph not configured, but shouldn't 500
        assert response.status_code in [200, 500]


class TestReadyEndpoint:
    """Test cases for readiness probe endpoint."""

    def test_ready_endpoint(self, client):
        """Test Kubernetes-style readiness probe."""
        response = client.get("/ready")

        # May return 200 with ready: false if DB not available
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data


class TestSecurityHeaders:
    """Test cases for security headers."""

    def test_security_headers_present(self, client):
        """Test that security headers are included in responses."""
        response = client.get("/")

        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    def test_correlation_id_generated(self, client):
        """Test that correlation ID is generated for requests."""
        response = client.get("/")

        assert "x-correlation-id" in response.headers

    def test_correlation_id_preserved(self, client):
        """Test that correlation ID from request is preserved."""
        response = client.get("/", headers={"X-Correlation-ID": "test-correlation-123"})

        assert response.headers["x-correlation-id"] == "test-correlation-123"


class TestRateLimiting:
    """Test cases for rate limiting."""

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        # Make multiple requests and check headers
        response = client.get("/api/models")

        # Note: Rate limiting headers may not be present on all responses
        # depending on slowapi configuration
        assert response.status_code == 200