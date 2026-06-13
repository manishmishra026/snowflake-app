import time
import logging
from typing import Any, Dict, Optional
import requests
import jwt
from jwt import InvalidTokenError, PyJWKClient
import snowflake.connector
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

logger = logging.getLogger("app")
security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Token caching (Service Principal)
# ---------------------------------------------------------------------------
_azure_snowflake_token: Optional[str] = None
_azure_snowflake_token_expires_at: float = 0.0


def get_azure_access_token_for_snowflake() -> str:
    """Obtain Azure access token for Snowflake using client credentials flow."""
    scope = settings.SNOWFLAKE_APPLICATION_ID_URI
    if not scope.endswith("/.default"):
        scope = f"{scope}/.default"

    token_url = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"
    try:
        response = requests.post(
            token_url,
            data={
                "client_id": settings.AZURE_CLIENT_ID,
                "client_secret": settings.AZURE_CLIENT_SECRET,
                "scope": scope,
                "grant_type": "client_credentials",
            },
            timeout=settings.TOKEN_REFRESH_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            error_desc = payload.get("error_description", "Unknown error")
            logger.error("No access token in Azure response: %s", error_desc)
            raise RuntimeError(f"Azure token error: {error_desc}")
        return token
    except Exception as exc:
        logger.error("Failed to obtain Azure access token for Snowflake: %s", exc, exc_info=True)
        raise RuntimeError("Failed to acquire access token") from exc


def refresh_azure_snowflake_token() -> str:
    """Get or refresh the cached Azure Snowflake access token."""
    global _azure_snowflake_token, _azure_snowflake_token_expires_at

    now = time.time()
    if _azure_snowflake_token and now < _azure_snowflake_token_expires_at:
        return _azure_snowflake_token

    logger.info("Refreshing Azure Snowflake access token")
    token = get_azure_access_token_for_snowflake()
    _azure_snowflake_token = token
    _azure_snowflake_token_expires_at = now + settings.TOKEN_CACHE_DURATION
    return token


# ---------------------------------------------------------------------------
# User AD Token verification (for OBO endpoints)
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Validate Azure AD bearer token and return token claims."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Check settings
        if not settings.USER_AUTH_AZURE_CLIENT_ID:
            raise RuntimeError("User auth variables not set")
    except Exception as exc:
        logger.error("User auth configuration error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User authentication not configured on server",
        )

    try:
        jwk_client = PyJWKClient(settings.azure_jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(credentials.credentials)
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.azure_allowed_audiences,
            options={"verify_exp": True, "verify_aud": True, "verify_iss": False},
        )
        
        token_iss = payload.get("iss")
        allowed_issuers = [
            settings.azure_issuer,
            f"https://sts.windows.net/{settings.USER_AUTH_AZURE_TENANT_ID}/",
            f"https://sts.windows.net/{settings.USER_AUTH_AZURE_TENANT_ID}",
        ]
        if token_iss not in allowed_issuers:
            raise InvalidTokenError(f"Invalid issuer: {token_iss}")

        user_id = payload.get("oid") or payload.get("sub", "unknown")
        logger.info("User authenticated: %s", user_id)
        return payload
    except InvalidTokenError as exc:
        logger.warning("Invalid token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.error("Token validation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation error",
        ) from exc


# ---------------------------------------------------------------------------
# OBO token exchange & Snowflake Connection (User Auth Flow)
# ---------------------------------------------------------------------------
def get_user_snowflake_token(user_token: str) -> str:
    """Exchange user Azure AD token for Snowflake token via on-behalf-of (OBO) flow."""
    scope = settings.USER_AUTH_SNOWFLAKE_APPLICATION_ID_URI
    if not scope.endswith("/.default"):
        scope = f"{scope}/.default"

    token_url = f"https://login.microsoftonline.com/{settings.USER_AUTH_AZURE_TENANT_ID}/oauth2/v2.0/token"
    logger.info("Exchanging user token for Snowflake token via OBO flow")

    try:
        response = requests.post(
            token_url,
            data={
                "client_id": settings.USER_AUTH_AZURE_CLIENT_ID,
                "client_secret": settings.USER_AUTH_AZURE_CLIENT_SECRET,
                "assertion": user_token,
                "requested_token_use": "on_behalf_of",
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "scope": scope,
            },
            timeout=settings.TOKEN_REFRESH_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            error_desc = payload.get("error_description", "Unknown error")
            logger.error("No access token in Azure response: %s", error_desc)
            raise RuntimeError(f"Token exchange error: {error_desc}")
        return token
    except Exception as exc:
        logger.error("OBO token exchange failed: %s", exc, exc_info=True)
        raise RuntimeError("Failed to exchange token via OBO flow") from exc


def get_user_snowflake_connection(user_token: str) -> Any:
    """Create a Snowflake connection using user's token via OBO flow."""
    try:
        sf_token = get_user_snowflake_token(user_token)
        connection_params: Dict[str, Any] = {
            "account": settings.USER_AUTH_SNOWFLAKE_ACCOUNT,
            "authenticator": "oauth",
            "token": sf_token,
        }

        if settings.USER_AUTH_SNOWFLAKE_WAREHOUSE:
            connection_params["warehouse"] = settings.USER_AUTH_SNOWFLAKE_WAREHOUSE

        if settings.USER_AUTH_SNOWFLAKE_ROLE:
            connection_params["role"] = settings.USER_AUTH_SNOWFLAKE_ROLE

        conn = snowflake.connector.connect(**connection_params)

        # Set database and schema
        cursor = conn.cursor()
        try:
            cursor.execute(f'USE DATABASE "{settings.USER_AUTH_SNOWFLAKE_DATABASE}"')
            if settings.USER_AUTH_SNOWFLAKE_SCHEMA:
                cursor.execute(f'USE SCHEMA "{settings.USER_AUTH_SNOWFLAKE_SCHEMA}"')
        finally:
            cursor.close()

        return conn
    except Exception as exc:
        logger.error("Snowflake connection failed for user token: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to database using user token",
        ) from exc
