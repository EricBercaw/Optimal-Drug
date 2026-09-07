def get_drug_options(
    df,
    drug,
    price_type=None,
    strength_unit=None,
):
    """
    Return normalized pricing options for a selected drug.

    Parameters
    ----------
    df : pandas.DataFrame
        Normalized drug pricing data.

    drug : str
        Generic or trade drug name.

    price_type : str, optional
        Example: "FSS" or "Big4".

    strength_unit : str, optional
        Example: "MG" or "MCG".

    Returns
    -------
    pandas.DataFrame
        Available drug pricing options.
    """

    result = df.copy()

    mask = (
        result["Generic"]
        .astype(str)
        .str.contains(
            drug,
            case=False,
            na=False,
        )
        |
        result["TradeName"]
        .astype(str)
        .str.contains(
            drug,
            case=False,
            na=False,
        )
    )

    result = result[mask]

    if price_type:
        result = result[
            result["PriceType"]
            .astype(str)
            .str.upper()
            .eq(price_type.upper())
        ]

    if strength_unit:
        result = result[
            result["StrengthUnit"]
            .astype(str)
            .str.upper()
            .eq(strength_unit.upper())
        ]

    columns = [
        "TradeName",
        "Generic",
        "NDCWithDashes",
        "PackageDescription",
        "StrengthValue",
        "StrengthUnit",
        "PackageQuantity",
        "Price",
        "PricePerPackageUnit",
        "PriceType",
        "VendorName",
        "Source",
    ]

    result = result[columns]

    result = result.sort_values(
        by=[
            "StrengthValue",
            "PricePerPackageUnit",
        ]
    )

    return result.reset_index(drop=True)