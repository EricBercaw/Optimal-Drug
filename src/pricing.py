def get_drug_options(
    df,
    trade_name=None,
    generic_name=None,
    ndc=None,
):
    """
    Filter pharmaceutical pricing data using optional user criteria.

    All filters are optional.

    Parameters
    ----------
    df : pandas.DataFrame
        Normalized pharmaceutical pricing data.

    trade_name : str, optional
        Partial match against TradeName.

    generic_name : str, optional
        Partial match against Generic.

    ndc : str, optional
        Partial match against NDCWithDashes.

    Returns
    -------
    pandas.DataFrame
        Filtered pricing data with all original and derived columns retained.
    """

    result = df.copy()

    # ---------------------------------------------------------
    # Trade name filter
    # ---------------------------------------------------------

    if trade_name:
        result = result[
            result["TradeName"]
            .astype(str)
            .str.contains(
                trade_name,
                case=False,
                na=False,
                regex=False,
            )
        ]

    # ---------------------------------------------------------
    # Generic name filter
    # ---------------------------------------------------------

    if generic_name:
        result = result[
            result["Generic"]
            .astype(str)
            .str.contains(
                generic_name,
                case=False,
                na=False,
                regex=False,
            )
        ]

    # ---------------------------------------------------------
    # NDC filter
    # ---------------------------------------------------------

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

    return result.reset_index(drop=True)