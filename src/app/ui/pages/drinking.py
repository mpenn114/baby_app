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
DRINKING_TABLE = "archie-baby-app.baby_app.drinking_refactored"


def display_drinking():
    """
    Display the sleeping page
    """
    # Display the title
    st.markdown(
        "<h1 style='text-align: center;'>Drinking 🍼</h1>", unsafe_allow_html=True
    )
    # Retrieve the drinking data
    if "drinking_cache" not in st.session_state:
        st.session_state["drinking_cache"] = 0
    drinking_data = get_drinking_data(st.session_state["drinking_cache"]).sort_values(
        by=["feed_date"], ascending=False
    )
    col1,col2 = st.columns(2)
    with col1:
        with st.form('add_drinking_data'):

            start_date = st.date_input('Start Date')
            start_time = st.time_input('Start Time')
            bottle_fed = st.checkbox('Bottle Fed?')
            st.markdown('________')
            st.write('Breastfeed Information (leave blank if bottle fed)')
            side = st.selectbox('Select Start Side',['None','Left','Right'],help = 'This is the side from your point of view')
            start_side_time = st.number_input('Time on Start Side (Minutes)', step=1)
            total_time = st.number_input('Total Time (Minutes)',step=1)
            st.markdown('________')
            st.write('Bottle Information (leave blank if breastfed)')
            total_volume = st.number_input('Feed Volume (ml)', step=1)

            add_drink = st.form_submit_button('Add Drink!')
    if add_drink:
        if total_time < start_side_time:
            st.error('Total time should not be less than the time on the start side!')
        new_drink_date = pd.DataFrame({
            'feed_date':[
                    datetime.combine(start_date, start_time)
                ],
            'breastfeed_duration':[total_time],
            'start_side':[side],
            'start_side_time':[start_side_time],
            'bottle_fed':[bottle_fed],
            'bottle_quantity':[total_volume]

        })
        drinking_data = pd.concat([drinking_data, new_drink_date])
        save_drinking_data(drinking_data)

    with col1:
        with st.form('delete_drink'):
            st.markdown(
                    "<h4 style='text-align: center;'>Delete Drink</h4>",
                    unsafe_allow_html=True,
            )
            st.write('The baby does this by vomiting, but this form is less messy')
            delete_drink_time = st.selectbox('Select Drink',options = drinking_data['feed_date'].unique())
            delete_drink = st.form_submit_button('Delete Drink')
    if delete_drink:
        drinking_data = drinking_data[drinking_data['feed_date']!=delete_drink_time].reset_index(drop=True)
        save_drinking_data(drinking_data)

    with col2:
        st.pyplot(plot_drinks_per_day(drinking_data))
        st.pyplot(plot_bottle_drink_volume_per_day(drinking_data))
        st.pyplot(plot_bottle_drink_volume_rolling_24h(drinking_data))

    st.markdown("_____________________")
    st.markdown(
        "<h3 style='text-align: center;'>All Drinking Data</h3>", unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center;'>I promise we'll feed him real food one day...</p>",
        unsafe_allow_html=True,
    )
    display_drinking_data(drinking_data)


@st.cache_data(show_spinner="Not that kind of drinking...")
def get_drinking_data(cache_index: int) -> pd.DataFrame:
    """
    Get the sleeping data from GBQ
    """
    client = bq_client()
    return client.query(f"SELECT * FROM {DRINKING_TABLE}").to_dataframe()


def plot_drinks_per_day(df: pd.DataFrame):
    """
    Plot number of drinks per day, with bottle-fed drinks as a separate line.
    """
    df = df.copy()
    df["feed_date"] = pd.to_datetime(df["feed_date"])
    df["day"] = df["feed_date"].dt.date

    total_counts = df.groupby("day").size()
    bottle_counts = df[df["bottle_fed"]].groupby("day").size()

    fig, ax = plt.subplots(figsize=(8, 5))
    total_counts.plot(ax=ax, marker="o", color=COLOURS.PINK_HEX, label="All drinks")
    bottle_counts.plot(ax=ax, marker="o", color='k', label="Bottle-fed drinks")


    plt.ylabel("Number of drinks", fontsize=14)
    plt.title("Number of Drinks per Day", fontsize=18)
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    # Ensure that there are whole days shown on the x axis
    locator = mdates.AutoDateLocator(
        minticks=1, maxticks=10, interval_multiples=True
    )
    ax.xaxis.set_major_locator(locator)
    plt.tight_layout()
    return fig

def _get_gradient_colours(values:pd.Series, hex_colour:str, minimum:float = None):
    """
    Map values to a gradient between white and the given hex colour.
    """
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["#ffffff", hex_colour])
    norm = mcolors.Normalize(vmin=values.min() if minimum is None else minimum, vmax=values.max())
    return [cmap(norm(v)) for v in values]


def plot_bottle_drink_volume_per_day(df: pd.DataFrame):
    """
    Plot total duration of drinks per day (based on feed start day).
    Colours scaled white → pink.
    """
    df = df.copy()
    df["feed_date"] = pd.to_datetime(df["feed_date"])
    df["day"] = df["feed_date"].dt.date

    duration_by_day = df.dropna(subset=['bottle_quantity']).groupby("day")["bottle_quantity"].sum()
    colours = _get_gradient_colours(duration_by_day.values, COLOURS.PINK_HEX)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(duration_by_day.index, duration_by_day.values, color=colours, ec='k')

    plt.ylabel("Total Volume (ml)", fontsize=14)
    plt.xlabel("Date", fontsize=14)
    plt.title("Total Bottle Drink Volume Per Day", fontsize=18)
    plt.xticks(rotation=45, ha="right")
    # Ensure that there are whole days shown on the x axis
    locator = mdates.AutoDateLocator(
        minticks=1, maxticks=10, interval_multiples=True
    )
    ax.xaxis.set_major_locator(locator)
    plt.tight_layout()
    return fig
def plot_bottle_drink_volume_rolling_24h(df: pd.DataFrame):
    """
    Plot the rolling 24-hour total bottle quantity.
    Each point represents the total intake over the previous 24 hours.
    """
    df = df.copy()
    df["feed_date"] = pd.to_datetime(df["feed_date"])
    df = df.dropna(subset=["bottle_quantity"])
    df = df.set_index("feed_date").sort_index()

    # Resample to an hourly total (adjust frequency if you need finer resolution)
    hourly = df["bottle_quantity"].resample("1h").sum()

    # Rolling 24-hour total
    rolling_24h_total = hourly.rolling("24h").sum()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(rolling_24h_total.index, rolling_24h_total.values, color=COLOURS.PINK_HEX, lw=2)

    ax.set_ylabel("Rolling 24-Hour Total (ml)", fontsize=14)
    ax.set_xlabel("Date", fontsize=14)
    ax.set_title("Bottle Intake: Rolling 24-Hour Total", fontsize=18)

    locator = mdates.AutoDateLocator(minticks=1, maxticks=10, interval_multiples=True)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    return fig

def plot_duration_by_side(df: pd.DataFrame):
    """
    Plot drink duration from each side ('Left' and 'Right').
    Colours scaled white → pink.
    """
    df = df.copy()
    df = df.dropna(subset=["duration", "start_side", "start_side_time"])

    # Calculate durations for each side
    df["left_duration"] = df.apply(
        lambda row: row["start_side_time"] if row["start_side"] == "Left" else row["duration"] - row["start_side_time"],
        axis=1,
    )
    df["right_duration"] = df.apply(
        lambda row: row["start_side_time"] if row["start_side"] == "Right" else row["duration"] - row["start_side_time"],
        axis=1,
    )
    total_duration = df[['left_duration','right_duration']].sum().sum()
    side_durations = pd.Series({
        "Left": 100*df["left_duration"].sum()/total_duration,
        "Right": 100*df["right_duration"].sum()/total_duration,
    })

    colours = _get_gradient_colours(side_durations.values, COLOURS.PINK_HEX, minimum=0)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(side_durations.index, side_durations.values, color=colours, ec='k')

    plt.ylabel("Percentage Duration", fontsize=14)
    plt.xlabel("Side", fontsize=14)

    plt.title("Drink Duration by Side", fontsize=18)
    plt.tight_layout()
    return fig

def save_drinking_data(drinking_data: pd.DataFrame):
    """
    Save the drinking data
    """
    # Ensure data has the correct type
    drinking_data["feed_date"] = pd.to_datetime(
        drinking_data["feed_date"]
    )

    # Job config to overwrite table
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("feed_date", "DATETIME"),
            bigquery.SchemaField("breastfeed_duration", "FLOAT"),
            bigquery.SchemaField("start_side", "STRING"),
            bigquery.SchemaField("start_side_time", "FLOAT"),
            bigquery.SchemaField('bottle_fed','BOOLEAN'),
            bigquery.SchemaField('bottle_quantity','FLOAT'),


        ],
    )

    # Upload dataframe
    job = bq_client().load_table_from_dataframe(
        drinking_data, DRINKING_TABLE, job_config=job_config
    )
    job.result()  # Wait for the job to complete

    # Update cache and rerun
    st.success("Drinking Data Updated!")
    st.session_state["drinking_cache"] += 1
    st.rerun()


def display_drinking_data(df: pd.DataFrame):
    """
    Display the full sleeping data
    """
    # Tidy columns
    df = df[
        [
            "feed_date",
            "bottle_fed",
            "breastfeed_duration",
            "start_side",
            "start_side_time",
            'bottle_quantity'
        ]
    ].reset_index(drop=True)
    df.index += 1
    df.columns = [
        x.replace("_", " ").title().replace("Duration","Duration (Mins)").replace("Time", "Time (Mins)").replace('Quantity','Quantity (ml)')
        for x in df.columns
    ]
    st.dataframe(df)
