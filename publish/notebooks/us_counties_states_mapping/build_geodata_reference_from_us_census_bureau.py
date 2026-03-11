# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.20.4",
#     "pandas==3.0.1",
#     "requests==2.32.5",
# ]
# ///

# title: Linear Regression Tutorial
# draft: true

import marimo

__generated_with = "0.20.4"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # U.S. Geography Reference Builder (2020 Census + 2023 CT Planning Regions)

    *Dataset: U.S. Census ANSI/FIPS/NS Codes (2020 release) + Connecticut Planning Regions (2023+)*

    Builds a canonical U.S. geographic reference table combining **state and county reference files** from the Census Bureau and extends it with **Connecticut planning regions introduced in 2023**.

    **Source**
    U.S. Census Bureau – ANSI/FIPS/NS Codes
    https://www.census.gov/library/reference/code-lists/ansi.html

    Direct downloads used in this notebook:

    - States: https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt
    - Counties: https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt

    **Dataset**

    - Pipe-delimited national files (`|`) for states and counties
    - Includes all **50 states, DC, Puerto Rico, and Island Areas**
    - Adds **historical Connecticut counties** and **2023+ planning regions**
    - Relationships: one row per **county / county-equivalent entity**

    **Columns (standardized)**

    - `state_name`, `state_abbrev`, `state_fips_2d`
    - `county_name`, `county_fips_3d`, `county_ns_8d`
    - `class_fp`, `func_stat`
    - `full_fips_5d` (combined state+county FIPS)
    - `full_fips_numeric` (numeric version for calculations, BI use)

    **Common Uses**

    - Geographic joins across **county and state datasets**
    - BI-friendly tables for **Tableau, Excel, Power BI**
    - Historical vs. current **Connecticut regional analysis**
    - Reference for **spatial, demographic, and policy datasets**

    **Outputs**

    - `data/processed/census_county_equivalent_reference.txt` (raw Census-style, pipe-delimited)
    - `data/processed/census_county_equivalent_reference.csv` (raw Census-style, comma-delimited)
    - `data/processed/us_geography_reference.txt` (curated BI-friendly, pipe-delimited)
    - `data/processed/us_geography_reference.csv` (curated BI-friendly, comma-delimited)
    """)
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import requests
    from pathlib import Path

    return Path, mo, pd, requests


@app.cell
def _(Path):
    # ----------------------------------------------------------
    # 1. DIRECTORY CONFIGURATION
    # ----------------------------------------------------------
    BASE_DIR = Path("data")
    RAW_DIR = BASE_DIR / "raw"            # Original Census/raw files
    PROCESSED_DIR = BASE_DIR / "processed" # Processed output files

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return PROCESSED_DIR, RAW_DIR


@app.cell
def _(PROCESSED_DIR, RAW_DIR, pd, requests):
    # ----------------------------------------------------------
    # 2. SOURCE FILES (Census 2020)
    # ----------------------------------------------------------
    STATE_URL = "https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt"
    COUNTY_URL = "https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt"

    STATE_FILE = RAW_DIR / "national_state2020.txt"
    COUNTY_FILE = RAW_DIR / "national_county2020.txt"

    # ----------------------------------------------------------
    # 3. DOWNLOAD FUNCTION
    # ----------------------------------------------------------
    def download_file(url, path):
        """Download file if not already present."""
        if not path.exists():
            print(f"Downloading {path.name}")
            resp = requests.get(url)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        else:
            print(f"{path.name} already exists (skipping download)")

    download_file(STATE_URL, STATE_FILE)
    download_file(COUNTY_URL, COUNTY_FILE)

    # ----------------------------------------------------------
    # 4. LOAD STATE REFERENCE
    # ----------------------------------------------------------
    states = pd.read_csv(STATE_FILE, sep="|", dtype=str)
    states = states.rename(columns={
        "STATE": "state_abbrev",
        "STATEFP": "state_fips_2d",     # 2-digit FIPS
        "STATE_NAME": "state_name",
        "STATENS": "state_ns_8d"        # State NS code (8 digits)
    })
    states["state_fips_2d"] = states["state_fips_2d"].str.zfill(2)

    # Keep only relevant columns
    states = states[["state_fips_2d", "state_abbrev", "state_name", "state_ns_8d"]]

    # ----------------------------------------------------------
    # 5. LOAD COUNTY REFERENCE (Census 2020)
    # ----------------------------------------------------------
    counties = pd.read_csv(COUNTY_FILE, sep="|", dtype=str)
    counties = counties.rename(columns={
        "STATEFP": "state_fips_2d",
        "COUNTYFP": "county_fips_3d",  # 3-digit FIPS
        "COUNTYNS": "county_ns_8d",    # 8-digit National Standard
        "COUNTYNAME": "county_name",
        "CLASSFP": "class_fp",
        "FUNCSTAT": "func_stat"
    })

    # Ensure proper zero-padding
    counties["state_fips_2d"] = counties["state_fips_2d"].str.zfill(2)
    counties["county_fips_3d"] = counties["county_fips_3d"].str.zfill(3)
    counties["county_ns_8d"] = counties["county_ns_8d"].str.zfill(8)

    # Add state name and abbreviation
    counties = counties.merge(states, on="state_fips_2d", how="left")

    # ----------------------------------------------------------
    # 6. CONNECTICUT DATA (HISTORICAL + 2023+ PLANNING REGIONS)
    # ----------------------------------------------------------

    # Historical CT counties (pre-2023)
    ct_historical_counties = pd.DataFrame({
        "state_fips_2d": ["09"]*8,
        "county_fips_3d": ["001","003","005","007","009","011","013","015"],
        "county_ns_8d": ["212794","212338","212796","212797","212798","212799","212668","212801"],
        "county_name": [
            "Fairfield County","Hartford County","Litchfield County","Middlesex County",
            "New Haven County","New London County","Tolland County","Windham County"
        ],
        "class_fp": ["H4"]*8,
        "func_stat": ["N"]*8,
        "state_abbrev": ["CT"]*8
    })
    ct_historical_counties["county_ns_8d"] = ct_historical_counties["county_ns_8d"].str.zfill(8)
    ct_historical_counties = ct_historical_counties.merge(
        states[["state_fips_2d", "state_name"]],
        on="state_fips_2d",
        how="left"
    )

    # New CT planning regions (2023+)
    ct_planning_regions = pd.DataFrame({
        "state_fips_2d": ["09"]*9,
        "county_fips_3d": ["110","120","130","140","150","160","170","180","190"],
        "county_ns_8d": ["2830244","2830245","2830246","2830249","2830250",
                          "2830251","2830252","2830253","2830254"],
        "county_name": [
            "Capitol Planning Region","Greater Bridgeport Planning Region",
            "Lower Connecticut River Valley Planning Region","Naugatuck Valley Planning Region",
            "Northeastern Connecticut Planning Region","Northwest Hills Planning Region",
            "South Central Connecticut Planning Region","Southeastern Connecticut Planning Region",
            "Western Connecticut Planning Region"
        ],
        "class_fp": ["H1"]*9,
        "func_stat": ["S"]*9,
        "state_abbrev": ["CT"]*9
    })
    ct_planning_regions["county_ns_8d"] = ct_planning_regions["county_ns_8d"].str.zfill(8)
    ct_planning_regions = ct_planning_regions.merge(
        states[["state_fips_2d", "state_name"]],
        on="state_fips_2d",
        how="left"
    )

    # ----------------------------------------------------------
    # 7. BUILD CENSUS-STYLE STANDARD TABLE
    # ----------------------------------------------------------
    # Exclude official CT counties to avoid duplicates
    counties_no_ct = counties[counties["state_fips_2d"] != "09"]

    standard_table = pd.concat([counties_no_ct, ct_historical_counties, ct_planning_regions], ignore_index=True)

    # Create full FIPS (5-digit) for BI and reference
    standard_table["full_fips_5d"] = standard_table["state_fips_2d"].str.zfill(2) + standard_table["county_fips_3d"].str.zfill(3)

    # Save raw Census-style table for reference
    # --- 10a. Standard Census-style table (raw) ---

    # TXT version (pipe-delimited, preserves raw structure)
    standard_output_txt = PROCESSED_DIR / "census_county_equivalent_reference.txt"
    standard_table.to_csv(
        standard_output_txt,
        sep="|",
        index=False
    )
    print("Standard Census-style TXT table created:", standard_output_txt)

    # CSV version (comma-delimited, quotes FIPS columns to preserve leading zeros)
    standard_output_csv = PROCESSED_DIR / "census_county_equivalent_reference.csv"
    standard_table.to_csv(
        standard_output_csv,
        index=False
    )
    print("Standard Census-style CSV table created:", standard_output_csv)

    # ----------------------------------------------------------
    # 8. BUILD BI-FRIENDLY CURATED TABLE
    # ----------------------------------------------------------
    curated_table = standard_table.copy()

    # Explicitly label numeric version for calculations
    curated_table["full_fips_numeric"] = curated_table["full_fips_5d"].astype(int)

    # Reorder columns with explicit names
    curated_table = curated_table[
        ["state_name","state_abbrev","state_fips_2d",
         "county_name","county_fips_3d","county_ns_8d",
         "class_fp","func_stat",
         "full_fips_5d","full_fips_numeric"]
    ]

    # Save curated BI-friendly table (CSV ensures FIPS columns remain text)
    # CSV version (primary for Tableau/Excel/Power BI)
    curated_output_csv = PROCESSED_DIR / "us_geography_reference.csv"
    curated_table.to_csv(
        curated_output_csv,
        index=False
    )
    print("Curated BI-friendly CSV table created:", curated_output_csv)

    # Optional TXT version of curated table (pipe-delimited)
    curated_output_txt = PROCESSED_DIR / "us_geography_reference.txt"
    curated_table.to_csv(
        curated_output_txt,
        sep="|",
        index=False
    )
    print("Curated BI-friendly TXT table created:", curated_output_txt)
    return curated_table, standard_table


@app.cell
def _(standard_table):
    # ----------------------------------------------------------
    # 3. Display DataFrame (Standard Table)
    # ----------------------------------------------------------
    standard_table
    return


@app.cell
def _(curated_table):
    # ----------------------------------------------------------
    # 4. Display DataFrame (Curated Table)
    # ----------------------------------------------------------
    curated_table
    return


if __name__ == "__main__":
    app.run()

