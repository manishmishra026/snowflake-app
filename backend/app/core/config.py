import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Settings
    ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"
    API_TITLE: str = "Buyback API"
    API_VERSION: str = "1.0.0"
    ALLOWED_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"

    # Azure AD Client Token Validation (Option 1)
    AZURE_TENANT_ID: str = ""
    BACKEND_API_CLIENT_ID: str = ""
    ALLOWED_CLIENT_IDS: str = ""  # Comma-separated list of allowed calling client IDs
    WEB_APP_CLIENT_ID: str = ""   # Client ID of the web app (passed dynamically to frontend)

    # Snowflake Connection Parameters (Service Account Only)
    SNOWFLAKE_ACCOUNT: str = ""
    SNOWFLAKE_DATABASE: str = ""
    SNOWFLAKE_SCHEMA: str = "PUBLIC"
    SNOWFLAKE_WAREHOUSE: str = ""
    SNOWFLAKE_ROLE: str = ""
    SNOWFLAKE_SERVICE_ACCOUNT_USER: str = "webapp_user"
    SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD: str = ""
    SNOWFLAKE_SERVICE_ACCOUNT_ROLE: str = ""

    # Application Insights Connection String
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = ""

    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_ACCOUNT_URL: str = ""  # For Managed Identity (e.g. https://<account>.blob.core.windows.net)
    AZURE_STORAGE_CONTAINER_NAME: str = "uploads"

    @property
    def azure_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}/v2.0"

    @property
    def azure_jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}/discovery/v2.0/keys"

    @property
    def allowed_client_ids_list(self) -> List[str]:
        return [cid.strip() for cid in self.ALLOWED_CLIENT_IDS.split(",") if cid.strip()]

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
