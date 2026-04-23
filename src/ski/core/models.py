from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ConnectionInfo:
    port: str
    baudrate: int
    transport: str = "USB"


@dataclass(slots=True)
class DownloadResult:
    local_directory: Path
    downloaded_files: list[Path] = field(default_factory=list)
    selected_raw_file: Path | None = None


@dataclass(slots=True)
class TxtConversionArtifacts:
    source_txt_path: Path
    metadata_csv_path: Path
    data_csv_path: Path
    bad_rows_csv_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessingArtifacts:
    working_directory: Path
    converted_raw_csv_path: Path | None = None
    cleaned_imu_csv_path: Path | None = None
    processed_motion_csv_path: Path | None = None
    processing_summary_json_path: Path | None = None


@dataclass(slots=True)
class LoadedDataset:
    source_type: str
    source_path: Path
    rows: list[dict[str, Any]]
    columns: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    metadata_csv_path: Path | None = None
    data_csv_path: Path | None = None
    bad_rows_csv_path: Path | None = None
    raw_txt_path: Path | None = None
    source_raw_csv_path: Path | None = None
    processing_artifacts: ProcessingArtifacts | None = None
    conversions: list[TxtConversionArtifacts] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def has_data(self) -> bool:
        return bool(self.rows)