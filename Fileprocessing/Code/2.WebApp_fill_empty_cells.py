#!/usr/bin/env python3
"""
expand_rates.py

Traite les 6 fichiers functional parameters en remplaçant chaque ligne
ayant des cellules vides dans les 7 premières colonnes par N lignes complètes.

Sources de lookup :
- BB_LEGAL_ENTITY          -> CD_LEGAL_ENTITY_CODE -> CD_COUNTRY_CODE + CD_BRAND_LIST_CODE
- compat_channels          -> pays -> channels
- Referentiel V2           -> LCDV / energy pour PCD et OV
- CFA_TRANSCODED.xlsx      -> LCDV / energy pour FCA
- ENT_UC_STOCK_IMAGE.CSV -> LCDV / energy pour FCA (agrégé avec CFA)
"""

import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter
from tqdm import tqdm

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=UserWarning)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Dossier contenant les 6 fichiers functional parameters
# (already enriched by Script 1 with user/date columns where applicable).
INPUT_DIR = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\2. Webapp_Add_User_and_Dates"

# Préfixes des 6 fichiers à traiter
# IMPORTANT:
# Invoice file (BB_INVOICE_NV_WEBAPP...) is intentionally excluded here.
# This script applies functional-parameter expansion logic only to the
# six pricing tables below.
FILE_PREFIXES = [
    "BB_RATE_OF_RETURN",
    "BB_UC_DISTRIBUTION_COSTS",
    "BB_UC_COMMERCIAL_MEANS",
    "BB_NET_RESTORATION_COSTS",
    "BB_RESIDUAL_VALUES_ADJUSTMENTS",
    "BB_DEDUCTIBLE_FOR_REPAIR_COSTS",
]

# Dossiers de sortie
OUTPUT_DIR     = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\3. Webapp_Fill_Empty_Cells"
RECAP_DIR      = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\3. Webapp_Fill_Empty_Cells\RECAP"
UNRESOLVED_DIR = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\3. Webapp_Fill_Empty_Cells\UNRESOLVED"

# BB_LEGAL_ENTITY
LE_FILE = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\04. Data\Flat Files\1. Webapp_Upload\BB_LEGAL_ENTITY_20260615.CSV"

# [Placeholder for missing lines 58-61 (e.g. REF_FILE, CFA_FILE)]

ENT_FILE = r"C:\Users\TE292QJ\EY\Stellantis - New Buyback tool - General\04. Development - 2026 - 01 to 12\05. CSV Data\DB_TL_FIN_LAB\ENT_UC_STOCK_IMAGE.CSV"

# Colonnes techniques des fichiers functional parameters
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

# Colonnes techniques de BB_LEGAL_ENTITY
LE_COL_CODE = "Legal_Entity_Code"
LE_COL_COUNTRY = "Country"
LE_COL_BRANDS = "Brand"

# Colonnes dans CFA et ENT
CFA_COL_COUNTRY = "Country"
CFA_COL_BRAND   = "BRAND_NAME"
CFA_COL_LCDV    = "LCDV"

ENT_COL_COUNTRY = "CD_COUNTRY_CODE"
ENT_COL_BRAND   = "CD_BRAND_CODE"
ENT_COL_LCDV    = "CD_LCDV_CODE"

# Marques présentes dans BB_LEGAL_ENTITY mais à ne PAS utiliser pour l'expansion
BRANDS_IGNORED = {"CH", "DO", "OT", "LE"}

# ==============================================================================
# GROUPS DE MARQUES
# ==============================================================================
PCD_BRANDS = {"AC", "DS", "AP"}
OV_BRANDS = {"OV"}
FCA_BRANDS = {"AB", "AR", "FI", "JP", "LA", "MA", "LE", "OT", "CH", "DO"}

def get_brand_group(brand: str) -> str | None:
    """Map a brand code to its processing group (PCD/OV/FCA) or None if unknown."""
    if brand in PCD_BRANDS:
        return "PCD"
    if brand in OV_BRANDS:
        return "OV"
    if brand in FCA_BRANDS:
        return "FCA"
    return None

# ==============================================================================
# TIMER
# ==============================================================================
class Timer:
    """Small utility to measure and print elapsed time by named processing step."""
    def __init__(self):
        self._starts: dict[str, float] = {}
        self.elapsed: dict[str, float] = {}

    def reset(self):
        """Reset all timers and elapsed records."""
        self._starts = {}
        self.elapsed = {}

    def start(self, label: str):
        """Record the start time for the named step."""
        self._starts[label] = time.perf_counter()

    def stop(self, label: str):
        """Stop the named step and store its elapsed duration."""
        self.elapsed[label] = time.perf_counter() - self._starts.get(label, time.perf_counter())

    def report(self, title: str = "RAPPORT DE PERFORMANCE"):
        """Print a formatted performance report showing elapsed time per step with percentage bars."""
        total = sum(self.elapsed.values()) or 1
        print(f"\n+==================================================+")
        print(f"| {title:<48}|")
        print(f"+==================================================+")
        for label, secs in sorted(self.elapsed.items(), key=lambda x: x[1], reverse=True):
            pct = 100 * secs / total
            bar = "#" * int(pct / 4)
            print(f"| {label:<26} {secs:7.2f}s {pct:5.1f}% {bar:<25}|")
        print(f"+==================================================+")
        print(f"| {'TOTAL':<26} {total:7.2f}s                           |")
        print(f"+==================================================+")

# ==============================================================================
# UTILITAIRES
# ==============================================================================
def safe_read_excel(path: str, label: str, **kwargs) -> pd.DataFrame | None:
    """Read an Excel file as strings; return None with a clear message if file is missing."""
    if not Path(path).exists():
        print(f" !! {label} introuvable : {path}")
        return None
    return pd.read_excel(path, dtype=str, engine="calamine", **kwargs)

def safe_read_csv(path: str, label: str, **kwargs) -> pd.DataFrame | None:
    """Read a CSV file as strings; return None with a clear message if file is missing."""
    if not Path(path).exists():
        print(f" !! {label} introuvable : {path}")
        return None
    return pd.read_csv(path, dtype=str, **kwargs)

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

# ==============================================================================
# HELPERS LCDV
# ==============================================================================
def get_expected_lcdv_lengths(brand: str) -> set[int]:
    """
    Return the LCDV lengths considered "complete" for a given brand.
    """
    brand = str(brand or "").strip().upper()

    if brand in PCD_BRANDS:
        return {16}

    if brand in OV_BRANDS:
        return {9, 16}

    if brand == "FI":  # exception Fiat
        return {10, 12}

    if brand in FCA_BRANDS:
        return {12}

    return set()

def get_energy_from_lcdv(lcdv: str) -> str | None:
    """
    Derive the energy code from the LCDV string.
    Current rule keeps positions 8-9 (Python slice [7:9]).
    """
    lcdv = _clean_lcdv(lcdv)
    if not lcdv:
        return None
    return lcdv[7:9] if len(lcdv) >= 9 else None

def is_complete_lcdv_for_brand(lcdv: str, brand: str) -> bool:
    """
    Return True when LCDV is complete for the brand:
    - no '_' or '*'
    - length matches expected lengths for that brand
    """
    lcdv = _clean_lcdv(lcdv)
    if not lcdv:
        return False

    if "_" in lcdv or "*" in lcdv:
        return False

    expected_lengths = get_expected_lcdv_lengths(brand)
    return len(lcdv) in expected_lengths

def is_partial_lcdv_for_brand(lcdv: str, brand: str) -> bool:
    """
    Return True when LCDV should be treated as a pattern:
    - contains '_' or '*'
    - or is not recognized as a complete LCDV
    """
    lcdv = _clean_lcdv(lcdv)
    if not lcdv:
        return False

    if "_" in lcdv or "*" in lcdv:
        return True

    return not is_complete_lcdv_for_brand(lcdv, brand)

def lcdv_matches_pattern(candidate: str, pattern: str) -> bool:
    """
    Compare one candidate LCDV against a pattern.

    Rules:
    - '_' or '*' are wildcards
    - a shorter pattern is treated as a prefix of the candidate
      (only pattern positions are compared)
    - if candidate is shorter than pattern, return False
    """
    candidate = _clean_lcdv(candidate)
    pattern = _clean_lcdv(pattern)

    if not candidate or not pattern:
        return False

    if len(candidate) < len(pattern):
        return False

    for i, p in enumerate(pattern):
        if p in {"_", "*"}:
            continue
        if candidate[i] != p:
            return False

    return True

def _get_candidate_pairs(country: str, brand: str, energy: str | None = None) -> set[tuple[str, str | None]]:
    """
    Return candidate (lcdv, energy) pairs based on brand group.
    If energy is provided, pre-filter candidates by energy.
    """
    group = get_brand_group(brand)
    energy = None if is_empty(energy) else str(energy)

    if group in ("PCD", "OV"):
        if energy:
            lcdvs = ref_cbm.get((country, brand, energy), set())
            return {(lv, energy) for lv in lcdvs}
        return set(ref_cb.get((country, brand), set()))

    if group == "FCA":
        if energy:
            lcdvs = cfa_cbe.get((country, brand, energy), set()) | ent_cbe.get((country, brand, energy), set())
            return {(lv, energy) for lv in lcdvs}
        return set(cfa_cb.get((country, brand), set())) | set(ent_cb.get((country, brand), set()))

    return set()

def _clean_lcdv(v) -> str | None:
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

def find_file(directory: str, prefix: str) -> Path | None:
    """Return the most recent file by descending name sort for a given prefix."""
    d = Path(directory)
    if not d.exists():
        return None
    matches = []
    for ext in (".xlsx", ".xls", ".csv"):
        matches.extend(d.glob(f"{prefix}*{ext}"))
    return sorted(matches, key=lambda p: p.name, reverse=True)[0] if matches else None

def _detect_sep(path: Path) -> str:
    """Detect delimiter from first line of the file (';' preferred when tied)."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        first_line = f.readline()
    return ";" if first_line.count(";") >= first_line.count(",") else ","

def read_input_file(path: Path) -> tuple[pd.DataFrame, str]:
    """Read one input table and return both DataFrame and detected separator."""
    sep = _detect_sep(path)
    print(f" Séparateur détecté : {repr(sep)}")
    df = pd.read_csv(
        path,
        dtype=str,
        sep=sep,
        keep_default_na=False,
        na_values=["", " ", "nan", "NULL", "N/A"],
    )
    return df, sep

# ==============================================================================
# # ÉTAPE 1 - BB_LEGAL_ENTITY
# ==============================================================================
print("\n[1/5] Chargement de BB_LEGAL_ENTITY...")
timer_global = Timer()
timer_global.start("1_legal_entity")

compat_le: dict[str, dict] = {}

df_le = safe_read_csv(LE_FILE, "BB_LEGAL_ENTITY", sep=";")
if df_le is not None:
    df_le.columns = df_le.columns.str.strip()

    for _, row in df_le.iterrows():
        le_code = row.get(LE_COL_CODE)
        country = row.get(LE_COL_COUNTRY)
        brand_str = str(row.get(LE_COL_BRANDS) or "")
        brands_raw = [b.strip() for b in brand_str.split() if b.strip()]
        brands = [b for b in brands_raw if b not in BRANDS_IGNORED]

        if le_code and not is_empty(le_code):
            compat_le[str(le_code).strip()] = {
                "country": str(country).strip() if not is_empty(country) else None,
                "brands": brands,
            }

timer_global.stop("1_legal_entity")
print(f" OK {len(compat_le)} legal entities | marques ignorées : {sorted(BRANDS_IGNORED)}")

# ==============================================================================
# # ÉTAPE 1b - Section 2 compatibility (Country -> Channels)
# ==============================================================================
print(" Section 2 (channels) codée en dur...", end=" ", flush=True)
compat_channels: dict[str, list[str]] = {
    "BE": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
    "ES": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
    "FR": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
    "NL": ["1", "2", "5", "6", "7", "9", "10", "13", "16"],
}
print(f"OK {len(compat_channels)} pays")

# ==============================================================================
# # ÉTAPE 2 - Référentiel (PCD + OV)
# ==============================================================================
print("\n[2/5] Chargement du référentiel (PCD + OV)...")
timer_global.start("2_referentiel")
print(REF_FILE)
df_ref = pd.read_excel(
    REF_FILE, sheet_name="Vehicle", header=4,
    usecols=["country_id", "brand_id", "lcdv_16", "motor_id"],
    dtype=str, engine="calamine",
)

df_ref.dropna(subset=["country_id", "brand_id", "lcdv_16", "motor_id"], inplace=True)
df_ref["lcdv_16"] = df_ref["lcdv_16"].apply(_clean_lcdv)

print(" Indexing référentiel...", end=" ", flush=True)
ref_cbm: dict[tuple, set] = (
    df_ref.groupby(["country_id", "brand_id", "motor_id"])["lcdv_16"].apply(set).to_dict()
)
ref_cb: dict[tuple, set] = (
    df_ref.groupby(["country_id", "brand_id"])
    .apply(lambda g: set(zip(g["lcdv_16"], g["motor_id"])), include_groups=False)
    .to_dict()
)
timer_global.stop("2_referentiel")
print(f"OK {len(df_ref):,} lignes  |  {len(ref_cb):,} clés (country, brand)")

# ==============================================================================
# # ÉTAPE 3 - CFA_TRANSCODED (FCA)
# ==============================================================================
print("\n[3/5] Chargement de CFA_TRANSCODED (FCA)...")
timer_global.start("3_cfa_transcoded")

cfa_cbe: dict[tuple, set] = {}
cfa_cb: dict[tuple, set] = {}

df_cfa = safe_read_excel(
    CFA_FILE,
    "CFA_TRANSCODED",
    usecols=[CFA_COL_COUNTRY, CFA_COL_BRAND, CFA_COL_LCDV],
)
if df_cfa is not None:
    df_cfa.dropna(subset=[CFA_COL_COUNTRY, CFA_COL_BRAND, CFA_COL_LCDV], inplace=True)
    df_cfa[CFA_COL_LCDV] = df_cfa[CFA_COL_LCDV].apply(_clean_lcdv)
    df_cfa = df_cfa[df_cfa[CFA_COL_LCDV].str.len() >= 9].copy()
    df_cfa["energy"] = df_cfa[CFA_COL_LCDV].str[7:9]

    print(" Indexing CFA_TRANSCODED...", end=" ", flush=True)
    cfa_cbe = df_cfa.groupby([CFA_COL_COUNTRY, CFA_COL_BRAND, "energy"])[CFA_COL_LCDV].apply(set).to_dict()
    cfa_cb = (
        df_cfa.groupby([CFA_COL_COUNTRY, CFA_COL_BRAND])
        .apply(lambda g: set(zip(g[CFA_COL_LCDV], g["energy"])), include_groups=False)
        .to_dict()
    )
    print(f"OK {len(df_cfa):,} lignes | {len(cfa_cb):,} clés (country, brand)")

timer_global.stop("3_cfa_transcoded")

# ==============================================================================
# # ÉTAPE 4 - ENT_UC_STOCK_IMAGE (FCA)
# ==============================================================================
print("\n[4/5] Chargement de ENT_UC_STOCK_IMAGE (FCA)...")
timer_global.start("4_ent_uc_stock")

ent_cbe: dict[tuple, set] = {}
ent_cb: dict[tuple, set] = {}

df_ent = safe_read_csv(
    ENT_FILE,
    "ENT_UC_STOCK_IMAGE",
    usecols=[ENT_COL_COUNTRY, ENT_COL_BRAND, ENT_COL_LCDV],
    sep=";",
)
if df_ent is not None:
    df_ent.dropna(subset=[ENT_COL_COUNTRY, ENT_COL_BRAND, ENT_COL_LCDV], inplace=True)
    df_ent[ENT_COL_LCDV] = df_ent[ENT_COL_LCDV].apply(_clean_lcdv)
    df_ent = df_ent[df_ent[ENT_COL_LCDV].str.len() >= 9].copy()
    df_ent["energy"] = df_ent[ENT_COL_LCDV].str[7:9]

    print(" Indexing ENT_UC_STOCK_IMAGE...", end=" ", flush=True)
    ent_cbe = df_ent.groupby([ENT_COL_COUNTRY, ENT_COL_BRAND, "energy"])[ENT_COL_LCDV].apply(set).to_dict()
    ent_cb = (
        df_ent.groupby([ENT_COL_COUNTRY, ENT_COL_BRAND])
        .apply(lambda g: set(zip(g[ENT_COL_LCDV], g["energy"])), include_groups=False)
        .to_dict()
    )
    print(f"OK {len(df_ent):,} lignes | {len(ent_cb):,} clés (country, brand)")

timer_global.stop("4_ent_uc_stock")

# ==============================================================================
# # FONCTION DE RÉSOLUTION LCDV + Energy
# ==============================================================================
# # FONCTION DE RÉSOLUTION LCDV + Energy
# ==============================================================================
def resolve_lcdv_energy(lcdv, energy, country, brand) -> list[tuple]:
    """
    Resolve LCDV and Energy with two paths:

    1) LCDV missing:
       - fetch all possible LCDV values for (country, brand)

    2) LCDV provided (complete or partial):
       - always search references using pattern matching
       - complete LCDV without wildcard behaves like exact match
       - fallback: if no match, keep original LCDV and derive energy when possible
    """
    brand = str(brand or "").strip()
    country = str(country or "").strip()

    lcdv_in = None if is_empty(lcdv) else _clean_lcdv(lcdv)
    energy_in = None if is_empty(energy) else str(energy).strip()

    # --------------------------------------------------------------------------
    # CAS 1 : LCDV ABSENT
    # --------------------------------------------------------------------------
    if not lcdv_in:
        pairs = _get_candidate_pairs(country, brand, energy_in)
        return list(pairs) or [(None, energy_in if energy_in else None)]

    # --------------------------------------------------------------------------
    # CAS 2 : LCDV PRÉSENT -> pattern matching (complet ou partiel)
    # --------------------------------------------------------------------------
    candidate_pairs = _get_candidate_pairs(country, brand, energy_in)

    matched_pairs = []
    for lv, ev in candidate_pairs:
        if lcdv_matches_pattern(lv, lcdv_in):
            matched_pairs.append((lv, ev if ev is not None else get_energy_from_lcdv(lv)))

    matched_pairs = list(dict.fromkeys(matched_pairs))

    if matched_pairs:
        return matched_pairs

    # Fallback : LCDV non trouvé dans les référentiels -> conserver tel quel
    derived_energy = get_energy_from_lcdv(lcdv_in)
    return [(lcdv_in, derived_energy or energy_in)]

# ==============================================================================
# # FONCTIONS KM / DURATION
# ==============================================================================
def _compute_gaps(intervals: list[tuple[float, float]], max_default: float) -> list[tuple[float, float]]:
    """Compute missing intervals in [0, max_default] from already-covered intervals."""
    sorted_ivs = sorted(intervals)
    cur_s, cur_e = sorted_ivs[0]
    merged: list[tuple[float, float]] = []

    for s, e in sorted_ivs[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    gaps: list[tuple[float, float]] = []
    prev = 0.0
    for s, e in merged:
        if s > prev:
            gaps.append((prev, s))
        prev = max(prev, e)

    if prev < max_default:
        gaps.append((prev, max_default))

    return gaps

def _fmt_range(v: float) -> int | float:
    """Format numeric range bounds without trailing .0 when value is an integer."""
    return int(v) if v == int(v) else v

def fill_range_gaps(
    rows: list[dict],
    colors: list[str | None],
    key_cols: list[str],
    min_col: str,
    max_col: str,
    max_default: float,
) -> tuple[list[dict], list[str | None], dict]:
    """Generic post-processing for filling gaps on a (min_col, max_col) interval pair."""
    if not rows:
        return rows, colors, {}

    sample = rows[0]
    if min_col not in sample and max_col not in sample:
        return rows, colors, {}

    key_intervals: dict[tuple, list[tuple[float, float]]] = defaultdict(list)

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

    new_rows: list[dict] = []
    new_colors: list[str | None] = []
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

# ==============================================================================
# # ÉTAPE 5 - BOUCLE SUR LES 6 FICHIERS
# ==============================================================================
# Ensure output folders exist before processing any input file.
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(RECAP_DIR).mkdir(parents=True, exist_ok=True)
Path(UNRESOLVED_DIR).mkdir(parents=True, exist_ok=True)

# Discover one latest file per expected prefix and track missing ones.
input_files: list[tuple[str, Path]] = []
missing_prefixes: list[str] = []

for prefix in FILE_PREFIXES:
    found = find_file(INPUT_DIR, prefix)
    if found:
        input_files.append((prefix, found))
    else:
        missing_prefixes.append(prefix)

print(f"\n[5/5] Expansion - {len(input_files)} fichier(s) trouvé(s) sur {len(FILE_PREFIXES)}")
if missing_prefixes:
    print(f"  !! Fichiers introuvables : {missing_prefixes}")

# Keep one summary dictionary per processed file for the final global report.
global_stats: dict[str, dict] = {}

# Main loop: process each functional-parameter file independently.
for file_num, (prefix, input_path) in enumerate(input_files):

    remaining = len(input_files) - file_num - 1
    print(f"\n{'='*60}")
    print(f" Fichier {file_num + 1}/{len(input_files)} : {input_path.name}")
    print(f" ({remaining} fichier(s) restant(s) après celui-ci)")
    print(f"{'='*60}")

    timer_file = Timer()
    timer_file.start("lecture")

    # Read the file with auto-detected separator and normalize to string columns.
    df_in, input_sep = read_input_file(input_path)

    # Tout passer en string (fix warning pandas)
    df_in = df_in.astype(str)

    timer_file.stop("lecture")
    print(f" Lignes en entrée : {len(df_in):,}")
    print(f" Colonnes          : {list(df_in.columns[:7])}")

    print(" Cellules vides par colonne :")
    total_vides = 0
    for col in df_in.columns[:7]:
        n = df_in[col].isna().sum()
        total_vides += n
        if n > 0:
            print(f"     {col:<40} : {n:,} vide(s)")
    print(
        f" Total : {total_vides:,} cellule(s) vide(s) | "
        f"{df_in.iloc[:, :7].isna().any(axis=1).sum():,} ligne(s) concernée(s)"
    )

    # Prepare working containers for expanded output, recap, unresolved rows, and stats.
    all_rows = df_in.to_dict(orient="records")
    output_rows: list[dict] = []
    output_colors: list[str | None] = []
    recap_long: list[dict] = []
    unresolved: list[dict] = []
    stats: dict[str, int] = defaultdict(int)

    timer_file.start("expansion")

    # Row-level expansion pipeline: fill empty dimensions and fan out combinations.
    for src_idx, row_dict in enumerate(tqdm(all_rows, desc=f" {prefix}", unit="rows")):
        lcdv_raw = row_dict.get(COL_LCDV_GROUP)
        source_has_empty = any(is_empty(row_dict.get(col)) for col in df_in.columns[:7])
        source_lcdv_present = not is_empty(lcdv_raw)

        if not source_has_empty and not source_lcdv_present:
            output_rows.append(row_dict)
            output_colors.append(None)
            continue

        # Build candidate rows from legal-entity compatibility context.
        le_info = compat_le.get(str(row_dict.get(COL_LEGAL_ENTITY)) or "", {})
        country = le_info.get("country")
        candidates: list[dict] = [row_dict.copy()]

        usable_brands: list[str] = []
        channels: list[str] = []

        # # 1. Scenario
        if is_empty(row_dict.get(COL_SCENARIO)):
            stats["scenario_filled"] += 1
            for c in candidates:
                c[COL_SCENARIO] = "RE"

        # # 2. NV / UC
        if is_empty(row_dict.get(COL_NV_UC)):
            stats["nv_uc_expanded"] += 1
            expanded: list[dict] = []
            for c in candidates:
                for val in ("NV", "UC"):
                    nc = c.copy()
                    nc[COL_NV_UC] = val
                    expanded.append(nc)
            candidates = expanded

        # # 3. Brand
        if is_empty(row_dict.get(COL_BRAND)):
            stats["brand_expanded"] += 1
            usable_brands = le_info.get("brands", [])
            if usable_brands:
                expanded = []
                for c in candidates:
                    for b in usable_brands:
                        nc = c.copy()
                        nc[COL_BRAND] = b
                        expanded.append(nc)
                candidates = expanded

        # # 4. Channel
        if is_empty(row_dict.get(COL_CHANNEL)):
            stats["channel_expanded"] += 1
            channels = compat_channels.get(str(country or ""), [])
            if channels:
                expanded = []
                for c in candidates:
                    for ch in channels:
                        nc = c.copy()
                        nc[COL_CHANNEL] = ch
                        expanded.append(nc)
                candidates = expanded

        # # 5 + 6. LCDV + Energy
        lcdv_val_raw = row_dict.get(COL_LCDV_GROUP)
        lcdv_empty = is_empty(lcdv_val_raw)
        lcdv_is_partial = not lcdv_empty # toujours chercher par pattern, taille non fiable
        energy_empty = is_empty(row_dict.get(COL_ENERGY))

        if lcdv_empty or lcdv_is_partial or energy_empty:
            stats["lcdv_energy_rows"] += 1
            count_before = len(candidates)
            expanded = []
            logged_partial: set[tuple] = set()

            # Resolve LCDV/Energy for each candidate brand-country combination.
            for c in candidates:
                brand = c.get(COL_BRAND)
                if is_empty(brand):
                    expanded.append(c)
                    continue

                lcdv_in = None if is_empty(c.get(COL_LCDV_GROUP)) else c.get(COL_LCDV_GROUP)
                energy_in = None if is_empty(c.get(COL_ENERGY)) else c.get(COL_ENERGY)

                pairs = resolve_lcdv_energy(lcdv_in, energy_in, str(country or ""), str(brand))

                lcdv_c = c.get(COL_LCDV_GROUP)
                lcdv_needs_replace = True # pattern matching systématique : on remplace toujours

                # Log LCDV partiels (une seule fois par pattern * brand)
                if lcdv_is_partial and lcdv_needs_replace and lcdv_in:
                    log_key = (lcdv_in, str(brand))
                    if log_key not in logged_partial:
                        logged_partial.add(log_key)
                        matched = [(lv, ev) for lv, ev in pairs if lv is not None]
                        tqdm.write(
                            f"\n [LCDV PATTERN] pattern='{lcdv_in}'"
                            f" brand={brand} country={country}"
                            f" -> {len(matched)} LCDV(s) trouvé(s)"
                        )
                    for lv, ev in matched[:3]:
                        tqdm.write(f"      -> {lv} (energy={ev})")
                    if len(matched) > 3:
                        tqdm.write(f"      ... et {len(matched) - 3} autre(s)")
                    if not matched:
                        tqdm.write(f"      (aucun match dans les référentiels)")

                for (lv, ev) in pairs:
                    nc = c.copy()
                    if lcdv_needs_replace:
                        nc[COL_LCDV_GROUP] = lv
                    if is_empty(nc.get(COL_ENERGY)):
                        nc[COL_ENERGY] = ev
                    expanded.append(nc)

            # Persist expanded candidates and update expansion counters.
            candidates = expanded
            factor = len(candidates) // max(count_before, 1)

            if lcdv_empty or lcdv_is_partial:
                stats["lcdv_group_rows"] += 1
            if energy_empty:
                stats["energy_type_rows"] += 1

        # Classify rows: unresolved rows are stored separately, resolved rows go to output.
        for c in candidates:
            n_vides = sum(1 for col in df_in.columns[:7] if is_empty(c.get(col)))
            if n_vides > 0:
                stats["unresolved_cells"] += n_vides
                unresolved.append(c)
            else:
                output_rows.append(c)
                output_colors.append("green" if source_has_empty else None)

        # Console sample and recap-source accounting for rows with original empty cells.
        if source_has_empty:
            cols_show = [COL_BRAND, COL_LCDV_GROUP, COL_ENERGY, COL_NV_UC, COL_CHANNEL]
            tqdm.write(
                f" Source LE={row_dict.get(COL_LEGAL_ENTITY)} | "
                f"Brand={row_dict.get(COL_BRAND)} | "
                f"LCDV={row_dict.get(COL_LCDV_GROUP)} | "
                f"Energy={row_dict.get(COL_ENERGY)} | "
                f"-> {len(candidates)} combinaison(s)"
            )
            for c in candidates[:5]:
                tqdm.write("  " + " | ".join(f"{col}={c.get(col)}" for col in cols_show if col in c))
            if len(candidates) > 5:
                tqdm.write(f"   ... et {len(candidates) - 5} autre(s)")

            # Recap pivoté
            seven_cols = list(df_in.columns[:7])
            for col_idx, col in enumerate(seven_cols):
                if not is_empty(row_dict.get(col)):
                    continue

                cell_ref = f"{get_column_letter(col_idx + 1)}{src_idx + 2}"
                header = f"{cell_ref} ({col})"

                if col in (COL_SCENARIO, COL_NV_UC):
                    pass
                elif col == COL_BRAND:
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
                    brands_check = (
                        [row_dict.get(COL_BRAND)]
                        if not is_empty(row_dict.get(COL_BRAND))
                        else usable_brands
                    )

                    tot_ref = tot_cfa = tot_ent = 0
                    e_val = None if is_empty(row_dict.get(COL_ENERGY)) else row_dict.get(COL_ENERGY)

                    for b in brands_check:
                        grp = get_brand_group(str(b)) if b else None
                        if grp in ("PCD", "OV"):
                            tot_ref += len(
                                ref_cbm.get((country, b, e_val), set()) if e_val
                                else ref_cb.get((country, b), set())
                            )
                        elif grp == "FCA":
                            tot_cfa += len(
                                cfa_cbe.get((country, b, e_val), set()) if e_val
                                else set(lv for lv, _ in cfa_cb.get((country, b), set()))
                            )
                        elif grp == "ENT":
                            tot_ent += len(
                                ent_cbe.get((country, b, e_val), set()) if e_val
                                else set(lv for lv, _ in ent_cb.get((country, b), set()))
                            )

                    if tot_ref:
                        recap_long.append({"EMPTY CELL": "Referentiel V2", "cell": header, "count": tot_ref})
                    if tot_cfa:
                        recap_long.append({"EMPTY CELL": "CFA_TRANSCODED", "cell": header, "count": tot_cfa})
                    if tot_ent:
                        recap_long.append({"EMPTY CELL": "ENT_UC_STOCK", "cell": header, "count": tot_ent})
                    if not (tot_ref or tot_cfa or tot_ent):
                        recap_long.append({"EMPTY CELL": "aucune source", "cell": header, "count": 0})

    timer_file.stop("expansion")

    # Post-process numeric intervals: complete missing KM ranges using sibling rows/gaps.
    range_key_cols = list(df_in.columns[:7])
    output_rows, output_colors, km_s = fill_range_gaps(
        output_rows,
        output_colors,
        range_key_cols,
        COL_KM_MIN,
        COL_KM_MAX,
        9_999_999,
    )
    if any(km_s.values()):
        print(" KM complétion :")
        if km_s["simple"]:
            print(f"      Sans sibling -> (0 ; 9 999 999)               : {km_s['simple']:,} ligne(s)")
        if km_s["gap_sources"]:
            print(
                f"      Gap-filling                                   : "
                f"{km_s['gap_sources']:,} source(s) -> {km_s['gap_rows']:,} ligne(s) gap"
            )

    # Post-process contract duration intervals with the same gap-filling strategy.
    output_rows, output_colors, dur_s = fill_range_gaps(
        output_rows,
        output_colors,
        range_key_cols,
        COL_DURATION_MIN,
        COL_DURATION_MAX,
        200,
    )
    if any(dur_s.values()):
        print(" Durée contrat complétion :")
        if dur_s["simple"]:
            print(f"      Sans sibling -> (0 ; 200)                     : {dur_s['simple']:,} ligne(s)")
        if dur_s["gap_sources"]:
            print(
                f"      Gap-filling                                   : "
                f"{dur_s['gap_sources']:,} source(s) -> {dur_s['gap_rows']:,} ligne(s) gap"
            )

    print(f" OK {len(output_rows):,} lignes en sortie (facteur {len(output_rows)/max(len(df_in),1):.2f})")
    if unresolved:
        print(f" !! {len(unresolved):,} lignes avec cellules encore vides")

    # Build final output DataFrame preserving input column order.
    output_path = Path(OUTPUT_DIR) / input_path.name
    print(f"\n Ecriture -> {output_path.name} ...")
    timer_file.start("ecriture")

    df_out = pd.DataFrame(output_rows, columns=df_in.columns)

    # Sanity check: input/output schema consistency before writing files.
    cols_in = list(df_in.columns)
    cols_out = list(df_out.columns)
    if cols_in == cols_out:
        print(f"  ✓ Colonnes OK : {len(cols_in)} colonnes, ordre identique")
    else:
        missing = [c for c in cols_in if c not in cols_out]
        extra = [c for c in cols_out if c not in cols_in]
        wrong_order = cols_in != cols_out and not missing and not extra
        if missing:
            print(f"  !! Colonnes manquantes dans l'output : {missing}")
        if extra:
            print(f"  !! Colonnes en trop dans l'output : {extra}")
        if wrong_order:
            print(f"  !! Ordre des colonnes différent")
            print(f"     Input : {cols_in}")
            print(f"     Output : {cols_out}")

    # Remove duplicates introduced by combinatorial expansion.
    before_dedup = len(df_out)
    df_out = df_out.drop_duplicates()
    n_dupes = before_dedup - len(df_out)
    if n_dupes:
        print(f"  !! {n_dupes:,} doublon(s) supprimé(s) ({before_dedup:,} -> {len(df_out):,} lignes)")
    else:
        print(f"  ✓ Aucun doublon")

    df_out.to_csv(str(output_path), sep=input_sep, index=False, encoding="utf-8-sig")

    # Report resolved expansion count and unresolved exclusion count.
    cnt_green = sum(1 for c in output_colors if c == "green")
    if cnt_green:
        print(f"  {cnt_green:,} ligne(s) expansées et résolues")
    if unresolved:
        print(f"  {len(unresolved):,} ligne(s) non résolues -> exclues de l'output principal")

    # Write recap pivot (source by empty cell) when recap data exists.
    if recap_long:
        recap_path = Path(RECAP_DIR) / f"{prefix}_RECAP.CSV"
        df_rl = pd.DataFrame(recap_long)
        df_recap = df_rl.pivot_table(
            index="EMPTY CELL",
            columns="cell",
            values="count",
            aggfunc="sum",
            fill_value="",
        )
        df_recap.columns.name = None
        df_recap.to_csv(str(recap_path), sep=";", encoding="utf-8-sig")
        print(
            f"   Recap : {len(df_recap)} source(s) x {len(df_recap.columns)} cellule(s) vide(s) "
            f"-> {recap_path.name}"
        )

    # Write unresolved rows for manual investigation.
    if unresolved:
        unres_path = Path(UNRESOLVED_DIR) / f"{prefix}_UNRESOLVED.CSV"
        df_unres = pd.DataFrame(unresolved, columns=df_in.columns)
        df_unres.to_csv(str(unres_path), sep=";", index=False, encoding="utf-8-sig")
        print(f"  Unresolved -> {unres_path.name}")

    timer_file.stop("ecriture")

    # Build per-file KPI summary used in per-file and global reporting.
    summary = {
        "lignes_entrée": len(df_in),
        "lignes_sortie": len(df_out),
        "facteur_expansion": f"{len(df_out)/max(len(df_in),1):.2f}x",
        "scenario_remplis": stats["scenario_filled"],
        "nv_uc_expansions": stats["nv_uc_expanded"],
        "brand_expansions": stats["brand_expanded"],
        "channel_expansions": stats["channel_expanded"],
        "LCDV_group_expansions": stats["lcdv_group_rows"],
        "Energy_type_expansions": stats["energy_type_rows"],
        "km_sans_sibling": km_s.get("simple", 0),
        "km_gap_lignes": km_s.get("gap_rows", 0),
        "duree_sans_sibling": dur_s.get("simple", 0),
        "duree_gap_lignes": dur_s.get("gap_rows", 0),
        "cellules_non_resolues": stats["unresolved_cells"],
    }

    print(f"\n +-- STATISTIQUES : {prefix} --+")
    for k, v in summary.items():
        print(f"  | {k:<30} {str(v):>10} |")
    print(f" +{'-'*44}+")

    timer_file.report(f"PERF {prefix[:30]}")
    global_stats[prefix] = summary

# ==============================================================================
# RAPPORT GLOBAL
# ==============================================================================
# Print one-line synthesis per file plus global loading/processing timings.
print(f"\n{'='*60}")
print(f" TRAITEMENT TERMINE : {len(input_files)}/{len(FILE_PREFIXES)} fichier(s)")
print(f"{'='*60}")
for prefix, s in global_stats.items():
    print(f" {prefix:<40} {s['lignes_entrée']:>8} -> {s['lignes_sortie']:>8} lignes ({s['facteur_expansion']})")
timer_global.report("PERF GLOBALE (chargement data)")

























