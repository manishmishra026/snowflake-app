import logging
from fastapi import APIRouter
from app.core.config import settings
from app.models.schemas import HealthResponse, ClientConfigResponse

router = APIRouter()
logger = logging.getLogger("app")

@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health status verification endpoint."""
    return HealthResponse(status="ok")

@router.get("/config/client-settings", response_model=ClientConfigResponse)
def get_client_settings() -> ClientConfigResponse:
    """Return non-sensitive config parameters dynamically for the frontend client."""
    logger.info("Providing dynamic client configuration settings")
    client_id = settings.WEB_APP_CLIENT_ID
    tenant_id = settings.AZURE_TENANT_ID
    
    # Standard scope list for the frontend app registration
    scopes = ["openid", "profile", "email"]
    if settings.BACKEND_API_CLIENT_ID:
        scopes.append(f"api://{settings.BACKEND_API_CLIENT_ID}/user_impersonation")

    return ClientConfigResponse(
        app_insights_connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING,
        client_id=client_id,
        tenant_id=tenant_id,
        scopes=scopes
    )
