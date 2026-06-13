import os
import logging
from typing import Any, Optional
import snowflake.connector
from fastapi import HTTPException, status, Request
from app.core.config import settings
from app.db.security import get_user_snowflake_connection, refresh_azure_snowflake_token

logger = logging.getLogger("app")

def get_snowflake_connection() -> Any:
    """Create a Snowflake connection using Azure Service Principal OAuth token."""
    try:
        token = refresh_azure_snowflake_token()
        connection_params = {
            "account": settings.SNOWFLAKE_ACCOUNT,
            "authenticator": "oauth",
            "token": token,
        }

        if settings.SNOWFLAKE_WAREHOUSE:
            connection_params["warehouse"] = settings.SNOWFLAKE_WAREHOUSE

        if settings.SNOWFLAKE_ROLE:
            connection_params["role"] = settings.SNOWFLAKE_ROLE

        conn = snowflake.connector.connect(**connection_params)

        # Set database and schema
        _setup_database_session(conn, settings.SNOWFLAKE_DATABASE, settings.SNOWFLAKE_SCHEMA)
        return conn
    except Exception as exc:
        _handle_connection_error("Service Principal", exc)


def get_service_account_connection() -> Any:
    """Create a Snowflake connection using Service Account credentials (user/password)."""
    try:
        user = settings.SNOWFLAKE_SERVICE_ACCOUNT_USER.strip()
        password = settings.SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD.strip()
        role = settings.SNOWFLAKE_SERVICE_ACCOUNT_ROLE.strip()

        if not password:
            raise RuntimeError("SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD env variable is not set")

        connection_params = {
            "account": settings.SNOWFLAKE_ACCOUNT,
            "user": user,
            "password": password,
        }

        if settings.SNOWFLAKE_WAREHOUSE:
            connection_params["warehouse"] = settings.SNOWFLAKE_WAREHOUSE

        if role:
            connection_params["role"] = role
        elif settings.SNOWFLAKE_ROLE:
            connection_params["role"] = settings.SNOWFLAKE_ROLE

        conn = snowflake.connector.connect(**connection_params)

        # Set database and schema
        _setup_database_session(conn, settings.SNOWFLAKE_DATABASE, settings.SNOWFLAKE_SCHEMA)
        return conn
    except Exception as exc:
        _handle_connection_error("Service Account", exc)


def _setup_database_session(conn: Any, db: str, schema: str) -> None:
    try:
        cursor = conn.cursor()
        cursor.execute(f'USE DATABASE "{db}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema}"')
    finally:
        cursor.close()


def _handle_connection_error(flow_name: str, exc: Exception) -> None:
    logger.error("Snowflake connection failed using %s flow: %s", flow_name, exc, exc_info=True)
    if isinstance(exc, (snowflake.connector.DatabaseError, snowflake.connector.ProgrammingError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Database connection failed ({flow_name})",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Unable to connect to database using {flow_name} credentials",
    )


# FastAPI Dependency for abstract database connection
def get_db_connection(request: Request) -> Any:
    """FastAPI dependency that returns a connection using the active auth flow config."""
    flow = settings.SNOWFLAKE_AUTH_FLOW
    logger.info("Initializing database connection using active flow: %s", flow)

    if flow == "user-auth":
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_token = auth_header[7:]  # Remove "Bearer "
        return get_user_snowflake_connection(user_token)
        
    elif flow == "service-account":
        return get_service_account_connection()
        
    else:  # "service-principal"
        return get_snowflake_connection()
