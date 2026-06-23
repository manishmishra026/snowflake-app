import os
import sys

# Add the backend directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

try:
    print("--- Snowflake Key Vault & Connection Diagnostic ---")
    
    from app.core.config import settings
    print(f"1. Azure Key Vault URL: {settings.AZURE_KEYVAULT_URL}")
    print(f"2. Key Vault Secret Name: {settings.SNOWFLAKE_PRIVATE_KEY_SECRET_NAME}")
    print(f"3. Snowflake Account: {settings.SNOWFLAKE_ACCOUNT}")
    print(f"4. Snowflake User: {settings.SNOWFLAKE_SERVICE_ACCOUNT_USER}")
    print(f"5. Snowflake Role: {settings.SNOWFLAKE_ROLE}")
    
    print("\nAttempting to connect to Snowflake...")
    from app.db.connection import create_raw_service_account_connection
    conn = create_raw_service_account_connection()
    
    print("\nConnection successful! Executing test query...")
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ROLE()")
    row = cursor.fetchone()
    print(f"-> Snowflake Version: {row[0]}")
    print(f"-> Connected as User: {row[1]}")
    print(f"-> Active Role: {row[2]}")
    
    cursor.close()
    conn.close()
    print("\n--- Diagnostic Completed Successfully! Connection is fully working. ---")

except Exception as exc:
    print(f"\n[ERROR] Connection failed: {exc}")
    import traceback
    traceback.print_exc()
