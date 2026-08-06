import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import azure.functions as func

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from function_app import webapp_add_user_id_dates, webapp_fill_empty_cells

@patch.dict(os.environ, {
    "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
    "INPUT_CONTAINER_1": "input-1",
    "OUTPUT_CONTAINER_1": "output-1"
})
@patch("shared_code.file_engine.read_blob_metadata")
@patch("shared_code.file_engine.add_user_id_and_dates")
@patch("shared_code.file_engine.upload_processed_file")
def test_webapp_add_user_id_dates_success(mock_upload, mock_enrich, mock_metadata):
    # Set up mocks
    mock_metadata.return_value = {
        "user_identification": "test_user",
        "validity_start_date": "2026-07-08",
        "validity_end_date": "9999-12-31"
    }
    mock_enrich.return_value = b"enriched-content"
    
    mock_blob = MagicMock(spec=func.InputStream)
    mock_blob.name = "input-1/test_file.csv"
    mock_blob.read.return_value = b"original-content"
    
    webapp_add_user_id_dates(mock_blob)
    
    mock_metadata.assert_called_once_with("input-1", "test_file.csv", "UseDevelopmentStorage=true")
    mock_enrich.assert_called_once_with("test_file.csv", b"original-content", "test_user", "2026-07-08", "9999-12-31")
    mock_upload.assert_called_once_with("test_file.csv", b"enriched-content", "output-1", "UseDevelopmentStorage=true")

@patch.dict(os.environ, {
    "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
    "INPUT_CONTAINER_2": "input-2",
    "OUTPUT_CONTAINER_2": "output-2"
})
@patch("shared_code.snowflake_connection.create_snowflake_connection")
@patch("shared_code.snowflake_service.get_all_lookup_data")
@patch("shared_code.file_engine.fill_empty_cells")
@patch("shared_code.file_engine.upload_processed_file")
def test_webapp_fill_empty_cells_success(mock_upload, mock_fill, mock_service, mock_conn):
    # Set up mocks
    mock_conn.return_value = MagicMock()
    mock_service.return_value = {"BB_LEGAL_ENTITY": []}
    mock_fill.return_value = (b"processed", b"recap", b"unresolved")
    
    mock_blob = MagicMock(spec=func.InputStream)
    mock_blob.name = "input-2/test_file.csv"
    mock_blob.read.return_value = b"original-content"
    
    webapp_fill_empty_cells(mock_blob)
    
    mock_conn.assert_called_once()
    mock_service.assert_called_once()
    mock_fill.assert_called_once_with(b"original-content", {"BB_LEGAL_ENTITY": []})
    assert mock_upload.call_count == 3
