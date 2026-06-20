from fastapi import APIRouter
from app.api.endpoints import health, tables, upload

api_router = APIRouter()

# Register health check and config routes
api_router.include_router(health.router, tags=["health"])

# Register dynamic tables routes
api_router.include_router(tables.router, tags=["tables"])

# Register file upload routes
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])

