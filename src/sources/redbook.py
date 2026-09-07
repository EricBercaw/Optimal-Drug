from io import BytesIO

import pandas as pd


REDBOOK_SOURCE_NAME = (
    "RED BOOK (Not Linked - Test Upload)"
)


# ============================================================
# Mock RED BOOK template
# ============================================================

def create_redbook_test_template():
    """
    Create a synthetic RED BOOK-like Excel template.

    This contains fake/example data only and is intended
    solely for testing the application's future RED BOOK
    integration workflow.
    """

    template = pd.DataFrame(
        [
            {
                "NDC": "00000-0001-01",
                "TradeName": "TestDrug A",
                "GenericName": "testgeneric-a",
                "Manufacturer": "Test Pharma",
                "Strength": "100 MG",
                "PackageSize": "1 vial",
                "WACPackagePrice": 1000.00,
                "WACUnitPrice": 10.00,
                "WACEffectiveDate": "2026-09-01",
                "AWPPackagePrice": 1200.00,
                "AWPUnitPrice": 12.00,
                "AWPEffectiveDate": "2026-09-01",
            },
            {
                "NDC": "00000-0002-01",
                "TradeName": "TestDrug B",
                "GenericName": "testgeneric-b",
                "Manufacturer": "Example Therapeutics",
                "Strength": "50 MG",
                "PackageSize": "2 vials",
                "WACPackagePrice": 800.00,
                "WACUnitPrice": 8.00,
                "WACEffectiveDate": "2026-09-01",
                "AWPPackagePrice": 960.00,
                "AWPUnitPrice": 9.60,
                "AWPEffectiveDate": "2026-09-01",
            },
        ]
    )

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        template.to_excel(
            writer,
            index=False,
            sheet_name="RED BOOK Test Data",
        )

    output.seek(0)

    return output.getvalue()


# ============================================================
# RED BOOK-like uploaded file loader
# ============================================================

def load_redbook_test_file(
    file_bytes,
    filename,
):
    """
    Load a user-supplied synthetic RED BOOK-like file.

    Supported formats:
        XLSX
        XLS
        CSV

    The file must use the expected testing schema.
    """

    lower_name = filename.lower()

    if lower_name.endswith(
        (
            ".xlsx",
            ".xls",
        )
    ):

        df = pd.read_excel(
            BytesIO(file_bytes)
        )

    elif lower_name.endswith(".csv"):

        df = pd.read_csv(
            BytesIO(file_bytes)
        )

    else:

        raise ValueError(
            "Unsupported RED BOOK test file type. "
            "Please upload XLSX, XLS, or CSV."
        )

    return normalize_redbook_test_file(
        df
    )


# ============================================================
# Test-file normalization
# ============================================================

def normalize_redbook_test_file(df):
    """
    Normalize the synthetic RED BOOK-like test dataset.

    Original columns are retained.
    """

    result = df.copy()

    result.columns = [
        str(column).strip()
        for column in result.columns
    ]

    required_columns = [
        "NDC",
        "TradeName",
        "GenericName",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in result.columns
    ]

    if missing_columns:

        missing_text = ", ".join(
            missing_columns
        )

        raise ValueError(
            "The RED BOOK test file is missing "
            f"required columns: {missing_text}"
        )

    # --------------------------------------------------------
    # Clean identifying fields
    # --------------------------------------------------------

    for column in [
        "NDC",
        "TradeName",
        "GenericName",
        "Manufacturer",
        "Strength",
        "PackageSize",
    ]:

        if column in result.columns:

            result[column] = (
                result[column]
                .astype(str)
                .str.strip()
            )

    # --------------------------------------------------------
    # Pricing fields
    # --------------------------------------------------------

    for column in [
        "WACPackagePrice",
        "WACUnitPrice",
        "AWPPackagePrice",
        "AWPUnitPrice",
    ]:

        if column in result.columns:

            result[column] = (
                pd.to_numeric(
                    result[column],
                    errors="coerce",
                )
            )

    # --------------------------------------------------------
    # Date fields
    # --------------------------------------------------------

    for column in [
        "WACEffectiveDate",
        "AWPEffectiveDate",
    ]:

        if column in result.columns:

            result[column] = (
                pd.to_datetime(
                    result[column],
                    errors="coerce",
                )
            )

    # --------------------------------------------------------
    # Source metadata
    # --------------------------------------------------------

    result["Source"] = (
        REDBOOK_SOURCE_NAME
    )

    result["DataStatus"] = (
        "Synthetic/Test Upload - Not Linked"
    )

    return result