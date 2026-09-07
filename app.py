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

    df = normalize_va_catalog(df)

    return df


def clean_filter(value):
    """
    Convert empty user input to None.
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


def dataframe_to_excel(df):
    """
    Convert a DataFrame into an Excel file held in memory.
    """

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Drug Prices",
        )

    output.seek(0)

    return output.getvalue()


# ============================================================
# Application header
# ============================================================

st.title("💊 Drug Price Explorer")

st.write(
    "Search pharmaceutical pricing data and calculate normalized unit costs."
)


# ============================================================
# Load data
# ============================================================

df = load_data()


# ============================================================
# Search inputs
# ============================================================

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
# Search button
# ============================================================

search_clicked = st.button(
    "Search",
    type="primary",
)


# ============================================================
# Search results
# ============================================================

if search_clicked:

    results = get_drug_options(
        df,
        trade_name=clean_filter(trade_name),
        generic_name=clean_filter(generic_name),
        ndc=clean_filter(ndc),
    )

    if results.empty:

        st.warning(
            "No matching products found."
        )

    else:

        # ----------------------------------------------------
        # Sort results
        # ----------------------------------------------------

        sort_columns = []

        if "TradeName" in results.columns:
            sort_columns.append("TradeName")

        if "Generic" in results.columns:
            sort_columns.append("Generic")

        if "PriceType" in results.columns:
            sort_columns.append("PriceType")

        if sort_columns:
            results = results.sort_values(
                by=sort_columns,
                na_position="last",
            )

        # ----------------------------------------------------
        # Display results
        # ----------------------------------------------------

        st.subheader("Results")

        st.write(
            f"**{len(results):,} matching pricing records**"
        )

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn(
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

        # ----------------------------------------------------
        # Determine filename drug identifier
        # ----------------------------------------------------

        if trade_name.strip():

            drug_name = trade_name

        elif generic_name.strip():

            drug_name = generic_name

        elif ndc.strip():

            drug_name = ndc

        else:

            drug_name = "All"

        # ----------------------------------------------------
        # Generate dynamic filename
        # ----------------------------------------------------

        filename = (
            f"VA_"
            f"VAPharm_"
            f"{clean_filename(drug_name)}_"
            f"{date.today().isoformat()}.xlsx"
        )

        # ----------------------------------------------------
        # Excel download
        # ----------------------------------------------------

        excel_data = dataframe_to_excel(
            results
        )

        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name=filename,
            mime=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            type="primary",
        )