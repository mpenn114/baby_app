import streamlit as st
from src.clients.bigquery_client import bq_client
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
