"""Pytest configuration and shared fixtures."""

import os
import pytest


def pytest_configure(config):
    """Set required environment variables for tests before any imports."""
    test_env = {
        # Service principal (required by Settings in main.py)
        "AZURE_TENANT_ID": "test-tenant-id",
        "AZURE_CLIENT_ID": "test-client-id",
        "AZURE_CLIENT_SECRET": "test-client-secret",
        "SNOWFLAKE_ACCOUNT": "test-account",
        "SNOWFLAKE_DATABASE": "test-database",
        "SNOWFLAKE_APPLICATION_ID_URI": "https://test.snowflakecomputing.com",
    }
    for key, value in test_env.items():
        os.environ.setdefault(key, value)
