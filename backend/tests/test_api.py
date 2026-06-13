"""Example tests for the Snowflake API."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import TableInfo
from app.db.connection import get_db_connection

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_client_settings():
    """Test the client config settings endpoint."""
    response = client.get("/config/client-settings")
    assert response.status_code == 200
    data = response.json()
    assert "app_insights_connection_string" in data
    assert "client_id" in data
    assert "tenant_id" in data


def test_security_headers():
    """Test that security headers are present."""
    response = client.get("/health")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers


def test_list_tables_mocked():
    """Test the /tables endpoint with mocked connection and service."""
    mock_conn = MagicMock()
    mock_tables = [
        TableInfo(schema_name="PUBLIC", name="EMPLOYEES"),
        TableInfo(schema_name="PUBLIC", name="ADMIN_EMPLOYEES")
    ]
    
    app.dependency_overrides[get_db_connection] = lambda: mock_conn
    try:
        with patch("app.services.snowflake_service.SnowflakeService.list_tables", return_value=(mock_tables, 2)):
            response = client.get("/tables")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            # Notice schema_name is serialized as "schema" in json response
            assert data["tables"][0]["schema"] == "PUBLIC"
            assert data["tables"][0]["name"] == "EMPLOYEES"
    finally:
        app.dependency_overrides.clear()


def test_get_table_data_mocked():
    """Test the /tables/{table_name}/data endpoint with mocked query results."""
    mock_conn = MagicMock()
    mock_tables = [
        TableInfo(schema_name="PUBLIC", name="EMPLOYEES")
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, "Alice", "Smith", "Engineering", "Developer")]
    mock_cursor.description = [
        ("EMPLOYEE_ID",), ("FIRST_NAME",), ("LAST_NAME",), ("DEPARTMENT",), ("JOB_TITLE",)
    ]
    mock_conn.cursor.return_value = mock_cursor

    app.dependency_overrides[get_db_connection] = lambda: mock_conn
    try:
        with patch("app.services.snowflake_service.SnowflakeService.list_tables", return_value=(mock_tables, 1)):
            response = client.get("/tables/EMPLOYEES/data")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["table_name"] == "EMPLOYEES"
            assert data["columns"] == ["EMPLOYEE_ID", "FIRST_NAME", "LAST_NAME", "DEPARTMENT", "JOB_TITLE"]
            assert data["data"][0]["FIRST_NAME"] == "Alice"
    finally:
        app.dependency_overrides.clear()


def test_get_table_data_blocked_by_whitelist():
    """Test that dynamic query fails if the table is not in the whitelist."""
    mock_conn = MagicMock()
    mock_tables = [
        TableInfo(schema_name="PUBLIC", name="EMPLOYEES")
    ]

    app.dependency_overrides[get_db_connection] = lambda: mock_conn
    try:
        with patch("app.services.snowflake_service.SnowflakeService.list_tables", return_value=(mock_tables, 1)):
            response = client.get("/tables/ADMIN_EMPLOYEES/data")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "restricted" in data["error"] or "not found" in data["error"]
    finally:
        app.dependency_overrides.clear()
