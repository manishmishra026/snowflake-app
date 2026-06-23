import logging
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
    """Validate incoming Bearer ID Token issued by Azure AD for the Frontend Client."""
    if credentials is None or not credentials.credentials:
        logger.warning("Request rejected: Missing authorization header / bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Fetch Microsoft public keys
        jwk_client = PyJWKClient(settings.azure_jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(credentials.credentials)

        # Since the token is the frontend's ID token, the audience is the WEB_APP_CLIENT_ID
        allowed_audiences = [settings.WEB_APP_CLIENT_ID]

        # Decode and validate signature, expiration, and audience
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=allowed_audiences,
            options={"verify_exp": True, "verify_aud": True, "verify_iss": False},
        )

        # Verify issuer matches current tenant
        token_iss = payload.get("iss")
        allowed_issuers = [
            settings.azure_issuer,
            f"https://sts.windows.net/{settings.AZURE_TENANT_ID}/",
            f"https://sts.windows.net/{settings.AZURE_TENANT_ID}",
        ]
        if token_iss not in allowed_issuers:
            raise InvalidTokenError(f"Invalid issuer: {token_iss}")

        return payload

    except InvalidTokenError as exc:
        logger.warning("Invalid token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.error("Token verification failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification error",
        ) from exc
