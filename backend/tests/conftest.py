"""Pytest configuration and shared fixtures."""

import os
import pytest


def pytest_configure(config):
    """Set required environment variables for tests before any imports."""
    test_env = {
        "AZURE_TENANT_ID": "test-tenant-id",
        "BACKEND_API_CLIENT_ID": "test-api-client-id",
        "ALLOWED_CLIENT_IDS": "test-webapp-client-id,test-daemon-client-id",
        "WEB_APP_CLIENT_ID": "test-webapp-client-id",
        "SNOWFLAKE_ACCOUNT": "test-account",
        "SNOWFLAKE_DATABASE": "test-database",
        "SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD": "test-password",
    }
    for key, value in test_env.items():
        os.environ.setdefault(key, value)
