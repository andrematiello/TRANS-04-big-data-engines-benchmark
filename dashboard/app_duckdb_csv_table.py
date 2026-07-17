"""Streamlit dashboard for the station metrics mart."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MART_PATH = PROJECT_ROOT / "data" / "station_metrics_mart.csv"

st.set_page_config(page_title="Weather Station Metrics", layout="wide")
st.title("Weather Station Metrics")
st.caption("Interactive view of the DuckDB-generated station metrics mart.")


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """Load the dashboard mart with a semicolon delimiter."""

    return pd.read_csv(path, sep=";")


if not MART_PATH.exists():
    st.error(
        "The dashboard data is missing. Run the DuckDB pipeline and then "
        "create_station_metrics_mart.py first."
    )
    st.stop()

try:
    data = load_data(MART_PATH)
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Unable to load the dashboard data: {error}")
    st.stop()

if data.empty:
    st.warning("The dashboard data contains no records.")
    st.stop()

station_options = ["All stations", *sorted(data["Station"].dropna().unique())]
selected_station = st.selectbox("Filter by station", station_options)
filtered_data = (
    data
    if selected_station == "All stations"
    else data[data["Station"] == selected_station]
)

minimum = filtered_data["Min Temperature (°C)"].min()
average = filtered_data["Average Temperature (°C)"].mean()
maximum = filtered_data["Max Temperature (°C)"].max()
metric_columns = st.columns(3)
metric_columns[0].metric("Minimum temperature", f"{minimum:.2f} °C")
metric_columns[1].metric("Average temperature", f"{average:.2f} °C")
metric_columns[2].metric("Maximum temperature", f"{maximum:.2f} °C")

st.subheader("Station statistics")
st.dataframe(filtered_data, use_container_width=True, hide_index=True)

st.subheader("Average temperature by station")
st.plotly_chart(
    px.bar(
        filtered_data,
        x="Station",
        y="Average Temperature (°C)",
        labels={"Average Temperature (°C)": "Average temperature (°C)"},
    ),
    use_container_width=True,
)

st.subheader("Minimum temperature by station")
st.plotly_chart(
    px.bar(
        filtered_data,
        x="Station",
        y="Min Temperature (°C)",
        color="Min Temperature (°C)",
        color_continuous_scale="Blues",
        labels={"Min Temperature (°C)": "Minimum temperature (°C)"},
    ),
    use_container_width=True,
)

st.subheader("Maximum temperature by station")
st.plotly_chart(
    px.bar(
        filtered_data,
        x="Station",
        y="Max Temperature (°C)",
        color="Max Temperature (°C)",
        color_continuous_scale="Reds",
        labels={"Max Temperature (°C)": "Maximum temperature (°C)"},
    ),
    use_container_width=True,
)

st.subheader("Minimum versus maximum temperature")
st.plotly_chart(
    px.scatter(
        filtered_data,
        x="Min Temperature (°C)",
        y="Max Temperature (°C)",
        size=filtered_data["Average Temperature (°C)"].abs(),
        hover_name="Station",
        labels={
            "Min Temperature (°C)": "Minimum temperature (°C)",
            "Max Temperature (°C)": "Maximum temperature (°C)",
        },
    ),
    use_container_width=True,
)

st.caption("Data generated locally with the One Billion Row Challenge pipelines.")
