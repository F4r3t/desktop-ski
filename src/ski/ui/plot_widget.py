from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from core.plot_models import PlotComputationResult


class SensorPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.updateGeometry()

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.placeholder_label = QLabel(self)
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(
            "font-size: 11pt; color: #475569; padding: 12px;"
        )
        self.placeholder_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.toolbar, 0)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.placeholder_label, 1)

        self.toolbar.hide()
        self.canvas.hide()
        self.show_placeholder("Данные ещё не загружены.")

    def show_placeholder(self, text: str) -> None:
        self.figure.clear()
        self.canvas.draw_idle()
        self.toolbar.hide()
        self.canvas.hide()
        self.placeholder_label.setText(text)
        self.placeholder_label.show()

    def plot_data(self, data: PlotComputationResult) -> None:
        self.placeholder_label.hide()
        self.toolbar.show()
        self.canvas.show()

        self.figure.clear()

        grid = self.figure.add_gridspec(
            3,
            2,
            height_ratios=[1.0, 1.0, 1.15],
            hspace=0.22,
            wspace=0.18,
        )

        ax_accel = self.figure.add_subplot(grid[0, 0])
        ax_velocity = self.figure.add_subplot(grid[0, 1])
        ax_coord_x = self.figure.add_subplot(grid[1, 0])
        ax_coord_z = self.figure.add_subplot(grid[1, 1])
        ax_traj = self.figure.add_subplot(grid[2, :])

        ax_accel.plot(data.time_s, data.accel_x_ms2, label="a_x(t)")
        ax_accel.plot(data.time_s, data.accel_z_ms2, label="a_z(t)")
        ax_accel.set_title("1. Ускорение от времени", fontsize=10)
        ax_accel.set_xlabel("t, с")
        ax_accel.set_ylabel("a, м/с²")
        ax_accel.grid(True, alpha=0.3)
        ax_accel.legend(fontsize=8)

        ax_velocity.plot(data.time_s, data.velocity_x_ms, label="V_x(t)")
        ax_velocity.plot(data.time_s, data.velocity_z_ms, label="V_z(t)")
        ax_velocity.plot(data.time_s, data.speed_ms, label="|V|(t)")
        ax_velocity.set_title("2. Скорости от времени", fontsize=10)
        ax_velocity.set_xlabel("t, с")
        ax_velocity.set_ylabel("V, м/с")
        ax_velocity.grid(True, alpha=0.3)
        ax_velocity.legend(fontsize=8)

        ax_coord_x.plot(data.time_s, data.coord_x_m)
        ax_coord_x.set_title("3. Координата x(t)", fontsize=10)
        ax_coord_x.set_xlabel("t, с")
        ax_coord_x.set_ylabel("x, м")
        ax_coord_x.grid(True, alpha=0.3)

        ax_coord_z.plot(data.time_s, data.coord_z_m)
        ax_coord_z.set_title("4. Координата z(t)", fontsize=10)
        ax_coord_z.set_xlabel("t, с")
        ax_coord_z.set_ylabel("z, м")
        ax_coord_z.grid(True, alpha=0.3)

        x = data.coord_x_m
        z = data.coord_z_m
        color_speed = data.trajectory_color_speed_ms

        points = np.column_stack([x, z]).reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        if len(segments) > 0:
            line_collection = LineCollection(segments, cmap="viridis")
            line_collection.set_array(color_speed[:-1])
            line_collection.set_linewidth(2.0)
            ax_traj.add_collection(line_collection)
            colorbar = self.figure.colorbar(line_collection, ax=ax_traj, shrink=0.85, pad=0.02)
            colorbar.set_label("|v|, м/с")

        ax_traj.scatter(x[:1], z[:1], s=35, label="Старт")
        ax_traj.scatter(x[-1:], z[-1:], s=35, label="Финиш")
        ax_traj.autoscale()
        ax_traj.set_title("5. Траектория z(x) с раскраской по |v|", fontsize=10)
        ax_traj.set_xlabel("x, м")
        ax_traj.set_ylabel("z, м")
        ax_traj.grid(True, alpha=0.3)
        ax_traj.legend(fontsize=8)

        self.canvas.draw_idle()