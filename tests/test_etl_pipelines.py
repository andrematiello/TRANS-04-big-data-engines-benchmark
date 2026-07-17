from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from src import etl_duckdb
from src import etl_pandas
from src import etl_pandas_chunking
from src import etl_python
from src import etl_python_chunking
from src import etl_python_polars
from src import etl_python_polars_lazy
from src import etl_python_pyarrow
from src.create_station_metrics_mart import create_station_metrics_mart
from src.etl_utils import aggregate_measurements, finalize_stats


def write_fixture(path: Path) -> None:
    path.write_text(
        "station;temperature\n"
        "Alpha;1.00\n"
        "Beta;-2.00\n"
        "Alpha;3.00\n"
        "Malformed row\n"
        "Beta;not-a-number\n",
        encoding="utf-8",
    )


def assert_expected_output(path: Path, parquet: bool = False) -> None:
    frame = pd.read_parquet(path) if parquet else pd.read_csv(path, sep=";")
    assert list(frame.columns) == ["station", "min", "mean", "max"]
    assert frame.to_dict(orient="records") == [
        {"station": "Alpha", "min": 1.0, "mean": 2.0, "max": 3.0},
        {"station": "Beta", "min": -2.0, "mean": -2.0, "max": -2.0},
    ]


def test_shared_aggregator_handles_header_and_invalid_rows(tmp_path: Path) -> None:
    input_path = tmp_path / "weather_stations.csv"
    write_fixture(input_path)

    stats, rows_seen, invalid_rows = aggregate_measurements(input_path)
    assert rows_seen == 6
    assert invalid_rows == 2
    assert finalize_stats(stats) == [
        {"station": "Alpha", "min": 1.0, "mean": 2.0, "max": 3.0},
        {"station": "Beta", "min": -2.0, "mean": -2.0, "max": -2.0},
    ]


@pytest.mark.parametrize(
    ("name", "runner"),
    [
        (
            "python",
            lambda input_path, output_csv, output_parquet, log_path: etl_python.process_temperatures(
                input_path,
                output_csv,
                output_parquet,
                output_csv.parent / "intermediate.csv",
            ),
        ),
        (
            "python_chunking",
            lambda input_path, output_csv, output_parquet, log_path: etl_python_chunking.process_temperatures(
                input_path, 2, output_csv, output_parquet
            ),
        ),
        (
            "pyarrow",
            lambda input_path, output_csv, output_parquet, log_path: etl_python_pyarrow.process_temperatures(
                input_path, output_csv, output_parquet
            ),
        ),
        (
            "pandas",
            lambda input_path, output_csv, output_parquet, log_path: etl_pandas.process_with_pandas(
                input_path, output_csv, output_parquet
            ),
        ),
        (
            "pandas_chunking",
            lambda input_path, output_csv, output_parquet, log_path: etl_pandas_chunking.process_with_pandas_chunked(
                input_path, 2, output_csv, output_parquet
            ),
        ),
        (
            "polars",
            lambda input_path, output_csv, output_parquet, log_path: etl_python_polars.process_with_polars(
                input_path, output_csv, output_parquet
            ),
        ),
        (
            "polars_lazy",
            lambda input_path, output_csv, output_parquet, log_path: etl_python_polars_lazy.process_with_polars_lazy(
                input_path, output_csv, output_parquet
            ),
        ),
        (
            "duckdb",
            lambda input_path, output_csv, output_parquet, log_path: etl_duckdb.process_with_duckdb(
                input_path, output_csv, output_parquet
            ),
        ),
    ],
)
def test_pipeline_implementations(
    name: str,
    runner,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "weather_stations.csv"
    output_csv = tmp_path / f"{name}.csv"
    output_parquet = tmp_path / f"{name}.parquet"
    write_fixture(input_path)

    modules = {
        "python": etl_python,
        "python_chunking": etl_python_chunking,
        "pyarrow": etl_python_pyarrow,
        "pandas": etl_pandas,
        "pandas_chunking": etl_pandas_chunking,
        "polars": etl_python_polars,
        "polars_lazy": etl_python_polars_lazy,
        "duckdb": etl_duckdb,
    }
    modules[name].LOG_PATH = tmp_path / f"{name}.log.csv"

    assert runner(input_path, output_csv, output_parquet, modules[name].LOG_PATH) == 2
    assert_expected_output(output_csv)
    assert_expected_output(output_parquet, parquet=True)


def test_dashboard_mart_has_presentation_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "measurements_duckdb.csv"
    output_path = tmp_path / "station_metrics_mart.csv"
    input_path.write_text(
        "station;min;mean;max\nAlpha;1;2;3\nBeta;-2;-2;-2\n",
        encoding="utf-8",
    )

    assert create_station_metrics_mart(input_path, output_path) == 2
    with output_path.open(encoding="utf-8", newline="") as output_file:
        rows = list(csv.DictReader(output_file, delimiter=";"))
    assert rows[0]["Station"] == "Alpha"
    assert rows[0]["Average Temperature (°C)"] == "2.00"
