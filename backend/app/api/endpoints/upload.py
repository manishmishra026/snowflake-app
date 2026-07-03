import logging
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

from app.core.config import settings
from app.db.security import verify_api_token
from app.models.schemas import UploadResponse

router = APIRouter()
logger = logging.getLogger("app")

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit

def get_user_email(payload: dict) -> str:
    """Helper to extract user email/principal username from jwt token claims."""
    return (
        payload.get("preferred_username")
        or payload.get("email")
        or payload.get("upn")
        or payload.get("unique_name")
        or "unknown_user"
    )

def get_blob_service_client() -> BlobServiceClient:
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        logger.info("Initializing BlobServiceClient using Connection String")
        return BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING,
            connection_timeout=5,
            read_timeout=5
        )
    elif settings.AZURE_STORAGE_ACCOUNT_URL:
        logger.info("Initializing BlobServiceClient using Managed Identity / DefaultAzureCredential")
        credential = DefaultAzureCredential()
        return BlobServiceClient(
            account_url=settings.AZURE_STORAGE_ACCOUNT_URL,
            credential=credential,
            connection_timeout=5,
            read_timeout=5
        )
    else:
        logger.error("Azure Storage is not configured. Missing AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Storage is not configured on the server."
        )

@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    validity_start_date: str = Form(None),
    token_payload: dict = Depends(verify_api_token)
) -> UploadResponse:
    """Upload a CSV or XLSX file to Azure Storage Blob Container with user email metadata."""
    filename = file.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided."
        )
        
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("Upload rejected: Invalid file extension %s", ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed."
        )
    
    user_email = get_user_email(token_payload)
    logger.info("File upload request received from user %s for file: %s", user_email, filename)
    
    try:
        # Read file content and validate size
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE_BYTES:
            logger.warning("Upload rejected: File too large (%d bytes)", len(file_content))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File is too large. Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
            )

        blob_service_client = get_blob_service_client()
        container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        
        # Initialize container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it does not exist (useful for local development with Azurite)
        try:
            container_client.create_container()
            logger.info("Container '%s' did not exist and was created.", container_name)
        except Exception:
            # Container already exists, or no permissions to create
            pass
        
        blob_client = container_client.get_blob_client(filename)
        
        metadata = {
            "email": user_email,
            "uploaded_by": user_email,
            "user_identification": user_email
        }
        if validity_start_date:
            metadata["validity_start_date"] = validity_start_date
        
        logger.info("Uploading blob %s to container %s", filename, container_name)
        blob_client.upload_blob(file_content, overwrite=True, metadata=metadata)
        logger.info("Successfully uploaded blob %s", filename)
        
        return UploadResponse(
            success=True,
            message="File uploaded successfully.",
            blob_name=filename
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to upload file to Azure Storage: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred during file upload: {str(exc)}"
        )
