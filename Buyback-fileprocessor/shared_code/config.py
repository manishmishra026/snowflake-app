# Columns mappings for Script 1
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
    "BB_DEDUCTIBLE_FOR_REPAIR_COSTS": COMMON_PRICING_COLUMNS,
    "BB_NET_RESTORATION_COSTS": COMMON_PRICING_COLUMNS,
    "BB_RATE_OF_RETURN": COMMON_PRICING_COLUMNS,
    "BB_RESIDUAL_VALUES_ADJUSTMENTS": COMMON_PRICING_COLUMNS,
    "BB_UC_COMMERCIAL_MEANS": COMMON_PRICING_COLUMNS,
    "BB_UC_DISTRIBUTION_COSTS": COMMON_PRICING_COLUMNS,
    "BB_CURRENCY_CONVERSION": [
        "Currency_origin_code",
        "Currency_target_code",
        "Value",
        "Validity_Start_date",
        "Validity_End_date",
        "User_Identification"
    ],
    "BB_BUYER_ID": [
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
    "BB_LEGAL_ENTITY": [
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
    "BB_CHART_OF_ACCOUNT": [
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
    "BB_INVOICE_NV_WEBAPP": [
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

# Pricing prefix files to process for expansion (Script 2)
FILE_PREFIXES = [
    "BB_RATE_OF_RETURN",
    "BB_UC_DISTRIBUTION_COSTS",
    "BB_UC_COMMERCIAL_MEANS",
    "BB_NET_RESTORATION_COSTS",
    "BB_RESIDUAL_VALUES_ADJUSTMENTS",
    "BB_DEDUCTIBLE_FOR_REPAIR_COSTS",
]

# Brand processing groups and ignored brands
PCD_BRANDS = {"AC", "DS", "AP"}
OV_BRANDS = {"OV"}
FCA_BRANDS = {"AB", "AR", "FI", "JP", "LA", "MA", "LE", "OT", "CH", "DO"}
BRANDS_IGNORED = {"CH", "DO", "OT", "LE"}

# Channels compatibility by country
compat_channels = {
    "BE": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
    "ES": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
    "FR": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
    "NL": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
}
