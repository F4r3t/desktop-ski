from __future__ import annotations

from typing import Iterable

import numpy as np

from core.exceptions import DataOperationError
from core.models import LoadedDataset
from core.plot_models import PlotComputationResult


class PlotProcessingService:
    REQUIRED_COLUMNS = (
        "time_rel_s",
        "dt_ms",
        "accel_x",
        "accel_z",
    )

    def prepare_plot_data(self, dataset: LoadedDataset) -> PlotComputationResult:
        self._validate_columns(dataset.columns)

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
        )

    def _validate_columns(self, columns: Iterable[str]) -> None:
        missing = [column for column in self.REQUIRED_COLUMNS if column not in columns]
        if missing:
            raise DataOperationError(
                "Для построения графиков не хватает столбцов: " + ", ".join(missing)
            )

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