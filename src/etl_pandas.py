"""Full-file aggregation using pandas."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

try:
    from src.etl_utils import (
        INPUT_PATH,
        PROJECT_ROOT,
        log_step as append_log,
        write_results_csv,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility.
    from etl_utils import (  # type: ignore[no-redef]
        INPUT_PATH,
        PROJECT_ROOT,
        log_step as append_log,
        write_results_csv,
    )

OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_pandas.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")
LOG_PATH = PROJECT_ROOT / "logs" / "log_pandas.csv"


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def load_measurements(path: Path) -> pd.DataFrame:
    """Load the headerless challenge CSV and discard invalid rows."""

    frame = pd.read_csv(
        path,
        sep=";",
        header=None,
        names=["station", "temperature"],
        comment="#",
        dtype={"station": "string"},
        on_bad_lines="skip",
    )
    frame["station"] = frame["station"].str.strip()
    frame["temperature"] = pd.to_numeric(frame["temperature"], errors="coerce")
    frame = frame.dropna(subset=["station", "temperature"])
    return frame[frame["station"] != ""]


def aggregate(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate sorted, two-decimal statistics per station."""

    result = (
        frame.groupby("station", sort=True, as_index=False)["temperature"]
        .agg(min="min", mean="mean", max="max")
        .round({"min": 2, "mean": 2, "max": 2})
    )
    return result


def process_with_pandas(
    input_path: Path = INPUT_PATH,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Run the pandas pipeline and return the number of stations."""

    start_time = time.perf_counter()
    frame = load_measurements(input_path)
    log_step("Read input", f"Success: {len(frame):,} valid rows")

    results = aggregate(frame)
    output_rows = results.to_dict(orient="records")
    write_results_csv(output_rows, output_csv)  # type: ignore[arg-type]
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    results.to_parquet(output_parquet, index=False)

    elapsed = time.perf_counter() - start_time
    log_step("Pipeline", f"Success: {len(results)} stations in {elapsed:.2f} seconds")
    print(
        f"Pandas pipeline completed: {len(results)} stations in "
        f"{elapsed:.2f} seconds."
    )
    return len(results)


def main() -> None:
    """Run the pandas implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_with_pandas()


if __name__ == "__main__":
    main()
