#!/usr/bin/env python
"""Generate synthetic measurements for the One Billion Row Challenge.

The generated file intentionally has no header, matching the original 1BRC
input contract: ``station;temperature`` per line.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

from src.etl_utils import PROJECT_ROOT, read_station_names

MODEL_PATH = PROJECT_ROOT / "data" / "model.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "weather_stations.csv"
DEFAULT_BATCH_SIZE = 10_000
LOWEST_TEMPERATURE = -99.9
HIGHEST_TEMPERATURE = 99.9


def _positive_integer(value: str) -> int:
    """Parse a positive integer while allowing underscore notation."""

    try:
        parsed = int(value.replace("_", ""))
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def check_args(file_args: list[str]) -> int:
    """Validate command-line arguments and return the requested row count."""

    parser = argparse.ArgumentParser(
        description="Generate a semicolon-delimited weather measurements file."
    )
    parser.add_argument(
        "rows",
        type=_positive_integer,
        help="number of records to generate (for example, 1_000_000_000)",
    )
    return parser.parse_args(file_args[1:]).rows


def build_weather_station_name_list(model_path: Path = MODEL_PATH) -> list[str]:
    """Load unique, non-comment station names from the model file."""

    station_names = read_station_names(model_path)
    if not station_names:
        raise ValueError(f"No station names found in {model_path}")
    return station_names


def convert_bytes(num: float) -> str:
    """Convert a byte count to a human-readable binary unit."""

    value = float(num)
    for unit in ("bytes", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:3.1f} {unit}"
        value /= 1024
    return f"{value:3.1f} TiB"


def format_elapsed_time(seconds: float) -> str:
    """Format elapsed seconds for a human-readable CLI message."""

    if seconds < 60:
        return f"{seconds:.3f} seconds"
    minutes, remaining_seconds = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes} minutes {remaining_seconds} seconds"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} hours {minutes} minutes {remaining_seconds} seconds"


def estimate_file_size(
    weather_station_names: list[str], num_rows_to_create: int
) -> str:
    """Estimate the uncompressed size of the generated CSV."""

    if not weather_station_names:
        raise ValueError("At least one weather station is required")
    average_name_bytes = sum(
        len(name.encode("utf-8")) for name in weather_station_names
    ) / len(weather_station_names)
    average_temperature_bytes = 4.400200100050025
    average_line_length = average_name_bytes + average_temperature_bytes + 2
    return (
        "Estimated uncompressed file size: "
        f"{convert_bytes(num_rows_to_create * average_line_length)}."
    )


def build_test_data(
    weather_station_names: list[str],
    num_rows_to_create: int,
    output_path: Path = OUTPUT_PATH,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    """Generate measurements in bounded batches and write them to disk."""

    if num_rows_to_create <= 0:
        raise ValueError("num_rows_to_create must be positive")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if not weather_station_names:
        raise ValueError("At least one weather station is required")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()
    print(f"Generating {num_rows_to_create:,} measurements...")

    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        generated = 0
        next_progress = 0
        while generated < num_rows_to_create:
            current_batch_size = min(batch_size, num_rows_to_create - generated)
            batch = random.choices(weather_station_names, k=current_batch_size)
            output_file.write(
                "\n".join(
                    f"{station};{random.uniform(LOWEST_TEMPERATURE, HIGHEST_TEMPERATURE):.1f}"
                    for station in batch
                )
                + "\n"
            )
            generated += current_batch_size
            progress = generated * 100 // num_rows_to_create
            if progress >= next_progress:
                bars = "=" * (progress // 2)
                sys.stdout.write(f"\r[{bars:<50}] {progress:3d}%")
                sys.stdout.flush()
                next_progress = progress + 1

    sys.stdout.write("\n")
    elapsed = time.perf_counter() - start_time
    print(f"Generated file: {output_path}")
    print(f"Actual file size: {convert_bytes(output_path.stat().st_size)}")
    print(f"Elapsed time: {format_elapsed_time(elapsed)}")


def main(argv: list[str] | None = None) -> None:
    """Run the generator from the command line."""

    arguments = [sys.argv[0], *(argv if argv is not None else sys.argv[1:])]
    row_count = check_args(arguments)
    station_names = build_weather_station_name_list()
    print(estimate_file_size(station_names, row_count))
    build_test_data(station_names, row_count)
    print("Measurement generation complete.")


if __name__ == "__main__":
    main()
