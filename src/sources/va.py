from pathlib import Path

import pandas as pd
import requests


VA_URL = (
    "YOUR_EXISTING_VA_URL_HERE"
)

DATA_DIR = Path("data/raw/va")
OUTPUT_FILE = DATA_DIR / "va_pharmaceutical_prices.xlsx"


def download_va_prices():
    """Download the VA pharmaceutical pricing workbook."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading VA pharmaceutical pricing data...")

    response = requests.get(VA_URL, timeout=60)
    response.raise_for_status()

    OUTPUT_FILE.write_bytes(response.content)

    print(f"Saved to: {OUTPUT_FILE}")

    return OUTPUT_FILE


def load_va_prices():
    """Load VA pharmaceutical prices into a pandas DataFrame."""

    if not OUTPUT_FILE.exists():
        download_va_prices()

    return pd.read_excel(OUTPUT_FILE)


def search_va_catalog(
    df,
    drug=None,
    price_type=None,
    vendor=None,
):
    """
    Search and filter the VA pharmaceutical catalog.

    Parameters
    ----------
    df : pandas.DataFrame
        VA pricing catalog.

    drug : str, optional
        Drug name or search term.

    price_type : str, optional
        Example: NC, FSS.

    vendor : str, optional
        Vendor/manufacturer search term.

    Returns
    -------
    pandas.DataFrame
        Filtered VA catalog.
    """

    result = df.copy()

    # ---------------------------------------------------------
    # Drug search
    # ---------------------------------------------------------

    if drug:

        possible_drug_columns = [
            "GenericName",
            "TradeName",
            "DrugName",
            "Description",
        ]

        drug_columns = [
            col
            for col in possible_drug_columns
            if col in result.columns
        ]

        if not drug_columns:
            raise ValueError(
                "Could not identify a drug-name column."
            )

        mask = False

        for col in drug_columns:
            mask = (
                mask
                | result[col]
                .astype(str)
                .str.contains(
                    drug,
                    case=False,
                    na=False,
                )
            )

        result = result[mask]

    # ---------------------------------------------------------
    # Price type
    # ---------------------------------------------------------

    if price_type and "PriceType" in result.columns:

        result = result[
            result["PriceType"]
            .astype(str)
            .str.upper()
            == price_type.upper()
        ]

    # ---------------------------------------------------------
    # Vendor
    # ---------------------------------------------------------

    if vendor and "VendorName" in result.columns:

        result = result[
            result["VendorName"]
            .astype(str)
            .str.contains(
                vendor,
                case=False,
                na=False,
            )
        ]

    return result.reset_index(drop=True)


if __name__ == "__main__":

    df = load_va_prices()

    print("VA catalog loaded.")
    print(f"Rows: {len(df):,}")

    print("\nColumns:")
    print(df.columns.tolist())

    # Example search
    results = search_va_catalog(
        df,
        drug="Nplate",
    )

    print("\nSearch Results:")
    print(results.to_string(index=False))