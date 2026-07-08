import pytest
import queue
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.core.config import settings
from app.db.connection import SimpleConnectionPool, PooledConnectionProxy, _setup_database_session
from app.db.security import (
    _decode_unverified_payload, 
    _validate_token_claims_and_client, 
    verify_api_token
)
from jwt import InvalidTokenError
import jwt

# ==============================================================================
# CONNECTION POOL TESTS
# ==============================================================================
def test_connection_pool_get_and_release():
    mock_creator = MagicMock()
    mock_conn = MagicMock()
    mock_conn.is_closed.return_value = False
    mock_creator.return_value = mock_conn

    pool = SimpleConnectionPool(mock_creator, max_size=2)

    # Acquire connection
    conn1 = pool.get_connection()
    assert isinstance(conn1, PooledConnectionProxy)
    mock_creator.assert_called_once()
    assert pool._created_count == 1

    # Acquire second connection
    _ = pool.get_connection()
    assert pool._created_count == 2

    # Attempting to get third connection should block and raise exception on queue timeout
    with pytest.raises(HTTPException) as excinfo:
        with patch.object(pool._pool, "get", side_effect=queue.Empty):
            pool._wait_for_connection()
    assert excinfo.value.status_code == 503

    # Release connection
    conn1.close()
    assert pool._pool.qsize() == 1

def test_setup_database_session_success():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    _setup_database_session(mock_conn, "test_db", "test_schema")
    mock_cursor.execute.assert_any_call('USE DATABASE "test_db"')
    mock_cursor.execute.assert_any_call('USE SCHEMA "test_schema"')
    mock_cursor.close.assert_called_once()

def test_setup_database_session_failure():
    mock_conn = MagicMock()
    mock_conn.cursor.side_effect = Exception("failed to get cursor")

    with pytest.raises(Exception):
        _setup_database_session(mock_conn, "test_db", "test_schema")

# ==============================================================================
# SECURITY UTILS TESTS
# ==============================================================================
def test_decode_unverified_payload_valid():
    token = jwt.encode({"ver": "2.0", "iss": "test-issuer"}, "secret", algorithm="HS256")
    payload = _decode_unverified_payload(token)
    assert payload["ver"] == "2.0"

def test_decode_unverified_payload_invalid():
    with pytest.raises(InvalidTokenError):
        _decode_unverified_payload("invalid_token_format")

def test_validate_token_claims_and_client_valid():
    with patch.object(settings, "ALLOWED_CLIENT_IDS", "test-client-id"):
        with patch.object(settings, "AZURE_TENANT_ID", "test-tenant-id"):
            azure_issuer = f"https://sts.windows.net/test-tenant-id/"
            payload = {
                "iss": azure_issuer,
                "scp": "user_impersonation",
                "appid": "test-client-id"
            }
            # Should not raise exception
            _validate_token_claims_and_client(payload)

def test_validate_token_claims_and_client_invalid_issuer():
    with patch.object(settings, "ALLOWED_CLIENT_IDS", "test-client-id"):
        payload = {
            "iss": "invalid-issuer",
            "scp": "user_impersonation",
            "appid": "test-client-id"
        }
        with pytest.raises(InvalidTokenError):
            _validate_token_claims_and_client(payload)
