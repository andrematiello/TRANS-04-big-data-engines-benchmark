"""Streaming aggregation with PyArrow output."""

from __future__ import annotations

import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

try:
    from src.etl_utils import (
        INPUT_PATH,
        PROJECT_ROOT,
        ResultRow,
        StationStats,
        aggregate_measurements,
        finalize_stats,
        log_step as append_log,
        write_results_csv,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility.
    from etl_utils import (  # type: ignore[no-redef]
        INPUT_PATH,
        PROJECT_ROOT,
        ResultRow,
        StationStats,
        aggregate_measurements,
        finalize_stats,
        log_step as append_log,
        write_results_csv,
    )

LOG_PATH = PROJECT_ROOT / "logs" / "log_pyarrow.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_pyarrow.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def read_and_aggregate(
    path_to_csv: Path = INPUT_PATH,
) -> tuple[dict[str, StationStats], int, int]:
    """Aggregate input rows with a streaming CSV reader."""

    stats, rows_seen, invalid_rows = aggregate_measurements(path_to_csv)
    log_step(
        "Read and aggregate",
        f"Success: {len(stats)} stations from {rows_seen:,} rows; "
        f"{invalid_rows:,} invalid rows skipped",
    )
    return stats, rows_seen, invalid_rows


def format_results(stats: dict[str, StationStats]) -> list[ResultRow]:
    """Return sorted numeric results rounded to two decimal places."""

    results = finalize_stats(stats)
    log_step("Format results", f"Success: {len(results)} stations")
    return results


def save_results_to_csv(
    results: list[ResultRow],
    path: Path = OUTPUT_CSV_PATH,
) -> None:
    """Write results to the challenge-compatible CSV format."""

    write_results_csv(results, path)
    log_step("Save results (CSV)", "Success")


def save_results_to_parquet(
    results: list[ResultRow],
    path: Path = OUTPUT_PARQUET_PATH,
) -> None:
    """Write numeric result columns to Parquet with PyArrow."""

    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(results), path)
    log_step("Save results (Parquet)", "Success")


def process_temperatures(
    input_path: Path = INPUT_PATH,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Run the PyArrow implementation and return station count."""

    start_time = time.perf_counter()
    stats, _, _ = read_and_aggregate(input_path)
    results = format_results(stats)
    save_results_to_csv(results, output_csv)
    save_results_to_parquet(results, output_parquet)
    elapsed = time.perf_counter() - start_time
    log_step("Pipeline", f"Completed in {elapsed:.2f} seconds")
    print(
        f"PyArrow pipeline completed: {len(results)} stations in "
        f"{elapsed:.2f} seconds."
    )
    return len(results)


def main() -> None:
    """Run the PyArrow implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_temperatures()


if __name__ == "__main__":
    main()
