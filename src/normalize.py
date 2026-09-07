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

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(MCG|MG|G)",
        str(trade_name).upper()
    )

    if match:
        return float(match.group(1)), match.group(2)

    return None, None


def extract_package_quantity(package_description):
    """
    Extract the number of units in the VA package description.

    Examples
    --------
    "'1X0.25ML'" -> 1
    "'1X0.5ML'"  -> 1
    "'1X1ML'"    -> 1
    "2"          -> 2
    "10X1ML"     -> 10
    """

    if pd.isna(package_description):
        return None

    text = str(package_description).upper().strip()

    # Remove surrounding quotes/apostrophes sometimes present in VA data
    text = text.strip("'\"")

    # Examples: 1X0.25ML, 10X1ML
    match = re.match(r"(\d+)\s*X", text)

    if match:
        return float(match.group(1))

    # Examples: 1, 2, 10
    try:
        return float(text)
    except ValueError:
        return None


def normalize_va_catalog(df):
    """
    Convert raw VA catalog data into standardized pricing fields.
    """

    result = df.copy()

    strengths = result["TradeName"].apply(extract_strength)

    result["StrengthValue"] = strengths.apply(lambda x: x[0])
    result["StrengthUnit"] = strengths.apply(lambda x: x[1])

    result["PackageQuantity"] = (
        result["PackageDescription"]
        .apply(extract_package_quantity)
    )

    result["PricePerPackageUnit"] = (
        result["Price"] / result["PackageQuantity"]
    )

    result["Source"] = "VA"

    return result