import logging
from typing import Any
from fastapi import APIRouter, Depends, Query
from app.db.connection import get_db_connection
from app.db.security import verify_api_token
from app.services.snowflake_service import SnowflakeService
from app.models.schemas import TablesResponse, TableDataResponse

router = APIRouter()
logger = logging.getLogger("app")

@router.get("/tables", response_model=TablesResponse)
def list_tables(
    conn: Any = Depends(get_db_connection),
    token: dict = Depends(verify_api_token)
) -> TablesResponse:
    """Fetch list of database tables using the active authentication mechanism."""
    try:
        tables, count = SnowflakeService.list_tables(conn)
        return TablesResponse(tables=tables, count=count)
    finally:
        conn.close()

@router.get("/tables/{table_name}/data", response_model=TableDataResponse)
def get_table_data(
    table_name: str,
    limit: int = Query(50, ge=1, le=1000),
    conn: Any = Depends(get_db_connection),
    token: dict = Depends(verify_api_token)
) -> TableDataResponse:
    """Fetch columns and row records dynamically for a given table name."""
    try:
        response = SnowflakeService.get_table_data(conn, table_name, limit)
        return response
    finally:
        conn.close()
