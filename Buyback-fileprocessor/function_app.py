import os
import logging
import azure.functions as func

from shared_code import snowflake_connection, snowflake_service, file_engine

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="%AZURE_STORAGE_CONTAINER_NAME%/{name}",
                  connection="mmstraccnt0001_STORAGE") 
def file_processor(myblob: func.InputStream):
    logging.info(f"--- File Processor Triggered ---")
    logging.info(f"Blob Name: {myblob.name}")
    logging.info(f"Blob Size: {myblob.length} bytes")
    
    connection_str = os.environ.get("mmstraccnt0001_STORAGE")
    if not connection_str:
        logging.error("mmstraccnt0001_STORAGE connection string not found in environment.")
        return

    # 1. Parse container name and blob name from trigger path
    parts = myblob.name.split('/', 1)
    if len(parts) == 2:
        container_name, blob_name = parts[0], parts[1]
    else:
        container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "uploads")
        blob_name = myblob.name

    # 2. Read and log blob metadata
    metadata = {}
    try:
        metadata = file_engine.read_blob_metadata(container_name, blob_name, connection_str)
        logging.info(f"Blob Metadata: {metadata}")
    except Exception as exc:
        logging.error(f"Failed to retrieve blob metadata: {exc}", exc_info=True)

    # 3. Retrieve Snowflake data using Service Account Key Vault Authentication
    snowflake_data = {}
    conn = None
    try:
        logging.info("Connecting to Snowflake...")
        conn = snowflake_connection.create_snowflake_connection()
        logging.info("Connected to Snowflake successfully. Listing tables...")
        
        tables = snowflake_service.list_tables(conn)
        logging.info(f"Tables found in database: {[t[1] for t in tables]}")
        
        # Log and retrieve data for each table
        for schema, table_name in tables:
            logging.info(f"Retrieving data for table: {schema}.{table_name}")
            # Get table data (limit 50 rows) to use as reference data for update
            table_rows = snowflake_service.get_table_data(conn, schema, table_name, limit=50)
            snowflake_data[table_name] = table_rows
            logging.info(f"Successfully retrieved {len(table_rows)} rows for '{table_name}'")
            
    except Exception as exc:
        logging.error(f"Error during Snowflake database operations: {exc}", exc_info=True)
    finally:
        if conn:
            try:
                conn.close()
                logging.info("Snowflake connection closed.")
            except Exception:
                pass

    # 4. Read Excel/CSV file content and run update engine
    try:
        # Seek back to start if required and read blob bytes
        myblob.seek(0)
        file_content = myblob.read()
        
        # Call the update excel stub
        logging.info("Processing Excel file updates...")
        updated_content = file_engine.update_excel_file(file_content, snowflake_data)
        
        # 5. Upload the updated excel to the processed container
        destination_container = os.environ.get("AZURE_STORAGE_PROCESSED_CONTAINER_NAME", "processed")
        file_engine.upload_processed_file(blob_name, updated_content, destination_container, connection_str)
        
    except Exception as exc:
        logging.error(f"Error during file processing/upload flow: {exc}", exc_info=True)

    logging.info(f"--- File Processor Execution Completed ---")
