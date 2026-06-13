from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TableInfo(BaseModel):
    """Information for a single table."""
    schema_name: str = Field(..., serialization_alias="schema")
    name: str

    model_config = {
        "populate_by_name": True
    }

class TablesResponse(BaseModel):
    """Response payload for table listings."""
    tables: List[TableInfo]
    count: int

class HealthResponse(BaseModel):
    """Health check status payload."""
    status: str

class ClientConfigResponse(BaseModel):
    """Dynamic client configurations shared from backend to frontend."""
    app_insights_connection_string: str
    client_id: str
    tenant_id: str
    scopes: List[str]

class TableDataResponse(BaseModel):
    """Generic payload containing query results for any table."""
    success: bool
    table_name: str
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    error: Optional[str] = None
