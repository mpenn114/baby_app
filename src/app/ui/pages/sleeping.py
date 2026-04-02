import streamlit as st
from src.clients.bigquery_client import bq_client
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from src.cfg.colour_config import ColourConfig

COLOURS = ColourConfig()
SLEEPING_TABLE = "archie-baby-app.baby_app.sleeping"


def display_sleeping():
    """Display the sleeping page"""
    st.markdown(
        "<h1 style='text-align: center;'>Sleeping 😴</h1>", unsafe_allow_html=True
    )

    if "sleeping_cache" not in st.session_state:
        st.session_state["sleeping_cache"] = 0
    sleeping_data = get_sleeping_data(st.session_state["sleeping_cache"]).sort_values(
        by=["sleep_start_time"], ascending=False
    )

    col1, col2 = st.columns(2)

    with col1:
        # --- Log Nap ---
        with st.form("nap_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Log Nap</h4>", unsafe_allow_html=True
            )
            nap_date = st.date_input("Nap Date", value=datetime.today())
            nap_start_time = st.time_input("Start Time")
            nap_end_time = st.time_input("End Time")
            nap_location = st.selectbox(
                "Location",
                options=["Pram", "Cot"],
            )
            nap_submit = st.form_submit_button("Log Nap")

        # --- Log Bedtime ---
        with st.form("bedtime_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Log Bedtime</h4>",
                unsafe_allow_html=True,
            )
            bed_date = st.date_input("Date", value=datetime.today())
            bed_time_input = st.time_input("Bedtime")
            settle_mins = st.number_input("Time to Settle (Minutes)", min_value=0)
            bed_location = st.selectbox(
                "Location",
                options=["Pram", "Cot"],
            )
            existing_techniques = list(
                set(
                    x
                    for _, row in sleeping_data.iterrows()
                    for x in (row["settling_techniques"] or [])
                )
            )
            bed_techniques = st.multiselect(
                "Settling Techniques",
                options=list(
                    set(
                        ["Singing", "Bouncing", "Feeding", "Dummy"]
                        + existing_techniques
                    )
                ),
            )
            bedtime_submit = st.form_submit_button("Log Bedtime")

        # --- Log Wake Up ---
        open_sleeps = sleeping_data[pd.isna(sleeping_data["sleep_end_time"])][
            "sleep_start_time"
        ].unique().tolist()
        with st.form("wakeup_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Log Wake Up</h4>",
                unsafe_allow_html=True,
            )
            if open_sleeps:
                selected_sleep = st.selectbox("Select Sleep", options=open_sleeps)
            else:
                st.caption("No open sleeps to wake up from!")
                selected_sleep = None
                st.selectbox("Select Sleep", options=[], disabled=True)
            wakeup_date = st.date_input("Wake Up Date")
            wakeup_time_val = st.time_input("Wake Up Time")
            is_temporary = st.checkbox("Evening / Temporary Wake Up?")
            wakeup_submit = st.form_submit_button("Log Wake Up")

        # --- Delete Sleep ---
        with st.form("delete_form"):
            st.markdown(
                "<h4 style='text-align: center;'>Delete Sleep</h4>",
                unsafe_allow_html=True,
            )
            st.caption("When the nightmares get too real...")
            del_sleep = st.selectbox(
                "Select Sleep", options=sleeping_data["sleep_start_time"].unique()
            )
            delete_submit = st.form_submit_button("Delete Sleep")

    # --- Handle submissions ---
    if nap_submit:
        new_id = 0 if len(sleeping_data) == 0 else int(sleeping_data["sleep_id"].max()) + 1
        new_nap = pd.DataFrame(
            {
                "sleep_id": [new_id],
                "sleep_start_time": [datetime.combine(nap_date, nap_start_time)],
                "sleep_end_time": [datetime.combine(nap_date, nap_end_time)],
                "time_to_settle": [0],
                "sleep_location": [nap_location],
                "settling_techniques": [[]],
                "temporary_wake_up_times": [[]],
                "sleep_type": ["Nap"],
            }
        )
        save_sleeping_data(
            pd.concat([sleeping_data, new_nap]).reset_index(drop=True)
        )

    if bedtime_submit:
        new_id = 0 if len(sleeping_data) == 0 else int(sleeping_data["sleep_id"].max()) + 1
        new_night = pd.DataFrame(
            {
                "sleep_id": [new_id],
                "sleep_start_time": [datetime.combine(bed_date, bed_time_input)],
                "sleep_end_time": [pd.NaT],
                "time_to_settle": [int(settle_mins)],
                "sleep_location": [bed_location],
                "settling_techniques": [bed_techniques],
                "temporary_wake_up_times": [[]],
                "sleep_type": ["Night"],
            }
        )
        save_sleeping_data(
            pd.concat([sleeping_data, new_night]).reset_index(drop=True)
        )

    if wakeup_submit and selected_sleep is not None:
        original = sleeping_data[
            sleeping_data["sleep_start_time"] == selected_sleep
        ].iloc[0]
        wakeup_dt = datetime.combine(wakeup_date, wakeup_time_val)
        sleep_type = original["sleep_type"] if pd.notna(original.get("sleep_type")) else "Night"
        if not is_temporary:
            updated = pd.DataFrame(
                {
                    "sleep_id": [original["sleep_id"]],
                    "sleep_start_time": [original["sleep_start_time"]],
                    "sleep_end_time": [wakeup_dt],
                    "time_to_settle": [original["time_to_settle"]],
                    "sleep_location": [original["sleep_location"]],
                    "settling_techniques": [original["settling_techniques"]],
                    "temporary_wake_up_times": [original["temporary_wake_up_times"]],
                    "sleep_type": [sleep_type],
                }
            )
        else:
            wake_list = [
                pd.to_datetime(x).to_pydatetime()
                for x in list(original["temporary_wake_up_times"] or [])
            ]
            wake_list.append(wakeup_dt)
            updated = pd.DataFrame(
                {
                    "sleep_id": [original["sleep_id"]],
                    "sleep_start_time": [original["sleep_start_time"]],
                    "sleep_end_time": [pd.NaT],
                    "time_to_settle": [original["time_to_settle"]],
                    "sleep_location": [original["sleep_location"]],
                    "settling_techniques": [original["settling_techniques"]],
                    "temporary_wake_up_times": [wake_list],
                    "sleep_type": [sleep_type],
                }
            )
        save_sleeping_data(
            pd.concat(
                [
                    sleeping_data[sleeping_data["sleep_start_time"] != selected_sleep],
                    updated,
                ]
            ).reset_index(drop=True)
        )

    if delete_submit:
        save_sleeping_data(
            sleeping_data[sleeping_data["sleep_start_time"] != del_sleep].reset_index(
                drop=True
            )
        )

    # --- Charts ---
    night_data = sleeping_data[sleeping_data["sleep_type"] == "Night"].copy()
    nap_data = sleeping_data[sleeping_data["sleep_type"] == "Nap"].copy()

    with col2:
        st.pyplot(plot_settle_time_over_time(night_data))
        st.pyplot(plot_total_sleep_by_day(sleeping_data))
        if len(nap_data) > 0:
            st.pyplot(plot_nap_duration_by_day(nap_data))
        st.pyplot(plot_evening_wakeups(night_data))
        st.pyplot(plot_sleep_proportion_by_hour(sleeping_data))

    # --- Data table ---
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
    """Get the sleeping data from BigQuery"""
    client = bq_client()
    df = client.query(f"SELECT * FROM {SLEEPING_TABLE}").to_dataframe()
    # Backward compat: existing records are night sleeps
    if "sleep_type" not in df.columns:
        df["sleep_type"] = "Night"
    else:
        df["sleep_type"] = df["sleep_type"].fillna("Night")
    return df


def save_sleeping_data(sleeping_data: pd.DataFrame):
    """Save the sleeping data"""
    sleeping_data["sleep_start_time"] = pd.to_datetime(
        sleeping_data["sleep_start_time"]
    )
    sleeping_data["sleep_end_time"] = pd.to_datetime(sleeping_data["sleep_end_time"])

    # Fill missing sleep_type
    if "sleep_type" not in sleeping_data.columns:
        sleeping_data["sleep_type"] = "Night"
    else:
        sleeping_data["sleep_type"] = sleeping_data["sleep_type"].fillna("Night")

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
            bigquery.SchemaField("sleep_type", "STRING"),
        ],
    )

    job = bq_client().load_table_from_dataframe(
        sleeping_data, SLEEPING_TABLE, job_config=job_config
    )
    job.result()

    st.success("Sleeping Data Updated!")
    st.session_state["sleeping_cache"] += 1
    st.rerun()


def plot_settle_time_over_time(df: pd.DataFrame) -> plt.Figure:
    """
    Scatter + linear regression of evening settle time over time.
    Forecasts (and annotates) the date when settle time reaches zero.
    """
    df = df.copy()
    df = df[df["time_to_settle"] > 0].dropna(
        subset=["time_to_settle", "sleep_start_time"]
    )
    df["date"] = pd.to_datetime(df["sleep_start_time"]).dt.normalize()
    daily = df.groupby("date")["time_to_settle"].mean().reset_index().sort_values("date")

    fig, ax = plt.subplots(figsize=(8, 5))

    if len(daily) < 2:
        ax.text(
            0.5, 0.5, "Not enough data yet!",
            ha="center", va="center", transform=ax.transAxes, fontsize=14,
        )
        ax.set_title("Evening Settle Time Over Time", fontsize=18)
        return fig

    x_origin = daily["date"].min()
    x_num = np.array([(d - x_origin).days for d in daily["date"]])
    y = daily["time_to_settle"].values

    slope, intercept = np.polyfit(x_num, y, 1)

    # Scatter actual data
    ax.scatter(
        daily["date"], y,
        color=COLOURS.PINK_HEX, edgecolors=COLOURS.BROWN_HEX, zorder=3, s=70,
        label="Actual",
    )

    # Determine end of regression line
    zero_date = None
    if slope < 0:
        days_to_zero = -intercept / slope
        if days_to_zero > x_num[-1]:  # projection is in the future
            zero_date = x_origin + pd.Timedelta(days=int(days_to_zero))

    x_end = zero_date if zero_date is not None else daily["date"].max() + pd.Timedelta(days=7)
    fit_dates = pd.date_range(x_origin, x_end, periods=200)
    fit_x = np.array([(d - x_origin).days for d in fit_dates])
    fit_y = slope * fit_x + intercept

    mask = fit_y >= 0
    style = "--" if zero_date is not None else "-"
    ax.plot(
        fit_dates[mask], fit_y[mask],
        color=COLOURS.BROWN_HEX, linestyle=style, linewidth=2,
        label="Trend" + (" (forecast)" if zero_date is not None else ""),
    )

    if zero_date is not None:
        ax.axvline(zero_date, color="green", linestyle=":", linewidth=1.5, alpha=0.8)
        ax.annotate(
            f"Settles instantly:\n{zero_date.strftime('%d %b %Y')}",
            xy=(zero_date, 0),
            xytext=(
                zero_date - pd.Timedelta(days=max(3, int(days_to_zero * 0.15))),
                max(y) * 0.55,
            ),
            fontsize=9,
            color="green",
            arrowprops=dict(arrowstyle="->", color="green"),
        )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Avg Time to Settle (Mins)", fontsize=13)
    plt.title("Evening Settle Time Over Time", fontsize=18)
    plt.legend()
    plt.tight_layout()
    return fig


def plot_total_sleep_by_day(df: pd.DataFrame) -> plt.Figure:
    """Total sleep duration (hours) per calendar day, all sleep types combined."""
    df = df.copy()
    df["sleep_start_time"] = pd.to_datetime(df["sleep_start_time"])
    df["sleep_end_time"] = pd.to_datetime(df["sleep_end_time"])

    daily_sleep = []
    for _, row in df.iterrows():
        start, end = row["sleep_start_time"], row["sleep_end_time"]
        if pd.isnull(start) or pd.isnull(end):
            continue
        current = start
        while current.date() <= end.date():
            day_end = min(
                end,
                pd.Timestamp.combine(current.date(), pd.Timestamp.max.time()),
            )
            hours = (day_end - current).total_seconds() / 3600
            daily_sleep.append({"date": current.date(), "hours": hours})
            current = pd.Timestamp.combine(
                current.date() + pd.Timedelta(days=1), pd.Timestamp.min.time()
            )

    if not daily_sleep:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No completed sleeps yet!", ha="center", va="center", transform=ax.transAxes, fontsize=14)
        ax.set_title("Total Sleep by Day", fontsize=18)
        return fig

    sleep_by_day = pd.DataFrame(daily_sleep).groupby("date")["hours"].sum()
    rng = sleep_by_day.max() - sleep_by_day.min()
    scaled = (sleep_by_day - sleep_by_day.min()) / rng if rng > 0 else sleep_by_day * 0 + 0.5
    colors = [tuple(x * c + (1 - x) for c in COLOURS.PINK_RGB) for x in scaled]

    fig, ax = plt.subplots(figsize=(8, 5))
    sleep_by_day.plot(kind="bar", ax=ax, color=colors, ec="k")
    plt.ylabel("Total Sleep (hours)", fontsize=13)
    plt.title("Total Sleep by Day", fontsize=18)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig


def plot_nap_duration_by_day(df: pd.DataFrame) -> plt.Figure:
    """Bar chart of total daytime nap hours per day, with nap count on secondary axis."""
    df = df.copy()
    df = df.dropna(subset=["sleep_start_time", "sleep_end_time"])
    df["date"] = pd.to_datetime(df["sleep_start_time"]).dt.date
    df["hours"] = (
        pd.to_datetime(df["sleep_end_time"]) - pd.to_datetime(df["sleep_start_time"])
    ).dt.total_seconds() / 3600

    by_day = (
        df.groupby("date")
        .agg(total_hours=("hours", "sum"), nap_count=("hours", "count"))
        .reset_index()
        .sort_values("date")
    )
    by_day["date"] = pd.to_datetime(by_day["date"])

    rng = by_day["total_hours"].max() - by_day["total_hours"].min()
    scaled = (by_day["total_hours"] - by_day["total_hours"].min()) / rng if rng > 0 else by_day["total_hours"] * 0 + 0.5
    colors = [tuple(x * c + (1 - x) for c in COLOURS.PINK_RGB) for x in scaled]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    x = range(len(by_day))
    ax1.bar(x, by_day["total_hours"], color=colors, edgecolor="k", label="Total nap hours")
    ax1.set_ylabel("Total Nap Hours", fontsize=13)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(
        [d.strftime("%d %b") for d in by_day["date"]], rotation=45, ha="right"
    )

    ax2 = ax1.twinx()
    ax2.plot(
        list(x), by_day["nap_count"],
        color=COLOURS.BROWN_HEX, marker="o", linewidth=2, label="Nap count",
    )
    ax2.set_ylabel("Number of Naps", fontsize=12, color=COLOURS.BROWN_HEX)
    ax2.tick_params(axis="y", labelcolor=COLOURS.BROWN_HEX)
    ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    plt.title("Daytime Naps by Day", fontsize=18)
    plt.tight_layout()
    return fig


def plot_evening_wakeups(df: pd.DataFrame) -> plt.Figure:
    """Bar chart of evening / temporary wake-up count per night."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["sleep_start_time"]).dt.date
    df["wakeup_count"] = df["temporary_wake_up_times"].apply(
        lambda x: len(x) if x else 0
    )

    by_day = (
        df.groupby("date")["wakeup_count"].sum().reset_index().sort_values("date")
    )
    by_day["date"] = pd.to_datetime(by_day["date"])

    rng = by_day["wakeup_count"].max() - by_day["wakeup_count"].min()
    scaled = (by_day["wakeup_count"] - by_day["wakeup_count"].min()) / rng if rng > 0 else by_day["wakeup_count"] * 0 + 0.5
    colors = [tuple(x * c + (1 - x) for c in COLOURS.PINK_RGB) for x in scaled]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(len(by_day)), by_day["wakeup_count"], color=colors, edgecolor="k")
    ax.set_xticks(range(len(by_day)))
    ax.set_xticklabels(
        [d.strftime("%d %b") for d in by_day["date"]], rotation=45, ha="right"
    )
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.ylabel("Evening Wake Ups", fontsize=13)
    plt.title("Evening Wake Ups per Night", fontsize=18)
    plt.tight_layout()
    return fig


def plot_sleep_proportion_by_hour(df: pd.DataFrame) -> plt.Figure:
    """Proportion of time asleep in each hour of the day, averaged across all days."""
    df = df.copy()
    df["sleep_start_time"] = pd.to_datetime(df["sleep_start_time"])
    df["sleep_end_time"] = pd.to_datetime(df["sleep_end_time"])
    df = df.dropna(subset=["sleep_start_time", "sleep_end_time"])

    asleep_minutes = np.zeros(24)
    for _, row in df.iterrows():
        start, end = row["sleep_start_time"], row["sleep_end_time"]
        if end <= start:
            end += pd.Timedelta(days=1)
        current = start.floor("h")
        while current < end:
            next_hour = current + pd.Timedelta(hours=1)
            overlap = (min(end, next_hour) - max(start, current)).total_seconds() / 60.0
            if overlap > 0:
                asleep_minutes[current.hour] += overlap
            current = next_hour

    num_days = df["sleep_start_time"].dt.normalize().nunique()
    proportions = asleep_minutes / max(num_days * 60.0, 1)
    colors = [tuple(x * c + (1 - x) for c in COLOURS.PINK_RGB) for x in proportions]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(24), 100 * proportions, color=colors, edgecolor="k")
    plt.xticks(range(24))
    plt.xlabel("Hour of Day", fontsize=13)
    plt.ylabel("% of Time Asleep", fontsize=13)
    plt.title("Proportion of Time Asleep by Hour", fontsize=18)
    plt.tight_layout()
    return fig


def display_sleeping_data(df: pd.DataFrame):
    """Display the full sleeping data table"""
    cols = [
        "sleep_start_time",
        "sleep_end_time",
        "sleep_type",
        "time_to_settle",
        "sleep_location",
        "temporary_wake_up_times",
        "settling_techniques",
    ]
    df = df[[c for c in cols if c in df.columns]].reset_index(drop=True)
    df["temporary_wake_up_times"] = df["temporary_wake_up_times"].apply(
        lambda lst: [pd.to_datetime(x).strftime("%Y-%m-%d %H:%M") for x in (lst or [])]
    )
    df.index += 1
    df.columns = [
        x.replace("_", " ").title().replace("Time To Settle", "Time To Settle (Mins)")
        for x in df.columns
    ]
    st.dataframe(df)
