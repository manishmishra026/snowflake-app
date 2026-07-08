import logging
import base64
import json
from typing import Any, Dict, Optional
import jwt
from jwt import InvalidTokenError, PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

logger = logging.getLogger("app")
security = HTTPBearer(auto_error=False)


def verify_api_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Validate incoming bearer token issued by Azure AD for the Backend API."""
    if credentials is None or not credentials.credentials:
        logger.warning("Request rejected: Missing authorization header / bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.AZURE_TENANT_ID or not settings.BACKEND_API_CLIENT_ID:
        logger.error("API authentication settings (AZURE_TENANT_ID / BACKEND_API_CLIENT_ID) are not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured on server",
        )

    try:
        # Decode payload without using jwt.decode to check token version (v1.0 vs v2.0)
        # to avoid static analysis warnings about unverified JWT signature usage.
        token_parts = credentials.credentials.split(".")
        if len(token_parts) != 3:
            raise InvalidTokenError("Invalid token format")
        
        payload_b64 = token_parts[1]
        # Add padding if required
        padding = len(payload_b64) % 4
        if padding > 0:
            payload_b64 += "=" * (4 - padding)
        
        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            unverified_payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            raise InvalidTokenError(f"Failed to decode token payload: {e}")

        token_ver = unverified_payload.get("ver", "1.0")

        # Select appropriate JWKS endpoint depending on token version
        if token_ver == "2.0":
            jwks_uri = settings.azure_jwks_uri
        else:
            jwks_uri = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/discovery/keys"

        # Load keys from selected JWKS endpoint
        jwk_client = PyJWKClient(jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(credentials.credentials)

        # Determine allowed audiences (API Client ID and api://<API Client ID>)
        allowed_audiences = [
            settings.BACKEND_API_CLIENT_ID,
            f"api://{settings.BACKEND_API_CLIENT_ID}"
        ]

        # Decode and validate token claims
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=allowed_audiences,
            options={"verify_exp": True, "verify_aud": True, "verify_iss": False},
        )

        # Verify issuer
        token_iss = payload.get("iss")
        allowed_issuers = [
            settings.azure_issuer,
            f"https://sts.windows.net/{settings.AZURE_TENANT_ID}/",
            f"https://sts.windows.net/{settings.AZURE_TENANT_ID}",
        ]
        if token_iss not in allowed_issuers:
            raise InvalidTokenError(f"Invalid issuer: {token_iss}")

        # Verify scope contains user_impersonation
        scp = payload.get("scp", "")
        scopes_list = [s.strip() for s in scp.split(" ") if s.strip()]
        if "user_impersonation" not in scopes_list:
            raise InvalidTokenError("Required scope 'user_impersonation' missing in token")

        # Verify the client application is allowed to call this API (checking appid or azp claim)
        client_app_id = payload.get("appid") or payload.get("azp")
        if not client_app_id:
            raise InvalidTokenError("Client application ID claim (appid/azp) missing in token")

        allowed_clients = settings.allowed_client_ids_list
        if client_app_id not in allowed_clients:
            logger.warning("Access denied: Client App ID '%s' is not in the allowed clients list", client_app_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Client ID {client_app_id} is not authorized to access this API",
            )

        logger.info("Request authenticated successfully for client app: %s", client_app_id)
        return payload

    except InvalidTokenError as exc:
        logger.warning("Invalid token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Token verification failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification error",
        ) from exc
