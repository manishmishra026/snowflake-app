import os
import logging
from typing import Any
import snowflake.connector

def _setup_database_session(conn: Any, db: str, schema: str) -> None:
    """Sets database and schema context for the session."""
    try:
        cursor = conn.cursor()
        if db:
            cursor.execute(f'USE DATABASE "{db}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema}"')
    finally:
        cursor.close()

def create_snowflake_connection() -> Any:
    """Creates a Snowflake connection using Service Account credentials with Password Auth."""
    # Ensure settings are loaded from environment (loaded via config.py if running locally)
    
    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_SERVICE_ACCOUNT_USER", "webapp_user").strip()
    password = os.environ.get("SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD", "").strip()
    role = os.environ.get("SNOWFLAKE_SERVICE_ACCOUNT_ROLE") or os.environ.get("SNOWFLAKE_ROLE", "").strip()
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "").strip()
    db = os.environ.get("SNOWFLAKE_DATABASE")
    schema = os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC")
    
    connection_params = {
        "account": account,
        "user": user,
        "password": password,
    }

    if warehouse:
        connection_params["warehouse"] = warehouse

    if role:
        connection_params["role"] = role

    logging.info(f"Connecting to Snowflake. Account={account}, User={user}, Role={role}, Warehouse={warehouse}")
    conn = snowflake.connector.connect(**connection_params)
    _setup_database_session(conn, db, schema)
    return conn
