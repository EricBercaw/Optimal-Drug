from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

from src.sources.va import load_va_prices
from src.normalize import normalize_va_catalog
from src.pricing import get_drug_options


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
def load_data():
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
        value.strip()
        .replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
    )


def dataframe_to_excel(results_df, searches_df):
    """
    Create an Excel workbook containing:
      1. Combined pharmaceutical pricing results
      2. Search criteria used
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


def build_search_label(
    trade_name=None,
    generic_name=None,
    ndc=None,
):
    """
    Create a readable description of the search.
    """

    parts = []

    if trade_name:
        parts.append(f"Trade: {trade_name}")

    if generic_name:
        parts.append(f"Generic: {generic_name}")

    if ndc:
        parts.append(f"NDC: {ndc}")

    if not parts:
        return "All VA Products"

    return " | ".join(parts)


def build_filename(searches_df):
    """
    Create a dynamic Excel filename.

    One search:
        VA_VAPharm_Nplate_2026-09-06.xlsx

    Multiple searches:
        VA_VAPharm_MultiDrug_3Searches_2026-09-06.xlsx
    """

    access_date = date.today().isoformat()

    number_searches = len(searches_df)

    if number_searches == 1:

        row = searches_df.iloc[0]

        if row["TradeName"]:
            identifier = row["TradeName"]

        elif row["GenericName"]:
            identifier = row["GenericName"]

        elif row["NDC"]:
            identifier = row["NDC"]

        else:
            identifier = "All"

        identifier = clean_filename(identifier)

        return (
            f"VA_"
            f"VAPharm_"
            f"{identifier}_"
            f"{access_date}.xlsx"
        )

    return (
        f"VA_"
        f"VAPharm_"
        f"MultiDrug_"
        f"{number_searches}Searches_"
        f"{access_date}.xlsx"
    )


# ============================================================
# Session state
# ============================================================

if "combined_results" not in st.session_state:
    st.session_state.combined_results = pd.DataFrame()


if "search_history" not in st.session_state:
    st.session_state.search_history = []


# ============================================================
# Header
# ============================================================

st.title("💊 Drug Price Explorer")

st.write(
    "Search pharmaceutical pricing data and build a combined "
    "drug pricing dataset."
)


# ============================================================
# Load catalog
# ============================================================

df = load_data()


# ============================================================
# Search criteria
# ============================================================

st.subheader("Search Criteria")


pricing_source = st.selectbox(
    "Pricing source",
    [
        "VA Pharmaceutical Catalog",
    ],
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
# Buttons
# ============================================================

button_col1, button_col2 = st.columns(
    [1, 1]
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

    st.session_state.combined_results = pd.DataFrame()

    st.session_state.search_history = []

    st.success(
        "Dataset cleared."
    )


# ============================================================
# Add search to dataset
# ============================================================

if add_clicked:

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
        df,
        trade_name=trade_filter,
        generic_name=generic_filter,
        ndc=ndc_filter,
    )


    if results.empty:

        st.warning(
            "No matching products found. "
            "Nothing was added to the dataset."
        )


    else:

        # ----------------------------------------------------
        # Record search
        # ----------------------------------------------------

        search_number = (
            len(st.session_state.search_history)
            + 1
        )

        search_label = build_search_label(
            trade_name=trade_filter,
            generic_name=generic_filter,
            ndc=ndc_filter,
        )


        search_record = {
            "SearchNumber": search_number,
            "PricingSource": pricing_source,
            "TradeName": trade_filter or "",
            "GenericName": generic_filter or "",
            "NDC": ndc_filter or "",
            "SearchLabel": search_label,
            "RowsMatched": len(results),
        }

        st.session_state.search_history.append(
            search_record
        )


        # ----------------------------------------------------
        # Combine with existing dataset
        # ----------------------------------------------------

        if st.session_state.combined_results.empty:

            st.session_state.combined_results = (
                results.copy()
            )

        else:

            st.session_state.combined_results = (
                pd.concat(
                    [
                        st.session_state.combined_results,
                        results,
                    ],
                    ignore_index=True,
                )
            )


        # ----------------------------------------------------
        # Remove duplicate VA records
        # ----------------------------------------------------

        st.session_state.combined_results = (
            st.session_state.combined_results
            .drop_duplicates()
            .reset_index(drop=True)
        )


        st.success(
            f"Added {len(results):,} matching rows "
            f"for {search_label}."
        )


# ============================================================
# Search history
# ============================================================

if st.session_state.search_history:

    st.divider()

    st.subheader("Added Searches")

    searches_df = pd.DataFrame(
        st.session_state.search_history
    )

    st.dataframe(
        searches_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Combined results
# ============================================================

if not st.session_state.combined_results.empty:

    st.divider()

    results = (
        st.session_state.combined_results
        .copy()
    )


    # --------------------------------------------------------
    # Sort combined results
    # --------------------------------------------------------

    sort_columns = []

    if "TradeName" in results.columns:
        sort_columns.append(
            "TradeName"
        )

    if "Generic" in results.columns:
        sort_columns.append(
            "Generic"
        )

    if "PriceType" in results.columns:
        sort_columns.append(
            "PriceType"
        )


    if sort_columns:

        results = results.sort_values(
            by=sort_columns,
            na_position="last",
        )


    # --------------------------------------------------------
    # Results heading
    # --------------------------------------------------------

    st.subheader("Combined Dataset")

    st.write(
        f"**{len(results):,} unique pricing records** "
        f"from "
        f"**{len(st.session_state.search_history):,} searches**"
    )


    # --------------------------------------------------------
    # Display ALL VA + calculated columns
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
        },
    )


    # --------------------------------------------------------
    # Excel export
    # --------------------------------------------------------

    searches_df = pd.DataFrame(
        st.session_state.search_history
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