import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Settings
    ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"
    API_TITLE: str = "Snowflake Tables API"
    API_VERSION: str = "1.0.0"
    ALLOWED_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"

    # Active auth flow: service-principal, user-auth, service-account
    SNOWFLAKE_AUTH_FLOW: str = "service-principal"

    # Service Principal Flow (Default)
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    SNOWFLAKE_ACCOUNT: str = ""
    SNOWFLAKE_DATABASE: str = ""
    SNOWFLAKE_SCHEMA: str = "PUBLIC"
    SNOWFLAKE_WAREHOUSE: str = ""
    SNOWFLAKE_ROLE: str = ""
    SNOWFLAKE_APPLICATION_ID_URI: str = ""

    # User Auth Flow / OBO Flow (Optional)
    USER_AUTH_AZURE_TENANT_ID: str = ""
    USER_AUTH_AZURE_CLIENT_ID: str = ""
    USER_AUTH_AZURE_CLIENT_SECRET: str = ""
    USER_AUTH_AZURE_AUDIENCE: str = ""
    USER_AUTH_SNOWFLAKE_ACCOUNT: str = ""
    USER_AUTH_SNOWFLAKE_DATABASE: str = ""
    USER_AUTH_SNOWFLAKE_APPLICATION_ID_URI: str = ""
    USER_AUTH_SNOWFLAKE_SCHEMA: str = "PUBLIC"
    USER_AUTH_SNOWFLAKE_WAREHOUSE: str = ""
    USER_AUTH_SNOWFLAKE_ROLE: str = ""

    # Service Account Flow (Optional)
    SNOWFLAKE_SERVICE_ACCOUNT_USER: str = "webapp_user"
    SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD: str = ""
    SNOWFLAKE_SERVICE_ACCOUNT_ROLE: str = ""

    # Application Insights Connection String
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = ""

    # Token caching intervals (Service Principal)
    TOKEN_CACHE_DURATION: int = 3300  # 55 minutes
    TOKEN_REFRESH_TIMEOUT: int = 10   # seconds

    @property
    def azure_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.USER_AUTH_AZURE_TENANT_ID}/v2.0"

    @property
    def azure_jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.USER_AUTH_AZURE_TENANT_ID}/discovery/v2.0/keys"

    @property
    def azure_allowed_audiences(self) -> List[str]:
        allowed = set()
        if self.USER_AUTH_AZURE_AUDIENCE:
            allowed.add(self.USER_AUTH_AZURE_AUDIENCE)
            if self.USER_AUTH_AZURE_AUDIENCE.startswith("api://"):
                allowed.add(self.USER_AUTH_AZURE_AUDIENCE[6:])
            else:
                allowed.add(f"api://{self.USER_AUTH_AZURE_AUDIENCE}")
        if self.USER_AUTH_AZURE_CLIENT_ID:
            allowed.add(self.USER_AUTH_AZURE_CLIENT_ID)
            if self.USER_AUTH_AZURE_CLIENT_ID.startswith("api://"):
                allowed.add(self.USER_AUTH_AZURE_CLIENT_ID[6:])
            else:
                allowed.add(f"api://{self.USER_AUTH_AZURE_CLIENT_ID}")
        return list(allowed)

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
