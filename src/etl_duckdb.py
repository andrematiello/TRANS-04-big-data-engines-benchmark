"""Out-of-core aggregation using DuckDB."""

from __future__ import annotations

import time
from pathlib import Path

import duckdb

try:
    from src.etl_utils import INPUT_PATH, PROJECT_ROOT, log_step as append_log
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility.
    from etl_utils import INPUT_PATH, PROJECT_ROOT, log_step as append_log  # type: ignore[no-redef]

LOG_PATH = PROJECT_ROOT / "logs" / "log_duckdb.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_duckdb.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def _sql_path(path: Path) -> str:
    """Escape a local path for use in a DuckDB SQL string literal."""

    return path.as_posix().replace("'", "''")


def process_with_duckdb(
    input_path: Path = INPUT_PATH,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Aggregate the input with DuckDB and write CSV and Parquet outputs."""

    start_time = time.perf_counter()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    escaped_input = _sql_path(input_path)
    escaped_csv = _sql_path(output_csv)
    escaped_parquet = _sql_path(output_parquet)

    try:
        with duckdb.connect(database=":memory:") as connection:
            connection.execute(f"""
                CREATE TABLE station_metrics AS
                SELECT
                    station,
                    ROUND(MIN(temperature), 2)::DOUBLE AS min,
                    ROUND(AVG(temperature), 2)::DOUBLE AS mean,
                    ROUND(MAX(temperature), 2)::DOUBLE AS max
                FROM read_csv(
                    '{escaped_input}',
                    delim=';',
                    header=false,
                    columns={{'station': 'VARCHAR', 'temperature': 'DOUBLE'}},
                    ignore_errors=true
                )
                GROUP BY station
                ORDER BY station;
                """)
            station_count = connection.execute(
                "SELECT COUNT(*) FROM station_metrics"
            ).fetchone()[0]
            connection.execute(f"""
                COPY station_metrics TO '{escaped_csv}'
                (FORMAT CSV, HEADER TRUE, DELIMITER ';');
                """)
            connection.execute(f"""
                COPY station_metrics TO '{escaped_parquet}'
                (FORMAT PARQUET);
                """)
    except Exception as error:
        log_step("Pipeline", f"Failed: {error}")
        raise

    elapsed = time.perf_counter() - start_time
    log_step(
        "Pipeline",
        f"Success: {station_count} stations in {elapsed:.2f} seconds",
    )
    print(
        f"DuckDB pipeline completed: {station_count} stations in "
        f"{elapsed:.2f} seconds."
    )
    return int(station_count)


def main() -> None:
    """Run the DuckDB implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_with_duckdb()


if __name__ == "__main__":
    main()
