from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from core.exceptions import DataOperationError
from core.models import DownloadResult, LoadedDataset, TxtConversionArtifacts
from infrastructure.files.raw_txt_converter import convert_file
from services.motion_processing_service import MotionProcessingService


class DataService:
    SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "cp1251", "latin-1")
    CANDIDATE_DELIMITERS = (",", ";", "\t")
    PROCESSED_MARKER_COLUMNS = ("x_coord", "z_coord", "velocity", "vx", "vz")

    def __init__(
            self,
            motion_processing_service: MotionProcessingService | None = None,
    ) -> None:
        self.motion_processing_service = motion_processing_service or MotionProcessingService()

    def load_dataset_from_download(self, download_result: DownloadResult) -> LoadedDataset:
        raw_txt_path = download_result.selected_raw_file

        if raw_txt_path is None:
            raise DataOperationError(
                "После выгрузки не найден TXT-файл с сырыми данными для конвертации."
            )

        output_prefix = raw_txt_path.with_suffix("")

        try:
            (
                metadata_csv_path,
                data_csv_path,
                bad_rows_csv_path,
                metadata,
                _,
            ) = convert_file(
                raw_txt_path,
                output_prefix=output_prefix,
            )

        except Exception as exc:
            raise DataOperationError(
                f"Не удалось сконвертировать TXT-файл после выгрузки: {exc}"
            ) from exc

        rows, columns = self._read_csv_rows_and_columns(data_csv_path)

        if not rows:
            raise DataOperationError(
                "TXT-файл был сконвертирован, но итоговый CSV не содержит строк данных."
            )

        conversion = TxtConversionArtifacts(
            source_txt_path=raw_txt_path,
            metadata_csv_path=metadata_csv_path,
            data_csv_path=data_csv_path,
            bad_rows_csv_path=bad_rows_csv_path,
            metadata=metadata,
        )

        dataset = LoadedDataset(
            source_type="download",
            source_path=data_csv_path,
            rows=rows,
            columns=columns,
            metadata=metadata,
            metadata_csv_path=metadata_csv_path,
            data_csv_path=data_csv_path,
            bad_rows_csv_path=bad_rows_csv_path,
            raw_txt_path=raw_txt_path,
            conversions=[conversion],
        )

        processing_dir = raw_txt_path.parent / f"{raw_txt_path.stem}_motion"
        return self._process_motion_if_needed(dataset, output_dir=processing_dir)

    def import_file(
            self,
            file_path: Path,
            txt_output_dir: Path | None = None,
    ) -> LoadedDataset:
        file_path = Path(file_path)

        if not file_path.exists():
            raise DataOperationError(f"Файл не найден: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            return self.import_csv(file_path)

        if suffix == ".txt":
            return self.import_txt(file_path, output_dir=txt_output_dir)

        raise DataOperationError(
            f"Неподдерживаемый формат файла: {suffix}. "
            "Можно импортировать только CSV или TXT."
        )

    def import_txt(
            self,
            txt_path: Path,
            output_dir: Path | None = None,
    ) -> LoadedDataset:

        txt_path = Path(txt_path)

        if not txt_path.exists():
            raise DataOperationError(f"TXT-файл не найден: {txt_path}")

        if txt_path.suffix.lower() != ".txt":
            raise DataOperationError(
                f"Ожидался TXT-файл, но получен файл: {txt_path.name}"
            )

        try:
            if output_dir is None:
                output_prefix = txt_path.with_suffix("")
            else:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_prefix = output_dir / txt_path.stem

            (
                metadata_csv_path,
                data_csv_path,
                bad_rows_csv_path,
                metadata,
                _,
            ) = convert_file(
                txt_path,
                output_prefix=output_prefix,
            )

        except Exception as exc:
            raise DataOperationError(
                f"Не удалось конвертировать TXT-файл {txt_path.name}: {exc}"
            ) from exc

        rows, columns = self._read_csv_rows_and_columns(data_csv_path)

        if not rows:
            raise DataOperationError(
                f"TXT-файл {txt_path.name} был сконвертирован, "
                "но итоговый CSV не содержит строк данных."
            )

        conversion = TxtConversionArtifacts(
            source_txt_path=txt_path,
            metadata_csv_path=metadata_csv_path,
            data_csv_path=data_csv_path,
            bad_rows_csv_path=bad_rows_csv_path,
            metadata=metadata,
        )

        dataset = LoadedDataset(
            source_type="import_txt",
            source_path=data_csv_path,
            rows=rows,
            columns=columns,
            metadata=metadata,
            metadata_csv_path=metadata_csv_path,
            data_csv_path=data_csv_path,
            bad_rows_csv_path=bad_rows_csv_path,
            raw_txt_path=txt_path,
            conversions=[conversion],
        )

        base_dir = output_dir if output_dir is not None else txt_path.parent / f"{txt_path.stem}_motion"
        return self._process_motion_if_needed(dataset, output_dir=Path(base_dir))

    def import_csv(self, csv_path: Path) -> LoadedDataset:
        rows, columns = self._read_csv_rows_and_columns(csv_path)
        if not rows:
            raise DataOperationError("CSV-файл пустой или не содержит строк данных.")

        dataset = LoadedDataset(
            source_type="import",
            source_path=csv_path,
            rows=rows,
            columns=columns,
            source_raw_csv_path=csv_path,
        )

        processing_dir = csv_path.parent / f"{csv_path.stem}_motion"
        return self._process_motion_if_needed(dataset, output_dir=processing_dir)

    def export_csv(self, dataset: LoadedDataset, target_path: Path) -> None:
        if not dataset.rows:
            raise DataOperationError("Нет данных для экспорта в CSV.")

        target_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = self._resolve_export_columns(dataset)
        normalized_rows = [self._normalize_row_for_export(row, fieldnames) for row in dataset.rows]

        with target_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                delimiter=",",
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(normalized_rows)

    def _process_motion_if_needed(
            self,
            dataset: LoadedDataset,
            output_dir: Path,
    ) -> LoadedDataset:
        if not self._looks_like_raw_motion_csv(dataset.columns):
            return dataset

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        artifacts = self.motion_processing_service.process_raw_csv_file(
            csv_path=dataset.source_path,
            output_dir=output_dir,
            metadata=dataset.metadata,
        )

        processed_rows, processed_columns = self._read_csv_rows_and_columns(
            artifacts.processed_motion_csv_path
        )

        if not processed_rows:
            raise DataOperationError(
                "IMU-обработка завершилась, но итоговый processed_motion.csv оказался пустым."
            )

        return LoadedDataset(
            source_type=dataset.source_type,
            source_path=artifacts.processed_motion_csv_path,
            rows=processed_rows,
            columns=processed_columns,
            metadata=dataset.metadata,
            metadata_csv_path=dataset.metadata_csv_path,
            data_csv_path=dataset.data_csv_path,
            bad_rows_csv_path=dataset.bad_rows_csv_path,
            raw_txt_path=dataset.raw_txt_path,
            source_raw_csv_path=dataset.source_path,
            processing_artifacts=artifacts,
            conversions=dataset.conversions,
        )

    def _looks_like_raw_motion_csv(self, columns: list[str]) -> bool:
        column_set = set(columns)
        required_raw = set(MotionProcessingService.RAW_REQUIRED_COLUMNS)
        if not required_raw.issubset(column_set):
            return False
        if any(marker in column_set for marker in self.PROCESSED_MARKER_COLUMNS):
            return False
        return True

    def _resolve_export_columns(self, dataset: LoadedDataset) -> list[str]:
        ordered_columns: list[str] = []
        seen: set[str] = set()

        for column in dataset.columns:
            normalized = self._normalize_header_name(column)
            if normalized and normalized not in seen:
                ordered_columns.append(normalized)
                seen.add(normalized)

        for row in dataset.rows:
            for key in row.keys():
                normalized = self._normalize_header_name(key)
                if normalized and normalized not in seen:
                    ordered_columns.append(normalized)
                    seen.add(normalized)

        if not ordered_columns:
            raise DataOperationError("Не удалось определить столбцы для экспорта CSV.")

        return ordered_columns

    def _normalize_row_for_export(
            self,
            row: dict[str, Any],
            fieldnames: list[str],
    ) -> dict[str, Any]:
        normalized_source = {
            self._normalize_header_name(key): value
            for key, value in row.items()
            if self._normalize_header_name(key)
        }

        result: dict[str, Any] = {}
        for field in fieldnames:
            value = normalized_source.get(field, "")
            if value is None:
                value = ""
            result[field] = value
        return result

    def _read_csv_rows_and_columns(self, csv_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
        if not csv_path.exists():
            raise DataOperationError(f"Файл не найден: {csv_path}")

        last_error: Exception | None = None

        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                text = csv_path.read_text(encoding=encoding)
                delimiter = self._detect_delimiter(text)

                reader = csv.DictReader(
                    text.splitlines(),
                    delimiter=delimiter,
                )

                if reader.fieldnames is None:
                    raise DataOperationError("CSV-файл не содержит заголовка столбцов.")

                columns = self._normalize_fieldnames(reader.fieldnames)
                rows: list[dict[str, Any]] = []

                for raw_row in reader:
                    normalized_row: dict[str, Any] = {}
                    for original_key, value in raw_row.items():
                        normalized_key = self._normalize_header_name(original_key)
                        if not normalized_key:
                            continue
                        normalized_row[normalized_key] = "" if value is None else value
                    rows.append(normalized_row)

                return rows, columns

            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except Exception as exc:
                last_error = exc
                continue

        if isinstance(last_error, UnicodeDecodeError):
            raise DataOperationError(
                f"Не удалось прочитать CSV ни в одной из поддерживаемых кодировок: {csv_path.name}"
            ) from last_error

        if last_error is not None:
            raise DataOperationError(
                f"Не удалось импортировать CSV-файл {csv_path.name}: {last_error}"
            ) from last_error

        raise DataOperationError(f"Не удалось импортировать CSV-файл {csv_path.name}")

    def _normalize_fieldnames(self, fieldnames: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for field in fieldnames:
            normalized = self._normalize_header_name(field)
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)

        if not result:
            raise DataOperationError("После нормализации не осталось валидных заголовков CSV.")

        return result

    @staticmethod
    def _normalize_header_name(value: Any) -> str:
        if value is None:
            return ""
        return str(value).replace("\ufeff", "").strip()

    def _detect_delimiter(self, text: str) -> str:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            raise DataOperationError("CSV-файл пустой.")

        sample = "\n".join(lines[:5])

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(self.CANDIDATE_DELIMITERS))
            return dialect.delimiter
        except csv.Error:
            header_line = lines[0]
            delimiter_counts = {
                delimiter: header_line.count(delimiter) for delimiter in self.CANDIDATE_DELIMITERS
            }
            best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
            if delimiter_counts[best_delimiter] == 0:
                return ","
            return best_delimiter
