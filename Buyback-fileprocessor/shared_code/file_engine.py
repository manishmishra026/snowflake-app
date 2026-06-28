import logging
from typing import Any, Dict, List
from azure.storage.blob import BlobServiceClient

def read_blob_metadata(container_name: str, blob_name: str, connection_str: str) -> Dict[str, str]:
    """Reads and returns metadata of a blob in Azure Storage."""
    logging.info(f"Retrieving metadata for blob: container={container_name}, blob={blob_name}")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        properties = blob_client.get_blob_properties()
        return properties.metadata or {}
    except Exception as exc:
        logging.error(f"Failed to read blob metadata: {exc}", exc_info=True)
        return {}

def update_excel_file(file_content: bytes, snowflake_data: Dict[str, List[Dict[str, Any]]]) -> bytes:
    """Stub function to update/process the Excel file using data retrieved from Snowflake.
    
    Args:
        file_content: The raw byte content of the uploaded Excel/CSV file.
        snowflake_data: A dictionary mapping table names to list of dictionaries (rows).
        
    Returns:
        bytes: The processed Excel/CSV file content.
    """
    logging.info("Running Excel processing engine stub...")
    logging.info(f"Available Snowflake tables in cache: {list(snowflake_data.keys())}")
    for table_name, rows in snowflake_data.items():
        logging.info(f"Table '{table_name}' has {len(rows)} rows loaded as reference data")
        
    # TODO: Implement the business logic to read Excel, reference the Snowflake data, and write updates.
    # Currently returning the original file content.
    processed_content = file_content
    logging.info("Excel processing stub completed. Returning processed content.")
    return processed_content

def upload_processed_file(blob_name: str, updated_content: bytes, destination_container: str, connection_str: str) -> None:
    """Uploads the processed Excel file content to a new Azure Storage container."""
    logging.info(f"Uploading processed file '{blob_name}' to container '{destination_container}'")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_str)
        container_client = blob_service_client.get_container_client(destination_container)
        
        # Ensure container exists (e.g. for development with Azurite)
        try:
            container_client.create_container()
            logging.info(f"Container '{destination_container}' did not exist and was created.")
        except Exception:
            pass  # Container already exists
            
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(updated_content, overwrite=True)
        logging.info(f"Successfully uploaded processed file to {destination_container}/{blob_name}")
    except Exception as exc:
        logging.error(f"Failed to upload processed file to container '{destination_container}': {exc}", exc_info=True)
        raise
