import logging
from typing import Any, List, Dict

def fetch_table_rows(conn: Any, table_name: str, columns: List[str]) -> List[Dict[str, Any]]:
    """Fetches specific columns for a specific table, converting result columns to lowercase."""
    cursor = conn.cursor()
    columns_str = ", ".join(f'"{col}"' for col in columns)
    # Try querying with double-quotes first
    query = f'SELECT {columns_str} FROM "{table_name}"'
    logging.info(f"Querying Snowflake table: {query}")
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns_lower = [col.lower() for col in columns]
        return [dict(zip(columns_lower, row)) for row in rows]
    except Exception as exc:
        logging.warning(f"Failed to query '{table_name}' with quotes. Retrying without quotes... Error: {exc}")
        try:
            fallback_columns_str = ", ".join(columns)
            fallback_query = f'SELECT {fallback_columns_str} FROM {table_name}'
            cursor.execute(fallback_query)
            rows = cursor.fetchall()
            columns_lower = [col.lower() for col in columns]
            return [dict(zip(columns_lower, row)) for row in rows]
        except Exception as retry_exc:
            logging.error(f"Failed to fetch data for table {table_name}: {retry_exc}", exc_info=True)
            raise retry_exc
    finally:
        cursor.close()

def get_all_lookup_data(conn: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves lookup datasets for all 4 tables required by the fill-empty-cells logic."""
    required_columns = {
        "CFA_TRANSCODED": ["country", "brand_name", "lcdv"],
        "REFERENCIAL_DATA_UCDM": ["country_id", "brand_id", "lcdv_16", "motor_id"],
        "BB_LEGAL_ENTITY": ["legal_entity_code", "country", "brand"],
        "ENT_UC_STOCK_IMAGE": ["cd_country_code", "cd_brand_code", "cd_lcdv_code"]
    }
    data = {}
    for table, columns in required_columns.items():
        logging.info(f"Fetching Snowflake table: {table}")
        data[table] = fetch_table_rows(conn, table, columns)
        logging.info(f"Successfully loaded {len(data[table])} rows for table '{table}'")
    return data
