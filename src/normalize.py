import re

import pandas as pd


def extract_strength(trade_name):
    """
    Extract the first strength value and unit from TradeName.

    Examples
    --------
    "NPLATE 250MCG SDV INJ" -> (250, "MCG")
    "KEYTRUDA 100MG INJ" -> (100, "MG")
    "KEYTRUDA QLEX 395MG" -> (395, "MG")
    """

    if pd.isna(trade_name):
        return None, None

    text = str(trade_name).upper().strip()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(MCG|MG|G)",
        text,
    )

    if match:
        return float(match.group(1)), match.group(2)

    return None, None


def extract_package_quantity(package_description):
    """
    Extract the number of package units.

    Examples
    --------
    "'1X0.25ML'" -> 1
    "1X0.5ML" -> 1
    "10X1ML" -> 10
    "1ML" -> 1
    "2ML" -> 1
    "1" -> 1
    "2" -> 2
    """

    if pd.isna(package_description):
        return None

    text = str(package_description).upper().strip()

    # VA data sometimes contains literal quotes
    text = text.strip("'\"")

    # Examples:
    # 1X0.25ML
    # 2X4ML
    # 10X1ML
    match = re.match(
        r"(\d+)\s*X",
        text,
    )

    if match:
        return float(match.group(1))

    # A single container described by its volume
    # Examples:
    # 1ML
    # 2ML
    # 0.5ML
    if re.fullmatch(
        r"\d+(?:\.\d+)?\s*ML",
        text,
    ):
        return 1.0

    # Plain package counts
    # Examples:
    # 1
    # 2
    # 30
    try:
        return float(text)

    except ValueError:
        return None


def normalize_va_catalog(df):
    """
    Convert raw VA pharmaceutical pricing data into standardized
    fields useful for unit-cost calculations.
    """

    result = df.copy()

    # ---------------------------------------------------------
    # Extract strength
    # ---------------------------------------------------------

    strengths = result["TradeName"].apply(
        extract_strength
    )

    result["StrengthValue"] = strengths.apply(
        lambda x: x[0]
    )

    result["StrengthUnit"] = strengths.apply(
        lambda x: x[1]
    )

    # ---------------------------------------------------------
    # Extract package quantity
    # ---------------------------------------------------------

    result["PackageQuantity"] = (
        result["PackageDescription"]
        .apply(extract_package_quantity)
    )

    # ---------------------------------------------------------
    # Price per package unit
    # ---------------------------------------------------------

    result["PricePerPackageUnit"] = (
        result["Price"]
        / result["PackageQuantity"]
    )

    # ---------------------------------------------------------
    # Total strength contained in package
    #
    # Example:
    # 100 MG × package quantity 2 = 200 MG
    # ---------------------------------------------------------

    result["TotalStrengthPerPackage"] = (
        result["StrengthValue"]
        * result["PackageQuantity"]
    )

    # ---------------------------------------------------------
    # Price per strength unit
    #
    # Examples:
    # $1,216.29 / 125 MCG = $9.73 per MCG
    #
    # $8,479.22 / 200 MG = $42.40 per MG
    # ---------------------------------------------------------

    result["PricePerStrengthUnit"] = (
        result["Price"]
        / result["TotalStrengthPerPackage"]
    )

    # ---------------------------------------------------------
    # Source
    # ---------------------------------------------------------

    result["Source"] = "VA"

    return result