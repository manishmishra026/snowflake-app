import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import requests
import snowflake.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth_user import get_current_user, get_user_snowflake_connection
from app.config import (
    API_TITLE,
    API_VERSION,
    ALLOWED_ORIGINS,
    TOKEN_CACHE_DURATION,
    TOKEN_REFRESH_TIMEOUT,
)

load_dotenv(override=True)

# Configure logging to write both to console and a file in the workspace
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.log")

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("app")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TableInfo(BaseModel):
    """Single table information."""

    schema: str
    name: str


class TablesResponse(BaseModel):
    """Response containing list of tables."""

    tables: list[TableInfo]
    count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str


class TableDataResult(BaseModel):
    """Result of querying a single table."""

    success: bool
    data: Optional[list[Dict[str, Any]]] = None
    error: Optional[str] = None


class TableDataResponse(BaseModel):
    """Response containing data query results for both tables."""

    employees: TableDataResult
    admin_employees: TableDataResult


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.azure_tenant_id = self._get_required("AZURE_TENANT_ID")
        self.azure_client_id = self._get_required("AZURE_CLIENT_ID")
        self.azure_client_secret = self._get_required("AZURE_CLIENT_SECRET")
        self.snowflake_account = self._get_required("SNOWFLAKE_ACCOUNT")
        self.snowflake_database = self._get_required("SNOWFLAKE_DATABASE")
        self.snowflake_schema = self._get_optional("SNOWFLAKE_SCHEMA", "PUBLIC")
        self.snowflake_warehouse = self._get_optional("SNOWFLAKE_WAREHOUSE")
        self.snowflake_role = self._get_optional("SNOWFLAKE_ROLE")
        self.snowflake_application_id_uri = self._get_required("SNOWFLAKE_APPLICATION_ID_URI")

    @staticmethod
    def _get_required(key: str) -> str:
        value = os.getenv(key, "").strip()
        if not value:
            raise RuntimeError(f"Environment variable {key} is required")
        return value

    @staticmethod
    def _get_optional(key: str, default: str = "") -> str:
        return os.getenv(key, default).strip()


settings = Settings()


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

_azure_snowflake_token: Optional[str] = None
_azure_snowflake_token_expires_at: float = 0.0


def get_azure_access_token_for_snowflake() -> str:
    """Obtain Azure access token for Snowflake using client credentials flow."""
    scope = settings.snowflake_application_id_uri
    if not scope.endswith("/.default"):
        scope = f"{scope}/.default"

    token_url = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/token"
    try:
        response = requests.post(
            token_url,
            data={
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "scope": scope,
                "grant_type": "client_credentials",
            },
            timeout=TOKEN_REFRESH_TIMEOUT,
        )
        response.raise_for_status()
    except requests.ConnectionError as exc:
        logger.error("Failed to connect to Azure token endpoint: %s", exc)
        raise RuntimeError("Azure token service unreachable") from exc
    except requests.Timeout as exc:
        logger.error("Azure token request timed out: %s", exc)
        raise RuntimeError("Azure token request timeout") from exc
    except requests.HTTPError as exc:
        logger.error("Azure token request failed: %s - %s", exc.response.status_code, exc.response.text)
        raise RuntimeError(f"Azure token request failed: {exc.response.status_code}") from exc
    except Exception as exc:
        logger.error("Unexpected error during Azure token request: %s", exc)
        raise RuntimeError("Failed to obtain Azure access token") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("Invalid JSON response from Azure: %s", response.text)
        raise RuntimeError("Invalid Azure token response") from exc

    token = payload.get("access_token")
    if not token:
        error_desc = payload.get("error_description", "Unknown error")
        logger.error("No access token in Azure response: %s", error_desc)
        raise RuntimeError(f"Azure token error: {error_desc}")

    return token


def refresh_azure_snowflake_token() -> str:
    """Get or refresh the cached Azure Snowflake access token."""
    global _azure_snowflake_token, _azure_snowflake_token_expires_at

    now = time.time()
    if _azure_snowflake_token and now < _azure_snowflake_token_expires_at:
        remaining = _azure_snowflake_token_expires_at - now
        logger.debug("Using cached service principal token, expires in %.0f seconds", remaining)
        return _azure_snowflake_token

    logger.info("Refreshing Azure Snowflake access token")
    token = get_azure_access_token_for_snowflake()
    _azure_snowflake_token = token
    _azure_snowflake_token_expires_at = now + TOKEN_CACHE_DURATION
    return token


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration and warm up token cache on startup."""
    try:
        logger.info("Application starting...")
        refresh_azure_snowflake_token()
        logger.info("Application initialized successfully")
    except Exception as exc:
        logger.error("Failed to initialize application: %s", exc, exc_info=True)
        raise
    yield
    logger.info("Application shutting down...")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Security headers middleware (registered first, runs as inner middleware)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# CORS middleware (registered after security headers → runs as outer middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Snowflake connection
# ---------------------------------------------------------------------------

def get_snowflake_connection() -> Any:
    """Create a Snowflake connection using Azure OAuth token."""
    try:
        token = refresh_azure_snowflake_token()
        connection_params = {
            "account": settings.snowflake_account,
            "authenticator": "oauth",
            "token": token,
        }

        if settings.snowflake_warehouse:
            connection_params["warehouse"] = settings.snowflake_warehouse

        if settings.snowflake_role:
            connection_params["role"] = settings.snowflake_role

        conn = snowflake.connector.connect(**connection_params)

        # Explicitly set database and schema
        try:
            cursor = conn.cursor()
            cursor.execute(f'USE DATABASE "{settings.snowflake_database}"')
            if settings.snowflake_schema:
                cursor.execute(f'USE SCHEMA "{settings.snowflake_schema}"')
        finally:
            cursor.close()

        return conn
    except snowflake.connector.DatabaseError as exc:
        logger.error("Snowflake database error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Database connection failed",
        ) from exc
    except snowflake.connector.ProgrammingError as exc:
        logger.error("Snowflake programming error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid database or schema",
        ) from exc
    except Exception as exc:
        logger.error("Snowflake connection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to database",
        ) from exc

def get_service_account_connection() -> Any:
    """Create a Snowflake connection using Username and Password authentication."""
    try:
        user = os.getenv("SNOWFLAKE_SERVICE_ACCOUNT_USER", "webapp_user").strip()
        password = os.getenv("SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD", "").strip()
        if not password:
            raise RuntimeError("SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD env variable is not set")

        connection_params = {
            "account": settings.snowflake_account,
            "user": user,
            "password": password,
        }

        if settings.snowflake_warehouse:
            connection_params["warehouse"] = settings.snowflake_warehouse

        service_account_role = os.getenv("SNOWFLAKE_SERVICE_ACCOUNT_ROLE", "").strip()
        if service_account_role:
            connection_params["role"] = service_account_role
        elif settings.snowflake_role:
            connection_params["role"] = settings.snowflake_role

        conn = snowflake.connector.connect(**connection_params)

        # Explicitly set database and schema
        try:
            cursor = conn.cursor()
            cursor.execute(f'USE DATABASE "{settings.snowflake_database}"')
            if settings.snowflake_schema:
                cursor.execute(f'USE SCHEMA "{settings.snowflake_schema}"')
        finally:
            cursor.close()

        return conn
    except snowflake.connector.DatabaseError as exc:
        logger.error("Snowflake database error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Database connection failed",
        ) from exc
    except snowflake.connector.ProgrammingError as exc:
        logger.error("Snowflake programming error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid database or schema",
        ) from exc
    except Exception as exc:
        logger.error("Snowflake connection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to database",
        ) from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/tables", response_model=TablesResponse)
def list_tables() -> TablesResponse:
    """List all tables in the configured database and schema."""
    conn = None
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )
            rows = cursor.fetchall()
            tables = [TableInfo(schema=row[0], name=row[1]) for row in rows]
            logger.info(
                "Retrieved %d tables from %s.%s",
                len(tables),
                settings.snowflake_database,
                settings.snowflake_schema,
            )
            return TablesResponse(tables=tables, count=len(tables))
        finally:
            cursor.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve tables: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tables",
        ) from exc
    finally:
        if conn:
            conn.close()


@app.get("/tables-as-user", response_model=TablesResponse)
def list_tables_as_user(
    request: Request,
    user_claims: Dict[str, Any] = Depends(get_current_user),
) -> TablesResponse:
    """List all tables queried as the authenticated user.

    Requires Azure AD bearer token. Queries Snowflake with user's permissions.
    """
    user_id = user_claims.get("oid") or user_claims.get("sub", "unknown")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user_token = auth_header[7:]  # Remove "Bearer " prefix

    conn = None
    try:
        conn = get_user_snowflake_connection(user_token)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )
            rows = cursor.fetchall()
            tables = [TableInfo(schema=row[0], name=row[1]) for row in rows]
            logger.info(
                "User %s retrieved %d tables with their permissions",
                user_id,
                len(tables),
            )
            return TablesResponse(tables=tables, count=len(tables))
        finally:
            cursor.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve tables for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tables",
        ) from exc
    finally:
        if conn:
            conn.close()


@app.get("/table-data-as-user", response_model=TableDataResponse)
def get_table_data_as_user(
    request: Request,
    user_claims: Dict[str, Any] = Depends(get_current_user),
) -> TableDataResponse:
    """Query EMPLOYEES and ADMIN_EMPLOYEES tables as the user.

    Uses user's OBO token and lets Snowflake resolve the active/default role.
    Catches access denied errors individually for each table.
    """
    user_id = user_claims.get("oid") or user_claims.get("sub", "unknown")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user_token = auth_header[7:]  # Remove "Bearer " prefix

    conn = None
    try:
        conn = get_user_snowflake_connection(user_token)
        
        def query_table(table_name: str) -> TableDataResult:
            cursor = conn.cursor()
            try:
                # Limit rows to avoid returning huge amounts of data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 50")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in rows]
                return TableDataResult(success=True, data=data, error=None)
            except snowflake.connector.ProgrammingError as exc:
                err_msg = str(exc)
                logger.warning("Access to table %s failed for user %s: %s", table_name, user_id, err_msg)
                return TableDataResult(
                    success=False,
                    data=None,
                    error=f"User does not have access to table '{table_name}'"
                )
            finally:
                cursor.close()

        employees_result = query_table("EMPLOYEES")
        admin_employees_result = query_table("ADMIN_EMPLOYEES")

        return TableDataResponse(
            employees=employees_result,
            admin_employees=admin_employees_result
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve table data for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve table data",
        ) from exc
    finally:
        if conn:
            conn.close()


@app.get("/tables-as-service-account", response_model=TablesResponse)
def list_tables_as_service_account() -> TablesResponse:
    """List all tables queried using the Service Account connection."""
    conn = None
    try:
        conn = get_service_account_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )
            rows = cursor.fetchall()
            tables = [TableInfo(schema=row[0], name=row[1]) for row in rows]
            logger.info(
                "Service Account retrieved %d tables from %s.%s",
                len(tables),
                settings.snowflake_database,
                settings.snowflake_schema,
            )
            return TablesResponse(tables=tables, count=len(tables))
        finally:
            cursor.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve tables as Service Account: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tables",
        ) from exc
    finally:
        if conn:
            conn.close()


@app.get("/table-data-as-service-account", response_model=TableDataResponse)
def get_table_data_as_service_account() -> TableDataResponse:
    """Query EMPLOYEES and ADMIN_EMPLOYEES tables as the Service Account."""
    conn = None
    try:
        conn = get_service_account_connection()
        
        def query_table(table_name: str) -> TableDataResult:
            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 50")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in rows]
                return TableDataResult(success=True, data=data, error=None)
            except snowflake.connector.ProgrammingError as exc:
                err_msg = str(exc)
                logger.warning("Access to table %s failed for Service Account: %s", table_name, err_msg)
                return TableDataResult(
                    success=False,
                    data=None,
                    error=f"Service account does not have access to table '{table_name}'"
                )
            finally:
                cursor.close()

        employees_result = query_table("EMPLOYEES")
        admin_employees_result = query_table("ADMIN_EMPLOYEES")

        return TableDataResponse(
            employees=employees_result,
            admin_employees=admin_employees_result
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve table data for Service Account: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve table data",
        ) from exc
    finally:
        if conn:
            conn.close()
