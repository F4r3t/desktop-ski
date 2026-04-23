from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from core.exceptions import DataOperationError
from core.models import DownloadResult, LoadedDataset
from infrastructure.files.raw_txt_converter import convert_file


class DataService:
    def load_dataset_from_download(self, download_result: DownloadResult) -> LoadedDataset:
        raw_txt_path = download_result.selected_raw_file
        if raw_txt_path is None:
            raise DataOperationError(
                "После выгрузки не найден TXT-файл с сырыми данными для конвертации."
            )

        output_prefix = raw_txt_path.with_suffix("")
        metadata_csv_path, data_csv_path, bad_rows_csv_path, metadata, data_rows = convert_file(
            raw_txt_path,
            output_prefix=output_prefix,
        )

        rows = self._read_csv_rows(data_csv_path)
        columns = list(rows[0].keys()) if rows else []

        return LoadedDataset(
            source_type="download",
            source_path=data_csv_path,
            rows=rows,
            columns=columns,
            metadata=metadata,
            metadata_csv_path=metadata_csv_path,
            data_csv_path=data_csv_path,
            bad_rows_csv_path=bad_rows_csv_path,
            raw_txt_path=raw_txt_path,
        )

    def import_csv(self, csv_path: Path) -> LoadedDataset:
        rows = self._read_csv_rows(csv_path)
        if not rows:
            raise DataOperationError("CSV-файл пустой или не содержит строк данных.")

        return LoadedDataset(
            source_type="import",
            source_path=csv_path,
            rows=rows,
            columns=list(rows[0].keys()),
        )

    def export_csv(self, dataset: LoadedDataset, target_path: Path) -> None:
        if not dataset.rows:
            raise DataOperationError("Нет данных для экспорта в CSV.")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=dataset.columns)
            writer.writeheader()
            writer.writerows(dataset.rows)

    def _read_csv_rows(self, csv_path: Path) -> list[dict[str, Any]]:
        if not csv_path.exists():
            raise DataOperationError(f"Файл не найден: {csv_path}")

        try:
            with csv_path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None:
                    raise DataOperationError("CSV-файл не содержит заголовка столбцов.")
                return [dict(row) for row in reader]
        except UnicodeDecodeError as exc:
            raise DataOperationError(
                f"Не удалось прочитать CSV как UTF-8: {csv_path.name}"
            ) from exc