"""Shared utilities used by the benchmark implementations.

The challenge intentionally keeps several processing strategies side by side.
This module centralizes the input contract, incremental aggregation, logging,
and deterministic output formatting so that each implementation can focus on
its engine-specific behavior.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "weather_stations.csv"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"


class StationStats(TypedDict):
    """Running aggregate for one weather station."""

    total: float
    count: int
    minimum: float
    maximum: float


class ResultRow(TypedDict):
    """Stable output contract shared by all benchmark implementations."""

    station: str
    min: float
    mean: float
    max: float


def ensure_parent(path: Path) -> Path:
    """Create the parent directory for *path* and return the path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_step(log_path: Path, step: str, status: str) -> None:
    """Append a timestamped status row to a CSV log."""

    ensure_parent(log_path)
    with log_path.open("a", encoding="utf-8", newline="") as log_file:
        csv.writer(log_file).writerow(
            [datetime.now(timezone.utc).isoformat(), step, status]
        )


def iter_measurements(path: Path) -> Iterator[tuple[str, float]]:
    """Yield valid ``(station, temperature)`` pairs from a semicolon CSV.

    The generated challenge file has no header, but accepting an optional
    ``station;temperature`` header makes the readers safer for hand-created
    fixtures and downstream exports. Comment and malformed rows are ignored by
    design; callers can count them separately when needed.
    """

    with path.open("r", encoding="utf-8", newline="") as input_file:
        for row in csv.reader(input_file, delimiter=";"):
            if len(row) != 2:
                continue
            station, temperature_text = (cell.strip() for cell in row)
            if not station or station.startswith("#"):
                continue
            if station.casefold() in {"station", "station_name"} and (
                temperature_text.casefold() in {"temperature", "temp"}
            ):
                continue
            try:
                temperature = float(temperature_text)
            except ValueError:
                continue
            yield station, temperature


def aggregate_measurements(
    path: Path,
    progress_interval: int | None = 50_000_000,
) -> tuple[dict[str, StationStats], int, int]:
    """Aggregate minimum, mean, and maximum values in one streaming pass.

    Returns ``(stats, rows_seen, invalid_rows)``. The implementation retains
    only one small aggregate record per station, so memory usage is independent
    of the number of input rows.
    """

    stats: dict[str, StationStats] = {}
    rows_seen = 0
    invalid_rows = 0

    with path.open("r", encoding="utf-8", newline="") as input_file:
        for row in csv.reader(input_file, delimiter=";"):
            rows_seen += 1
            if len(row) != 2:
                invalid_rows += 1
                continue
            station, temperature_text = (cell.strip() for cell in row)
            if not station or station.startswith("#"):
                invalid_rows += 1
                continue
            if station.casefold() in {"station", "station_name"} and (
                temperature_text.casefold() in {"temperature", "temp"}
            ):
                continue
            try:
                temperature = float(temperature_text)
            except ValueError:
                invalid_rows += 1
                continue

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

            if progress_interval and rows_seen % progress_interval == 0:
                print(f"Processed {rows_seen:,} input rows...")

    return stats, rows_seen, invalid_rows


def finalize_stats(stats: dict[str, StationStats]) -> list[ResultRow]:
    """Return sorted, numerically typed results rounded to two decimals."""

    results: list[ResultRow] = []
    for station in sorted(stats):
        values = stats[station]
        if values["count"] == 0:
            continue
        results.append(
            {
                "station": station,
                "min": round(values["minimum"], 2),
                "mean": round(values["total"] / values["count"], 2),
                "max": round(values["maximum"], 2),
            }
        )
    return results


def write_results_csv(results: Iterable[ResultRow], path: Path) -> None:
    """Write the common result schema to a semicolon-delimited CSV."""

    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        output = csv.writer(output_file, delimiter=";", lineterminator="\n")
        output.writerow(["station", "min", "mean", "max"])
        for row in results:
            output.writerow(
                [
                    row["station"],
                    f"{row['min']:.2f}",
                    f"{row['mean']:.2f}",
                    f"{row['max']:.2f}",
                ]
            )


def read_station_names(model_path: Path) -> list[str]:
    """Read unique station names from the challenge model file."""

    station_names = {
        line.split(";", 1)[0].strip()
        for line in model_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return sorted(name for name in station_names if name)
