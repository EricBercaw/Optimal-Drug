from io import BytesIO
from urllib.parse import urljoin
import re
import zipfile

import pandas as pd
import requests
from bs4 import BeautifulSoup


CMS_ASP_PAGE = (
    "https://www.cms.gov/medicare/payment/"
    "part-b-drugs/asp-pricing-files"
)

QUARTER_ORDER = {
    "JANUARY": 1,
    "APRIL": 2,
    "JULY": 3,
    "OCTOBER": 4,
}


# ============================================================
# CMS website discovery
# ============================================================

def discover_latest_cms_files():
    """
    Query the CMS ASP webpage and identify the newest
    quarterly Medicare Part B payment-limit file and its
    matching NDC-HCPCS crosswalk.

    Seasonal vaccine files are intentionally excluded.
    """

    response = requests.get(
        CMS_ASP_PAGE,
        timeout=30,
        headers={
            "User-Agent": (
                "DrugPriceExplorer/1.0 "
                "(personal research application)"
            )
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    payment_candidates = []
    crosswalk_candidates = []

    quarter_pattern = re.compile(
        r"(January|April|July|October)\s+(\d{4})",
        re.IGNORECASE,
    )

    for link in soup.find_all("a", href=True):

        label = " ".join(
            link.stripped_strings
        ).strip()

        if not label:
            continue

        lower_label = label.lower()

        # Seasonal vaccine files now have their own CMS process.
        if "seasonal" in lower_label:
            continue

        match = quarter_pattern.search(label)

        if not match:
            continue

        quarter = match.group(1).title()
        year = int(match.group(2))

        href = urljoin(
            CMS_ASP_PAGE,
            link["href"],
        )

        parent_text = (
            link.parent.get_text(
                " ",
                strip=True,
            )
            if link.parent
            else label
        )

        record = {
            "quarter": quarter,
            "year": year,
            "quarter_rank": QUARTER_ORDER[
                quarter.upper()
            ],
            "label": label,
            "status_text": parent_text,
            "url": href,
        }

        # NDC-HCPCS Crosswalk
        if (
            "crosswalk" in lower_label
            and "ndc" in lower_label
        ):
            crosswalk_candidates.append(
                record
            )
            continue

        # Main ASP / payment-limit file
        if (
            "payment limit" in lower_label
            or "asp pricing file" in lower_label
        ):
            # Do not accidentally use NOC files
            if "noc" not in lower_label:
                payment_candidates.append(
                    record
                )

    if not payment_candidates:
        raise RuntimeError(
            "Could not identify a Medicare Part B "
            "payment-limit file on the CMS website."
        )

    latest_payment = max(
        payment_candidates,
        key=lambda x: (
            x["year"],
            x["quarter_rank"],
        ),
    )

    matching_crosswalks = [
        item
        for item in crosswalk_candidates
        if (
            item["year"]
            == latest_payment["year"]
            and item["quarter"]
            == latest_payment["quarter"]
        )
    ]

    latest_crosswalk = (
        matching_crosswalks[0]
        if matching_crosswalks
        else None
    )

    return {
        "payment": latest_payment,
        "crosswalk": latest_crosswalk,
        "cms_page": CMS_ASP_PAGE,
    }


# ============================================================
# File downloading
# ============================================================

def download_cms_file(url):
    """
    Download a CMS file and return its raw bytes.
    """

    response = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": (
                "DrugPriceExplorer/1.0 "
                "(personal research application)"
            )
        },
    )

    response.raise_for_status()

    return response.content


# ============================================================
# Generic CMS file reader
# ============================================================

def _normalize_text(value):
    """
    Normalize text for column matching.
    """

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower(),
    )


def _detect_header_row(
    preview,
    required_terms,
):
    """
    Identify the most likely header row in a CMS worksheet.
    """

    best_row = None
    best_score = 0

    normalized_terms = [
        _normalize_text(term)
        for term in required_terms
    ]

    for row_number in range(
        len(preview)
    ):

        row_text = " ".join(
            str(value)
            for value in preview.iloc[
                row_number
            ].tolist()
            if pd.notna(value)
        )

        normalized_row = _normalize_text(
            row_text
        )

        score = sum(
            term in normalized_row
            for term in normalized_terms
        )

        if score > best_score:
            best_score = score
            best_row = row_number

    if best_score == 0:
        return 0

    return best_row


def _read_excel_bytes(
    file_bytes,
    required_terms,
):
    """
    Read an Excel CMS file while automatically detecting
    the worksheet and header row.
    """

    file_object = BytesIO(
        file_bytes
    )

    excel_file = pd.ExcelFile(
        file_object
    )

    best_sheet = None
    best_header = 0
    best_score = -1

    normalized_terms = [
        _normalize_text(term)
        for term in required_terms
    ]

    for sheet in excel_file.sheet_names:

        preview = pd.read_excel(
            excel_file,
            sheet_name=sheet,
            header=None,
            nrows=30,
        )

        header_row = _detect_header_row(
            preview,
            required_terms,
        )

        if header_row >= len(preview):
            continue

        row_text = " ".join(
            str(value)
            for value in preview.iloc[
                header_row
            ].tolist()
            if pd.notna(value)
        )

        normalized_row = _normalize_text(
            row_text
        )

        score = sum(
            term in normalized_row
            for term in normalized_terms
        )

        if score > best_score:
            best_score = score
            best_sheet = sheet
            best_header = header_row

    if best_sheet is None:
        best_sheet = excel_file.sheet_names[
            0
        ]

    file_object.seek(0)

    excel_file = pd.ExcelFile(
        file_object
    )

    df = pd.read_excel(
        excel_file,
        sheet_name=best_sheet,
        header=best_header,
    )

    return df


def _read_csv_bytes(
    file_bytes,
    required_terms,
):
    """
    Read a CSV while attempting to detect the header row.
    """

    preview = pd.read_csv(
        BytesIO(file_bytes),
        header=None,
        nrows=30,
    )

    header_row = _detect_header_row(
        preview,
        required_terms,
    )

    return pd.read_csv(
        BytesIO(file_bytes),
        header=header_row,
    )


def _read_zip_bytes(
    file_bytes,
    required_terms,
    file_kind,
):
    """
    Extract and read an Excel/CSV file contained in a CMS ZIP.
    """

    with zipfile.ZipFile(
        BytesIO(file_bytes)
    ) as archive:

        files = [
            name
            for name in archive.namelist()
            if (
                name.lower().endswith(
                    (
                        ".xlsx",
                        ".xls",
                        ".csv",
                    )
                )
                and not name.startswith(
                    "__MACOSX"
                )
                and not name.startswith(
                    "~$"
                )
            )
        ]

        if not files:
            raise ValueError(
                "No Excel or CSV file was found "
                "inside the CMS ZIP file."
            )

        def file_score(name):

            lower = name.lower()

            score = 0

            if file_kind == "payment":

                if "payment" in lower:
                    score += 10

                if "asp" in lower:
                    score += 5

                if "price" in lower:
                    score += 4

                if "crosswalk" in lower:
                    score -= 20

                if "noc" in lower:
                    score -= 20

            elif file_kind == "crosswalk":

                if "crosswalk" in lower:
                    score += 20

                if "ndc" in lower:
                    score += 10

            if lower.endswith(
                ".xlsx"
            ):
                score += 3

            return score

        selected_file = max(
            files,
            key=file_score,
        )

        extracted_bytes = archive.read(
            selected_file
        )

    return _read_tabular_bytes(
        extracted_bytes,
        selected_file,
        required_terms,
        file_kind,
    )


def _read_tabular_bytes(
    file_bytes,
    filename,
    required_terms,
    file_kind,
):
    """
    Read ZIP, XLSX, XLS, or CSV CMS data.
    """

    lower_name = filename.lower()

    if lower_name.endswith(".zip"):

        return _read_zip_bytes(
            file_bytes,
            required_terms,
            file_kind,
        )

    if lower_name.endswith(
        (
            ".xlsx",
            ".xls",
        )
    ):

        return _read_excel_bytes(
            file_bytes,
            required_terms,
        )

    if lower_name.endswith(".csv"):

        return _read_csv_bytes(
            file_bytes,
            required_terms,
        )

    raise ValueError(
        "Unsupported CMS file type. "
        "Use ZIP, XLSX, XLS, or CSV."
    )


# ============================================================
# Column detection
# ============================================================

def _find_column(
    df,
    possible_names,
):
    """
    Find a CMS column using flexible normalized matching.
    """

    normalized_columns = {
        _normalize_text(column): column
        for column in df.columns
    }

    # Exact normalized match first
    for name in possible_names:

        normalized_name = (
            _normalize_text(name)
        )

        if normalized_name in (
            normalized_columns
        ):
            return normalized_columns[
                normalized_name
            ]

    # Partial normalized match
    for name in possible_names:

        normalized_name = (
            _normalize_text(name)
        )

        for normalized_column, original in (
            normalized_columns.items()
        ):

            if (
                normalized_name
                in normalized_column
            ):
                return original

    return None


# ============================================================
# Payment-limit normalization
# ============================================================

def normalize_payment_file(
    df,
    quarter=None,
    status=None,
):
    """
    Preserve CMS source columns and add standardized
    helper columns for searching.
    """

    result = df.copy()

    # Remove fully empty columns
    result = result.dropna(
        axis=1,
        how="all",
    )

    hcpcs_col = _find_column(
        result,
        [
            "HCPCS Level II Code",
            "HCPCS Code",
            "HCPCS",
        ],
    )

    description_col = _find_column(
        result,
        [
            "Short Description",
            "Description",
        ],
    )

    dosage_col = _find_column(
        result,
        [
            "HCPCS Level II Code Dosage",
            "HCPCS Code Dosage",
            "HCPCS Dosage",
            "Dosage",
        ],
    )

    payment_col = _find_column(
        result,
        [
            "Payment Limit",
            "Payment Limit Amount",
        ],
    )

    if hcpcs_col:
        result["HCPCS"] = (
            result[hcpcs_col]
            .astype(str)
            .str.strip()
        )

    if description_col:
        result[
            "MedicareDescription"
        ] = (
            result[description_col]
            .astype(str)
            .str.strip()
        )

    if dosage_col:
        result[
            "HCPCSDosage"
        ] = result[dosage_col]

    if payment_col:
        result[
            "PaymentLimit"
        ] = pd.to_numeric(
            result[payment_col],
            errors="coerce",
        )

    result["CMSQuarter"] = (
        quarter or ""
    )

    result["CMSFileStatus"] = (
        status or ""
    )

    result["Source"] = (
        "Medicare Part B ASP"
    )

    return result


# ============================================================
# Crosswalk normalization
# ============================================================

def normalize_crosswalk_file(df):
    """
    Preserve CMS crosswalk columns and add standardized
    helper columns.
    """

    result = df.copy()

    result = result.dropna(
        axis=1,
        how="all",
    )

    hcpcs_col = _find_column(
        result,
        [
            "HCPCS Level II Code",
            "HCPCS Code",
            "HCPCS",
        ],
    )

    ndc_col = _find_column(
        result,
        [
            "NDC2",
            "NDC",
        ],
    )

    drug_col = _find_column(
        result,
        [
            "Drug Name",
        ],
    )

    labeler_col = _find_column(
        result,
        [
            "Labeler Name",
        ],
    )

    bill_units_pkg_col = _find_column(
        result,
        [
            "BILLUNITSPKG",
            "Bill Units Package",
        ],
    )

    if hcpcs_col:
        result["HCPCS"] = (
            result[hcpcs_col]
            .astype(str)
            .str.strip()
        )

    if ndc_col:
        result["NDC"] = (
            result[ndc_col]
            .astype(str)
            .str.strip()
        )

    if drug_col:
        result[
            "MedicareDrugName"
        ] = (
            result[drug_col]
            .astype(str)
            .str.strip()
        )

    if labeler_col:
        result[
            "MedicareLabeler"
        ] = (
            result[labeler_col]
            .astype(str)
            .str.strip()
        )

    if bill_units_pkg_col:
        result[
            "BillingUnitsPerPackage"
        ] = pd.to_numeric(
            result[
                bill_units_pkg_col
            ],
            errors="coerce",
        )

    return result


# ============================================================
# Build searchable Medicare dataset
# ============================================================

def build_medicare_dataset(
    payment_bytes,
    payment_filename,
    crosswalk_bytes=None,
    crosswalk_filename=None,
    quarter=None,
    status=None,
):
    """
    Build a searchable Medicare Part B dataset from a
    payment-limit file and optional NDC-HCPCS crosswalk.
    """

    payment_df = _read_tabular_bytes(
        payment_bytes,
        payment_filename,
        required_terms=[
            "HCPCS",
            "Payment Limit",
        ],
        file_kind="payment",
    )

    payment_df = normalize_payment_file(
        payment_df,
        quarter=quarter,
        status=status,
    )

    if (
        crosswalk_bytes is None
        or crosswalk_filename is None
    ):
        return payment_df

    crosswalk_df = _read_tabular_bytes(
        crosswalk_bytes,
        crosswalk_filename,
        required_terms=[
            "HCPCS",
            "NDC",
        ],
        file_kind="crosswalk",
    )

    crosswalk_df = (
        normalize_crosswalk_file(
            crosswalk_df
        )
    )

    if (
        "HCPCS" not in payment_df.columns
        or "HCPCS"
        not in crosswalk_df.columns
    ):
        return payment_df

    result = payment_df.merge(
        crosswalk_df,
        on="HCPCS",
        how="left",
        suffixes=(
            "",
            "_Crosswalk",
        ),
    )

    # Optional calculated package-level payment limit
    if (
        "PaymentLimit"
        in result.columns
        and "BillingUnitsPerPackage"
        in result.columns
    ):

        result[
            "CalculatedPackagePaymentLimit"
        ] = (
            result["PaymentLimit"]
            * result[
                "BillingUnitsPerPackage"
            ]
        )

    return result


# ============================================================
# Load current CMS files
# ============================================================

def load_detected_cms_dataset(
    discovery,
):
    """
    Download and load the CMS files found by
    discover_latest_cms_files().
    """

    payment = discovery[
        "payment"
    ]

    payment_bytes = download_cms_file(
        payment["url"]
    )

    crosswalk = discovery.get(
        "crosswalk"
    )

    crosswalk_bytes = None
    crosswalk_filename = None

    if crosswalk:

        crosswalk_bytes = (
            download_cms_file(
                crosswalk["url"]
            )
        )

        crosswalk_filename = (
            crosswalk["url"]
            .split("/")[-1]
        )

    quarter = (
        f"{payment['quarter']} "
        f"{payment['year']}"
    )

    return build_medicare_dataset(
        payment_bytes=payment_bytes,
        payment_filename=(
            payment["url"]
            .split("/")[-1]
        ),
        crosswalk_bytes=(
            crosswalk_bytes
        ),
        crosswalk_filename=(
            crosswalk_filename
        ),
        quarter=quarter,
        status=payment[
            "status_text"
        ],
    )