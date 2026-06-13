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
    client_id = settings.USER_AUTH_AZURE_CLIENT_ID
    audience = settings.USER_AUTH_AZURE_AUDIENCE or (f"api://{client_id}" if client_id else "")
    scopes = ["openid", "profile", "email"]
    if audience:
        base_scope = audience if audience.startswith("api://") else f"api://{audience}"
        scopes.append(f"{base_scope}/user_impersonation")

    return ClientConfigResponse(
        app_insights_connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING,
        client_id=client_id,
        tenant_id=settings.USER_AUTH_AZURE_TENANT_ID,
        scopes=scopes
    )
