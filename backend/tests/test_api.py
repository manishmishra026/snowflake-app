"""Example tests for the Snowflake API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_response_schema():
    """Test that health endpoint returns correct schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert isinstance(data["status"], str)


def test_tables_response_schema():
    """Test that tables endpoint returns correct schema."""
    response = client.get("/tables")
    if response.status_code == 200:
        data = response.json()
        assert "tables" in data
        assert "count" in data
        assert isinstance(data["tables"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["tables"])


def test_security_headers():
    """Test that security headers are present."""
    response = client.get("/health")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers


def test_tables_as_user_no_token():
    """Test that tables-as-user endpoint rejects requests without a token."""
    response = client.get("/tables-as-user")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"

