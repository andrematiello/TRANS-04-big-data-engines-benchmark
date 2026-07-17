"""Lazy and streaming aggregation using Polars."""

from __future__ import annotations

import time
from pathlib import Path

import polars as pl

try:
    from src.etl_utils import INPUT_PATH, PROJECT_ROOT, log_step as append_log
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility.
    from etl_utils import INPUT_PATH, PROJECT_ROOT, log_step as append_log  # type: ignore[no-redef]

LOG_PATH = PROJECT_ROOT / "logs" / "log_polars_lazy.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_polars_lazy.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def read_and_aggregate_with_polars_lazy(
    path_to_csv: Path = INPUT_PATH,
) -> pl.DataFrame:
    """Build and execute a streaming lazy aggregation plan."""

    plan = (
        pl.scan_csv(
            path_to_csv,
            separator=";",
            has_header=False,
            new_columns=["station", "temperature"],
            comment_prefix="#",
            ignore_errors=True,
        )
        .with_columns(
            pl.col("station").cast(pl.String).str.strip_chars(),
            pl.col("temperature").cast(pl.Float64, strict=False),
        )
        .drop_nulls(["station", "temperature"])
        .filter(pl.col("station") != "")
        .group_by("station")
        .agg(
            pl.col("temperature").min().alias("min"),
            pl.col("temperature").mean().alias("mean"),
            pl.col("temperature").max().alias("max"),
        )
        .sort("station")
        .with_columns(
            pl.col("min").round(2),
            pl.col("mean").round(2),
            pl.col("max").round(2),
        )
    )
    try:
        frame = plan.collect(engine="streaming")
    except TypeError:  # Compatibility with older Polars releases.
        frame = plan.collect(streaming=True)
    log_step("Read and aggregate", f"Success: {frame.height} stations")
    return frame


def save_results(
    frame: pl.DataFrame,
    csv_path: Path = OUTPUT_CSV_PATH,
    parquet_path: Path = OUTPUT_PARQUET_PATH,
) -> None:
    """Write Polars results to CSV and Parquet."""

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_csv(csv_path, separator=";")
    frame.write_parquet(parquet_path)
    log_step("Save results", f"Success: {frame.height} stations")


def process_with_polars_lazy(
    input_path: Path = INPUT_PATH,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Run the lazy Polars pipeline and return station count."""

    start_time = time.perf_counter()
    frame = read_and_aggregate_with_polars_lazy(input_path)
    save_results(frame, output_csv, output_parquet)
    elapsed = time.perf_counter() - start_time
    log_step("Pipeline", f"Completed in {elapsed:.2f} seconds")
    print(
        f"Polars lazy pipeline completed: {frame.height} stations in "
        f"{elapsed:.2f} seconds."
    )
    return frame.height


def main() -> None:
    """Run the lazy Polars implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_with_polars_lazy()


if __name__ == "__main__":
    main()
