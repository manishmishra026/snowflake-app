"""User authentication and on-behalf-of (OBO) flow utilities."""

import logging
from typing import Any, Dict, Optional

import jwt
import requests
import snowflake.connector
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient

from app.config import TOKEN_REFRESH_TIMEOUT
from app.config_user_auth import get_user_auth_settings

logger = logging.getLogger("app")
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Validate Azure AD bearer token and return token claims.

    Requires USER_AUTH_* environment variables to be configured.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        settings = get_user_auth_settings()
    except RuntimeError as exc:
        logger.error("User auth not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User authentication not configured",
        ) from exc

    try:
        # Decode token without verification to inspect issuer/audience for debugging
        try:
            unverified = jwt.decode(credentials.credentials, options={"verify_signature": False})
            logger.info(
                "Incoming token - issuer (iss): %s, audience (aud): %s, expected issuer: %s, expected audiences: %s",
                unverified.get("iss"),
                unverified.get("aud"),
                settings.azure_issuer,
                settings.azure_allowed_audiences,
            )
        except Exception as debug_exc:
            logger.warning("Failed to decode token for debugging: %s", debug_exc)

        jwk_client = PyJWKClient(settings.azure_jwks_uri)
        signing_key = jwk_client.get_signing_key_from_jwt(credentials.credentials)
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.azure_allowed_audiences,
            options={"verify_exp": True, "verify_aud": True, "verify_iss": False},
        )
        
        # In Azure AD, access tokens can be v1.0 or v2.0 depending on the target resource app registration settings.
        # v1.0 tokens have issuer: https://sts.windows.net/{tenant_id}/
        # v2.0 tokens have issuer: https://login.microsoftonline.com/{tenant_id}/v2.0
        token_iss = payload.get("iss")
        allowed_issuers = [
            settings.azure_issuer,
            f"https://sts.windows.net/{settings.azure_tenant_id}/",
            f"https://sts.windows.net/{settings.azure_tenant_id}",
        ]
        if token_iss not in allowed_issuers:
            raise InvalidTokenError(f"Invalid issuer: {token_iss}")

        user_id = payload.get("oid") or payload.get("sub", "unknown")
        logger.info("User authenticated: %s", user_id)
    except InvalidTokenError as exc:
        logger.warning("Invalid token provided: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.error("Token validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation error",
        ) from exc

    return payload


def get_user_snowflake_token(user_token: str) -> str:
    """Exchange user Azure token for Snowflake token using on-behalf-of (OBO) flow."""
    settings = get_user_auth_settings()

    scope = settings.snowflake_application_id_uri
    if not scope.endswith("/.default"):
        scope = f"{scope}/.default"

    token_url = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/token"

    logger.info("Exchanging user token for Snowflake token via OBO flow")

    try:
        response = requests.post(
            token_url,
            data={
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "assertion": user_token,
                "requested_token_use": "on_behalf_of",
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "scope": scope,
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
        logger.error("OBO token exchange failed: %s - %s", exc.response.status_code, exc.response.text)
        raise RuntimeError(f"Token exchange failed: {exc.response.status_code}") from exc
    except Exception as exc:
        logger.error("Unexpected error during token exchange: %s", exc)
        raise RuntimeError("Failed to exchange token") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("Invalid JSON response from Azure: %s", response.text)
        raise RuntimeError("Invalid Azure token response") from exc

    token = payload.get("access_token")
    if not token:
        error_desc = payload.get("error_description", "Unknown error")
        logger.error("No access token in Azure response: %s", error_desc)
        raise RuntimeError(f"Token exchange error: {error_desc}")

    return token


def get_user_snowflake_connection(user_token: str) -> Any:
    """Create a Snowflake connection using user's token via OBO flow."""
    settings = get_user_auth_settings()

    try:
        sf_token = get_user_snowflake_token(user_token)
        
        # Decode token without verification to inspect Snowflake token claims for debugging
        try:
            sf_unverified = jwt.decode(sf_token, options={"verify_signature": False})
            logger.info(
                "Exchanged Snowflake token claims - iss: %s, aud: %s, upn: %s, email: %s, unique_name: %s, sub: %s, scp: %s, roles: %s",
                sf_unverified.get("iss"),
                sf_unverified.get("aud"),
                sf_unverified.get("upn"),
                sf_unverified.get("email"),
                sf_unverified.get("unique_name"),
                sf_unverified.get("sub"),
                sf_unverified.get("scp"),
                sf_unverified.get("roles"),
            )
        except Exception as debug_exc:
            logger.warning("Failed to decode Snowflake token for debugging: %s", debug_exc)

        connection_params: Dict[str, Any] = {
            "account": settings.snowflake_account,
            "authenticator": "oauth",
            "token": sf_token,
        }

        if settings.snowflake_warehouse:
            connection_params["warehouse"] = settings.snowflake_warehouse

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
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Snowflake connection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to database",
        ) from exc
