"""Chunked aggregation using pandas with bounded input memory."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

try:
    from src.etl_utils import (
        INPUT_PATH,
        PROJECT_ROOT,
        ResultRow,
        log_step as append_log,
        write_results_csv,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility.
    from etl_utils import (  # type: ignore[no-redef]
        INPUT_PATH,
        PROJECT_ROOT,
        ResultRow,
        log_step as append_log,
        write_results_csv,
    )

OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "measurements_pandas_chunk.csv"
OUTPUT_PARQUET_PATH = OUTPUT_CSV_PATH.with_suffix(".parquet")
LOG_PATH = PROJECT_ROOT / "logs" / "log_pandas_chunk.csv"
CHUNK_SIZE = 100_000_000


def log_step(step: str, status: str) -> None:
    """Append a step to this implementation's log."""

    append_log(LOG_PATH, step, status)


def _aggregate_chunk(
    chunk: pd.DataFrame,
) -> dict[str, dict[str, float | int]]:
    """Aggregate one pandas chunk into mergeable station statistics."""

    chunk = chunk.copy()
    chunk["station"] = chunk["station"].astype("string").str.strip()
    chunk["temperature"] = pd.to_numeric(chunk["temperature"], errors="coerce")
    chunk = chunk.dropna(subset=["station", "temperature"])
    chunk = chunk[chunk["station"] != ""]

    partials: dict[str, dict[str, float | int]] = {}
    grouped = chunk.groupby("station", sort=False)["temperature"]
    for station, values in grouped:
        partials[str(station)] = {
            "total": float(values.sum()),
            "count": int(values.count()),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
        }
    return partials


def _merge_stats(
    target: dict[str, dict[str, float | int]],
    partials: dict[str, dict[str, float | int]],
) -> None:
    """Merge one chunk's aggregates into the global result."""

    for station, values in partials.items():
        if station not in target:
            target[station] = values.copy()
            continue
        current = target[station]
        current["total"] = float(current["total"]) + float(values["total"])
        current["count"] = int(current["count"]) + int(values["count"])
        current["minimum"] = min(float(current["minimum"]), float(values["minimum"]))
        current["maximum"] = max(float(current["maximum"]), float(values["maximum"]))


def load_and_aggregate(
    input_path: Path = INPUT_PATH,
    chunksize: int = CHUNK_SIZE,
) -> list[ResultRow]:
    """Read, merge, and finalize pandas chunks."""

    if chunksize <= 0:
        raise ValueError("chunksize must be positive")
    stats: dict[str, dict[str, float | int]] = {}
    chunks = pd.read_csv(
        input_path,
        sep=";",
        header=None,
        names=["station", "temperature"],
        comment="#",
        dtype={"station": "string"},
        chunksize=chunksize,
        on_bad_lines="skip",
    )
    for chunk in tqdm(chunks, desc="Reading pandas chunks", unit="chunk"):
        _merge_stats(stats, _aggregate_chunk(chunk))

    results: list[ResultRow] = []
    for station in sorted(stats):
        values = stats[station]
        results.append(
            {
                "station": station,
                "min": round(float(values["minimum"]), 2),
                "mean": round(float(values["total"]) / int(values["count"]), 2),
                "max": round(float(values["maximum"]), 2),
            }
        )
    return results


def process_with_pandas_chunked(
    input_path: Path = INPUT_PATH,
    chunksize: int = CHUNK_SIZE,
    output_csv: Path = OUTPUT_CSV_PATH,
    output_parquet: Path = OUTPUT_PARQUET_PATH,
) -> int:
    """Run the chunked pandas pipeline and return station count."""

    start_time = time.perf_counter()
    results = load_and_aggregate(input_path, chunksize)
    write_results_csv(results, output_csv)
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_parquet(output_parquet, index=False)
    elapsed = time.perf_counter() - start_time
    log_step("Pipeline", f"Success: {len(results)} stations in {elapsed:.2f} seconds")
    print(
        f"Pandas chunked pipeline completed: {len(results)} stations in "
        f"{elapsed:.2f} seconds."
    )
    return len(results)


def main() -> None:
    """Run the chunked pandas implementation from the command line."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Generate it first."
        )
    process_with_pandas_chunked()


if __name__ == "__main__":
    main()
