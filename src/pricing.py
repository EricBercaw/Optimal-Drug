def get_drug_options(
    df,
    trade_name=None,
    generic_name=None,
    ndc=None,
    price_type=None,
    strength_unit=None,
):
    """
    Return drug pricing options using optional filters.

    All filters are optional.
    """

    result = df.copy()

    if trade_name:
        result = result[
            result["TradeName"]
            .astype(str)
            .str.contains(
                trade_name,
                case=False,
                na=False,
            )
        ]

    if generic_name:
        result = result[
            result["Generic"]
            .astype(str)
            .str.contains(
                generic_name,
                case=False,
                na=False,
            )
        ]

    if ndc:
        result = result[
            result["NDCWithDashes"]
            .astype(str)
            .str.contains(
                ndc,
                case=False,
                na=False,
                regex=False,
            )
        ]

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

    return result.reset_index(drop=True)