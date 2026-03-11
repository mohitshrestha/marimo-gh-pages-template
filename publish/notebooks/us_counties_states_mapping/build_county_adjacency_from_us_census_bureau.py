# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.20.4",
#     "pandas==3.0.1",
#     "requests==2.32.5",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 2025 Census County Adjacency Builder

    *Dataset: U.S. Census County Adjacency File (2025 release)*

    Download and prepare the **U.S. Census 2025 County Adjacency File**, which lists each county (or county equivalent) and its neighboring counties.

    **Source**
    U.S. Census Bureau – County Adjacency File
    https://www.census.gov/geographies/reference-files/time-series/geo/county-adjacency.html

    **Dataset**

    - Pipe-delimited national file (`|`)
    - Includes counties from all **50 states, DC, Puerto Rico, and Island Areas**
    - Each row represents one **county → neighboring county relationship**
    - Relationships appear **in both directions** (A → B and B → A)

    **Columns**

    - `County Name`
    - `County GEOID` (state FIPS + county FIPS)
    - `Neighbor Name`
    - `Neighbor GEOID`
    - `Length` (shared boundary length in meters, introduced in 2025)

    **Common Uses**

    - Building **county adjacency graphs**
    - Regional clustering or spatial modeling
    - Identifying **neighboring counties for spillover analysis**
    - Geographic joins across **county-level datasets**

    **Outputs**

    - `data/processed/county_adjacency2025.txt`
    - `data/processed/county_adjacency2025.csv`
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
    # 2. SOURCE FILES (US Census 2025 County Adjacency File)
    # ----------------------------------------------------------
    COUNTY_ADJACENCY_URL = "https://www2.census.gov/geo/docs/reference/county_adjacency/county_adjacency2025.txt"

    COUNTY_ADJACENCY_FILE = RAW_DIR / "county_adjacency2025.txt"

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

    download_file(COUNTY_ADJACENCY_URL, COUNTY_ADJACENCY_FILE)

    # ---------------------------------------------------------------
    # 3. Load Data
    # ---------------------------------------------------------------
    # County adjacency data is pipe-delimited
    df_county_adjacency = pd.read_csv(COUNTY_ADJACENCY_FILE, sep="|", dtype=str)

    # ---------------------------------------------------------------
    # 4. Export
    # ---------------------------------------------------------------
    print(f"\nSummary:")
    print(f"Rows: {len(df_county_adjacency):,}")
    # TXT version (pipe-delimited, preserves raw structure)
    df_county_adjacency_txt = PROCESSED_DIR / "county_adjacency2025.txt"
    df_county_adjacency.to_csv(
        df_county_adjacency_txt,
        sep="|",
        index=False
    )
    print("\nCounty adjacency in TXT format export complete:", df_county_adjacency_txt)

    # CSV version (comma-delimited, quotes FIPS columns to preserve leading zeros)
    df_county_adjacency_csv = PROCESSED_DIR / "county_adjacency2025.csv"
    df_county_adjacency.to_csv(
        df_county_adjacency_csv,
        index=False
    )
    print("\nCounty adjacency in CSV format export complete:", df_county_adjacency_csv)

    # ---------------------------------------------------------------
    # 5. Display DataFrame
    # ---------------------------------------------------------------
    df_county_adjacency
    return


if __name__ == "__main__":
    app.run()
