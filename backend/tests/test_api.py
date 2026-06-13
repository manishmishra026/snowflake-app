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


def test_tables_as_service_account_mocked():
    """Test the /tables-as-service-account endpoint with mocked Snowflake connection."""
    from unittest.mock import patch, MagicMock
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("PUBLIC", "EMPLOYEES"), ("PUBLIC", "ADMIN_EMPLOYEES")]
    mock_conn.cursor.return_value = mock_cursor

    with patch("app.main.get_service_account_connection", return_value=mock_conn):
        response = client.get("/tables-as-service-account")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["tables"][0]["name"] == "EMPLOYEES"
        assert data["tables"][1]["name"] == "ADMIN_EMPLOYEES"


def test_table_data_as_service_account_mocked():
    """Test the /table-data-as-service-account endpoint with mocked Snowflake connection."""
    from unittest.mock import patch, MagicMock
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        (1, "Alice", "Smith", "Engineering", "Developer"),
    ]
    mock_cursor.description = [
        ("EMPLOYEE_ID",), ("FIRST_NAME",), ("LAST_NAME",), ("DEPARTMENT",), ("JOB_TITLE",)
    ]
    mock_conn.cursor.return_value = mock_cursor

    with patch("app.main.get_service_account_connection", return_value=mock_conn):
        response = client.get("/table-data-as-service-account")
        assert response.status_code == 200
        data = response.json()
        assert data["employees"]["success"] is True
        assert data["employees"]["data"][0]["FIRST_NAME"] == "Alice"
        assert data["admin_employees"]["success"] is True

