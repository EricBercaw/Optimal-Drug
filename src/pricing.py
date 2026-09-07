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


def get_medicare_options(
    df,
    drug_name=None,
    hcpcs=None,
    ndc=None,
):
    """
    Filter Medicare Part B ASP/payment-limit data.

    All filters are optional.
    """

    result = df.copy()

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

    if (
        hcpcs
        and "HCPCS" in result.columns
    ):

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

    if (
        ndc
        and "NDC" in result.columns
    ):

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