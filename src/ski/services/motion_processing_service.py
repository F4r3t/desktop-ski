from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from core.exceptions import DataOperationError
from core.models import ProcessingArtifacts

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import imufusion
except Exception:
    imufusion = None

try:
    from scipy.signal import butter, filtfilt
except Exception:
    butter = None
    filtfilt = None


G = 9.80665


class MotionProcessingService:
    DEFAULT_ACCEL_BIAS = (
        -0.0012499999999997513,
        0.011334166666666867,
        0.6161884306667309,
    )
    DEFAULT_ACCEL_SCALE = (
        -0.9974396913695297,
        -1.003306192808871,
        -0.9879855738397164,
    )

    RAW_REQUIRED_COLUMNS = (
        "time",
        "gyro_x",
        "gyro_y",
        "gyro_z",
        "accel_x",
        "accel_y",
        "accel_z",
        "pressure",
    )
    RAW_REQUIRED_COLUMNS_LIST = list(RAW_REQUIRED_COLUMNS)

    def __init__(
            self,
            accel_bias: Iterable[float] | None = None,
            accel_scale: Iterable[float] | None = None,
    ):
        self.accel_bias = np.asarray(
            list(accel_bias or self.DEFAULT_ACCEL_BIAS),
            dtype=float,
        )
        self.accel_scale = np.asarray(
            list(accel_scale or self.DEFAULT_ACCEL_SCALE),
            dtype=float,
        )

    def process_raw_csv_file(
            self,
            csv_path: Path,
            output_dir: Path,
            metadata: dict[str, Any] | None = None,
    ) -> ProcessingArtifacts:
        self._ensure_dependencies()

        csv_path = Path(csv_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.read_csv(csv_path)
        df = self._normalize_raw_dataframe(df)

        raw_csv_path = output_dir / "converted_raw.csv"
        cleaned_csv_path = output_dir / "cleaned_imu.csv"
        processed_csv_path = output_dir / "processed_motion.csv"
        summary_json_path = output_dir / "processing_summary.json"

        df.to_csv(raw_csv_path, index=False)

        accel_cal = self._calibrate_accelerometer(df)
        earth_acc, quat_wxyz, euler_deg, gyro_deg_corr = self._estimate_earth_acceleration(
            df=df,
            accel_cal_mps2=accel_cal,
        )

        stationary = self._detect_stationary(
            earth_acc_ned_mps2=earth_acc,
            gyro_deg_s=gyro_deg_corr,
            dt_s=df["dt_s"].to_numpy(dtype=float),
        )

        vel_ned, pos_ned = self._integrate_with_zupt(
            earth_acc_ned_mps2=earth_acc,
            dt_s=df["dt_s"].to_numpy(dtype=float),
            stationary=stationary,
        )

        pos_ned, vel_ned = self._stabilize_vertical_channel(
            pos_ned_m=pos_ned,
            vel_ned_mps=vel_ned,
            pressure_pa=df["pressure"].to_numpy(dtype=float),
            dt_s=df["dt_s"].to_numpy(dtype=float),
            stationary=stationary,
        )

        cleaned_df = df.copy()
        cleaned_df[["accel_x_cal", "accel_y_cal", "accel_z_cal"]] = accel_cal
        cleaned_df[["gyro_x_deg_s_corr", "gyro_y_deg_s_corr", "gyro_z_deg_s_corr"]] = gyro_deg_corr
        cleaned_df[["earth_acc_north", "earth_acc_east", "earth_acc_down"]] = earth_acc
        cleaned_df["stationary"] = stationary.astype(int)
        cleaned_df.to_csv(cleaned_csv_path, index=False)

        result_df = self._build_output_dataframe(
            df=df,
            accel_cal_mps2=accel_cal,
            earth_acc_ned_mps2=earth_acc,
            quat_wxyz=quat_wxyz,
            euler_deg=euler_deg,
            stationary=stationary,
            vel_ned_mps=vel_ned,
            pos_ned_m=pos_ned,
        )
        result_df.to_csv(processed_csv_path, index=False)

        summary = {
            "input_csv": str(csv_path),
            "rows": int(len(df)),
            "median_dt_s": float(df["dt_s"].median()),
            "duration_s": float(df["time_rel_s"].iloc[-1]),
            "raw_csv": str(raw_csv_path),
            "cleaned_csv": str(cleaned_csv_path),
            "result_csv": str(processed_csv_path),
            "max_speed_mps": float(result_df["velocity"].max()),
            "final_x_m": float(result_df["x_coord"].iloc[-1]),
            "final_y_m": float(result_df["y_coord"].iloc[-1]),
            "final_z_m": float(result_df["z_coord"].iloc[-1]),
            "stationary_fraction": float(result_df["stationary"].mean()),
            "metadata": metadata or {},
        }

        with summary_json_path.open("w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2, ensure_ascii=False)

        return ProcessingArtifacts(
            working_directory=output_dir,
            converted_raw_csv_path=raw_csv_path,
            cleaned_imu_csv_path=cleaned_csv_path,
            processed_motion_csv_path=processed_csv_path,
            processing_summary_json_path=summary_json_path,
        )

    def _ensure_dependencies(self) -> None:
        missing: list[str] = []
        if pd is None:
            missing.append("pandas")
        if imufusion is None:
            missing.append("imufusion")
        if butter is None or filtfilt is None:
            missing.append("scipy")

        if missing:
            raise DataOperationError(
                "Для IMU-обработки не хватает зависимостей: "
                + ", ".join(missing)
                + ". Установите их через requirements."
            )

    def _normalize_raw_dataframe(self, df):
        missing = [column for column in self.RAW_REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            raise DataOperationError(
                "CSV не содержит обязательных столбцов для IMU-обработки: "
                + ", ".join(missing)
            )

        df = df.copy()

        for column in self.RAW_REQUIRED_COLUMNS:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        if df[self.RAW_REQUIRED_COLUMNS_LIST].isnull().any().any():
            raise DataOperationError(
                "CSV содержит пустые или нечисловые значения в обязательных IMU-столбцах."
            )

        if "time_rel_ms" not in df.columns:
            df["time_rel_ms"] = df["time"] - df["time"].iloc[0]

        if "time_rel_s" not in df.columns:
            df["time_rel_s"] = df["time_rel_ms"] / 1000.0

        if "dt_ms" in df.columns:
            dt_ms = pd.to_numeric(df["dt_ms"], errors="coerce")
        else:
            dt_ms = None

        if dt_ms is None or dt_ms.isnull().all():
            dt_s = df["time_rel_s"].diff()
        else:
            dt_s = dt_ms / 1000.0

        if len(dt_s) > 1:
            valid = dt_s[(~dt_s.isnull()) & (dt_s > 0)]
            fallback = float(valid.median()) if len(valid) else 0.01
        else:
            fallback = 0.01

        dt_s = dt_s.fillna(fallback)
        dt_s = dt_s.clip(lower=1e-4)

        df["dt_s"] = dt_s
        df["dt_ms"] = df["dt_s"] * 1000.0

        return df

    def _lowpass_zero_phase(self, data: np.ndarray, fs_hz: float, cutoff_hz: float, order: int = 4) -> np.ndarray:
        if data.size == 0:
            return np.asarray(data, dtype=float)

        if cutoff_hz <= 0 or cutoff_hz >= fs_hz / 2:
            return np.asarray(data, dtype=float).copy()

        if len(data) < max(8, order * 3 + 1):
            return np.asarray(data, dtype=float).copy()

        b, a = butter(order, cutoff_hz / (fs_hz / 2.0), btype="low")
        return filtfilt(b, a, np.asarray(data, dtype=float), axis=0)

    @staticmethod
    def _pressure_to_relative_altitude_up(pressure_pa: np.ndarray) -> np.ndarray:
        pressure_pa = np.asarray(pressure_pa, dtype=float)
        p0 = float(pressure_pa[0])
        altitude = 44330.0 * (1.0 - np.power(pressure_pa / p0, 0.190263))
        return altitude - altitude[0]

    @staticmethod
    def _smooth_boolean_mask(mask: np.ndarray, min_true_samples: int, max_false_gap: int) -> np.ndarray:
        mask = np.asarray(mask, dtype=bool).copy()

        def runs(arr: np.ndarray):
            start = 0
            while start < len(arr):
                end = start
                while end < len(arr) and arr[end] == arr[start]:
                    end += 1
                yield start, end, bool(arr[start])
                start = end

        for start, end, value in list(runs(mask)):
            if value and (end - start) < min_true_samples:
                mask[start:end] = False

        changed = True
        while changed:
            changed = False
            runs_list = list(runs(mask))
            for index, (start, end, value) in enumerate(runs_list):
                if value:
                    continue
                gap = end - start
                prev_true = index > 0 and runs_list[index - 1][2]
                next_true = index < len(runs_list) - 1 and runs_list[index + 1][2]
                if prev_true and next_true and gap <= max_false_gap:
                    mask[start:end] = True
                    changed = True

        return mask

    def _calibrate_accelerometer(self, df) -> np.ndarray:
        raw = df[["accel_x", "accel_y", "accel_z"]].to_numpy(dtype=float)
        return (raw - self.accel_bias) * self.accel_scale

    def _estimate_earth_acceleration(
            self,
            df,
            accel_cal_mps2: np.ndarray,
    ):
        dt = df["dt_s"].to_numpy(dtype=float)
        sample_rate_hz = float(1.0 / np.median(dt))

        gyro_rad_s = df[["gyro_x", "gyro_y", "gyro_z"]].to_numpy(dtype=float)
        gyro_deg_s = np.rad2deg(gyro_rad_s)
        accel_g = accel_cal_mps2 / G

        offset = imufusion.Offset(int(round(sample_rate_hz)))
        ahrs = imufusion.Ahrs()
        ahrs.settings = imufusion.Settings(
            imufusion.CONVENTION_NED,
            0.5,
            250.0,
            10.0,
            0.0,
            int(round(5.0 * sample_rate_hz)),
        )

        earth_acc = np.zeros_like(accel_cal_mps2)
        quaternions = np.zeros((len(df), 4), dtype=float)
        euler_deg = np.zeros((len(df), 3), dtype=float)
        gyro_corr = np.zeros_like(gyro_deg_s)

        for index in range(len(df)):
            gyro_corr[index] = offset.update(gyro_deg_s[index])
            ahrs.update_no_magnetometer(gyro_corr[index], accel_g[index], float(dt[index]))
            earth_acc[index] = np.asarray(ahrs.earth_acceleration, dtype=float) * G

            quat = ahrs.quaternion
            quaternions[index] = np.array([quat.w, quat.x, quat.y, quat.z], dtype=float)
            euler_deg[index] = np.asarray(quat.to_euler(), dtype=float)

        earth_acc = self._lowpass_zero_phase(
            earth_acc,
            fs_hz=sample_rate_hz,
            cutoff_hz=6.0,
            order=4,
        )
        return earth_acc, quaternions, euler_deg, gyro_corr

    def _detect_stationary(
            self,
            earth_acc_ned_mps2: np.ndarray,
            gyro_deg_s: np.ndarray,
            dt_s: np.ndarray,
    ) -> np.ndarray:
        gyro_norm = np.linalg.norm(gyro_deg_s, axis=1)
        earth_norm = np.linalg.norm(earth_acc_ned_mps2, axis=1)

        raw_stationary = (gyro_norm < 1.2) & (earth_norm < 0.35)

        sample_rate_hz = float(1.0 / np.median(dt_s))
        min_true_samples = max(3, int(round(0.08 * sample_rate_hz)))
        max_false_gap = max(2, int(round(0.08 * sample_rate_hz)))

        stationary = self._smooth_boolean_mask(raw_stationary, min_true_samples, max_false_gap)

        tail_samples = max(5, int(round(sample_rate_hz * 1.0)))
        stationary[-tail_samples:] = True
        return stationary

    def _integrate_with_zupt(
            self,
            earth_acc_ned_mps2: np.ndarray,
            dt_s: np.ndarray,
            stationary: np.ndarray,
    ):
        n = len(dt_s)
        vel = np.zeros((n, 3), dtype=float)

        for index in range(1, n):
            vel[index] = (
                    vel[index - 1]
                    + 0.5 * (earth_acc_ned_mps2[index - 1] + earth_acc_ned_mps2[index]) * dt_s[index]
            )
            if stationary[index]:
                vel[index] = 0.0

        time_rel = np.cumsum(dt_s) - dt_s[0]
        vel_corr = vel.copy()

        index = 0
        while index < n:
            if stationary[index]:
                index += 1
                continue

            start = index
            while index < n and not stationary[index]:
                index += 1
            end = index - 1

            left_anchor = start - 1
            right_anchor = index if index < n else None

            v_left = vel[left_anchor] if left_anchor >= 0 else np.zeros(3, dtype=float)
            v_right = vel[right_anchor] if right_anchor is not None else np.zeros(3, dtype=float)

            t0 = time_rel[start]
            t1 = time_rel[end]
            duration = max(t1 - t0, dt_s[start])

            segment_indices = np.arange(start, end + 1)
            alpha = (time_rel[segment_indices] - t0) / duration
            drift = (1.0 - alpha[:, None]) * v_left[None, :] + alpha[:, None] * v_right[None, :]
            vel_corr[segment_indices] = vel_corr[segment_indices] - drift

        vel_corr[stationary] = 0.0

        pos = np.zeros((n, 3), dtype=float)
        for index in range(1, n):
            pos[index] = pos[index - 1] + 0.5 * (vel_corr[index - 1] + vel_corr[index]) * dt_s[index]

        return vel_corr, pos

    def _stabilize_vertical_channel(
            self,
            pos_ned_m: np.ndarray,
            vel_ned_mps: np.ndarray,
            pressure_pa: np.ndarray,
            dt_s: np.ndarray,
            stationary: np.ndarray,
    ):
        sample_rate_hz = float(1.0 / np.median(dt_s))

        alt_up = self._pressure_to_relative_altitude_up(pressure_pa)
        alt_up_lp = self._lowpass_zero_phase(
            alt_up,
            fs_hz=sample_rate_hz,
            cutoff_hz=1.0,
            order=2,
        )

        baro_down = -alt_up_lp

        pos_out = pos_ned_m.copy()
        vel_out = vel_ned_mps.copy()

        alpha = 0.25
        pos_out[:, 2] = (1.0 - alpha) * pos_out[:, 2] + alpha * baro_down

        time_s = np.cumsum(dt_s) - dt_s[0]
        vertical_vel_from_baro_down = np.gradient(baro_down, time_s)
        vel_out[:, 2] = (1.0 - alpha) * vel_out[:, 2] + alpha * vertical_vel_from_baro_down

        vel_out[stationary] = 0.0
        vel_out[0] = 0.0

        pos_out = pos_out - pos_out[0]
        return pos_out, vel_out

    @staticmethod
    def _build_output_dataframe(
            df,
            accel_cal_mps2: np.ndarray,
            earth_acc_ned_mps2: np.ndarray,
            quat_wxyz: np.ndarray,
            euler_deg: np.ndarray,
            stationary: np.ndarray,
            vel_ned_mps: np.ndarray,
            pos_ned_m: np.ndarray,
    ):
        return pd.DataFrame(
            {
                "time": df["time"].to_numpy(),
                "time_rel_ms": df["time_rel_ms"].to_numpy(),
                "time_rel_s": df["time_rel_s"].to_numpy(),
                "dt_ms": df["dt_ms"].to_numpy(),
                "accel_x_cal": accel_cal_mps2[:, 0],
                "accel_y_cal": accel_cal_mps2[:, 1],
                "accel_z_cal": accel_cal_mps2[:, 2],
                "earth_acc_north": earth_acc_ned_mps2[:, 0],
                "earth_acc_east": earth_acc_ned_mps2[:, 1],
                "earth_acc_up": -earth_acc_ned_mps2[:, 2],
                "roll_deg": euler_deg[:, 0],
                "pitch_deg": euler_deg[:, 1],
                "yaw_deg": euler_deg[:, 2],
                "quat_w": quat_wxyz[:, 0],
                "quat_x": quat_wxyz[:, 1],
                "quat_y": quat_wxyz[:, 2],
                "quat_z": quat_wxyz[:, 3],
                "stationary": stationary.astype(int),
                "vx": vel_ned_mps[:, 0],
                "vy": vel_ned_mps[:, 1],
                "vz": -vel_ned_mps[:, 2],
                "velocity": np.linalg.norm(vel_ned_mps, axis=1),
                "x_coord": pos_ned_m[:, 0],
                "y_coord": pos_ned_m[:, 1],
                "z_coord": -pos_ned_m[:, 2],
            }
        )