"""Configuration for user authentication flow."""

import os


class UserAuthSettings:
    """Configuration for user-based authentication and on-behalf-of (OBO) flow."""

    def __init__(self) -> None:
        self.azure_tenant_id = self._get_required("USER_AUTH_AZURE_TENANT_ID")
        self.azure_client_id = self._get_required("USER_AUTH_AZURE_CLIENT_ID")
        self.azure_client_secret = self._get_required("USER_AUTH_AZURE_CLIENT_SECRET")
        self.azure_audience = self._get_required("USER_AUTH_AZURE_AUDIENCE")
        self.snowflake_account = self._get_required("USER_AUTH_SNOWFLAKE_ACCOUNT")
        self.snowflake_database = self._get_required("USER_AUTH_SNOWFLAKE_DATABASE")
        self.snowflake_schema = self._get_optional("USER_AUTH_SNOWFLAKE_SCHEMA", "PUBLIC")
        self.snowflake_warehouse = self._get_optional("USER_AUTH_SNOWFLAKE_WAREHOUSE")
        self.snowflake_role = self._get_optional("USER_AUTH_SNOWFLAKE_ROLE")
        self.snowflake_application_id_uri = self._get_required("USER_AUTH_SNOWFLAKE_APPLICATION_ID_URI")

        # Derived values for Azure AD token validation
        self.azure_issuer = f"https://login.microsoftonline.com/{self.azure_tenant_id}/v2.0"
        self.azure_jwks_uri = (
            f"https://login.microsoftonline.com/{self.azure_tenant_id}/discovery/v2.0/keys"
        )
        
        # Build allowed audiences, supporting both raw and api:// prefixed formats
        allowed = {self.azure_audience, self.azure_client_id}
        if self.azure_audience.startswith("api://"):
            allowed.add(self.azure_audience[6:])
        else:
            allowed.add(f"api://{self.azure_audience}")
            
        if self.azure_client_id.startswith("api://"):
            allowed.add(self.azure_client_id[6:])
        else:
            allowed.add(f"api://{self.azure_client_id}")
            
        self.azure_allowed_audiences = tuple(allowed)

    @staticmethod
    def _get_required(key: str) -> str:
        value = os.getenv(key, "").strip()
        if not value:
            raise RuntimeError(f"Environment variable {key} is required for user auth flow")
        return value

    @staticmethod
    def _get_optional(key: str, default: str = "") -> str:
        return os.getenv(key, default).strip()


def get_user_auth_settings() -> UserAuthSettings:
    """Get user auth settings. Raises if required variables are missing."""
    try:
        return UserAuthSettings()
    except RuntimeError as e:
        raise RuntimeError(f"User authentication not configured: {e}") from e
