from datetime import date
from pathlib import Path

from src.sources.va import load_va_prices
from src.normalize import normalize_va_catalog
from src.pricing import get_drug_options


def clean_input(value):
    value = value.strip()

    if value == "":
        return None

    return value


def clean_filename(value):
    """
    Make user-entered text safe for filenames.
    """
    if not value:
        return "All"

    return (
        value.strip()
        .replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
    )


def main():
    print("\nDrug Price Explorer")
    print("-------------------")

    # ---------------------------------------------------------
    # Source information
    # ---------------------------------------------------------

    access_type = "VA"
    resource_abbreviation = "VAPharm"

    # ---------------------------------------------------------
    # Load VA pricing data
    # ---------------------------------------------------------

    df = load_va_prices()
    df = normalize_va_catalog(df)

    # ---------------------------------------------------------
    # User filters
    # ---------------------------------------------------------

    trade_name = clean_input(
        input("Trade name [optional]: ")
    )

    generic_name = clean_input(
        input("Generic name [optional]: ")
    )

    ndc = clean_input(
        input("NDC [optional]: ")
    )

    price_type = clean_input(
        input("Price type (FSS/Big4) [optional]: ")
    )

    strength_unit = clean_input(
        input("Strength unit (MG/MCG/G) [optional]: ")
    )

    # ---------------------------------------------------------
    # Filter data
    # ---------------------------------------------------------

    results = get_drug_options(
        df,
        trade_name=trade_name,
        generic_name=generic_name,
        ndc=ndc,
        price_type=price_type,
        strength_unit=strength_unit,
    )

    if results.empty:
        print("\nNo matching products found.")
        return

    # ---------------------------------------------------------
    # Display results
    # ---------------------------------------------------------

    columns = [
        "TradeName",
        "Generic",
        "NDCWithDashes",
        "PackageDescription",
        "StrengthValue",
        "StrengthUnit",
        "PackageQuantity",
        "TotalStrengthPerPackage",
        "Price",
        "PricePerStrengthUnit",
        "PriceType",
        "VendorName",
        "Source",
    ]

    results = results[columns]

    print(f"\nFound {len(results)} matching rows:\n")

    print(
        results.to_string(index=False)
    )

    # ---------------------------------------------------------
    # Determine drug name for filename
    # ---------------------------------------------------------

    if trade_name:
        drug_name = trade_name

    elif generic_name:
        drug_name = generic_name

    elif ndc:
        drug_name = ndc

    else:
        drug_name = "All"

    drug_name = clean_filename(drug_name)

    # ---------------------------------------------------------
    # Create filename
    # ---------------------------------------------------------

    access_date = date.today().isoformat()

    filename = (
        f"{access_type}_"
        f"{resource_abbreviation}_"
        f"{drug_name}_"
        f"{access_date}.xlsx"
    )

    # ---------------------------------------------------------
    # Save to Desktop
    # ---------------------------------------------------------

    desktop = Path.home() / "Desktop"
    desktop.mkdir(exist_ok=True)

    output_path = desktop / filename

    results.to_excel(
        output_path,
        index=False,
    )

    print("\nFile saved:")
    print(output_path)


if __name__ == "__main__":
    main()