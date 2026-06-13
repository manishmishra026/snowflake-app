import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.router import api_router
from app.db.security import refresh_azure_snowflake_token

# Configure logging format
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.log")

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("app")

# async lifespan for startup / shutdown hooks
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events manager for warm up and instrumentation."""
    try:
        logger.info("Application starting up...")
        
        # 1. Warm up MSAL cache if service-principal flow is active
        if settings.SNOWFLAKE_AUTH_FLOW == "service-principal":
            refresh_azure_snowflake_token()
            
        # 2. Setup Application Insights telemetry
        setup_logging(app)
        
        logger.info("Application startup completed successfully")
    except Exception as exc:
        logger.error("Failed to initialize application: %s", exc, exc_info=True)
        raise
    yield
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Global Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API endpoints
app.include_router(api_router)
