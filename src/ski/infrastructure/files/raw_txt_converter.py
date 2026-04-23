from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

EXPECTED_COLUMNS = [
    "time",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "accel_x",
    "accel_y",
    "accel_z",
    "pressure",
]


def _try_numeric(value: str) -> Any:
    value = value.strip()
    try:
        if re.fullmatch(r"[+-]?\d+", value):
            return int(value)
        return float(value)
    except ValueError:
        return value


def parse_metadata(lines: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for line in lines:
        line = line.strip()
        if not line or line.lower() == "metadata section":
            continue
        if line.lower() == "data section":
            break
        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if key == "gyro_offset_xyz":
            parts = [part for part in re.split(r"[\s,]+", raw_value) if part]
            metadata["gyro_offset_x"] = float(parts[0]) if len(parts) > 0 else None
            metadata["gyro_offset_y"] = float(parts[1]) if len(parts) > 1 else None
            metadata["gyro_offset_z"] = float(parts[2]) if len(parts) > 2 else None
            metadata[key] = raw_value
        else:
            metadata[key] = _try_numeric(raw_value)
    return metadata


def parse_data(lines: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    bad_rows: list[dict[str, Any]] = []
    in_data = False
    header_seen = False
    base_time = None
    prev_time = None

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not in_data:
            if line.lower() == "data section":
                in_data = True
            continue

        if in_data and not header_seen:
            if not line:
                continue
            header = line.split()
            if header != EXPECTED_COLUMNS:
                raise ValueError(
                    f"Неверный заголовок секции данных: {header}. Ожидалось: {EXPECTED_COLUMNS}"
                )
            header_seen = True
            continue

        if not line:
            continue

        parts = line.split()
        if len(parts) != len(EXPECTED_COLUMNS):
            bad_rows.append(
                {
                    "line_number": line_number,
                    "raw_line": raw_line.rstrip("\n"),
                    "reason": f"expected {len(EXPECTED_COLUMNS)} values, got {len(parts)}",
                }
            )
            continue

        try:
            parsed = {column: float(value) for column, value in zip(EXPECTED_COLUMNS, parts)}
            parsed["time"] = int(float(parsed["time"]))
        except ValueError as exc:
            bad_rows.append(
                {
                    "line_number": line_number,
                    "raw_line": raw_line.rstrip("\n"),
                    "reason": f"parse error: {exc}",
                }
            )
            continue

        if base_time is None:
            base_time = parsed["time"]
        parsed["time_rel_ms"] = parsed["time"] - base_time
        parsed["time_rel_s"] = (parsed["time"] - base_time) / 1000.0
        parsed["dt_ms"] = None if prev_time is None else parsed["time"] - prev_time
        prev_time = parsed["time"]
        rows.append(parsed)

    return rows, bad_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def convert_file(input_file: Path, output_prefix: Path | None = None) -> tuple[Path, Path, Path, dict[str, Any], list[dict[str, Any]]]:
    text = input_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    metadata = parse_metadata(lines)
    data_rows, bad_rows = parse_data(lines)

    if output_prefix is None:
        output_prefix = input_file.with_suffix("")

    metadata_path = output_prefix.parent / f"{output_prefix.name}_metadata.csv"
    data_path = output_prefix.parent / f"{output_prefix.name}_data.csv"
    bad_rows_path = output_prefix.parent / f"{output_prefix.name}_bad_rows.csv"

    metadata_rows = [{"key": key, "value": value} for key, value in metadata.items()]
    write_csv(metadata_path, metadata_rows, ["key", "value"])

    data_fieldnames = [
        "time",
        "time_rel_ms",
        "time_rel_s",
        "dt_ms",
        "gyro_x",
        "gyro_y",
        "gyro_z",
        "accel_x",
        "accel_y",
        "accel_z",
        "pressure",
    ]
    write_csv(data_path, data_rows, data_fieldnames)

    bad_fieldnames = ["line_number", "raw_line", "reason"]
    write_csv(bad_rows_path, bad_rows, bad_fieldnames)

    return metadata_path, data_path, bad_rows_path, metadata, data_rows