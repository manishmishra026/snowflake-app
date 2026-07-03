import os
import logging
import azure.functions as func

from shared_code import snowflake_connection, snowflake_service, file_engine, config

app = func.FunctionApp()

# ==============================================================================
# FUNCTION 1: Add User ID and Dates
# ==============================================================================
@app.blob_trigger(arg_name="myblob", 
                  path="%INPUT_CONTAINER_1%/{name}",
                  connection="AZURE_STORAGE_CONNECTION_STRING") 
def webapp_add_user_id_dates(myblob: func.InputStream):
    logging.info(f"--- Function 1: webapp_add_user_id_dates triggered ---")
    logging.info(f"Blob Name: {myblob.name} | Size: {myblob.length} bytes")
    
    connection_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        logging.error("AZURE_STORAGE_CONNECTION_STRING connection string not found in environment.")
        return

    # Parse container name and blob name from the trigger path
    parts = myblob.name.split('/', 1)
    if len(parts) == 2:
        container_name, blob_name = parts[0], parts[1]
    else:
        container_name = os.environ.get("INPUT_CONTAINER_1")
        blob_name = myblob.name

    if not container_name:
        logging.error("Container name not found (INPUT_CONTAINER_1 not in environment).")
        return

    # Retrieve blob metadata from Azure Storage
    metadata = {}
    try:
        metadata = file_engine.read_blob_metadata(container_name, blob_name, connection_str)
        logging.info(f"Retrieved Blob Metadata: {metadata}")
    except Exception as exc:
        logging.error(f"Failed to retrieve blob metadata: {exc}", exc_info=True)

    # Read target values from metadata (case-insensitive checks)
    normalized_metadata = {k.lower(): v for k, v in metadata.items()}
    user_id = normalized_metadata.get("user_identification") or normalized_metadata.get("useridentification")
    start_date = normalized_metadata.get("validity_start_date") or normalized_metadata.get("validitystartdate")
    end_date = normalized_metadata.get("validity_end_date") or normalized_metadata.get("validityenddate") or "31/12/9999"

    if not user_id or not start_date:
        logging.error("mandatory properties not found in blob metadata")
        logging.info("--- Function 1 execution completed ---")
        return

    logging.info(f"Processing with user_identification='{user_id}', validity_start_date='{start_date}', validity_end_date='{end_date}'")

    try:
        file_content = myblob.read()
        
        # Run Add User ID and Dates engine
        updated_content = file_engine.add_user_id_and_dates(blob_name, file_content, user_id, start_date, end_date)
        
        # Upload to modified container
        destination_container = os.environ.get("OUTPUT_CONTAINER_1")
        if not destination_container:
            logging.error("OUTPUT_CONTAINER_1 not found in environment.")
            return
        file_engine.upload_processed_file(blob_name, updated_content, destination_container, connection_str)
        
    except Exception as exc:
        logging.error(f"Error during Function 1 execution flow: {exc}", exc_info=True)

    logging.info(f"--- Function 1 execution completed ---")


# ==============================================================================
# FUNCTION 2: Fill Empty Cells (Combinatorial Expansion)
# ==============================================================================
@app.blob_trigger(arg_name="myblob", 
                  path="%INPUT_CONTAINER_2%/{name}",
                  connection="AZURE_STORAGE_CONNECTION_STRING") 
def webapp_fill_empty_cells(myblob: func.InputStream):
    logging.info(f"--- Function 2: webapp_fill_empty_cells triggered ---")
    logging.info(f"Blob Name: {myblob.name} | Size: {myblob.length} bytes")
    
    connection_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        logging.error("AZURE_STORAGE_CONNECTION_STRING connection string not found in environment.")
        return

    # Parse container name and blob name from the trigger path
    parts = myblob.name.split('/', 1)
    if len(parts) == 2:
        container_name, blob_name = parts[0], parts[1]
    else:
        container_name = os.environ.get("INPUT_CONTAINER_2")
        blob_name = myblob.name

    if not container_name:
        logging.error("Container name not found (INPUT_CONTAINER_2 not in environment).")
        return

    # Retrieve Snowflake reference data
    snowflake_data = {}
    conn = None
    try:
        logging.info("Connecting to Snowflake using Service Account credentials...")
        conn = snowflake_connection.create_snowflake_connection()
        logging.info("Connected to Snowflake successfully. Retrieving lookup datasets...")
        snowflake_data = snowflake_service.get_all_lookup_data(conn)
        logging.info("Snowflake reference datasets loaded successfully.")
    except Exception as exc:
        logging.error(f"Failed to retrieve reference datasets from Snowflake: {exc}", exc_info=True)
        return
    finally:
        if conn:
            try:
                conn.close()
                logging.info("Snowflake connection closed.")
            except Exception:
                pass

    # Run processing and expansion logic
    try:
        file_content = myblob.read()
        
        logging.info("Running empty cell expansion engine...")
        processed_content, recap_content, unresolved_content = file_engine.fill_empty_cells(
            blob_name, file_content, snowflake_data
        )
        
        # Upload primary processed file
        destination_container = os.environ.get("OUTPUT_CONTAINER_2")
        if not destination_container:
            logging.error("OUTPUT_CONTAINER_2 not found in environment.")
            return
        file_engine.upload_processed_file(blob_name, processed_content, destination_container, connection_str)
        
        # Upload Recap report if generated
        if recap_content:
            recap_name = f"recap/{os.path.splitext(blob_name)[0]}_RECAP.CSV"
            file_engine.upload_processed_file(recap_name, recap_content, destination_container, connection_str)

        # Upload Unresolved report if generated
        if unresolved_content:
            unresolved_name = f"unresolved/{os.path.splitext(blob_name)[0]}_UNRESOLVED.CSV"
            file_engine.upload_processed_file(unresolved_name, unresolved_content, destination_container, connection_str)
            
    except Exception as exc:
        logging.error(f"Error during Function 2 execution flow: {exc}", exc_info=True)

    logging.info(f"--- Function 2 execution completed ---")
