"""Build the dashboard-ready station metrics mart from DuckDB output."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from src.etl_utils import PROJECT_ROOT
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility.
    from etl_utils import PROJECT_ROOT  # type: ignore[no-redef]

INPUT_PATH = PROJECT_ROOT / "data" / "measurements_duckdb.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "station_metrics_mart.csv"


def create_station_metrics_mart(
    input_path: Path = INPUT_PATH,
    output_path: Path = OUTPUT_PATH,
) -> int:
    """Create a presentation-friendly CSV and return its station count."""

    frame = pd.read_csv(input_path, sep=";")
    required_columns = {"station", "min", "mean", "max"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"Input is missing required columns: {', '.join(sorted(missing_columns))}"
        )

    for column in ("min", "mean", "max"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    frame = frame.dropna(subset=["station", "min", "mean", "max"])
    frame = frame.sort_values("station")
    mart = frame.rename(
        columns={
            "station": "Station",
            "min": "Min Temperature (°C)",
            "mean": "Average Temperature (°C)",
            "max": "Max Temperature (°C)",
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mart.to_csv(output_path, sep=";", index=False, float_format="%.2f")
    print(f"Station metrics mart written to {output_path}")
    return len(mart)


def main() -> None:
    """Build the mart from the default DuckDB CSV output."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_PATH}. Run the DuckDB pipeline first."
        )
    create_station_metrics_mart()


if __name__ == "__main__":
    main()
