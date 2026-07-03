import logging
import io
import os
import pandas as pd
from typing import Any, Dict, List, Tuple
from azure.storage.blob import BlobServiceClient
from shared_code import config

# ==============================================================================
# BLOB STORAGE HELPERS
# ==============================================================================
def read_blob_metadata(container_name: str, blob_name: str, connection_str: str) -> Dict[str, str]:
    """Reads and returns metadata of a blob in Azure Storage."""
    logging.info(f"Retrieving metadata for blob: container={container_name}, blob={blob_name}")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        properties = blob_client.get_blob_properties()
        return properties.metadata or {}
    except Exception as exc:
        logging.error(f"Failed to read blob metadata: {exc}", exc_info=True)
        return {}

def upload_processed_file(blob_name: str, updated_content: bytes, destination_container: str, connection_str: str) -> None:
    """Uploads the processed file content to an Azure Storage container."""
    logging.info(f"Uploading file '{blob_name}' to container '{destination_container}'")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_str)
        container_client = blob_service_client.get_container_client(destination_container)
        
        # Ensure container exists (e.g. for development with Azurite)
        try:
            container_client.create_container()
            logging.info(f"Container '{destination_container}' did not exist and was created.")
        except Exception:
            pass  # Container already exists
            
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(updated_content, overwrite=True)
        logging.info(f"Successfully uploaded file to {destination_container}/{blob_name}")
    except Exception as exc:
        logging.error(f"Failed to upload file to container '{destination_container}': {exc}", exc_info=True)
        raise

# ==============================================================================
# GENERAL HELPERS
# ==============================================================================
def is_empty(v) -> bool:
    """Normalize emptiness checks across None/NaN/blank string representations."""
    if v is None:
        return True
    if isinstance(v, float) and v != v:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    try:
        return pd.isna(v)
    except (TypeError, ValueError):
        return False

def _clean_lcdv(v) -> str or None:
    """Normalize LCDV to a clean alphanumeric string (remove scientific notation)."""
    if v is None or (isinstance(v, float) and v != v):
        return None
    s = str(v).strip()
    if not s:
        return None
    if "e" in s.lower() and any(c.isdigit() for c in s):
        try:
            return str(int(float(s)))
        except (ValueError, OverflowError):
            pass
    return s

def get_column_letter(col_idx: int) -> str:
    """Convert a 1-based column index to an Excel column letter (replaces openpyxl)."""
    letter = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        letter = chr(65 + remainder) + letter
    return letter

def detect_sep_from_content(content_str: str) -> str:
    """Detect the CSV delimiter from the first line (';' preferred when tied)."""
    first_line = content_str.split("\n", 1)[0]
    return ";" if first_line.count(";") >= first_line.count(",") else ","

# ==============================================================================
# ENGINE 1: ADD USER ID AND DATES
# ==============================================================================
def get_validity_date_columns(expected_cols: List[str]) -> Tuple[str or None, str or None]:
    """Find validity start/end column names from the expected schema."""
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

def insert_column_if_missing(df: pd.DataFrame, col_name: str, expected_cols: List[str], default_value="") -> pd.DataFrame:
    """Insert one missing column at the right schema position without reordering."""
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
        df[col_name] = default_value
    else:
        insert_idx = df.columns.get_loc(insert_before)
        df.insert(insert_idx, col_name, default_value)

    return df

def add_user_id_and_dates(file_name: str, file_content: bytes, user_id: str, start_date: str, end_date: str) -> bytes:
    """Implements Script 1 logic to add/fill validity dates and user_id."""
    content_str = file_content.decode("utf-8-sig", errors="ignore")
    sep = detect_sep_from_content(content_str)
    
    df = pd.read_csv(
        io.StringIO(content_str),
        dtype=str,
        sep=sep,
        engine="python",
        keep_default_na=False
    )
    df.columns = df.columns.str.strip()

    # Find matching schema prefix in config
    matched_key = None
    for key in config.FINAL_COLUMNS.keys():
        if key.upper() in file_name.upper():
            matched_key = key
            break

    if not matched_key:
        logging.warning(f"File '{file_name}' not found in FINAL_COLUMNS schema mapping. Skipping schema enrichment.")
        # Default behavior: append at the end
        if "Validity_Start_date" not in df.columns:
            df["Validity_Start_date"] = start_date
        if "Validity_end_date" not in df.columns:
            df["Validity_end_date"] = end_date
        if "User_Identification" not in df.columns:
            df["User_Identification"] = user_id
    else:
        expected_cols = config.FINAL_COLUMNS[matched_key]
        add_validity_dates = "INVOICE" not in matched_key.upper()
        start_col, end_col = get_validity_date_columns(expected_cols)

        if add_validity_dates and start_col:
            df = insert_column_if_missing(df, start_col, expected_cols, start_date)
            df[start_col] = start_date

        if add_validity_dates and end_col:
            df = insert_column_if_missing(df, end_col, expected_cols, end_date)
            df[end_col] = end_date

        if "User_Identification" in expected_cols:
            df = insert_column_if_missing(df, "User_Identification", expected_cols, user_id)
            df["User_Identification"] = user_id

    # Always output with semicolon separator as in original script
    output_stream = io.StringIO()
    df.to_csv(output_stream, index=False, sep=";", encoding="utf-8-sig")
    return output_stream.getvalue().encode("utf-8-sig")

# ==============================================================================
# ENGINE 2: FILL EMPTY CELLS (COMBINATORIAL EXPANSION)
# ==============================================================================
def get_brand_group(brand: str) -> str or None:
    brand = str(brand or "").strip().upper()
    if brand in config.PCD_BRANDS:
        return "PCD"
    if brand in config.OV_BRANDS:
        return "OV"
    if brand in config.FCA_BRANDS:
        return "FCA"
    return None

def get_expected_lcdv_lengths(brand: str) -> set:
    brand = str(brand or "").strip().upper()
    if brand in config.PCD_BRANDS:
        return {16}
    if brand in config.OV_BRANDS:
        return {9, 16}
    if brand == "FI":
        return {10, 12}
    if brand in config.FCA_BRANDS:
        return {12}
    return set()

def get_energy_from_lcdv(lcdv: str) -> str or None:
    lcdv = _clean_lcdv(lcdv)
    if not lcdv:
        return None
    return lcdv[7:9] if len(lcdv) >= 9 else None

def is_complete_lcdv_for_brand(lcdv: str, brand: str) -> bool:
    lcdv = _clean_lcdv(lcdv)
    if not lcdv or "_" in lcdv or "*" in lcdv:
        return False
    expected_lengths = get_expected_lcdv_lengths(brand)
    return len(lcdv) in expected_lengths

def is_partial_lcdv_for_brand(lcdv: str, brand: str) -> bool:
    lcdv = _clean_lcdv(lcdv)
    if not lcdv:
        return False
    if "_" in lcdv or "*" in lcdv:
        return True
    return not is_complete_lcdv_for_brand(lcdv, brand)

def lcdv_matches_pattern(candidate: str, pattern: str) -> bool:
    candidate = _clean_lcdv(candidate)
    pattern = _clean_lcdv(pattern)
    if not candidate or not pattern or len(candidate) < len(pattern):
        return False
    for i, p in enumerate(pattern):
        if p in {"_", "*"}:
            continue
        if candidate[i] != p:
            return False
    return True

def _get_candidate_pairs(country: str, brand: str, energy: str or None, lookups: dict) -> set:
    group = config.PCD_BRANDS if brand in config.PCD_BRANDS else (config.OV_BRANDS if brand in config.OV_BRANDS else ("FCA" if brand in config.FCA_BRANDS else None))
    energy = None if is_empty(energy) else str(energy)

    if brand in config.PCD_BRANDS or brand in config.OV_BRANDS:
        if energy:
            lcdvs = lookups["ref_cbm"].get((country, brand, energy), set())
            return {(lv, energy) for lv in lcdvs}
        return set(lookups["ref_cb"].get((country, brand), set()))

    if brand in config.FCA_BRANDS:
        if energy:
            lcdvs = lookups["cfa_cbe"].get((country, brand, energy), set()) | lookups["ent_cbe"].get((country, brand, energy), set())
            return {(lv, energy) for lv in lcdvs}
        return set(lookups["cfa_cb"].get((country, brand), set())) | set(lookups["ent_cb"].get((country, brand), set()))

    return set()

def resolve_lcdv_energy(lcdv, energy, country, brand, lookups: dict) -> List[Tuple]:
    brand = str(brand or "").strip()
    country = str(country or "").strip()
    lcdv_in = None if is_empty(lcdv) else _clean_lcdv(lcdv)
    energy_in = None if is_empty(energy) else str(energy).strip()

    # Case 1: LCDV is empty
    if not lcdv_in:
        pairs = _get_candidate_pairs(country, brand, energy_in, lookups)
        return list(pairs) or [(None, energy_in if energy_in else None)]

    # Case 2: LCDV is present (exact or pattern)
    candidate_pairs = _get_candidate_pairs(country, brand, energy_in, lookups)
    matched_pairs = []
    for lv, ev in candidate_pairs:
        if lcdv_matches_pattern(lv, lcdv_in):
            matched_pairs.append((lv, ev if ev is not None else get_energy_from_lcdv(lv)))

    matched_pairs = list(dict.fromkeys(matched_pairs))
    if matched_pairs:
        return matched_pairs

    # Fallback
    derived_energy = get_energy_from_lcdv(lcdv_in)
    return [(lcdv_in, derived_energy or energy_in)]

def _compute_gaps(intervals: List[Tuple[float, float]], max_default: float) -> List[Tuple[float, float]]:
    if not intervals:
        return [(0.0, max_default)]
    sorted_ivs = sorted(intervals)
    cur_s, cur_e = sorted_ivs[0]
    merged = []

    for s, e in sorted_ivs[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    gaps = []
    prev = 0.0
    for s, e in merged:
        if s > prev:
            gaps.append((prev, s))
        prev = max(prev, e)

    if prev < max_default:
        gaps.append((prev, max_default))
    return gaps

def _fmt_range(v: float) -> Any:
    return int(v) if v == int(v) else v

def fill_range_gaps(rows: List[dict], colors: List[str or None], key_cols: List[str], min_col: str, max_col: str, max_default: float) -> Tuple[List[dict], List[str or None], dict]:
    if not rows:
        return rows, colors, {"simple": 0, "gap_sources": 0, "gap_rows": 0}

    sample = rows[0]
    if min_col not in sample and max_col not in sample:
        return rows, colors, {"simple": 0, "gap_sources": 0, "gap_rows": 0}

    from collections import defaultdict
    key_intervals = defaultdict(list)

    for row in rows:
        v_min = row.get(min_col)
        v_max = row.get(max_col)
        if not is_empty(v_min) and not is_empty(v_max):
            try:
                s, e = float(v_min), float(v_max)
                if s <= e:
                    key_intervals[tuple(row.get(c) for c in key_cols)].append((s, e))
            except (ValueError, TypeError):
                pass

    new_rows = []
    new_colors = []
    s_simple = s_gap_sources = s_gap_rows = 0

    for row, color in zip(rows, colors):
        v_min = row.get(min_col)
        v_max = row.get(max_col)

        if is_empty(v_min) and not is_empty(v_max):
            nr = row.copy()
            nr[min_col] = 0
            new_rows.append(nr)
            new_colors.append(color)
            s_simple += 1
            continue

        if not is_empty(v_min) and is_empty(v_max):
            key = tuple(row.get(c) for c in key_cols)
            intervals = key_intervals.get(key, [])
            if not intervals:
                nr = row.copy()
                nr[max_col] = _fmt_range(max_default)
                new_rows.append(nr)
                new_colors.append(color)
                s_simple += 1
            else:
                gaps = _compute_gaps(intervals, max_default)
                try:
                    v_min_f = float(v_min)
                    matched = next((g for g in gaps if g[0] <= v_min_f <= g[1]), None)
                except (ValueError, TypeError):
                    matched = None

                nr = row.copy()
                nr[max_col] = _fmt_range(matched[1] if matched else max_default)
                new_rows.append(nr)
                new_colors.append(color)
                s_gap_sources += 1
                s_gap_rows += 1
                continue

        if not (is_empty(v_min) and is_empty(v_max)):
            new_rows.append(row)
            new_colors.append(color)
            continue

        # Both empty
        gap_color = "red" if color == "red" else "green"
        key = tuple(row.get(c) for c in key_cols)
        intervals = key_intervals.get(key, [])

        if not intervals:
            nr = row.copy()
            nr[min_col] = 0
            nr[max_col] = _fmt_range(max_default)
            new_rows.append(nr)
            new_colors.append(gap_color)
            s_simple += 1
        else:
            gaps = _compute_gaps(intervals, max_default)
            if not gaps:
                new_rows.append(row)
                new_colors.append(color)
            else:
                s_gap_sources += 1
                for g_min, g_max in gaps:
                     nr = row.copy()
                     nr[min_col] = _fmt_range(g_min)
                     nr[max_col] = _fmt_range(g_max)
                     new_rows.append(nr)
                     new_colors.append(gap_color)
                     s_gap_rows += 1

    return new_rows, new_colors, {
        "simple": s_simple,
        "gap_sources": s_gap_sources,
        "gap_rows": s_gap_rows,
    }

def fill_empty_cells(file_name: str, file_content: bytes, snowflake_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[bytes, bytes or None, bytes or None]:
    """Implements Script 2 logic using Snowflake datasets instead of local CSV/Excel files."""
    from collections import defaultdict
    
    # --------------------------------------------------------------------------
    # 1. BUILD RESOLUTION LOOKUPS FROM SNOWFLAKE DATA
    # --------------------------------------------------------------------------
    # A. BB_LEGAL_ENTITY -> compat_le
    compat_le = {}
    for row in snowflake_data["BB_LEGAL_ENTITY"]:
        le_code = row.get("legal_entity_code")
        country = row.get("country")
        brand_str = str(row.get("brand") or "")
        brands_raw = [b.strip() for b in brand_str.split() if b.strip()]
        brands = [b for b in brands_raw if b not in config.BRANDS_IGNORED]
        if le_code and not is_empty(le_code):
            compat_le[str(le_code).strip()] = {
                "country": str(country).strip() if not is_empty(country) else None,
                "brands": brands,
            }

    # B. REFERENCIAL_DATA_UCDM -> ref_cbm, ref_cb
    ref_cbm = defaultdict(set)
    ref_cb = defaultdict(set)
    for row in snowflake_data["REFERENCIAL_DATA_UCDM"]:
        c_id = row.get("country_id")
        b_id = row.get("brand_id")
        l_16 = _clean_lcdv(row.get("lcdv_16"))
        m_id = row.get("motor_id")
        if not (is_empty(c_id) or is_empty(b_id) or is_empty(l_16) or is_empty(m_id)):
            c_id = str(c_id).strip()
            b_id = str(b_id).strip()
            l_16 = str(l_16).strip()
            m_id = str(m_id).strip()
            ref_cbm[(c_id, b_id, m_id)].add(l_16)
            ref_cb[(c_id, b_id)].add((l_16, m_id))

    # C. CFA_TRANSCODED -> cfa_cbe, cfa_cb
    cfa_cbe = defaultdict(set)
    cfa_cb = defaultdict(set)
    for row in snowflake_data["CFA_TRANSCODED"]:
        c = row.get("country")
        b = row.get("brand_name")
        lv = _clean_lcdv(row.get("lcdv"))
        if not (is_empty(c) or is_empty(b) or is_empty(lv)):
            c = str(c).strip()
            b = str(b).strip()
            lv = str(lv).strip()
            if len(lv) >= 9:
                energy = lv[7:9]
                cfa_cbe[(c, b, energy)].add(lv)
                cfa_cb[(c, b)].add((lv, energy))

    # D. ENT_UC_STOCK_IMAGE -> ent_cbe, ent_cb
    ent_cbe = defaultdict(set)
    ent_cb = defaultdict(set)
    for row in snowflake_data["ENT_UC_STOCK_IMAGE"]:
        c = row.get("cd_country_code")
        b = row.get("cd_brand_code")
        lv = _clean_lcdv(row.get("cd_lcdv_code"))
        if not (is_empty(c) or is_empty(b) or is_empty(lv)):
            c = str(c).strip()
            b = str(b).strip()
            lv = str(lv).strip()
            if len(lv) >= 9:
                energy = lv[7:9]
                ent_cbe[(c, b, energy)].add(lv)
                ent_cb[(c, b)].add((lv, energy))

    lookups = {
        "ref_cbm": ref_cbm,
        "ref_cb": ref_cb,
        "cfa_cbe": cfa_cbe,
        "cfa_cb": cfa_cb,
        "ent_cbe": ent_cbe,
        "ent_cb": ent_cb
    }

    # --------------------------------------------------------------------------
    # 2. PROCESS INPUT FILE
    # --------------------------------------------------------------------------
    content_str = file_content.decode("utf-8-sig", errors="ignore")
    sep = detect_sep_from_content(content_str)
    
    df_in = pd.read_csv(
        io.StringIO(content_str),
        dtype=str,
        sep=sep,
        keep_default_na=False,
        na_values=["", " ", "nan", "NULL", "N/A"]
    )
    df_in = df_in.astype(str)

    all_rows = df_in.to_dict(orient="records")
    output_rows = []
    output_colors = []
    recap_long = []
    unresolved = []

    COL_LEGAL_ENTITY = "Legal_Entity"
    COL_BRAND = "Brand"
    COL_CHANNEL = "standardized_UC_Origin_Channel"
    COL_LCDV_GROUP = "LCDV_group"
    COL_NV_UC = "nv_uc"
    COL_SCENARIO = "Scenario"
    COL_ENERGY = "Energy_type"
    COL_KM_MIN = "Km_minimum"
    COL_KM_MAX = "Km_maximum"
    COL_DURATION_MIN = "Minimum_Contract_duration"
    COL_DURATION_MAX = "Maximum_Contract_duration"

    for src_idx, row_dict in enumerate(all_rows):
        lcdv_raw = row_dict.get(COL_LCDV_GROUP)
        source_has_empty = any(is_empty(row_dict.get(col)) for col in df_in.columns[:7])
        source_lcdv_present = not is_empty(lcdv_raw)

        if not source_has_empty and not source_lcdv_present:
            output_rows.append(row_dict)
            output_colors.append(None)
            continue

        le_info = compat_le.get(str(row_dict.get(COL_LEGAL_ENTITY)) or "", {})
        country = le_info.get("country")
        candidates = [row_dict.copy()]

        usable_brands = []
        channels = []

        # 1. Scenario
        if is_empty(row_dict.get(COL_SCENARIO)):
            for c in candidates:
                c[COL_SCENARIO] = "RE"

        # 2. NV / UC
        if is_empty(row_dict.get(COL_NV_UC)):
            expanded = []
            for c in candidates:
                for val in ("NV", "UC"):
                    nc = c.copy()
                    nc[COL_NV_UC] = val
                    expanded.append(nc)
            candidates = expanded

        # 3. Brand
        if is_empty(row_dict.get(COL_BRAND)):
            usable_brands = le_info.get("brands", [])
            if usable_brands:
                expanded = []
                for c in candidates:
                    for b in usable_brands:
                        nc = c.copy()
                        nc[COL_BRAND] = b
                        expanded.append(nc)
                candidates = expanded

        # 4. Channel
        if is_empty(row_dict.get(COL_CHANNEL)):
            channels = config.compat_channels.get(str(country or ""), [])
            if channels:
                expanded = []
                for c in candidates:
                    for ch in channels:
                        nc = c.copy()
                        nc[COL_CHANNEL] = ch
                        expanded.append(nc)
                candidates = expanded

        # 5 & 6. LCDV + Energy
        lcdv_val_raw = row_dict.get(COL_LCDV_GROUP)
        lcdv_empty = is_empty(lcdv_val_raw)
        lcdv_is_partial = not lcdv_empty
        energy_empty = is_empty(row_dict.get(COL_ENERGY))

        if lcdv_empty or lcdv_is_partial or energy_empty:
            expanded = []
            for c in candidates:
                brand = c.get(COL_BRAND)
                if is_empty(brand):
                    expanded.append(c)
                    continue

                lcdv_in = None if is_empty(c.get(COL_LCDV_GROUP)) else c.get(COL_LCDV_GROUP)
                energy_in = None if is_empty(c.get(COL_ENERGY)) else c.get(COL_ENERGY)

                pairs = resolve_lcdv_energy(lcdv_in, energy_in, str(country or ""), str(brand), lookups)

                for (lv, ev) in pairs:
                    nc = c.copy()
                    nc[COL_LCDV_GROUP] = lv
                    if is_empty(nc.get(COL_ENERGY)):
                        nc[COL_ENERGY] = ev
                    expanded.append(nc)

            candidates = expanded

        # Row Classification
        for c in candidates:
            n_vides = sum(1 for col in df_in.columns[:7] if is_empty(c.get(col)))
            if n_vides > 0:
                unresolved.append(c)
            else:
                output_rows.append(c)
                output_colors.append("green" if source_has_empty else None)

        # Recap statistics aggregation
        if source_has_empty:
            seven_cols = list(df_in.columns[:7])
            for col_idx, col in enumerate(seven_cols):
                if not is_empty(row_dict.get(col)):
                    continue

                cell_ref = f"{get_column_letter(col_idx + 1)}{src_idx + 2}"
                header = f"{cell_ref} ({col})"

                if col == COL_BRAND:
                    recap_long.append({
                        "EMPTY CELL": "Compatibility S1",
                        "cell": header,
                        "count": len(usable_brands),
                    })
                elif col == COL_CHANNEL:
                    recap_long.append({
                        "EMPTY CELL": "Compatibility S2",
                        "cell": header,
                        "count": len(channels),
                    })
                elif col in (COL_LCDV_GROUP, COL_ENERGY):
                    brands_check = [row_dict.get(COL_BRAND)] if not is_empty(row_dict.get(COL_BRAND)) else usable_brands
                    tot_ref = tot_cfa = tot_ent = 0
                    e_val = None if is_empty(row_dict.get(COL_ENERGY)) else row_dict.get(COL_ENERGY)

                    for b in brands_check:
                        grp = get_brand_group(b)
                        if grp in ("PCD", "OV"):
                            tot_ref += len(ref_cbm.get((country, b, e_val), set()) if e_val else ref_cb.get((country, b), set()))
                        elif grp == "FCA":
                            tot_cfa += len(cfa_cbe.get((country, b, e_val), set()) if e_val else set(lv for lv, _ in cfa_cb.get((country, b), set())))
                            tot_ent += len(ent_cbe.get((country, b, e_val), set()) if e_val else set(lv for lv, _ in ent_cb.get((country, b), set())))

                    if tot_ref:
                        recap_long.append({"EMPTY CELL": "Referentiel V2", "cell": header, "count": tot_ref})
                    if tot_cfa:
                        recap_long.append({"EMPTY CELL": "CFA_TRANSCODED", "cell": header, "count": tot_cfa})
                    if tot_ent:
                        recap_long.append({"EMPTY CELL": "ENT_UC_STOCK", "cell": header, "count": tot_ent})
                    if not (tot_ref or tot_cfa or tot_ent):
                        recap_long.append({"EMPTY CELL": "aucune source", "cell": header, "count": 0})

    # Range gap completion (KM)
    range_key_cols = list(df_in.columns[:7])
    output_rows, output_colors, km_s = fill_range_gaps(
        output_rows,
        output_colors,
        range_key_cols,
        COL_KM_MIN,
        COL_KM_MAX,
        9999999.0
    )

    # Range gap completion (Contract Duration)
    output_rows, output_colors, dur_s = fill_range_gaps(
        output_rows,
        output_colors,
        range_key_cols,
        COL_DURATION_MIN,
        COL_DURATION_MAX,
        200.0
    )

    # Compile outputs
    df_out = pd.DataFrame(output_rows, columns=df_in.columns)
    df_out = df_out.drop_duplicates()
    
    # Processed CSV
    processed_stream = io.StringIO()
    df_out.to_csv(processed_stream, sep=sep, index=False, encoding="utf-8-sig")
    processed_bytes = processed_stream.getvalue().encode("utf-8-sig")

    # Recap report
    recap_bytes = None
    if recap_long:
        df_rl = pd.DataFrame(recap_long)
        df_recap = df_rl.pivot_table(
            index="EMPTY CELL",
            columns="cell",
            values="count",
            aggfunc="sum",
            fill_value=""
        )
        df_recap.columns.name = None
        recap_stream = io.StringIO()
        df_recap.to_csv(recap_stream, sep=";", encoding="utf-8-sig")
        recap_bytes = recap_stream.getvalue().encode("utf-8-sig")

    # Unresolved report
    unresolved_bytes = None
    if unresolved:
        df_unres = pd.DataFrame(unresolved, columns=df_in.columns)
        df_unres = df_unres.drop_duplicates()
        unres_stream = io.StringIO()
        df_unres.to_csv(unres_stream, sep=";", index=False, encoding="utf-8-sig")
        unresolved_bytes = unres_stream.getvalue().encode("utf-8-sig")

    return processed_bytes, recap_bytes, unresolved_bytes
