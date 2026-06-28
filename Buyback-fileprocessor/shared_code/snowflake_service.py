import logging
from typing import Any, List, Tuple

LIST_TABLES_QUERY = """
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

def list_tables(conn: Any) -> List[Tuple[str, str]]:
    """Retrieves all base tables (schema, table_name) in the active database."""
    cursor = conn.cursor()
    try:
        cursor.execute(LIST_TABLES_QUERY)
        rows = cursor.fetchall()
        return [(row[0], row[1]) for row in rows]
    except Exception as exc:
        logging.error(f"Failed to query tables list from Snowflake: {exc}", exc_info=True)
        raise
    finally:
        cursor.close()

def get_table_data(conn: Any, schema_name: str, table_name: str, limit: int = 50) -> List[dict]:
    """Retrieves row data for a specific table."""
    # Strip quotes for safety
    safe_schema = schema_name.replace('"', '')
    safe_table = table_name.replace('"', '')
    
    query = f'SELECT * FROM "{safe_schema}"."{safe_table}" LIMIT {limit}'
    logging.info(f"Querying Snowflake table data: {query}")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as exc:
        logging.error(f"Failed to fetch data for table {safe_schema}.{safe_table}: {exc}", exc_info=True)
        raise
    finally:
        cursor.close()
