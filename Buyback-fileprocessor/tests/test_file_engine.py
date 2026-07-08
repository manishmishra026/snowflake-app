import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import io

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_code import file_engine

def test_add_user_id_and_dates_schema_match():
    content = b"col1;col2\nval1;val2"
    result = file_engine.add_user_id_and_dates("BB_RATE_OF_RETURN.CSV", content, "user123", "2026-07-08", "9999-12-31")
    df = pd.read_csv(io.BytesIO(result), sep=";")
    assert "Validity_Start_date" in df.columns
    assert df["User_Identification"].iloc[0] == "user123"

def test_add_user_id_and_dates_fallback():
    content = b"col1;col2\nval1;val2"
    result = file_engine.add_user_id_and_dates("UNKNOWN_FILE.CSV", content, "user123", "2026-07-08", "9999-12-31")
    df = pd.read_csv(io.BytesIO(result), sep=";")
    assert "Validity_Start_date" in df.columns
    assert df["User_Identification"].iloc[0] == "user123"

def test_fill_range_gaps():
    rows = [
        {"Legal_Entity": "LE1", "Brand": "AP", "standardized_UC_Origin_Channel": "C1", "LCDV_group": "L1", "nv_uc": "NV", "Scenario": "RE", "Energy_type": "E1", "Km_minimum": "1000", "Km_maximum": "5000", "Minimum_Contract_duration": "12", "Maximum_Contract_duration": "24"},
        {"Legal_Entity": "LE1", "Brand": "AP", "standardized_UC_Origin_Channel": "C1", "LCDV_group": "L1", "nv_uc": "NV", "Scenario": "RE", "Energy_type": "E1", "Km_minimum": "", "Km_maximum": "5000", "Minimum_Contract_duration": "", "Maximum_Contract_duration": "24"},
    ]
    colors = [None, None]
    key_cols = ["Legal_Entity", "Brand", "standardized_UC_Origin_Channel", "LCDV_group", "nv_uc", "Scenario", "Energy_type"]
    new_rows, _, _ = file_engine.fill_range_gaps(rows, colors, key_cols, "Km_minimum", "Km_maximum", 9999999.0)
    assert len(new_rows) == 2
    assert new_rows[1]["Km_minimum"] == 0

def test_fill_empty_cells():
    snowflake_data = {
        "BB_LEGAL_ENTITY": [
            {"legal_entity_code": "LE1", "country": "FR", "brand": "AP DS"}
        ],
        "REFERENCIAL_DATA_UCDM": [
            {"country_id": "FR", "brand_id": "AP", "lcdv_16": "1234567890123456", "motor_id": "M1"}
        ],
        "CFA_TRANSCODED": [
            {"country": "FR", "brand_name": "AP", "lcdv": "123456789"}
        ],
        "ENT_UC_STOCK_IMAGE": [
            {"cd_country_code": "FR", "cd_brand_code": "AP", "cd_lcdv_code": "123456789"}
        ]
    }
    csv_content = (
        "Legal_Entity;Brand;standardized_UC_Origin_Channel;LCDV_group;nv_uc;Scenario;Energy_type;Km_minimum;Km_maximum;Minimum_Contract_duration;Maximum_Contract_duration\n"
        "LE1;AP;C1;1234567890123456;NV;RE;E1;1000;5000;12;24\n"
        "LE1;;1;;;;;1000;5000;12;24\n"
    ).encode("utf-8-sig")
    processed, _, _ = file_engine.fill_empty_cells(csv_content, snowflake_data)
    assert processed is not None
