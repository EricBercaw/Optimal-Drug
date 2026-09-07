# ============================================================
# VA search
# ============================================================

def get_drug_options(
    df,
    trade_name=None,
    generic_name=None,
    ndc=None,
):
    """
    Filter VA pharmaceutical pricing data.

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
                regex=False,
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
                regex=False,
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

    return result.reset_index(
        drop=True
    )


# ============================================================
# Medicare search
# ============================================================

def get_medicare_options(
    df,
    drug_name=None,
    hcpcs=None,
    ndc=None,
):
    """
    Filter Medicare Part B pricing data.

    All filters are optional.
    """

    result = df.copy()

    # --------------------------------------------------------
    # Drug-name search
    # --------------------------------------------------------

    if drug_name:

        masks = []

        for column in [
            "MedicareDrugName",
            "MedicareDescription",
        ]:

            if column in result.columns:

                masks.append(
                    result[column]
                    .astype(str)
                    .str.contains(
                        drug_name,
                        case=False,
                        na=False,
                        regex=False,
                    )
                )

        if masks:

            combined_mask = masks[0]

            for mask in masks[1:]:

                combined_mask = (
                    combined_mask
                    | mask
                )

            result = result[
                combined_mask
            ]

        else:

            return result.iloc[
                0:0
            ].copy()

    # --------------------------------------------------------
    # HCPCS
    # --------------------------------------------------------

    if hcpcs:

        if "HCPCS" not in result.columns:

            return result.iloc[
                0:0
            ].copy()

        result = result[
            result["HCPCS"]
            .astype(str)
            .str.contains(
                hcpcs,
                case=False,
                na=False,
                regex=False,
            )
        ]

    # --------------------------------------------------------
    # NDC
    # --------------------------------------------------------

    if ndc:

        if "NDC" not in result.columns:

            return result.iloc[
                0:0
            ].copy()

        result = result[
            result["NDC"]
            .astype(str)
            .str.contains(
                ndc,
                case=False,
                na=False,
                regex=False,
            )
        ]

    return result.reset_index(
        drop=True
    )


# ============================================================
# RED BOOK test search
# ============================================================

def get_redbook_options(
    df,
    trade_name=None,
    generic_name=None,
    ndc=None,
):
    """
    Filter synthetic RED BOOK-like test data.

    This function does not connect to RED BOOK.

    All filters are optional.
    """

    result = df.copy()

    # --------------------------------------------------------
    # Trade name
    # --------------------------------------------------------

    if trade_name:

        if "TradeName" not in result.columns:

            return result.iloc[
                0:0
            ].copy()

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

    # --------------------------------------------------------
    # Generic name
    # --------------------------------------------------------

    if generic_name:

        if "GenericName" not in result.columns:

            return result.iloc[
                0:0
            ].copy()

        result = result[
            result["GenericName"]
            .astype(str)
            .str.contains(
                generic_name,
                case=False,
                na=False,
                regex=False,
            )
        ]

    # --------------------------------------------------------
    # NDC
    # --------------------------------------------------------

    if ndc:

        if "NDC" not in result.columns:

            return result.iloc[
                0:0
            ].copy()

        result = result[
            result["NDC"]
            .astype(str)
            .str.contains(
                ndc,
                case=False,
                na=False,
                regex=False,
            )
        ]

    return result.reset_index(
        drop=True
    )