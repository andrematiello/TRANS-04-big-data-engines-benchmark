"""Two-pass streaming aggregation using the Python standard library."""

from __future__ import annotations

import csv
import time
from pathlib import Path

import pandas as pd

try:  # Supports both ``python -m src.etl_python`` and direct script execution.
    from src.etl_utils import (
        INPUT_PATH,
        PROJECT_ROOT,
        aggregate_measurements,
        finalize_stats,
        log_step as append_log,
        write_results_csv,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by direct CLI use.
    from etl_utils import (  # type: ignore[no-redef]
        INPUT_PATH,
        PROJECT_ROOT,
        aggregate_measurements,
        finalize_stats,
        log_step as append_log,
        write_results_csv,
    )

INTERMEDIATE_PATH = PROJECT_ROOT / "data" / "intermediate_stats.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_python.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")
LOG_PATH = PROJECT_ROOT / "logs" / "log_python.csv"


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def first_pass_aggregate(
    path_to_csv: Path = INPUT_PATH,
    intermediate_path: Path = INTERMEDIATE_PATH,
) -> int:
    """Aggregate input rows and persist compact intermediate statistics."""

    stats, rows_seen, invalid_rows = aggregate_measurements(path_to_csv)
    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
    with intermediate_path.open("w", encoding="utf-8", newline="") as output_file:
        output = csv.writer(output_file, delimiter=";", lineterminator="\n")
        output.writerow(["station", "total", "count", "min", "max"])
        for station in sorted(stats):
            values = stats[station]
            output.writerow(
                [
                    station,
                    values["total"],
                    values["count"],
                    values["minimum"],
                    values["maximum"],
                ]
            )
    log_step(
        "First-pass aggregation",
        f"Success: {len(stats)} stations from {rows_seen:,} rows; "
        f"{invalid_rows:,} invalid rows skipped",
    )
    return len(stats)


def second_pass_compute(
    intermediate_path: Path = INTERMEDIATE_PATH,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Compute means from intermediate totals and write both output formats."""

    stats = {}
    with intermediate_path.open("r", encoding="utf-8", newline="") as input_file:
        for row in csv.DictReader(input_file, delimiter=";"):
            stats[row["station"]] = {
                "total": float(row["total"]),
                "count": int(row["count"]),
                "minimum": float(row["min"]),
                "maximum": float(row["max"]),
            }

    results = finalize_stats(stats)
    write_results_csv(results, output_csv)
    pd.DataFrame(results).to_parquet(output_parquet, index=False)
    log_step("Second-pass output", f"Success: {len(results)} stations written")
    return len(results)


def process_temperatures(
    path_to_csv: Path = INPUT_PATH,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
    intermediate_path: Path = INTERMEDIATE_PATH,
) -> int:
    """Run the complete two-pass pipeline and return station count."""

    start_time = time.perf_counter()
    first_pass_aggregate(path_to_csv, intermediate_path)
    station_count = second_pass_compute(intermediate_path, output_csv, output_parquet)
    elapsed = time.perf_counter() - start_time
    log_step("Pipeline", f"Completed in {elapsed:.2f} seconds")
    print(
        f"Python two-pass pipeline completed: {station_count} stations in "
        f"{elapsed:.2f} seconds."
    )
    return station_count


def main() -> None:
    """Run the standard-library implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_temperatures()


if __name__ == "__main__":
    main()
