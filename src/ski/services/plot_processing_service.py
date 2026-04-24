from __future__ import annotations

from typing import Iterable

import numpy as np

from core.exceptions import DataOperationError
from core.models import LoadedDataset
from core.plot_models import PlotComputationResult


class PlotProcessingService:
    RAW_REQUIRED_COLUMNS = (
        "time_rel_s",
        "dt_ms",
        "accel_x",
        "accel_z",
    )

    PROCESSED_REQUIRED_COLUMNS = (
        "time_rel_s",
        "x_coord",
        "z_coord",
    )

    def prepare_plot_data(self, dataset: LoadedDataset) -> PlotComputationResult:
        columns = set(dataset.columns)

        if self._has_processed_columns(columns):
            return self._prepare_from_processed(dataset)

        return self._prepare_from_raw(dataset)

    def _has_processed_columns(self, columns: set[str]) -> bool:
        return all(column in columns for column in self.PROCESSED_REQUIRED_COLUMNS)

    def _prepare_from_processed(self, dataset: LoadedDataset) -> PlotComputationResult:
        time_s = self._column_to_float_array(dataset.rows, "time_rel_s")
        if time_s.size < 2:
            raise DataOperationError("Недостаточно точек для построения графиков.")

        time_s = self._sanitize_time(time_s)
        dt_s = self._build_dt_seconds(dataset.rows, time_s)

        accel_x = self._first_existing_column(
            dataset,
            ("earth_acc_north", "accel_x_cal", "accel_x"),
        )
        accel_z = self._first_existing_column(
            dataset,
            ("earth_acc_up", "accel_z_cal", "accel_z"),
        )

        velocity_x = self._first_existing_column(dataset, ("vx",), fallback=None)
        velocity_y = self._first_existing_column(dataset, ("vy",), fallback=None)
        velocity_z = self._first_existing_column(dataset, ("vz",), fallback=None)
        speed = self._first_existing_column(dataset, ("velocity",), fallback=None)
        coord_x = self._first_existing_column(dataset, ("x_coord",), fallback=None)
        coord_z = self._first_existing_column(dataset, ("z_coord",), fallback=None)

        if velocity_x is None:
            velocity_x = self._integrate_trapezoid(accel_x, dt_s)

        if velocity_z is None:
            velocity_z = self._integrate_trapezoid(accel_z, dt_s)

        if velocity_y is None:
            velocity_y = np.zeros_like(velocity_x, dtype=np.float64)

        if speed is None:
            speed = np.sqrt(velocity_x ** 2 + velocity_y ** 2 + velocity_z ** 2)

        if coord_x is None:
            coord_x = self._integrate_trapezoid(velocity_x, dt_s)

        if coord_z is None:
            coord_z = self._integrate_trapezoid(velocity_z, dt_s)

        trajectory_color_speed = speed.copy()

        return PlotComputationResult(
            time_s=time_s,
            accel_x_ms2=accel_x,
            accel_z_ms2=accel_z,
            velocity_x_ms=velocity_x,
            velocity_z_ms=velocity_z,
            speed_ms=speed,
            coord_x_m=coord_x,
            coord_z_m=coord_z,
            dt_s=dt_s,
            baseline_window=0,
            trajectory_color_speed_ms=trajectory_color_speed,
        )

    def _prepare_from_raw(self, dataset: LoadedDataset) -> PlotComputationResult:
        self._validate_columns(dataset.columns, self.RAW_REQUIRED_COLUMNS)

        time_s = self._column_to_float_array(dataset.rows, "time_rel_s")
        if time_s.size < 2:
            raise DataOperationError("Недостаточно точек для построения графиков.")

        time_s = self._sanitize_time(time_s)
        dt_s = self._build_dt_seconds(dataset.rows, time_s)

        accel_x_raw = self._column_to_float_array(dataset.rows, "accel_x")
        accel_z_raw = self._column_to_float_array(dataset.rows, "accel_z")

        baseline_window = min(max(len(time_s) // 10, 10), 50)
        accel_x = accel_x_raw - np.mean(accel_x_raw[:baseline_window])
        accel_z = accel_z_raw - np.mean(accel_z_raw[:baseline_window])

        accel_x = self._smooth(accel_x, window=5)
        accel_z = self._smooth(accel_z, window=5)

        velocity_x = self._integrate_trapezoid(accel_x, dt_s)
        velocity_z = self._integrate_trapezoid(accel_z, dt_s)
        speed = np.sqrt(velocity_x ** 2 + velocity_z ** 2)

        coord_x = self._integrate_trapezoid(velocity_x, dt_s)
        coord_z = self._integrate_trapezoid(velocity_z, dt_s)

        # Для raw-режима vy отсутствует, поэтому безопасный fallback:
        # используем текущий 2D-модуль по доступным осям.
        trajectory_color_speed = np.sqrt(velocity_x ** 2 + velocity_z ** 2)

        return PlotComputationResult(
            time_s=time_s,
            accel_x_ms2=accel_x,
            accel_z_ms2=accel_z,
            velocity_x_ms=velocity_x,
            velocity_z_ms=velocity_z,
            speed_ms=speed,
            coord_x_m=coord_x,
            coord_z_m=coord_z,
            dt_s=dt_s,
            baseline_window=baseline_window,
            trajectory_color_speed_ms=trajectory_color_speed,
        )

    def _validate_columns(self, columns: Iterable[str], required: Iterable[str]) -> None:
        missing = [column for column in required if column not in columns]
        if missing:
            raise DataOperationError(
                "Для построения графиков не хватает столбцов: " + ", ".join(missing)
            )

    def _first_existing_column(
            self,
            dataset: LoadedDataset,
            candidates: tuple[str, ...],
            fallback: np.ndarray | None = None,
    ) -> np.ndarray | None:
        for column in candidates:
            if column in dataset.columns:
                return self._column_to_float_array(dataset.rows, column)
        return fallback

    @staticmethod
    def _column_to_float_array(rows: list[dict[str, object]], column: str) -> np.ndarray:
        values: list[float] = []
        for index, row in enumerate(rows, start=1):
            raw_value = row.get(column)
            try:
                values.append(float(raw_value))
            except (TypeError, ValueError) as exc:
                raise DataOperationError(
                    f"Не удалось преобразовать значение столбца '{column}' в строке {index}: {raw_value}"
                ) from exc
        return np.asarray(values, dtype=np.float64)

    @staticmethod
    def _sanitize_time(time_s: np.ndarray) -> np.ndarray:
        sanitized = np.asarray(time_s, dtype=np.float64).copy()
        sanitized[0] = 0.0
        for index in range(1, len(sanitized)):
            if not np.isfinite(sanitized[index]) or sanitized[index] <= sanitized[index - 1]:
                sanitized[index] = sanitized[index - 1] + 1e-3
        return sanitized

    def _build_dt_seconds(
            self,
            rows: list[dict[str, object]],
            time_s: np.ndarray,
    ) -> np.ndarray:
        dt_ms: list[float] = []
        has_real_dt = False

        for row in rows:
            raw_value = row.get("dt_ms")
            try:
                value = float(raw_value)
                if np.isfinite(value) and value > 0:
                    has_real_dt = True
                    dt_ms.append(value)
                else:
                    dt_ms.append(np.nan)
            except (TypeError, ValueError):
                dt_ms.append(np.nan)

        if not has_real_dt:
            dt_s = np.diff(time_s, prepend=time_s[0])
        else:
            dt_s = np.asarray(dt_ms, dtype=np.float64) / 1000.0
            if len(dt_s) > 1:
                valid = dt_s[np.isfinite(dt_s) & (dt_s > 0)]
                fallback = float(np.median(valid)) if valid.size else 1e-2
                dt_s[0] = fallback
                invalid_mask = ~np.isfinite(dt_s) | (dt_s <= 0)
                dt_s[invalid_mask] = fallback
            else:
                dt_s[:] = 1e-2

        dt_s = np.asarray(dt_s, dtype=np.float64)
        dt_s[0] = dt_s[1] if len(dt_s) > 1 else 1e-2
        return dt_s

    @staticmethod
    def _smooth(values: np.ndarray, window: int = 5) -> np.ndarray:
        if window <= 1 or values.size < window:
            return values.copy()
        kernel = np.ones(window, dtype=np.float64) / float(window)
        return np.convolve(values, kernel, mode="same")

    @staticmethod
    def _integrate_trapezoid(values: np.ndarray, dt_s: np.ndarray) -> np.ndarray:
        result = np.zeros_like(values, dtype=np.float64)
        for index in range(1, len(values)):
            result[index] = (
                    result[index - 1]
                    + 0.5 * (values[index] + values[index - 1]) * dt_s[index]
            )
        return result