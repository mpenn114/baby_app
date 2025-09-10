import streamlit as st
from src.clients.bigquery_client import bq_client
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from src.cfg.colour_config import ColourConfig

COLOURS = ColourConfig()
SLEEPING_TABLE = "archie-baby-app.baby_app.sleeping"
SETTLING_TECHNIQUES_TABLE = "archie-baby-app.baby_app.settling_techniques"


def display_sleeping():
    """
    Display the sleeping page
    """
    # Display the title
    st.markdown(
        "<h1 style='text-align: center;'>Sleeping 😴</h1>", unsafe_allow_html=True
    )

    # Retrieve the sleeping data
    if "sleeping_cache" not in st.session_state:
        st.session_state["sleeping_cache"] = 0
    sleeping_data = get_sleeping_data(st.session_state["sleeping_cache"]).sort_values(
        by=["sleep_start_time"], ascending=False
    )

    # Create the new sleeping form
    col1, col2 = st.columns(2)
    with col1:
        with st.form("sleep_start_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Log New Sleep</h4>",
                unsafe_allow_html=True,
            )
            st.write(
                "Note: Please enter the time at which Archie went to sleep. Time taken to settle Archie is logged separately."  # noqa: E501
            )
            sleep_start_date = st.date_input("Sleep Start Date", value=datetime.today())
            sleep_start_time = st.time_input("Sleep Start Time")
            settle_time = st.number_input("Time to Settle (Minutes)", min_value=0)
            sleep_location = st.selectbox(
                "Sleep Location",
                options=list(
                    set(
                        ["Moses Basket", "Car Seat"]
                        + sleeping_data["sleep_location"].unique().tolist()
                    )
                ),
                accept_new_options=True,
            )
            # Add options for settling techniques
            settling_techniques = st.multiselect(
                "Settling Techniques",
                options=list(
                    set(
                        ["Singing", "Bouncing"]
                        + [
                            x
                            for _, row in sleeping_data.iterrows()
                            for x in row["settling_techniques"]
                        ]
                    )
                ),
            )
            # Add submission button
            new_sleep_submission = st.form_submit_button("Upload Sleep")

    # Upload new sleep data
    if new_sleep_submission:
        if len(sleeping_data) == 0:
            sleep_id = 0
        else:
            sleep_id = sleeping_data["sleep_id"].max() + 1
        new_sleep_data = pd.DataFrame(
            {
                "sleep_id": [sleep_id],
                "sleep_start_time": [
                    datetime.combine(sleep_start_date, sleep_start_time)
                ],
                "time_to_settle": [settle_time],
                "sleep_location": [sleep_location],
                "settling_techniques": [settling_techniques],
            }
        )
        sleeping_data = pd.concat([sleeping_data, new_sleep_data])
        save_sleeping_data(sleeping_data)

    # Add sleep end
    with col1:
        with st.form("sleep_end_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Log Wake Up</h4>",
                unsafe_allow_html=True,
            )
            st.write("All good things....")
            orig_sleep_start_date = st.selectbox(
                "Select Sleep",
                options=sleeping_data[pd.isna(sleeping_data["sleep_end_time"])][
                    "sleep_start_time"
                ]
                .unique()
                .tolist(),
            )

            wake_up_date = st.date_input("Wake Up Date")
            wake_up_time = st.time_input("Wake Up Time")
            temporary_wakeup = st.checkbox("Temporary Wake Up?")

            # Add submission button
            sleep_end_button = st.form_submit_button("Upload Wake Up")

    # Upload new wake up data
    if sleep_end_button:
        # Get the corresponding sleep data
        original_sleep_data = sleeping_data[
            sleeping_data["sleep_start_time"] == orig_sleep_start_date
        ].iloc[0]

        if not temporary_wakeup:
            # Add the end of the sleep
            new_sleep_data = pd.DataFrame(
                {
                    "sleep_id": [original_sleep_data["sleep_id"]],
                    "sleep_start_time": [original_sleep_data["sleep_start_time"]],
                    "sleep_end_time": [datetime.combine(wake_up_date, wake_up_time)],
                    "time_to_settle": [original_sleep_data["time_to_settle"]],
                    "sleep_location": [original_sleep_data["sleep_location"]],
                    "settling_techniques": [original_sleep_data["settling_techniques"]],
                    "temporary_wake_up_times": [
                        original_sleep_data["temporary_wake_up_times"]
                    ],
                }
            )
        else:
            # Update the temporary wake up list, ensuring
            # everything in the list is Python datetime
            wake_up_list = list(original_sleep_data["temporary_wake_up_times"])
            wake_up_list = [pd.to_datetime(x).to_pydatetime() for x in wake_up_list]

            wake_up_list.append(datetime.combine(wake_up_date, wake_up_time))
            # Add the temporary wake-up time
            new_sleep_data = pd.DataFrame(
                {
                    "sleep_id": [original_sleep_data["sleep_id"]],
                    "sleep_start_time": [original_sleep_data["sleep_start_time"]],
                    "time_to_settle": [original_sleep_data["time_to_settle"]],
                    "sleep_location": [original_sleep_data["sleep_location"]],
                    "settling_techniques": [original_sleep_data["settling_techniques"]],
                    "temporary_wake_up_times": [wake_up_list],
                }
            )
        sleeping_data = pd.concat(
            [
                sleeping_data[
                    sleeping_data["sleep_start_time"] != orig_sleep_start_date
                ],
                new_sleep_data,
            ]
        ).reset_index(drop=True)
        save_sleeping_data(sleeping_data)

    # Create delete sleep form
    with col1:
        with st.form('delete_sleep_form'):
            st.subheader('Delete Sleep')
            st.markdown('When the nightmares get too real...')
            deleted_sleep = st.selectbox(
                'Select Sleep Start Time', options = sleeping_data['sleep_start_time'].unique()
            )
            delete_sleep_button = st.form_submit_button('Delete Sleep')
    if delete_sleep_button:
        sleeping_data = sleeping_data[sleeping_data["sleep_start_time"] != deleted_sleep].reset_index(drop=True)
        save_sleeping_data(sleeping_data)

    # Create plots

    with col2:
        st.pyplot(plot_total_sleep_by_day(sleeping_data))
        st.pyplot(plot_settle_time_by_technique(sleeping_data))
        st.pyplot(plot_sleep_proportion_by_hour(sleeping_data))
    st.markdown("_____________________")
    st.markdown(
        "<h3 style='text-align: center;'>All Sleep Data</h3>", unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center;'>I promise he has (sometimes) slept...</p>",
        unsafe_allow_html=True,
    )
    display_sleeping_data(sleeping_data)


@st.cache_data(show_spinner="Shh... The baby's sleeping!")
def get_sleeping_data(cache_index: int) -> pd.DataFrame:
    """
    Get the sleeping data from GBQ
    """
    client = bq_client()
    return client.query(f"SELECT * FROM {SLEEPING_TABLE}").to_dataframe()


def save_sleeping_data(sleeping_data: pd.DataFrame):
    """
    Save the sleeping data
    """
    # Ensure data has the correct type
    sleeping_data["sleep_start_time"] = pd.to_datetime(
        sleeping_data["sleep_start_time"]
    )
    sleeping_data["sleep_end_time"] = pd.to_datetime(sleeping_data["sleep_end_time"])

    # Job config to overwrite table
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("sleep_start_time", "DATETIME"),
            bigquery.SchemaField("sleep_end_time", "DATETIME"),
            bigquery.SchemaField("time_to_settle", "INTEGER"),
            bigquery.SchemaField("sleep_location", "STRING"),
            bigquery.SchemaField(
                "temporary_wake_up_times", "DATETIME", mode="REPEATED"
            ),
            bigquery.SchemaField("settling_techniques", "STRING", mode="REPEATED"),
            bigquery.SchemaField("sleep_id", "INTEGER"),
        ],
    )

    # Upload dataframe
    job = bq_client().load_table_from_dataframe(
        sleeping_data, SLEEPING_TABLE, job_config=job_config
    )
    job.result()  # Wait for the job to complete

    # Update cache and rerun
    st.success("Sleeping Data Updated!")
    st.session_state["sleeping_cache"] += 1
    st.rerun()


def plot_total_sleep_by_day(df: pd.DataFrame):
    """
    Plot total sleep duration by day.
    Handles sleep episodes that span multiple days.
    """
    # Ensure datetime conversion
    df["sleep_start_time"] = pd.to_datetime(df["sleep_start_time"])
    df["sleep_end_time"] = pd.to_datetime(df["sleep_end_time"])

    daily_sleep = []

    for _, row in df.iterrows():
        start = row["sleep_start_time"]
        end = row["sleep_end_time"]
        if pd.isnull(start) or pd.isnull(end):
            continue

        # Iterate through each day spanned by the interval
        current = start
        while current.date() <= end.date():
            # End of this day (or actual end if earlier)
            day_end = min(end, pd.Timestamp.combine(current.date(), pd.Timestamp.max.time()))
            hours = (day_end - current).total_seconds() / 3600
            daily_sleep.append({"date": current.date(), "hours": hours})

            # Move to start of next day
            current = pd.Timestamp.combine(current.date() + pd.Timedelta(days=1), pd.Timestamp.min.time())

    # Aggregate
    if daily_sleep:
        sleep_by_day = pd.DataFrame(daily_sleep).groupby("date")["hours"].sum()
    else:
        sleep_by_day = pd.Series(dtype=float)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    scaled_sleep = (sleep_by_day - sleep_by_day.min())/(sleep_by_day.max() - sleep_by_day.min())
    colors = [tuple(x*c + (1-x) for c in COLOURS.PINK_RGB) for x in scaled_sleep]

    sleep_by_day.plot(kind="bar", ax=ax, color=colors, ec='k')
    plt.ylabel("Total Sleep (hours)", fontsize=14)
    plt.title("Total Sleep by Day", fontsize=18)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig


def plot_settle_time_by_technique(
    df: pd.DataFrame,
    fill_color: str = COLOURS.PINK_HEX,   # default fill
    line_color: str = COLOURS.BROWN_HEX     # default line colour
):
    """
    Boxplots of time_to_settle for each settling technique when used,
    with customisable fill and line colours.
    """
    df = df.copy()
    df = df.dropna(subset=["time_to_settle", "settling_techniques"])

    # Explode repeated techniques
    df = df.explode("settling_techniques")

    techniques = df["settling_techniques"].unique()
    data = [df.loc[df["settling_techniques"] == tech, "time_to_settle"] for tech in techniques]

    fig, ax = plt.subplots(figsize=(8, 5))
    boxprops = dict(facecolor=fill_color, color=line_color, linewidth=1.5)
    medianprops = dict(color=line_color, linewidth=2)
    whiskerprops = dict(color=line_color, linewidth=1.5)
    capprops = dict(color=line_color, linewidth=1.5)

    bp = ax.boxplot(
        data,
        labels=techniques,
        patch_artist=True,   # allows fill colour
        boxprops=boxprops,
        medianprops=medianprops,
        whiskerprops=whiskerprops,
        capprops=capprops
    )

    plt.ylabel("Time to Settle (Mins)", fontsize=14)
    plt.title("Time to Settle by Technique", fontsize=18)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig
def plot_sleep_proportion_by_hour(df: pd.DataFrame) -> plt.Figure:
    """
    Calculate the exact proportion of time asleep in each hour of the day (0–23),
    averaged across all days in the dataset.
    """
    df = df.copy()
    df["sleep_start_time"] = pd.to_datetime(df["sleep_start_time"])
    df["sleep_end_time"] = pd.to_datetime(df["sleep_end_time"])
    df = df.dropna(subset=["sleep_start_time", "sleep_end_time"])

    # Track total asleep minutes per hour
    asleep_minutes = np.zeros(24)

    for _, row in df.iterrows():
        start, end = row["sleep_start_time"], row["sleep_end_time"]

        # Ensure sleep end is after start (handle overnight if needed)
        if end <= start:
            end += pd.Timedelta(days=1)

        # Iterate hour blocks overlapping this sleep period
        current = start.floor("h")
        while current < end:
            next_hour = current + pd.Timedelta(hours=1)
            overlap_start = max(start, current)
            overlap_end = min(end, next_hour)
            minutes_asleep = (overlap_end - overlap_start).total_seconds() / 60.0
            if minutes_asleep > 0:
                asleep_minutes[current.hour] += minutes_asleep
            current = next_hour

    # Number of unique days in dataset (to normalise to "proportion of each day")
    num_days = df["sleep_start_time"].dt.normalize().nunique()
    total_minutes_per_hour = num_days * 60.0

    proportions = asleep_minutes / total_minutes_per_hour

    # Colour scale (pink intensity by proportion)
    colors = [tuple(x*c + (1-x) for c in COLOURS.PINK_RGB) for x in proportions]

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(24),100*proportions, color=colors, edgecolor="k")
    plt.xticks(range(24))
    plt.xlabel("Hour of Day", fontsize=14)
    plt.ylabel("Percentage of Time Asleep", fontsize=14)
    plt.title("Proportion of Time Asleep by Hour of Day", fontsize=18)
    plt.tight_layout()
    return fig

def display_sleeping_data(df: pd.DataFrame):
    """
    Display the full sleeping data
    """
    # Tidy columns
    df = df[
        [
            "sleep_start_time",
            "sleep_end_time",
            "time_to_settle",
            "sleep_location",
            "temporary_wake_up_times",
            "settling_techniques",
        ]
    ].reset_index(drop=True)
    df["temporary_wake_up_times"] = df["temporary_wake_up_times"].apply(
        lambda lst: [pd.to_datetime(x).strftime("%Y-%m-%d %H:%M:%S") for x in lst]
    )
    df.index += 1
    df.columns = [
        x.replace("_", " ").title().replace("Time To Settle", "Time To Settle (Mins)")
        for x in df.columns
    ]
    st.dataframe(df)
