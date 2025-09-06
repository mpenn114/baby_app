import streamlit as st
from src.clients.bigquery_client import bq_client
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from src.cfg.colour_config import ColourConfig

COLOURS = ColourConfig()
NAPPY_TABLE = "archie-baby-app.baby_app.nappies"


def display_bowels():
    """
    Display the bowels page
    """
    st.markdown("<h1 style='text-align: center;'>Bowels 💩</h1>", unsafe_allow_html=True)

    # Retrieve the nappies data
    if "nappy_cache" not in st.session_state:
        st.session_state["nappy_cache"] = 0
    nappies_data = get_nappies_data(st.session_state["nappy_cache"]).sort_values(
        by=["nappy_date", "nappy_time"], ascending=False
    )
    col1, col2 = st.columns(2)
    with col1:
        with st.form("nappy_submit_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Log New Nappy</h4>",
                unsafe_allow_html=True,
            )
            nappy_date = st.date_input("Nappy Date", value=datetime.today())
            nappy_time = st.time_input("Nappy Time")
            nappy_changer = st.selectbox(
                "Nappy Changer",
                list(
                    set(
                        ["Matt", "Grace"]
                        + nappies_data["nappy_changer"].unique().tolist()
                    )
                ),
                accept_new_options=True,
            )
            contains_wee = st.checkbox("Contains Wee?")
            contains_poo = st.checkbox("Contains Poo?")
            poo_colour = st.color_picker("Poo Colour")
            notes = st.text_input("Other Notes")

            form_submission = st.form_submit_button("Upload Nappy")

    if form_submission:
        new_nappy = pd.DataFrame(
            {
                "nappy_date": [nappy_date],
                "nappy_time": [nappy_time],
                "nappy_changer": [nappy_changer],
                "contains_wee": [contains_wee],
                "contains_poo": [contains_poo],
                "poo_colour": [poo_colour if contains_poo else None],
                "notes": [notes],
            }
        )
        overall_nappy_data = pd.concat([nappies_data, new_nappy])
        save_nappies_data(overall_nappy_data)

    with col1:
        with st.form("nappy_deletion"):
            st.markdown(
                "<h4 style='text-align: center;'>Delete Nappy</h4>",
                unsafe_allow_html=True,
            )
            nappy_date_time = (
                nappies_data["nappy_date"].apply(lambda x: x.strftime("%d-%m-%Y"))
                + " ("
                + nappies_data["nappy_time"].apply(lambda x: x.strftime("%H:%M"))
                + ")"
            )
            selected_nappy = st.selectbox("Select Nappy", nappy_date_time)
            delete_form_submit = st.form_submit_button(
                "Delete Nappy",
                help="Note that pressing this button will not remove your memory of this nappy",
            )
    if delete_form_submit:
        nappies_data = nappies_data[nappy_date_time != selected_nappy]
        save_nappies_data(nappies_data)

    # Plot the nappies over time
    with col2:
        nappies_per_day = (
            nappies_data.groupby("nappy_date")
            .agg(total=("nappy_date", "count"), poo=("contains_poo", "sum"))
            .sort_index()
            .reset_index()
        )
        fig, ax = plt.subplots(figsize=(12, 8))
        plt.plot(
            nappies_per_day["nappy_date"],
            nappies_per_day["total"],
            color=COLOURS.PINK_HEX,
            linewidth=2,
        )
        plt.scatter(
            nappies_per_day["nappy_date"],
            nappies_per_day["total"],
            color=COLOURS.PINK_HEX,
            s=400,
            ec="k",
            label="Total",
        )

        plt.plot(
            nappies_per_day["nappy_date"],
            nappies_per_day["poo"],
            color=COLOURS.BROWN_HEX,
            linewidth=2,
        )
        plt.scatter(
            nappies_per_day["nappy_date"],
            nappies_per_day["poo"],
            color=COLOURS.BROWN_HEX,
            s=400,
            ec="k",
            label="Poo",
        )
        plt.ylim([0, nappies_per_day["total"].max() + 1])
        plt.ylabel("Nappies", fontsize=18, color=COLOURS.BROWN_HEX)
        plt.xlabel("Date", fontsize=18, color=COLOURS.BROWN_HEX)
        # Ensure that there are whole days shown on the x axis
        locator = mdates.AutoDateLocator(minticks=3, maxticks=10, interval_multiples=True)
        ax.xaxis.set_major_locator(locator)
        # Format to show only dates (no times)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%y"))

        plt.xticks(fontsize=14)
        plt.title("Nappies Over Time", fontsize=24, color=COLOURS.BROWN_HEX)
        plt.legend(fontsize=14)
        st.pyplot(fig)

    # Plot the nappy leaderboard
    with col2:
        nappies_changed = (
            nappies_data.groupby("nappy_changer")
            .agg(count=("nappy_changer", "count"))
            .sort_values(by="count")
            .reset_index()
        )
        fig, ax = plt.subplots(figsize=(12, 8))
        plt.barh(
            nappies_changed["nappy_changer"],
            nappies_changed["count"],
            color=COLOURS.PINK_HEX,
            ec="k",
        )
        plt.title("Nappies Changed Per Person", fontsize=24, color=COLOURS.BROWN_HEX)
        plt.xlabel("Nappies Changed", fontsize=14, color=COLOURS.BROWN_HEX)
        plt.yticks(fontsize=14)
        st.pyplot(fig)

    st.markdown("_____________________")
    st.markdown(
        "<h3 style='text-align: center;'>All Nappies</h3>", unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center;'>Oh, what great memories are stored here...</p>",
        unsafe_allow_html=True,
    )
    display_nappies_data(nappies_data)


def display_nappies_data(df: pd.DataFrame):
    """
    Display the full nappies data
    """

    # Style function
    def highlight_hex(val):
        if isinstance(val, str) and val.startswith("#"):
            return f"background-color: {val}"
        return ""

    # Tidy columns
    df = df[
        [
            "nappy_date",
            "nappy_time",
            "nappy_changer",
            "contains_wee",
            "contains_poo",
            "poo_colour",
            "notes",
        ]
    ].reset_index(drop=True)
    df.index += 1
    df.columns = [x.replace("_", " ").title() for x in df.columns]
    # Apply styler
    styled_df = df.style.map(highlight_hex, subset=["Poo Colour"]).hide(axis="index")
    st.dataframe(styled_df)


@st.cache_data(show_spinner="Reminding ourselves of all the nappies...")
def get_nappies_data(cache_index: int) -> pd.DataFrame:
    """
    Get the nappies data from GBQ
    """
    client = bq_client()
    return client.query(f"SELECT * FROM {NAPPY_TABLE}").to_dataframe()


def save_nappies_data(nappy_data: pd.DataFrame):
    """
    Save the nappy data
    """
    # Job config to overwrite table
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    # Upload dataframe
    job = bq_client().load_table_from_dataframe(
        nappy_data, NAPPY_TABLE, job_config=job_config
    )
    job.result()  # Wait for the job to complete

    # Update cache and rerun
    st.success("Nappy Data Updated!")
    st.session_state["nappy_cache"] += 1
    st.rerun()
