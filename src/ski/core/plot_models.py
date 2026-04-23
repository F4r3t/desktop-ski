from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class PlotComputationResult:
    time_s: FloatArray
    accel_x_ms2: FloatArray
    accel_z_ms2: FloatArray
    velocity_x_ms: FloatArray
    velocity_z_ms: FloatArray
    speed_ms: FloatArray
    coord_x_m: FloatArray
    coord_z_m: FloatArray
    dt_s: FloatArray
    baseline_window: int