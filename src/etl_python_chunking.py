"""Chunked streaming aggregation using the Python standard library."""

from __future__ import annotations

import csv
import time
from collections.abc import Iterable
from itertools import islice
from pathlib import Path

import pandas as pd
from tqdm import tqdm

try:
    from src.etl_utils import (
        INPUT_PATH,
        PROJECT_ROOT,
        ResultRow,
        StationStats,
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
        finalize_stats,
        log_step as append_log,
        write_results_csv,
    )

LOG_PATH = PROJECT_ROOT / "logs" / "log_python_chunk.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_python_chunk.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")
CHUNK_SIZE = 10_000_000


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def _update_stats(row: list[str], stats: dict[str, StationStats]) -> bool:
    """Update an aggregate dictionary from one CSV row."""

    if len(row) != 2:
        return False
    station, temperature_text = (cell.strip() for cell in row)
    if not station or station.startswith("#"):
        return False
    if station.casefold() in {"station", "station_name"} and (
        temperature_text.casefold() in {"temperature", "temp"}
    ):
        return False
    try:
        temperature = float(temperature_text)
    except ValueError:
        return False

    current = stats.setdefault(
        station,
        {
            "total": 0.0,
            "count": 0,
            "minimum": float("inf"),
            "maximum": float("-inf"),
        },
    )
    current["total"] += temperature
    current["count"] += 1
    current["minimum"] = min(current["minimum"], temperature)
    current["maximum"] = max(current["maximum"], temperature)
    return True


def process_chunk(rows: Iterable[list[str]], stats: dict[str, StationStats]) -> int:
    """Process a bounded batch and return the number of valid rows."""

    return sum(_update_stats(row, stats) for row in rows)


def read_temperatures_in_chunks(
    path_to_csv: Path = INPUT_PATH,
    chunk_size: int = CHUNK_SIZE,
) -> tuple[dict[str, StationStats], int, int]:
    """Read and aggregate the CSV while keeping only one chunk in memory."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    stats: dict[str, StationStats] = {}
    rows_seen = 0
    valid_rows = 0

    with path_to_csv.open("r", encoding="utf-8", newline="") as input_file:
        csv_reader = csv.reader(input_file, delimiter=";")
        with tqdm(desc="Reading chunks", unit="rows") as progress:
            while chunk := list(islice(csv_reader, chunk_size)):
                rows_seen += len(chunk)
                valid_rows += process_chunk(chunk, stats)
                progress.update(len(chunk))

    invalid_rows = rows_seen - valid_rows
    log_step(
        "Chunked aggregation",
        f"Success: {len(stats)} stations from {rows_seen:,} rows; "
        f"{invalid_rows:,} invalid rows skipped",
    )
    return stats, rows_seen, invalid_rows


def format_results(stats: dict[str, StationStats]) -> list[ResultRow]:
    """Sort and round aggregate results using the shared output contract."""

    results = finalize_stats(stats)
    log_step("Format results", f"Success: {len(results)} stations")
    return results


def save_results_to_file(
    results: list[ResultRow],
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> None:
    """Write chunked results as numeric CSV and Parquet columns."""

    write_results_csv(results, output_csv)
    pd.DataFrame(results).to_parquet(output_parquet, index=False)
    log_step("Save results", f"Success: {len(results)} stations")


def process_temperatures(
    path_to_csv: Path = INPUT_PATH,
    chunk_size: int = CHUNK_SIZE,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Run the chunked pipeline and return the number of stations."""

    start_time = time.perf_counter()
    stats, _, _ = read_temperatures_in_chunks(path_to_csv, chunk_size)
    results = format_results(stats)
    save_results_to_file(results, output_csv, output_parquet)
    elapsed = time.perf_counter() - start_time
    log_step("Pipeline", f"Completed in {elapsed:.2f} seconds")
    print(
        f"Python chunked pipeline completed: {len(results)} stations in "
        f"{elapsed:.2f} seconds."
    )
    return len(results)


def main() -> None:
    """Run the chunked implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_temperatures()


if __name__ == "__main__":
    main()
