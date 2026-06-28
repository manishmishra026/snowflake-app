import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.router import api_router

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
        
        # Setup Application Insights telemetry
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



@app.get("/assets/config/config.json")
def get_frontend_config():
    """Dynamically serve frontend configurations using backend environment variables."""
    return {
        "app_insights_connection_string": settings.APPLICATIONINSIGHTS_CONNECTION_STRING,
        "client_id": settings.WEB_APP_CLIENT_ID,
        "tenant_id": settings.AZURE_TENANT_ID,
        "scopes": [
            "openid",
            "profile",
            "email",
            f"api://{settings.BACKEND_API_CLIENT_ID}/user_impersonation"
        ],
        "backend_url": ""  # Points relatively to the same origin host
    }


# Serve compiled static Angular files (SPA hosting)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

# Check if the static directory exists (e.g., when compiled and moved to backend)
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    logger.info("Static files directory found at %s. Initializing SPA hosting.", static_dir)
    
    # Mount assets directory (images, icons, etc.)
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{file_name}")
    def get_static_file(file_name: str):
        """Serve top-level static assets (e.g. main.js, styles.css) or fallback to SPA index.html."""
        file_path = os.path.join(static_dir, file_name)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fall back to index.html to let Angular routing handle client-side routing
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="File not found")

    @app.get("/{catchall:path}")
    def serve_spa(catchall: str):
        """Catch-all router to serve index.html for Angular SPA client routes."""
        # Do not intercept actual API endpoint routes
        if (
            catchall.startswith("api") or 
            catchall.startswith("tables") or 
            catchall.startswith("upload") or 
            catchall.startswith("docs") or 
            catchall.startswith("openapi.json")
        ):
            raise HTTPException(status_code=404, detail="Not Found")
            
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="SPA index.html not found")

