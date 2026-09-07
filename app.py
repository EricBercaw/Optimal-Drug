from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

from src.sources.va import load_va_prices
from src.normalize import normalize_va_catalog
from src.sources.medicare import (
    discover_latest_cms_files,
    load_detected_cms_dataset,
    build_medicare_dataset,
)
from src.pricing import (
    get_drug_options,
    get_medicare_options,
)


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="Drug Price Explorer",
    page_icon="💊",
    layout="wide",
)


# ============================================================
# Helper functions
# ============================================================

@st.cache_data
def load_va_data():
    """
    Load and normalize VA pharmaceutical pricing data.
    """

    df = load_va_prices()

    return normalize_va_catalog(df)


def clean_filter(value):
    """
    Convert blank user input to None.
    """

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def clean_filename(value):
    """
    Convert text into a filename-safe value.
    """

    if not value:
        return "All"

    return (
        str(value)
        .strip()
        .replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
    )


def dataframe_to_excel(
    results_df,
    searches_df,
):
    """
    Create Excel workbook with:
        1. Drug Prices
        2. Searches
    """

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        results_df.to_excel(
            writer,
            index=False,
            sheet_name="Drug Prices",
        )

        searches_df.to_excel(
            writer,
            index=False,
            sheet_name="Searches",
        )

    output.seek(0)

    return output.getvalue()


def build_va_search_label(
    trade_name=None,
    generic_name=None,
    ndc=None,
):
    """
    Create readable VA search label.
    """

    parts = []

    if trade_name:
        parts.append(
            f"Trade: {trade_name}"
        )

    if generic_name:
        parts.append(
            f"Generic: {generic_name}"
        )

    if ndc:
        parts.append(
            f"NDC: {ndc}"
        )

    if not parts:
        return "All VA Products"

    return " | ".join(parts)


def build_medicare_search_label(
    drug_name=None,
    hcpcs=None,
    ndc=None,
):
    """
    Create readable Medicare search label.
    """

    parts = []

    if drug_name:
        parts.append(
            f"Drug: {drug_name}"
        )

    if hcpcs:
        parts.append(
            f"HCPCS: {hcpcs}"
        )

    if ndc:
        parts.append(
            f"NDC: {ndc}"
        )

    if not parts:
        return "All Medicare Products"

    return " | ".join(parts)


def build_filename(searches_df):
    """
    Build dynamic output filename based on
    source and number of searches.
    """

    access_date = (
        date.today().isoformat()
    )

    number_searches = len(
        searches_df
    )

    sources = (
        searches_df[
            "PricingSource"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    # --------------------------------------------------------
    # Single search
    # --------------------------------------------------------

    if number_searches == 1:

        row = searches_df.iloc[0]

        source = row[
            "PricingSource"
        ]

        identifier = (
            row.get(
                "DrugIdentifier",
                "",
            )
        )

        identifier = (
            clean_filename(
                identifier
            )
        )

        if (
            source
            == "VA Pharmaceutical Catalog"
        ):

            return (
                f"VA_"
                f"VAPharm_"
                f"{identifier}_"
                f"{access_date}.xlsx"
            )

        if (
            source
            == "Medicare Part B ASP"
        ):

            return (
                f"Medicare_"
                f"ASP_"
                f"{identifier}_"
                f"{access_date}.xlsx"
            )

    # --------------------------------------------------------
    # Multiple searches - same source
    # --------------------------------------------------------

    if len(sources) == 1:

        source = sources[0]

        if (
            source
            == "VA Pharmaceutical Catalog"
        ):

            return (
                f"VA_"
                f"VAPharm_"
                f"MultiDrug_"
                f"{number_searches}Searches_"
                f"{access_date}.xlsx"
            )

        if (
            source
            == "Medicare Part B ASP"
        ):

            return (
                f"Medicare_"
                f"ASP_"
                f"MultiDrug_"
                f"{number_searches}Searches_"
                f"{access_date}.xlsx"
            )

    # --------------------------------------------------------
    # Multiple sources
    # --------------------------------------------------------

    return (
        f"MultiSource_"
        f"MultiDrug_"
        f"{number_searches}Searches_"
        f"{access_date}.xlsx"
    )


# ============================================================
# Session state
# ============================================================

if (
    "combined_results"
    not in st.session_state
):
    st.session_state.combined_results = (
        pd.DataFrame()
    )


if (
    "search_history"
    not in st.session_state
):
    st.session_state.search_history = []


if (
    "medicare_dataset"
    not in st.session_state
):
    st.session_state.medicare_dataset = None


# ============================================================
# Query CMS when a new app session launches
# ============================================================

if (
    "cms_discovery"
    not in st.session_state
):

    try:

        st.session_state.cms_discovery = (
            discover_latest_cms_files()
        )

        st.session_state[
            "cms_discovery_error"
        ] = None

    except Exception as error:

        st.session_state.cms_discovery = (
            None
        )

        st.session_state[
            "cms_discovery_error"
        ] = str(error)


# ============================================================
# Header
# ============================================================

st.title(
    "💊 Drug Price Explorer"
)

st.write(
    "Search pharmaceutical pricing sources "
    "and build a combined drug pricing dataset."
)


# ============================================================
# Load VA data
# ============================================================

va_df = load_va_data()


# ============================================================
# Pricing source
# ============================================================

pricing_source = st.selectbox(
    "Pricing source",
    [
        "VA Pharmaceutical Catalog",
        "Medicare Part B ASP",
    ],
)


# ============================================================
# Default input variables
# ============================================================

trade_name = None
generic_name = None
drug_name = None
hcpcs = None
ndc = None

medicare_mode = None
cms_confirmed = False

payment_upload = None
crosswalk_upload = None


# ============================================================
# VA search interface
# ============================================================

if (
    pricing_source
    == "VA Pharmaceutical Catalog"
):

    st.subheader(
        "Search Criteria"
    )

    trade_name = st.text_input(
        "Trade name",
        placeholder="Example: Nplate",
    )

    generic_name = st.text_input(
        "Generic name",
        placeholder="Example: Romiplostim",
    )

    ndc = st.text_input(
        "NDC",
        placeholder="Example: 55513-0223",
    )


# ============================================================
# Medicare search interface
# ============================================================

elif (
    pricing_source
    == "Medicare Part B ASP"
):

    st.subheader(
        "Medicare ASP Data"
    )

    discovery = (
        st.session_state
        .cms_discovery
    )

    # --------------------------------------------------------
    # Show detected CMS file
    # --------------------------------------------------------

    if discovery:

        payment = discovery[
            "payment"
        ]

        crosswalk = (
            discovery.get(
                "crosswalk"
            )
        )

        detected_quarter = (
            f"{payment['quarter']} "
            f"{payment['year']}"
        )

        st.success(
            f"CMS detected: "
            f"**{detected_quarter}**"
        )

        st.write(
            f"Payment file: "
            f"**{payment['label']}**"
        )

        if (
            payment.get(
                "status_text"
            )
        ):

            st.caption(
                payment[
                    "status_text"
                ]
            )

        if crosswalk:

            st.write(
                "NDC-HCPCS crosswalk: "
                f"**{crosswalk['label']}**"
            )

        else:

            st.warning(
                "A matching NDC-HCPCS "
                "crosswalk was not detected."
            )

    else:

        st.error(
            "The app could not automatically "
            "identify the current CMS ASP file."
        )

        if (
            st.session_state
            .cms_discovery_error
        ):

            st.caption(
                st.session_state
                .cms_discovery_error
            )


    # --------------------------------------------------------
    # Choose automatic or manual source
    # --------------------------------------------------------

    medicare_mode = st.radio(
        "Medicare data source",
        [
            "Use CMS-detected latest file",
            "Upload local CMS file",
        ],
    )


    # --------------------------------------------------------
    # CMS detected file confirmation
    # --------------------------------------------------------

    if (
        medicare_mode
        == "Use CMS-detected latest file"
    ):

        cms_confirmed = st.checkbox(
            "I confirm this is the CMS file "
            "I want to use."
        )


    # --------------------------------------------------------
    # User-supplied CMS files
    # --------------------------------------------------------

    else:

        payment_upload = (
            st.file_uploader(
                "Medicare Part B Payment Limit file",
                type=[
                    "xlsx",
                    "xls",
                    "csv",
                    "zip",
                ],
            )
        )

        crosswalk_upload = (
            st.file_uploader(
                "NDC-HCPCS Crosswalk",
                type=[
                    "xlsx",
                    "xls",
                    "csv",
                    "zip",
                ],
            )
        )

        st.caption(
            "The NDC-HCPCS crosswalk is "
            "recommended for searching by "
            "drug name or NDC."
        )


    # --------------------------------------------------------
    # Medicare search criteria
    # --------------------------------------------------------

    st.subheader(
        "Search Criteria"
    )

    drug_name = st.text_input(
        "Drug name / description",
        placeholder="Example: Pembrolizumab",
    )

    hcpcs = st.text_input(
        "HCPCS",
        placeholder="Example: J9271",
    )

    ndc = st.text_input(
        "NDC",
        placeholder="Optional",
    )


# ============================================================
# Dataset buttons
# ============================================================

button_col1, button_col2 = (
    st.columns(
        [1, 1]
    )
)


with button_col1:

    add_clicked = st.button(
        "Add to Dataset",
        type="primary",
        use_container_width=True,
    )


with button_col2:

    clear_clicked = st.button(
        "Clear Dataset",
        use_container_width=True,
    )


# ============================================================
# Clear dataset
# ============================================================

if clear_clicked:

    st.session_state.combined_results = (
        pd.DataFrame()
    )

    st.session_state.search_history = []

    st.success(
        "Dataset cleared."
    )


# ============================================================
# Add search to dataset
# ============================================================

if add_clicked:

    results = pd.DataFrame()

    search_label = ""

    drug_identifier = "All"


    # ========================================================
    # VA
    # ========================================================

    if (
        pricing_source
        == "VA Pharmaceutical Catalog"
    ):

        trade_filter = clean_filter(
            trade_name
        )

        generic_filter = clean_filter(
            generic_name
        )

        ndc_filter = clean_filter(
            ndc
        )

        results = get_drug_options(
            va_df,
            trade_name=trade_filter,
            generic_name=generic_filter,
            ndc=ndc_filter,
        )

        search_label = (
            build_va_search_label(
                trade_name=trade_filter,
                generic_name=generic_filter,
                ndc=ndc_filter,
            )
        )

        if trade_filter:

            drug_identifier = (
                trade_filter
            )

        elif generic_filter:

            drug_identifier = (
                generic_filter
            )

        elif ndc_filter:

            drug_identifier = (
                ndc_filter
            )


    # ========================================================
    # Medicare
    # ========================================================

    elif (
        pricing_source
        == "Medicare Part B ASP"
    ):

        # ----------------------------------------------------
        # Use detected CMS files
        # ----------------------------------------------------

        if (
            medicare_mode
            == "Use CMS-detected latest file"
        ):

            if (
                st.session_state
                .cms_discovery
                is None
            ):

                st.error(
                    "No CMS ASP file was "
                    "automatically detected."
                )

                st.stop()


            if not cms_confirmed:

                st.warning(
                    "Please confirm the "
                    "detected CMS file before "
                    "adding results."
                )

                st.stop()


            if (
                st.session_state
                .medicare_dataset
                is None
            ):

                with st.spinner(
                    "Downloading and loading "
                    "CMS Medicare data..."
                ):

                    try:

                        st.session_state[
                            "medicare_dataset"
                        ] = (
                            load_detected_cms_dataset(
                                st.session_state[
                                    "cms_discovery"
                                ]
                            )
                        )

                    except Exception as error:

                        st.error(
                            "CMS files could not "
                            "be loaded."
                        )

                        st.exception(
                            error
                        )

                        st.stop()


            medicare_df = (
                st.session_state[
                    "medicare_dataset"
                ]
            )


        # ----------------------------------------------------
        # Use uploaded CMS files
        # ----------------------------------------------------

        else:

            if payment_upload is None:

                st.warning(
                    "Please upload a Medicare "
                    "Part B Payment Limit file."
                )

                st.stop()


            payment_bytes = (
                payment_upload
                .getvalue()
            )


            crosswalk_bytes = None
            crosswalk_filename = None


            if (
                crosswalk_upload
                is not None
            ):

                crosswalk_bytes = (
                    crosswalk_upload
                    .getvalue()
                )

                crosswalk_filename = (
                    crosswalk_upload.name
                )


            try:

                medicare_df = (
                    build_medicare_dataset(
                        payment_bytes=(
                            payment_bytes
                        ),
                        payment_filename=(
                            payment_upload.name
                        ),
                        crosswalk_bytes=(
                            crosswalk_bytes
                        ),
                        crosswalk_filename=(
                            crosswalk_filename
                        ),
                        quarter=(
                            "User supplied"
                        ),
                        status=(
                            "User supplied file"
                        ),
                    )
                )

            except Exception as error:

                st.error(
                    "The uploaded CMS file "
                    "could not be loaded."
                )

                st.exception(
                    error
                )

                st.stop()


        # ----------------------------------------------------
        # Search Medicare dataset
        # ----------------------------------------------------

        drug_filter = clean_filter(
            drug_name
        )

        hcpcs_filter = clean_filter(
            hcpcs
        )

        ndc_filter = clean_filter(
            ndc
        )


        results = get_medicare_options(
            medicare_df,
            drug_name=drug_filter,
            hcpcs=hcpcs_filter,
            ndc=ndc_filter,
        )


        search_label = (
            build_medicare_search_label(
                drug_name=drug_filter,
                hcpcs=hcpcs_filter,
                ndc=ndc_filter,
            )
        )


        if drug_filter:

            drug_identifier = (
                drug_filter
            )

        elif hcpcs_filter:

            drug_identifier = (
                hcpcs_filter
            )

        elif ndc_filter:

            drug_identifier = (
                ndc_filter
            )


    # ========================================================
    # No results
    # ========================================================

    if results.empty:

        st.warning(
            "No matching products found. "
            "Nothing was added to the dataset."
        )


    # ========================================================
    # Add results
    # ========================================================

    else:

        search_number = (
            len(
                st.session_state
                .search_history
            )
            + 1
        )


        search_record = {
            "SearchNumber":
                search_number,

            "PricingSource":
                pricing_source,

            "DrugIdentifier":
                drug_identifier,

            "SearchLabel":
                search_label,

            "RowsMatched":
                len(results),
        }


        # Medicare quarter metadata
        if (
            pricing_source
            == "Medicare Part B ASP"
        ):

            if (
                medicare_mode
                == "Use CMS-detected latest file"
                and st.session_state
                .cms_discovery
            ):

                payment = (
                    st.session_state
                    .cms_discovery[
                        "payment"
                    ]
                )

                search_record[
                    "FilePeriod"
                ] = (
                    f"{payment['quarter']} "
                    f"{payment['year']}"
                )

            else:

                search_record[
                    "FilePeriod"
                ] = "User supplied"

        else:

            search_record[
                "FilePeriod"
            ] = ""


        st.session_state.search_history.append(
            search_record
        )


        # ----------------------------------------------------
        # Add source results to combined dataset
        # ----------------------------------------------------

        if (
            st.session_state
            .combined_results
            .empty
        ):

            st.session_state[
                "combined_results"
            ] = results.copy()

        else:

            st.session_state[
                "combined_results"
            ] = pd.concat(
                [
                    st.session_state[
                        "combined_results"
                    ],
                    results,
                ],
                ignore_index=True,
                sort=False,
            )


        # ----------------------------------------------------
        # Remove exact duplicate records
        # ----------------------------------------------------

        st.session_state[
            "combined_results"
        ] = (
            st.session_state[
                "combined_results"
            ]
            .drop_duplicates()
            .reset_index(
                drop=True
            )
        )


        st.success(
            f"Added {len(results):,} "
            f"matching rows for "
            f"{search_label}."
        )


# ============================================================
# Search history
# ============================================================

if (
    st.session_state
    .search_history
):

    st.divider()

    st.subheader(
        "Added Searches"
    )

    searches_df = pd.DataFrame(
        st.session_state
        .search_history
    )

    st.dataframe(
        searches_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Combined results
# ============================================================

if (
    not st.session_state
    .combined_results
    .empty
):

    st.divider()

    results = (
        st.session_state
        .combined_results
        .copy()
    )


    # --------------------------------------------------------
    # Sort results when possible
    # --------------------------------------------------------

    sort_columns = []

    for column in [
        "Source",
        "TradeName",
        "MedicareDrugName",
        "Generic",
        "HCPCS",
        "NDCWithDashes",
        "NDC",
        "PriceType",
    ]:

        if column in results.columns:

            sort_columns.append(
                column
            )


    if sort_columns:

        results = results.sort_values(
            by=sort_columns,
            na_position="last",
        )


    # --------------------------------------------------------
    # Results heading
    # --------------------------------------------------------

    st.subheader(
        "Combined Dataset"
    )

    st.write(
        f"**{len(results):,} unique pricing records** "
        f"from "
        f"**{len(st.session_state.search_history):,} searches**"
    )


    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price":
                st.column_config.NumberColumn(
                    "Price",
                    format="$%.2f",
                ),

            "PricePerPackageUnit":
                st.column_config.NumberColumn(
                    "Price Per Package Unit",
                    format="$%.4f",
                ),

            "PricePerStrengthUnit":
                st.column_config.NumberColumn(
                    "Price Per Strength Unit",
                    format="$%.4f",
                ),

            "PaymentLimit":
                st.column_config.NumberColumn(
                    "Medicare Payment Limit",
                    format="$%.4f",
                ),

            "CalculatedPackagePaymentLimit":
                st.column_config.NumberColumn(
                    "Calculated Package Payment Limit",
                    format="$%.4f",
                ),
        },
    )


    # --------------------------------------------------------
    # Excel export
    # --------------------------------------------------------

    searches_df = pd.DataFrame(
        st.session_state
        .search_history
    )


    filename = build_filename(
        searches_df
    )


    excel_data = dataframe_to_excel(
        results,
        searches_df,
    )


    st.download_button(
        label="Download Combined Excel File",
        data=excel_data,
        file_name=filename,
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        type="primary",
    )