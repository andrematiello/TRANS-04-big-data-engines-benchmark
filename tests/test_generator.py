from __future__ import annotations

from pathlib import Path

from create_measurements import (
    build_test_data,
    build_weather_station_name_list,
    check_args,
    estimate_file_size,
)


def test_generator_preserves_remainder_rows_and_uses_model(tmp_path: Path) -> None:
    model_path = tmp_path / "model.csv"
    model_path.write_text("# comment\nAlpha;0\nBeta;0\nAlpha;1\n", encoding="utf-8")
    output_path = tmp_path / "weather_stations.csv"

    stations = build_weather_station_name_list(model_path)
    build_test_data(stations, 7, output_path, batch_size=3)

    rows = output_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 7
    assert all(row.split(";", 1)[0] in {"Alpha", "Beta"} for row in rows)
    assert estimate_file_size(stations, 7).startswith(
        "Estimated uncompressed file size:"
    )


def test_generator_accepts_underscore_notation() -> None:
    assert check_args(["create_measurements.py", "1_000"]) == 1_000
