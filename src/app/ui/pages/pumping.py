import streamlit as st
from src.clients.bigquery_client import bq_client
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from src.cfg.colour_config import ColourConfig
import matplotlib.colors as mcolors
import matplotlib.dates as mdates

COLOURS = ColourConfig()
PUMPING_TABLE = "archie-baby-app.baby_app.pumping"


def display_pumping():
    """
    Display the pumping page
    """
    # Display the title
    st.markdown(
        "<h1 style='text-align: center;'>Pumping ⛽</h1>", unsafe_allow_html=True
    )
    # Retrieve the pumping data
    if "pumping_cache" not in st.session_state:
        st.session_state["pumping_cache"] = 0
    pumping_data = get_pumping_data(st.session_state["pumping_cache"]).sort_values(
        by=["pump_date"], ascending=False
    )
    col1, col2 = st.columns(2)
    with col1:
        with st.form('add_pumping_data'):
            st.markdown(
                "<h4 style='text-align: center;'>Add Pumping Session</h4>",
                unsafe_allow_html=True,
            )
            pump_date = st.date_input('Date')
            pump_time = st.time_input('Time')
            st.markdown('________')
            left_volume = st.number_input('Left Breast Volume (ml)', step=1, min_value=0)
            right_volume = st.number_input('Right Breast Volume (ml)', step=1, min_value=0)

            add_pump = st.form_submit_button('Add Session!')

    if add_pump:
        if left_volume == 0 and right_volume == 0:
            st.error('At least one breast volume must be greater than 0!')
        else:
            new_pump_session = pd.DataFrame({
                'pump_date': [datetime.combine(pump_date, pump_time)],
                'left_volume': [left_volume if left_volume > 0 else None],
                'right_volume': [right_volume if right_volume > 0 else None]
            })
            pumping_data = pd.concat([pumping_data, new_pump_session])
            save_pumping_data(pumping_data, expected_length_difference=1)

    with col1:
        with st.form('delete_pump'):
            st.markdown(
                "<h4 style='text-align: center;'>Delete Session</h4>",
                unsafe_allow_html=True,
            )
            st.write('For when you put the pump in reverse...')
            delete_pump_time = st.selectbox('Select Session', options=pumping_data['pump_date'].unique())
            delete_pump = st.form_submit_button('Delete Session')

    if delete_pump:
        pumping_data = pumping_data[pumping_data['pump_date'] != delete_pump_time].reset_index(drop=True)
        save_pumping_data(pumping_data, expected_length_difference=-1)

    with col2:
        st.pyplot(plot_volume_per_day(pumping_data))
        st.pyplot(plot_rolling_24h_by_breast(pumping_data))

    st.markdown("_____________________")
    st.markdown(
        "<h3 style='text-align: center;'>All Pumping Data</h3>", unsafe_allow_html=True
    )
    display_pumping_data(pumping_data)


@st.cache_data(show_spinner="Time to get PUMPED...")
def get_pumping_data(cache_index: int) -> pd.DataFrame:
    """
    Get the pumping data from GBQ
    """
    client = bq_client()
    return client.query(f"SELECT * FROM {PUMPING_TABLE}").to_dataframe()


def plot_volume_per_day(df: pd.DataFrame):
    """
    Plot total pumped volume per day as a stacked bar chart split by breast.
    """
    df = df.copy()
    df["pump_date"] = pd.to_datetime(df["pump_date"])
    df["day"] = df["pump_date"].dt.date

    left_by_day = df.groupby("day")["left_volume"].sum().fillna(0)
    right_by_day = df.groupby("day")["right_volume"].sum().fillna(0)

    # Ensure both series have the same index
    all_days = sorted(set(left_by_day.index) | set(right_by_day.index))
    left_by_day = left_by_day.reindex(all_days, fill_value=0)
    right_by_day = right_by_day.reindex(all_days, fill_value=0)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(left_by_day.index, left_by_day.values, color=COLOURS.PINK_HEX, label="Left", ec='k')
    ax.bar(right_by_day.index, right_by_day.values, bottom=left_by_day.values,
           color=COLOURS.BROWN_HEX, label="Right", ec='k')

    plt.ylabel("Total Volume (ml)", fontsize=14)
    plt.xlabel("Date", fontsize=14)
    plt.title("Total Pumped Volume Per Day", fontsize=18)
    ax.legend()
    plt.xticks(rotation=45, ha="right")

    locator = mdates.AutoDateLocator(minticks=1, maxticks=10, interval_multiples=True)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    plt.tight_layout()
    return fig


def plot_rolling_24h_by_breast(df: pd.DataFrame):
    """
    Plot the rolling 24-hour total volume for each breast separately.
    """
    df = df.copy()
    df["pump_date"] = pd.to_datetime(df["pump_date"])
    df = df.set_index("pump_date").sort_index()

    # Resample to hourly totals for each breast
    left_hourly = df["left_volume"].resample("1h").sum()
    right_hourly = df["right_volume"].resample("1h").sum()

    # Rolling 24-hour totals
    left_rolling = left_hourly.rolling("24h").sum()
    right_rolling = right_hourly.rolling("24h").sum()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(left_rolling.index, left_rolling.values, color=COLOURS.PINK_HEX,
            lw=2, label="Left", markersize=3)
    ax.plot(right_rolling.index, right_rolling.values,
            color=COLOURS.BROWN_HEX,
            lw=2, label="Right", markersize=3)

    ax.set_ylabel("Rolling 24-Hour Total (ml)", fontsize=14)
    ax.set_xlabel("Date", fontsize=14)
    ax.set_title("Pumped Volume: Rolling 24-Hour Total by Breast", fontsize=18)
    ax.legend()

    locator = mdates.AutoDateLocator(minticks=1, maxticks=10, interval_multiples=True)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    return fig


def save_pumping_data(pumping_data: pd.DataFrame, expected_length_difference: int):
    """
    Save the pumping data

    Args:
        pumping_data (pd.DataFrame): The pumping data to save
        expected_length_difference (int): The expected difference in length between the new data
            and the true dataset
    """
    # Get the (uncached) length of the true dataset
    client = bq_client()
    table_length = client.query(f"SELECT COUNT(*) AS length FROM {PUMPING_TABLE}").to_dataframe()['length'].to_numpy()[0]

    # Assert that the length is as expected
    if len(pumping_data) != table_length + expected_length_difference:
        st.toast('Unable to save data - please ensure that you have reset the cache to get the most recent table! This can be done using the button at the bottom of the page.')
        return

    # Ensure data has the correct type
    pumping_data["pump_date"] = pd.to_datetime(pumping_data["pump_date"])

    # Job config to overwrite table
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("pump_date", "DATETIME"),
            bigquery.SchemaField("left_volume", "FLOAT"),
            bigquery.SchemaField("right_volume", "FLOAT"),
        ],
    )

    # Upload dataframe
    job = bq_client().load_table_from_dataframe(
        pumping_data, PUMPING_TABLE, job_config=job_config
    )
    job.result()  # Wait for the job to complete

    # Update cache and rerun
    st.success("Pumping Data Updated!")
    st.session_state["pumping_cache"] += 1
    st.rerun()


def display_pumping_data(df: pd.DataFrame):
    """
    Display the full pumping data
    """
    # Tidy columns
    df = df[["pump_date", "left_volume", "right_volume"]].reset_index(drop=True)
    df.index += 1
    df.columns = [
        x.replace("_", " ").title().replace("Volume", "Volume (ml)")
        for x in df.columns
    ]
    st.dataframe(df)
