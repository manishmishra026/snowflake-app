import os
import pandas as pd

# ==========================================
# # LIST OF FILES
# ==========================================
INPUT_FILES = [
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_DEDUCTIBLE_FOR_REPAIR_COSTS_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_LEGAL_ENTITY_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_NET_RESTORATION_COSTS_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_RATE_OF_RETURN_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_RESIDUAL_VALUES_ADJUSTMENTS_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_UC_COMMERCIAL_MEANS_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_UC_DISTRIBUTION_COSTS_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_BUYER_ID_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_CHART_OF_ACCOUNT_20260615.CSV",
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_CURRENCY_CONVERSION_20260615.CSV",
]

INPUT_FILES_LPMI = [
    r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_INVOICE_NV_WEBAPP_2026_06_19.CSV"
]

# NOTE:
# Invoice file is handled in a dedicated list because it does NOT receive
# validity start/end dates in this step. Only User_Identification is added.

# ==========================================
# # OUTPUT DIRECTORY
# ==========================================
OUTPUT_DIR = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\Webapp_Add_User_and_Dates"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# # EXPECTED COLUMNS
# ==========================================
COMMON_PRICING_COLUMNS = [
    "Legal_Entity", "Brand", "standardized_UC_Origin_Channel",
    "LCDV_group", "nv_uc", "Scenario", "Energy_type",
    "Km_minimum", "Km_maximum",
    "Minimum_Contract_duration", "Maximum_Contract_duration",
    "Validity_Start_date", "Validity_end_date",
    "Value", "Value_Type", "Currency",
    "User_Identification"
]

FINAL_COLUMNS = {
    "BB_DEDUCTIBLE_FOR_REPAIR_COSTS_20260615.CSV": COMMON_PRICING_COLUMNS,
    "BB_NET_RESTORATION_COSTS_20260615.CSV": COMMON_PRICING_COLUMNS,
    "BB_RATE_OF_RETURN_20260615.CSV": COMMON_PRICING_COLUMNS,
    "BB_RESIDUAL_VALUES_ADJUSTMENTS_20260615.CSV": COMMON_PRICING_COLUMNS,
    "BB_UC_COMMERCIAL_MEANS_20260615.CSV": COMMON_PRICING_COLUMNS,
    "BB_UC_DISTRIBUTION_COSTS_20260615.CSV": COMMON_PRICING_COLUMNS,
    "BB_CURRENCY_CONVERSION_20260615.CSV": [
        "Currency_origin_code",
        "Currency_target_code",
        "Value",
        "Validity_Start_date",
        "Validity_End_date",
        "User_Identification"
    ],

    "BB_BUYER_ID_20260615.CSV": [
        "Buyer_ID",
        "Commercial_Name",
        "Brand_ID",
        "Country_ID",
        "Legal_Entity_Code",
        "Type",
        "Validity_start_date",
        "Validity_end_date",
        "User_Identification"
    ],

    "BB_LEGAL_ENTITY_20260615.CSV": [
        "Legal_Entity_Code",
        "Legal_Entity_Type",
        "SUIG_code",
        "RCGF_code",
        "Label",
        "Status",
        "Country",
        "Partner_Profit_Center",
        "LB_9DCO_Partner_Profit_Center",
        "START_code",
        "Webdac_code",
        "Type",
        "Local_currency_Code",
        "Brand",
        "Validity_start_date",
        "Validity_end_date",
        "User_Identification"
    ],

    "BB_CHART_OF_ACCOUNT_20260615.CSV": [
        "booking_code",
        "Legal_Entity_Code",
        "doc_id",
        "doc_label",
        "doc_header_label",
        "debit_credit_code",
        "transaction_type",
        "trading_partner",
        "partner_profit_center",
        "cost_center",
        "booking_label",
        "Posting_Scope",
        "account_category",
        "account_label",
        "account_number",
        "nv_uc_code",
        "event_code",
        "pc_lcv_code",
        "Validity_start_date",
        "Validity_end_date",
        "User_Identification"
    ],

    "BB_INVOICE_NV_WEBAPP_2026_06_19.CSV": [
        "CD_VIN_CODE",
        "NM_COGS_NUMBER",
        "NM_UP_TAX_COST_NUMBER",
        "NM_TAX_COST_NUMBER",
        "NM_NV_SALE_PRICE_NUMBER",
        "NM_SALE_PRICE_VER_NO_IMP_NUMBER",
        "NM_SALE_PRICE_IMP_NUMBER",
        "NM_SALE_PRICE_OPTIONS_NUMBER",
        "NM_SALE_PRICE_TRANSPORT_NUMBER",
        "NM_SALE_PRICE_PACKING_NUMBER",
        "NM_SALE_PRICE_ACCESSORY_NUMBER",
        "NM_SALE_PRICE_TRANSFO_NUMBER",
        "NM_WARRANTY_CT_NUMBER",
        "NM_COGS_COMP_NUMBER",
        "NM_UP_COGS_COMP_NUMBER",
        "NM_UP_TRANSPORT_COST_NUMBER",
        "NM_TRANSPORT_COST_NUMBER",
        "NM_UP_ANNEX_COST_NUMBER",
        "NM_ANNEX_COST_NUMBER",
        "NM_SALE_PRICE_PROTECT_NUMBER",
        "NM_SALE_PRICE_PERSO_NUMBER",
        "NM_PPI_PERSO_NUMBER",
        "NM_MCX_VARIABLES_NUMBER",
        "DT_NV_INVOICE_DATE",
        "DT_DELIVERY_DATE",
        "User_Identification"
    ],
}

# ==========================================
# # VALUES TO ADD
# ==========================================
USER_IDENTIFICATION_VALUE = "Rachel"
VALID_START_VALUE = "01/06/2026"
VALID_END_VALUE = "31/12/9999"

# ==========================================
# # HELPERS
# ==========================================
def detect_sep(path: str) -> str:
    """Detect the CSV delimiter from the first line (';' preferred when tied)."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        first_line = f.readline()
    return ";" if first_line.count(";") >= first_line.count(",") else ","

def get_validity_date_columns(expected_cols: list[str]) -> tuple[str | None, str | None]:
    """
    Find validity start/end column names from the expected schema.
    Supports mixed naming styles like Validity_Start_date / Validity_start_date.
    """
    start_col = None
    end_col = None
    for col in expected_cols:
        low = col.lower()
        if "validity" not in low:
            continue
        if "start" in low and start_col is None:
            start_col = col
        elif "end" in low and end_col is None:
            end_col = col

    return start_col, end_col

def insert_column_if_missing(df: pd.DataFrame, col_name: str, expected_cols: list[str], default_value="") -> pd.DataFrame:
    """
    Insert one missing column at the right schema position without reordering
    or touching existing business columns. If the column already exists,
    return the DataFrame unchanged.
    """
    if not col_name or col_name in df.columns:
        return df

    target_pos = expected_cols.index(col_name)

    # Find the first existing column that should come after the inserted one.
    insert_before = None
    for next_col in expected_cols[target_pos + 1:]:
        if next_col in df.columns:
            insert_before = next_col
            break

    if insert_before is None:
        # If no following expected column exists, append at the end.
        df[col_name] = default_value
    else:
        insert_idx = df.columns.get_loc(insert_before)
        df.insert(insert_idx, col_name, default_value)

    return df

def process_file(path: str, output_dir: str, add_validity_dates: bool = True):
    """
    add_validity_dates=True -> add/fill validity start + end + user columns
    add_validity_dates=False -> skip validity dates, add/fill user only
    """
    file_name = os.path.basename(path)
    print(f"\n📄 {file_name}")

    if file_name not in FINAL_COLUMNS:
        print(f"❌ Error on {file_name} : absent from FINAL_COLUMNS")
        return

    expected_cols = FINAL_COLUMNS[file_name]

    try:
        sep = detect_sep(path)
        df = pd.read_csv(
            path,
            dtype=str,
            sep=sep,
            engine="python",
            keep_default_na=False
        )
        df.columns = df.columns.str.strip()

        # Columns to insert only (and at the right place)
        start_col, end_col = get_validity_date_columns(expected_cols)

        if add_validity_dates and start_col:
            df = insert_column_if_missing(df, start_col, expected_cols, VALID_START_VALUE)
            df[start_col] = VALID_START_VALUE

        if add_validity_dates and end_col:
            df = insert_column_if_missing(df, end_col, expected_cols, VALID_END_VALUE)
            df[end_col] = VALID_END_VALUE

        if "User_Identification" in expected_cols:
            df = insert_column_if_missing(df, "User_Identification", expected_cols, USER_IDENTIFICATION_VALUE)
            df["User_Identification"] = USER_IDENTIFICATION_VALUE

        # 🔒 IMPORTANT :
        # DO NOT modify other columns (Value, Value_Type, Currency, etc.)
        # DO NOT perform reindex(columns=expected_cols)

        output_path = os.path.join(output_dir, file_name)
        df.to_csv(output_path, index=False, sep=";", encoding="utf-8-sig")

        print(f"✅ OK : {output_path}")

    except Exception as e:
        print(f"❌ Error on {file_name} : {e}")

# ==========================================
# # STANDARD TREATMENT
# ==========================================
# Standard tables: add validity dates + user identification.
for path in INPUT_FILES:
    process_file(path, OUTPUT_DIR, add_validity_dates=True)

# ==========================================
# # LPMI TREATMENT
# ==========================================
# Invoice table (LPMI): do not add validity dates, only user identification.
for path in INPUT_FILES_LPMI:
    process_file(path, OUTPUT_DIR, add_validity_dates=False)
