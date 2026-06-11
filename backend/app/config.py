"""Application configuration settings."""

import os

# Environment
ENV = os.getenv("ENV", "development")

# API
API_TITLE = "Snowflake Tables API"
API_VERSION = "1.0.0"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if ENV == "production" else "DEBUG")

# Token caching
TOKEN_CACHE_DURATION = 3300  # 55 minutes (token expires in 60 minutes)
TOKEN_REFRESH_TIMEOUT = 10  # seconds

# Snowflake query
QUERY_TIMEOUT = 60  # seconds

# Security
ENABLE_SECURITY_HEADERS = True

# CORS
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200",
    ).split(",")
    if origin.strip()
]
