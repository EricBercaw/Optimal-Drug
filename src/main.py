from src.sources.va import load_va_prices
from src.normalize import normalize_va_catalog
from src.optimizer import get_drug_options


def main():
    print("Drug Price Optimizer is running")

    # Load raw VA pharmaceutical catalog
    df = load_va_prices()

    # Normalize VA data into fields usable by the optimizer
    df = normalize_va_catalog(df)

    # Example drug search
    options = get_drug_options(
        df,
        drug="Nplate",
        price_type="FSS",
    )

    print("\nAvailable drug options:\n")

    print(
        options[
            [
                "TradeName",
                "NDCWithDashes",
                "StrengthValue",
                "StrengthUnit",
                "PackageQuantity",
                "Price",
                "PricePerPackageUnit",
                "PriceType",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()