# app/core/queries.py

# Query to list tables in the database and schema
LIST_TABLES_QUERY = """
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

def get_table_data_query(table_name: str, limit: int = 50) -> str:
    """Generate SQL query to fetch columns for a given table.
    
    Prevents SQL injection by sanitizing double-quotes and wrapping 
    the identifier in double-quotes.
    """
    sanitized_table = table_name.replace('"', '')
    return f'SELECT * FROM "{sanitized_table}" LIMIT {limit}'
