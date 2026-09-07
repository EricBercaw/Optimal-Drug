from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

from src.sources.va import (
    load_va_prices,
)

from src.sources.medicare import (
    discover_latest_cms_files,
    load_detected_cms_dataset,
    build_medicare_dataset,
)

from src.sources.redbook import (
    REDBOOK_SOURCE_NAME,
    create_redbook_test_template,
    load_redbook_test_file,
)

from src.normalize import (
    normalize_va_catalog,
)

from src.pricing import (
    get_drug_options,
    get_medicare_options,
    get_redbook_options,
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
# Source names
# ============================================================

VA_SOURCE = (
    "VA Pharmaceutical Catalog"
)

MEDICARE_SOURCE = (
    "Medicare Part B ASP"
)


# ============================================================
# Helpers
# ============================================================

@st.cache_data
def load_va_data():

    df = load_va_prices()

    return normalize_va_catalog(
        df
    )


def clean_filter(value):

    if value is None:
        return None

    value = str(
        value
    ).strip()

    if value == "":
        return None

    return value


def clean_filename(value):

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


def build_search_label(
    trade_name=None,
    generic_name=None,
    drug_name=None,
    hcpcs=None,
    ndc=None,
):

    parts = []

    if trade_name:

        parts.append(
            f"Trade: {trade_name}"
        )

    if generic_name:

        parts.append(
            f"Generic: {generic_name}"
        )

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
        return "All Products"

    return " | ".join(
        parts
    )


def build_filename(
    searches_df,
):

    today = (
        date.today()
        .isoformat()
    )

    count = len(
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
    # One search
    # --------------------------------------------------------

    if count == 1:

        row = searches_df.iloc[
            0
        ]

        source = row[
            "PricingSource"
        ]

        identifier = (
            clean_filename(
                row[
                    "DrugIdentifier"
                ]
            )
        )

        if source == VA_SOURCE:

            return (
                f"VA_VAPharm_"
                f"{identifier}_"
                f"{today}.xlsx"
            )

        if source == MEDICARE_SOURCE:

            return (
                f"Medicare_ASP_"
                f"{identifier}_"
                f"{today}.xlsx"
            )

        if source == REDBOOK_SOURCE_NAME:

            return (
                f"RedBook_Test_"
                f"{identifier}_"
                f"{today}.xlsx"
            )

    # --------------------------------------------------------
    # Multiple searches from same source
    # --------------------------------------------------------

    if len(sources) == 1:

        source = sources[
            0
        ]

        if source == VA_SOURCE:

            prefix = (
                "VA_VAPharm"
            )

        elif source == MEDICARE_SOURCE:

            prefix = (
                "Medicare_ASP"
            )

        elif source == REDBOOK_SOURCE_NAME:

            prefix = (
                "RedBook_Test"
            )

        else:

            prefix = (
                "DrugPrices"
            )

        return (
            f"{prefix}_"
            f"MultiDrug_"
            f"{count}Searches_"
            f"{today}.xlsx"
        )

    # --------------------------------------------------------
    # Multiple sources
    # --------------------------------------------------------

    return (
        f"MultiSource_"
        f"MultiDrug_"
        f"{count}Searches_"
        f"{today}.xlsx"
    )


# ============================================================
# Session state
# ============================================================

if (
    "combined_results"
    not in st.session_state
):

    st.session_state[
        "combined_results"
    ] = pd.DataFrame()


if (
    "search_history"
    not in st.session_state
):

    st.session_state[
        "search_history"
    ] = []


if (
    "medicare_dataset"
    not in st.session_state
):

    st.session_state[
        "medicare_dataset"
    ] = None


# ============================================================
# Query CMS once per Streamlit session
# ============================================================

if (
    "cms_discovery"
    not in st.session_state
):

    try:

        st.session_state[
            "cms_discovery"
        ] = (
            discover_latest_cms_files()
        )

        st.session_state[
            "cms_discovery_error"
        ] = None

    except Exception as error:

        st.session_state[
            "cms_discovery"
        ] = None

        st.session_state[
            "cms_discovery_error"
        ] = str(
            error
        )


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
# Load VA
# ============================================================

va_df = load_va_data()


# ============================================================
# Pricing source selector
# ============================================================

pricing_source = st.selectbox(
    "Pricing source",
    [
        VA_SOURCE,
        MEDICARE_SOURCE,
        REDBOOK_SOURCE_NAME,
    ],
)


# ============================================================
# Default variables
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

redbook_upload = None
redbook_df = None


# ============================================================
# VA interface
# ============================================================

if pricing_source == VA_SOURCE:

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
# Medicare interface
# ============================================================

elif pricing_source == MEDICARE_SOURCE:

    st.subheader(
        "Medicare ASP Data"
    )

    discovery = (
        st.session_state[
            "cms_discovery"
        ]
    )

    if discovery:

        payment = discovery[
            "payment"
        ]

        crosswalk = (
            discovery.get(
                "crosswalk"
            )
        )

        quarter = (
            f"{payment['quarter']} "
            f"{payment['year']}"
        )

        st.success(
            f"CMS detected: "
            f"**{quarter}**"
        )

        st.write(
            "Payment file: "
            f"**{payment['label']}**"
        )

        if crosswalk:

            st.write(
                "NDC-HCPCS crosswalk: "
                f"**{crosswalk['label']}**"
            )

        else:

            st.warning(
                "Matching NDC-HCPCS "
                "crosswalk not detected."
            )

    else:

        st.error(
            "CMS file discovery failed."
        )

        if (
            st.session_state[
                "cms_discovery_error"
            ]
        ):

            st.caption(
                st.session_state[
                    "cms_discovery_error"
                ]
            )


    medicare_mode = st.radio(
        "Medicare data source",
        [
            "Use CMS-detected latest file",
            "Upload local CMS file",
        ],
    )


    if (
        medicare_mode
        == "Use CMS-detected latest file"
    ):

        cms_confirmed = (
            st.checkbox(
                "I confirm this is the CMS "
                "file I want to use."
            )
        )

    else:

        payment_upload = (
            st.file_uploader(
                "Medicare Part B "
                "Payment Limit file",
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


    st.subheader(
        "Search Criteria"
    )

    drug_name = st.text_input(
        "Drug name / description",
        placeholder=(
            "Example: Pembrolizumab"
        ),
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
# RED BOOK test interface
# ============================================================

elif (
    pricing_source
    == REDBOOK_SOURCE_NAME
):

    st.subheader(
        "RED BOOK Test Integration"
    )

    st.warning(
        "This source is NOT connected to "
        "Merative RED BOOK. It is intended "
        "only for testing the future RED BOOK "
        "workflow using synthetic or "
        "user-created data."
    )


    # --------------------------------------------------------
    # Download synthetic template
    # --------------------------------------------------------

    redbook_template = (
        create_redbook_test_template()
    )

    st.download_button(
        label=(
            "Download RED BOOK Test Template"
        ),
        data=redbook_template,
        file_name=(
            "RedBook_Test_Template.xlsx"
        ),
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


    # --------------------------------------------------------
    # Upload test file
    # --------------------------------------------------------

    redbook_upload = (
        st.file_uploader(
            "Upload RED BOOK test file",
            type=[
                "xlsx",
                "xls",
                "csv",
            ],
        )
    )


    if redbook_upload is not None:

        try:

            redbook_df = (
                load_redbook_test_file(
                    redbook_upload.getvalue(),
                    redbook_upload.name,
                )
            )

            st.success(
                f"Loaded "
                f"{len(redbook_df):,} "
                f"test pricing records."
            )

        except Exception as error:

            st.error(
                "RED BOOK test file "
                "could not be loaded."
            )

            st.exception(
                error
            )


    st.subheader(
        "Search Criteria"
    )

    trade_name = st.text_input(
        "Trade name",
        placeholder="Example: TestDrug A",
    )

    generic_name = st.text_input(
        "Generic name",
        placeholder="Example: testgeneric-a",
    )

    ndc = st.text_input(
        "NDC",
        placeholder="Example: 00000-0001-01",
    )


# ============================================================
# Buttons
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

    st.session_state[
        "combined_results"
    ] = pd.DataFrame()

    st.session_state[
        "search_history"
    ] = []

    st.success(
        "Dataset cleared."
    )


# ============================================================
# Add search
# ============================================================

if add_clicked:

    results = pd.DataFrame()

    search_label = ""

    drug_identifier = "All"

    file_period = ""


    # ========================================================
    # VA
    # ========================================================

    if pricing_source == VA_SOURCE:

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
            build_search_label(
                trade_name=trade_filter,
                generic_name=generic_filter,
                ndc=ndc_filter,
            )
        )

        drug_identifier = (
            trade_filter
            or generic_filter
            or ndc_filter
            or "All"
        )


    # ========================================================
    # Medicare
    # ========================================================

    elif pricing_source == MEDICARE_SOURCE:

        if (
            medicare_mode
            == "Use CMS-detected latest file"
        ):

            if (
                st.session_state[
                    "cms_discovery"
                ]
                is None
            ):

                st.error(
                    "No CMS file was detected."
                )

                st.stop()


            if not cms_confirmed:

                st.warning(
                    "Please confirm the "
                    "detected CMS file."
                )

                st.stop()


            if (
                st.session_state[
                    "medicare_dataset"
                ]
                is None
            ):

                with st.spinner(
                    "Downloading CMS "
                    "Medicare data..."
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
                            "CMS data could not "
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


            payment = (
                st.session_state[
                    "cms_discovery"
                ][
                    "payment"
                ]
            )

            file_period = (
                f"{payment['quarter']} "
                f"{payment['year']}"
            )


        else:

            if payment_upload is None:

                st.warning(
                    "Please upload a "
                    "Payment Limit file."
                )

                st.stop()


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
                            payment_upload
                            .getvalue()
                        ),
                        payment_filename=(
                            payment_upload
                            .name
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
                    "CMS file could not "
                    "be loaded."
                )

                st.exception(
                    error
                )

                st.stop()


            file_period = (
                "User supplied"
            )


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
            build_search_label(
                drug_name=drug_filter,
                hcpcs=hcpcs_filter,
                ndc=ndc_filter,
            )
        )


        drug_identifier = (
            drug_filter
            or hcpcs_filter
            or ndc_filter
            or "All"
        )


    # ========================================================
    # RED BOOK test
    # ========================================================

    elif (
        pricing_source
        == REDBOOK_SOURCE_NAME
    ):

        if redbook_upload is None:

            st.warning(
                "Please upload a RED BOOK "
                "test file first."
            )

            st.stop()


        if redbook_df is None:

            st.warning(
                "The RED BOOK test file "
                "could not be loaded."
            )

            st.stop()


        trade_filter = clean_filter(
            trade_name
        )

        generic_filter = clean_filter(
            generic_name
        )

        ndc_filter = clean_filter(
            ndc
        )


        results = get_redbook_options(
            redbook_df,
            trade_name=trade_filter,
            generic_name=generic_filter,
            ndc=ndc_filter,
        )


        search_label = (
            build_search_label(
                trade_name=trade_filter,
                generic_name=generic_filter,
                ndc=ndc_filter,
            )
        )


        drug_identifier = (
            trade_filter
            or generic_filter
            or ndc_filter
            or "All"
        )


        file_period = (
            "Synthetic/Test Upload"
        )


    # ========================================================
    # No matches
    # ========================================================

    if results.empty:

        st.warning(
            "No matching products found. "
            "Nothing was added."
        )


    # ========================================================
    # Add matches
    # ========================================================

    else:

        search_number = (
            len(
                st.session_state[
                    "search_history"
                ]
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

            "FilePeriod":
                file_period,
        }


        st.session_state[
            "search_history"
        ].append(
            search_record
        )


        if (
            st.session_state[
                "combined_results"
            ].empty
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
            f"Added "
            f"{len(results):,} rows "
            f"for {search_label}."
        )


# ============================================================
# Search history
# ============================================================

if st.session_state[
    "search_history"
]:

    st.divider()

    st.subheader(
        "Added Searches"
    )

    searches_df = pd.DataFrame(
        st.session_state[
            "search_history"
        ]
    )

    st.dataframe(
        searches_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Combined dataset
# ============================================================

if (
    not st.session_state[
        "combined_results"
    ].empty
):

    st.divider()

    results = (
        st.session_state[
            "combined_results"
        ].copy()
    )


    st.subheader(
        "Combined Dataset"
    )


    st.write(
        f"**{len(results):,} unique pricing records** "
        f"from "
        f"**{len(st.session_state['search_history']):,} searches**"
    )


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

            "WACPackagePrice":
                st.column_config.NumberColumn(
                    "WAC Package Price",
                    format="$%.2f",
                ),

            "WACUnitPrice":
                st.column_config.NumberColumn(
                    "WAC Unit Price",
                    format="$%.4f",
                ),

            "AWPPackagePrice":
                st.column_config.NumberColumn(
                    "AWP Package Price",
                    format="$%.2f",
                ),

            "AWPUnitPrice":
                st.column_config.NumberColumn(
                    "AWP Unit Price",
                    format="$%.4f",
                ),
        },
    )


    searches_df = pd.DataFrame(
        st.session_state[
            "search_history"
        ]
    )


    filename = build_filename(
        searches_df
    )


    excel_data = (
        dataframe_to_excel(
            results,
            searches_df,
        )
    )


    st.download_button(
        label=(
            "Download Combined Excel File"
        ),
        data=excel_data,
        file_name=filename,
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        type="primary",
    )