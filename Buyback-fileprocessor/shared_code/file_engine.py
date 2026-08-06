import logging
import math
import io
import pandas as pd
from typing import Any, Dict, List, Tuple
from azure.storage.blob import BlobServiceClient
from shared_code import config

KEY_EMPTY_CELL = "EMPTY CELL"

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
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    try:
        return pd.isna(v)
    except (TypeError, ValueError):
        return False

def _clean_lcdv(v) -> str or None:
    """Normalize LCDV to a clean alphanumeric string (remove scientific notation)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
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

def _find_matched_schema_key(file_name: str) -> str or None:
    """Helper to find matching schema key prefix in config."""
    for key in config.FINAL_COLUMNS.keys():
        if key.upper() in file_name.upper():
            return key
    return None

def _apply_default_enrichment(df: pd.DataFrame, start_date: str, end_date: str, user_id: str) -> None:
    """Helper to apply default enrichment when schema is missing."""
    if "Validity_Start_date" not in df.columns:
        df["Validity_Start_date"] = start_date
    if "Validity_end_date" not in df.columns:
        df["Validity_end_date"] = end_date
    if "User_Identification" not in df.columns:
        df["User_Identification"] = user_id

def _apply_schema_enrichment(df: pd.DataFrame, matched_key: str, start_date: str, end_date: str, user_id: str) -> pd.DataFrame:
    """Helper to enrich dataframe based on matching schema mapping."""
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

    return df

def add_user_id_and_dates(file_name: str, file_content: bytes, user_id: str, start_date: str, end_date: str) -> bytes:
    """Enrich the input data with validity dates and user identification."""
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

    matched_key = _find_matched_schema_key(file_name)

    if not matched_key:
        logging.warning(f"File '{file_name}' not found in FINAL_COLUMNS schema mapping. Skipping schema enrichment.")
        _apply_default_enrichment(df, start_date, end_date, user_id)
    else:
        df = _apply_schema_enrichment(df, matched_key, start_date, end_date, user_id)

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

def _resolve_empty_lcdv(country: str, brand: str, energy_in: str or None, lookups: dict) -> List[Tuple]:
    """Helper to resolve LCDV when input is empty."""
    pairs = _get_candidate_pairs(country, brand, energy_in, lookups)
    if pairs:
        return list(pairs)
    fallback_energy = energy_in if energy_in else None
    return [(None, fallback_energy)]

def _resolve_present_lcdv(lcdv_in: str, country: str, brand: str, energy_in: str or None, lookups: dict) -> List[Tuple]:
    """Helper to resolve LCDV when input is present."""
    candidate_pairs = _get_candidate_pairs(country, brand, energy_in, lookups)
    matched_pairs = []
    for lv, ev in candidate_pairs:
        if not lcdv_matches_pattern(lv, lcdv_in):
            continue
        
        final_ev = ev
        if final_ev is None:
            final_ev = get_energy_from_lcdv(lv)
        matched_pairs.append((lv, final_ev))

    matched_pairs = list(dict.fromkeys(matched_pairs))
    if matched_pairs:
        return matched_pairs

    # Fallback
    derived_energy = get_energy_from_lcdv(lcdv_in)
    final_fallback_energy = derived_energy if derived_energy else energy_in
    return [(lcdv_in, final_fallback_energy)]

def resolve_lcdv_energy(lcdv, energy, country, brand, lookups: dict) -> List[Tuple]:
    """Resolves correct LCDV and Energy type pairs from available Snowflake context lookup mappings."""
    brand = str(brand or "").strip()
    country = str(country or "").strip()
    lcdv_in = None if is_empty(lcdv) else _clean_lcdv(lcdv)
    energy_in = None if is_empty(energy) else str(energy).strip()

    if not lcdv_in:
        return _resolve_empty_lcdv(country, brand, energy_in, lookups)

    return _resolve_present_lcdv(lcdv_in, country, brand, energy_in, lookups)

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

def _fill_range_gap_max_empty(
    row: dict,
    color: str or None,
    key_intervals: dict,
    max_col: str,
    max_default: float,
    key_cols: List[str],
    v_min: Any
) -> Tuple[List[dict], List[str or None], int, int, int]:
    """Helper to process the case when min_col is not empty, but max_col is empty."""
    key = tuple(row.get(c) for c in key_cols)
    intervals = key_intervals.get(key, [])
    if not intervals:
        nr = row.copy()
        nr[max_col] = _fmt_range(max_default)
        return [nr], [color], 1, 0, 0
    else:
        gaps = _compute_gaps(intervals, max_default)
        try:
            v_min_f = float(v_min)
            matched = next((g for g in gaps if g[0] <= v_min_f <= g[1]), None)
        except (ValueError, TypeError):
            matched = None

        nr = row.copy()
        nr[max_col] = _fmt_range(matched[1] if matched else max_default)
        return [nr], [color], 0, 1, 1

def _fill_range_gap_both_empty(
    row: dict,
    color: str or None,
    key_intervals: dict,
    min_col: str,
    max_col: str,
    max_default: float,
    key_cols: List[str]
) -> Tuple[List[dict], List[str or None], int, int, int]:
    """Helper to process the case when both min_col and max_col are empty."""
    gap_color = "red" if color == "red" else "green"
    key = tuple(row.get(c) for c in key_cols)
    intervals = key_intervals.get(key, [])

    if not intervals:
        nr = row.copy()
        nr[min_col] = 0
        nr[max_col] = _fmt_range(max_default)
        return [nr], [gap_color], 1, 0, 0
    else:
        gaps = _compute_gaps(intervals, max_default)
        if not gaps:
            return [row], [color], 0, 0, 0
        else:
            res_rows = []
            res_colors = []
            for g_min, g_max in gaps:
                 nr = row.copy()
                 nr[min_col] = _fmt_range(g_min)
                 nr[max_col] = _fmt_range(g_max)
                 res_rows.append(nr)
                 res_colors.append(gap_color)
            return res_rows, res_colors, 0, 1, len(gaps)

def _fill_range_gap_for_row(
    row: dict,
    color: str or None,
    key_intervals: dict,
    min_col: str,
    max_col: str,
    max_default: float,
    key_cols: List[str]
) -> Tuple[List[dict], List[str or None], int, int, int]:
    """Helper to process a single row's range gap completion."""
    v_min = row.get(min_col)
    v_max = row.get(max_col)

    min_is_empty = is_empty(v_min)
    max_is_empty = is_empty(v_max)

    # Case 1: min is empty, max is not empty
    if min_is_empty and not max_is_empty:
        nr = row.copy()
        nr[min_col] = 0
        return [nr], [color], 1, 0, 0

    # Case 2: min is not empty, max is empty
    if not min_is_empty and max_is_empty:
        return _fill_range_gap_max_empty(row, color, key_intervals, max_col, max_default, key_cols, v_min)

    # Case 3: Both are not empty
    if not min_is_empty and not max_is_empty:
        return [row], [color], 0, 0, 0

    # Case 4: Both are empty
    return _fill_range_gap_both_empty(row, color, key_intervals, min_col, max_col, max_default, key_cols)

def _build_key_intervals(rows: List[dict], min_col: str, max_col: str, key_cols: List[str]) -> dict:
    """Helper to compile and group intervals mapped by key columns."""
    from collections import defaultdict
    key_intervals = defaultdict(list)
    for row in rows:
        v_min = row.get(min_col)
        v_max = row.get(max_col)
        if is_empty(v_min) or is_empty(v_max):
            continue
        try:
            s, e = float(v_min), float(v_max)
            if s <= e:
                key_intervals[tuple(row.get(c) for c in key_cols)].append((s, e))
        except (ValueError, TypeError):
            pass
    return key_intervals

def fill_range_gaps(rows: List[dict], colors: List[str or None], key_cols: List[str], min_col: str, max_col: str, max_default: float) -> Tuple[List[dict], List[str or None], dict]:
    """Fills range gaps in km/duration columns based on available intervals."""
    if not rows:
        return rows, colors, {"simple": 0, "gap_sources": 0, "gap_rows": 0}

    sample = rows[0]
    if min_col not in sample and max_col not in sample:
        return rows, colors, {"simple": 0, "gap_sources": 0, "gap_rows": 0}

    key_intervals = _build_key_intervals(rows, min_col, max_col, key_cols)

    new_rows = []
    new_colors = []
    s_simple = s_gap_sources = s_gap_rows = 0

    for row, color in zip(rows, colors):
        nr_list, nc_list, d_simple, d_gap_sources, d_gap_rows = _fill_range_gap_for_row(
            row, color, key_intervals, min_col, max_col, max_default, key_cols
        )
        new_rows.extend(nr_list)
        new_colors.extend(nc_list)
        s_simple += d_simple
        s_gap_sources += d_gap_sources
        s_gap_rows += d_gap_rows

    return new_rows, new_colors, {
        "simple": s_simple,
        "gap_sources": s_gap_sources,
        "gap_rows": s_gap_rows,
    }

def _build_compat_le(rows: List[dict]) -> Dict[str, dict]:
    """Helper to build legal entity compatibility mapping."""
    compat_le = {}
    for row in rows:
        le_code = row.get("legal_entity_code")
        if not le_code or is_empty(le_code):
            continue

        country = row.get("country")
        country_clean = str(country).strip() if not is_empty(country) else None

        brand_str = str(row.get("brand") or "")
        brands_raw = [b.strip() for b in brand_str.split()]
        brands = [b for b in brands_raw if b and b not in config.BRANDS_IGNORED]

        compat_le[str(le_code).strip()] = {
            "country": country_clean,
            "brands": brands,
        }
    return compat_le

def _build_ref_lookups(rows: List[dict], ref_cbm: dict, ref_cb: dict) -> None:
    """Helper to populate UCDM reference table mappings."""
    for row in rows:
        c_id = row.get("country_id")
        b_id = row.get("brand_id")
        l_16 = _clean_lcdv(row.get("lcdv_16"))
        m_id = row.get("motor_id")

        if is_empty(c_id) or is_empty(b_id) or is_empty(l_16) or is_empty(m_id):
            continue

        c_id = str(c_id).strip()
        b_id = str(b_id).strip()
        l_16 = str(l_16).strip()
        m_id = str(m_id).strip()
        ref_cbm[(c_id, b_id, m_id)].add(l_16)
        ref_cb[(c_id, b_id)].add((l_16, m_id))

def _build_cfa_lookups(rows: List[dict], cfa_cbe: dict, cfa_cb: dict) -> None:
    """Helper to populate CFA transcode reference table mappings."""
    for row in rows:
        c = row.get("country")
        b = row.get("brand_name")
        lv = _clean_lcdv(row.get("lcdv"))

        if is_empty(c) or is_empty(b) or is_empty(lv):
            continue

        c = str(c).strip()
        b = str(b).strip()
        lv = str(lv).strip()
        if len(lv) < 9:
            continue

        energy = lv[7:9]
        cfa_cbe[(c, b, energy)].add(lv)
        cfa_cb[(c, b)].add((lv, energy))

def _build_ent_lookups(rows: List[dict], ent_cbe: dict, ent_cb: dict) -> None:
    """Helper to populate ENT stock image reference table mappings."""
    for row in rows:
        c = row.get("cd_country_code")
        b = row.get("cd_brand_code")
        lv = _clean_lcdv(row.get("cd_lcdv_code"))

        if is_empty(c) or is_empty(b) or is_empty(lv):
            continue

        c = str(c).strip()
        b = str(b).strip()
        lv = str(lv).strip()
        if len(lv) < 9:
            continue

        energy = lv[7:9]
        ent_cbe[(c, b, energy)].add(lv)
        ent_cb[(c, b)].add((lv, energy))

def _build_lookups(snowflake_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Builds the resolution lookup tables from Snowflake data."""
    compat_le = _build_compat_le(snowflake_data.get("BB_LEGAL_ENTITY", []))

    from collections import defaultdict
    ref_cbm = defaultdict(set)
    ref_cb = defaultdict(set)
    _build_ref_lookups(snowflake_data.get("REFERENCIAL_DATA_UCDM", []), ref_cbm, ref_cb)

    cfa_cbe = defaultdict(set)
    cfa_cb = defaultdict(set)
    _build_cfa_lookups(snowflake_data.get("CFA_TRANSCODED", []), cfa_cbe, cfa_cb)

    ent_cbe = defaultdict(set)
    ent_cb = defaultdict(set)
    _build_ent_lookups(snowflake_data.get("ENT_UC_STOCK_IMAGE", []), ent_cbe, ent_cb)

    lookups = {
        "ref_cbm": ref_cbm,
        "ref_cb": ref_cb,
        "cfa_cbe": cfa_cbe,
        "cfa_cb": cfa_cb,
        "ent_cbe": ent_cbe,
        "ent_cb": ent_cb
    }
    return compat_le, lookups

def _expand_scenario(candidates: List[dict], original_val: Any) -> List[dict]:
    if is_empty(original_val):
        for c in candidates:
            c["Scenario"] = "RE"
    return candidates

def _expand_nv_uc(candidates: List[dict], original_val: Any) -> List[dict]:
    if not is_empty(original_val):
        return candidates
    expanded = []
    for c in candidates:
        for val in ("NV", "UC"):
            nc = c.copy()
            nc["nv_uc"] = val
            expanded.append(nc)
    return expanded

def _expand_brand(candidates: List[dict], original_val: Any, le_info: dict) -> Tuple[List[dict], List[str]]:
    if not is_empty(original_val):
        return candidates, []
    usable_brands = le_info.get("brands", [])
    if not usable_brands:
        return candidates, []
    expanded = []
    for c in candidates:
        for b in usable_brands:
            nc = c.copy()
            nc["Brand"] = b
            expanded.append(nc)
    return expanded, usable_brands

def _expand_channel(candidates: List[dict], original_val: Any, country: str or None) -> Tuple[List[dict], List[str]]:
    if not is_empty(original_val):
        return candidates, []
    channels = config.compat_channels.get(str(country or ""), [])
    if not channels:
        return candidates, []
    expanded = []
    for c in candidates:
        for ch in channels:
            nc = c.copy()
            nc["standardized_UC_Origin_Channel"] = ch
            expanded.append(nc)
    return expanded, channels

def _get_candidate_pairs_resolved(c: dict, country: str or None, lookups: dict) -> List[Tuple]:
    brand = c.get("Brand")
    if is_empty(brand):
        return []

    lcdv_in = c.get("LCDV_group")
    if is_empty(lcdv_in):
        lcdv_in = None

    energy_in = c.get("Energy_type")
    if is_empty(energy_in):
        energy_in = None

    return resolve_lcdv_energy(lcdv_in, energy_in, str(country or ""), str(brand), lookups)

def _expand_candidate_with_pairs(c: dict, pairs: List[Tuple], expanded: List[dict]) -> None:
    for (lv, ev) in pairs:
        nc = c.copy()
        nc["LCDV_group"] = lv
        if is_empty(nc.get("Energy_type")):
            nc["Energy_type"] = ev
        expanded.append(nc)

def _expand_lcdv_energy(
    candidates: List[dict],
    original_lcdv: Any,
    original_energy: Any,
    country: str or None,
    lookups: dict
) -> List[dict]:
    lcdv_empty = is_empty(original_lcdv)
    energy_empty = is_empty(original_energy)

    if not (lcdv_empty or not lcdv_empty or energy_empty):
        return candidates

    expanded = []
    for c in candidates:
        pairs = _get_candidate_pairs_resolved(c, country, lookups)
        if not pairs:
            expanded.append(c)
        else:
            _expand_candidate_with_pairs(c, pairs, expanded)

    return expanded

def _expand_row(row_dict: dict, le_info: dict, country: str or None, lookups: dict) -> Tuple[List[dict], List[str], List[str]]:
    """Expands a single row's empty cells combinatorially."""
    candidates = [row_dict.copy()]

    candidates = _expand_scenario(candidates, row_dict.get("Scenario"))
    candidates = _expand_nv_uc(candidates, row_dict.get("nv_uc"))
    candidates, usable_brands = _expand_brand(candidates, row_dict.get("Brand"), le_info)
    candidates, channels = _expand_channel(candidates, row_dict.get("standardized_UC_Origin_Channel"), country)
    candidates = _expand_lcdv_energy(candidates, row_dict.get("LCDV_group"), row_dict.get("Energy_type"), country, lookups)

    return candidates, usable_brands, channels

def _get_brands_check(row_dict: dict, usable_brands: List[str]) -> List[str]:
    brand_val = row_dict.get("Brand")
    if not is_empty(brand_val):
        return [brand_val]
    return usable_brands

def _get_brand_recap_counts(b: str, country: str or None, e_val: str or None, lookups: dict) -> Tuple[int, int, int]:
    grp = get_brand_group(b)
    if grp in ("PCD", "OV"):
        if e_val:
            tot = len(lookups["ref_cbm"].get((country, b, e_val), set()))
        else:
            tot = len(lookups["ref_cb"].get((country, b), set()))
        return tot, 0, 0
        
    if grp == "FCA":
        if e_val:
            tot_cfa = len(lookups["cfa_cbe"].get((country, b, e_val), set()))
            tot_ent = len(lookups["ent_cbe"].get((country, b, e_val), set()))
        else:
            tot_cfa = len({lv for lv, _ in lookups["cfa_cb"].get((country, b), set())})
            tot_ent = len({lv for lv, _ in lookups["ent_cb"].get((country, b), set())})
        return 0, tot_cfa, tot_ent
        
    return 0, 0, 0

def _add_recap_lcdv_energy_records(
    row_dict: dict,
    header: str,
    usable_brands: List[str],
    country: str or None,
    lookups: dict,
    recap_long: List[dict]
) -> None:
    """Generates and appends recap entries for LCDV / Energy fields."""
    brands_check = _get_brands_check(row_dict, usable_brands)
    tot_ref = tot_cfa = tot_ent = 0
    
    e_val = row_dict.get("Energy_type")
    if is_empty(e_val):
        e_val = None

    for b in brands_check:
        dr, dc, de = _get_brand_recap_counts(b, country, e_val, lookups)
        tot_ref += dr
        tot_cfa += dc
        tot_ent += de

    if tot_ref:
        recap_long.append({KEY_EMPTY_CELL: "Referentiel V2", "cell": header, "count": tot_ref})
    if tot_cfa:
        recap_long.append({KEY_EMPTY_CELL: "CFA_TRANSCODED", "cell": header, "count": tot_cfa})
    if tot_ent:
        recap_long.append({KEY_EMPTY_CELL: "ENT_UC_STOCK", "cell": header, "count": tot_ent})
    if not (tot_ref or tot_cfa or tot_ent):
        recap_long.append({KEY_EMPTY_CELL: "aucune source", "cell": header, "count": 0})

def _add_recap_records(
    row_dict: dict,
    src_idx: int,
    df_columns: List[str],
    usable_brands: List[str],
    channels: List[str],
    country: str or None,
    lookups: dict,
    recap_long: List[dict]
) -> None:
    """Generates and appends recap entries for empty cells in a row."""
    seven_cols = list(df_columns[:7])
    for col_idx, col in enumerate(seven_cols):
        if not is_empty(row_dict.get(col)):
            continue

        cell_ref = f"{get_column_letter(col_idx + 1)}{src_idx + 2}"
        header = f"{cell_ref} ({col})"

        if col == "Brand":
            recap_long.append({
                KEY_EMPTY_CELL: "Compatibility S1",
                "cell": header,
                "count": len(usable_brands),
            })
        elif col == "standardized_UC_Origin_Channel":
            recap_long.append({
                KEY_EMPTY_CELL: "Compatibility S2",
                "cell": header,
                "count": len(channels),
            })
        elif col in ("LCDV_group", "Energy_type"):
            _add_recap_lcdv_energy_records(row_dict, header, usable_brands, country, lookups, recap_long)

def _check_source_has_empty(row_dict: dict, columns: List[str]) -> bool:
    """Helper to check if any of the columns in a row are empty."""
    for col in columns:
        if is_empty(row_dict.get(col)):
            return True
    return False

def _classify_candidates(
    candidates: List[dict],
    seven_cols: List[str],
    source_has_empty: bool,
    output_rows: List[dict],
    output_colors: List[str or None],
    unresolved: List[dict]
) -> None:
    """Helper to classify and sort candidate rows into processed or unresolved lists."""
    for c in candidates:
        has_vides = False
        for col in seven_cols:
            if is_empty(c.get(col)):
                has_vides = True
                break

        if has_vides:
            unresolved.append(c)
        else:
            output_rows.append(c)
            output_colors.append("green" if source_has_empty else None)

def _process_input_row(
    row_dict: dict,
    src_idx: int,
    df_columns: List[str],
    compat_le: dict,
    lookups: dict,
    output_rows: List[dict],
    output_colors: List[str or None],
    recap_long: List[dict],
    unresolved: List[dict]
) -> None:
    """Helper to process a single input row for empty cell filling."""
    seven_cols = list(df_columns[:7])
    source_has_empty = _check_source_has_empty(row_dict, seven_cols)
    source_lcdv_present = not is_empty(row_dict.get("LCDV_group"))

    if not source_has_empty and not source_lcdv_present:
        output_rows.append(row_dict)
        output_colors.append(None)
        return

    le_info = compat_le.get(str(row_dict.get("Legal_Entity")) or "", {})
    country = le_info.get("country")
    
    candidates, usable_brands, channels = _expand_row(row_dict, le_info, country, lookups)

    _classify_candidates(candidates, seven_cols, source_has_empty, output_rows, output_colors, unresolved)

    # Recap statistics aggregation
    if source_has_empty:
        _add_recap_records(row_dict, src_idx, df_columns, usable_brands, channels, country, lookups, recap_long)

def _compile_recap_report(recap_long: List[dict]) -> bytes or None:
    """Helper to compile and format the recap report bytes."""
    if not recap_long:
        return None
    df_rl = pd.DataFrame(recap_long)
    df_recap = df_rl.pivot_table(
        index=KEY_EMPTY_CELL,
        columns="cell",
        values="count",
        aggfunc="sum",
        fill_value=""
    )
    df_recap.columns.name = None
    recap_stream = io.StringIO()
    df_recap.to_csv(recap_stream, sep=";", encoding="utf-8-sig")
    return recap_stream.getvalue().encode("utf-8-sig")

def _compile_unresolved_report(unresolved: List[dict], df_columns: List[str]) -> bytes or None:
    """Helper to compile and format the unresolved report bytes."""
    if not unresolved:
        return None
    df_unres = pd.DataFrame(unresolved, columns=df_columns)
    df_unres = df_unres.drop_duplicates()
    unres_stream = io.StringIO()
    df_unres.to_csv(unres_stream, sep=";", index=False, encoding="utf-8-sig")
    return unres_stream.getvalue().encode("utf-8-sig")

def fill_empty_cells(file_content: bytes, snowflake_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[bytes, bytes or None, bytes or None]:
    """Process empty cell combinatorial expansion using Snowflake reference tables."""
    
    # --------------------------------------------------------------------------
    # 1. BUILD RESOLUTION LOOKUPS FROM SNOWFLAKE DATA
    # --------------------------------------------------------------------------
    compat_le, lookups = _build_lookups(snowflake_data)

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

    for src_idx, row_dict in enumerate(all_rows):
        _process_input_row(
            row_dict,
            src_idx,
            df_in.columns,
            compat_le,
            lookups,
            output_rows,
            output_colors,
            recap_long,
            unresolved
        )

    # Range gap completion (KM)
    range_key_cols = list(df_in.columns[:7])
    output_rows, output_colors, _ = fill_range_gaps(
        output_rows,
        output_colors,
        range_key_cols,
        "Km_minimum",
        "Km_maximum",
        9999999.0
    )

    # Range gap completion (Contract Duration)
    output_rows, output_colors, _ = fill_range_gaps(
        output_rows,
        output_colors,
        range_key_cols,
        "Minimum_Contract_duration",
        "Maximum_Contract_duration",
        200.0
    )

    # Compile outputs
    df_out = pd.DataFrame(output_rows, columns=df_in.columns)
    df_out = df_out.drop_duplicates()
    
    # Processed CSV
    processed_stream = io.StringIO()
    df_out.to_csv(processed_stream, sep=sep, index=False, encoding="utf-8-sig")
    processed_bytes = processed_stream.getvalue().encode("utf-8-sig")

    # Compile Reports
    recap_bytes = _compile_recap_report(recap_long)
    unresolved_bytes = _compile_unresolved_report(unresolved, df_in.columns)

    return processed_bytes, recap_bytes, unresolved_bytes
