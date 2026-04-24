from __future__ import annotations

import getpass
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QFont,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
)

from core.exceptions import ReportExportError
from core.models import LoadedDataset
from services.plot_processing_service import PlotProcessingService


class ReportService:
    def __init__(self, plot_processing_service: PlotProcessingService | None = None):
        self.plot_processing_service = plot_processing_service or PlotProcessingService()

    def export_pdf_report(
            self,
            dataset: LoadedDataset,
            target_path: Path,
            created_by: str | None = None,
    ) -> None:
        if not dataset.rows:
            raise ReportExportError("Нет данных для формирования PDF-отчёта.")

        target_path.parent.mkdir(parents=True, exist_ok=True)

        created_at = datetime.now()
        created_by = created_by or getpass.getuser() or "Не указано"

        try:
            plot_data = self.plot_processing_service.prepare_plot_data(dataset)
            summary = self._build_descent_summary(dataset, plot_data)
            graph_image = self._render_graphs_to_image(plot_data)

            writer = QPdfWriter(str(target_path))
            writer.setResolution(120)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageOrientation(QPageLayout.Orientation.Portrait)

            painter = QPainter(writer)
            if not painter.isActive():
                raise ReportExportError("Не удалось открыть PDF для записи.")

            try:
                self._draw_first_page(
                    painter=painter,
                    writer=writer,
                    dataset=dataset,
                    created_at=created_at,
                    created_by=created_by,
                    summary=summary,
                )

                writer.newPage()
                self._draw_graph_page(
                    painter=painter,
                    writer=writer,
                    graph_image=graph_image,
                    title="Графики спуска",
                )
            finally:
                painter.end()

        except ReportExportError:
            raise
        except Exception as exc:
            raise ReportExportError(f"Не удалось сформировать PDF-отчёт: {exc}") from exc

    def _draw_first_page(
            self,
            painter: QPainter,
            writer: QPdfWriter,
            dataset: LoadedDataset,
            created_at: datetime,
            created_by: str,
            summary: dict[str, str],
    ) -> None:
        page_width = writer.width()
        page_height = writer.height()
        margin = 70
        usable_width = page_width - 2 * margin
        y = 70

        title_font = QFont("Segoe UI", 16)
        title_font.setBold(True)

        section_font = QFont("Segoe UI", 11)
        section_font.setBold(True)

        text_font = QFont("Segoe UI", 10)
        small_font = QFont("Segoe UI", 9)

        painter.setFont(title_font)
        painter.drawText(
            QRectF(margin, y, usable_width, 32),
            Qt.AlignLeft,
            "Отчёт по спуску",
        )
        y += 42

        painter.setFont(small_font)
        header_lines = [
            f"Когда создано: {created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Кем создано: {created_by}",
            f"Источник данных: {dataset.source_type}",
            f"Файл: {dataset.source_path.name}",
        ]
        for line in header_lines:
            painter.drawText(QRectF(margin, y, usable_width, 20), Qt.AlignLeft, line)
            y += 18

        y += 14
        painter.setFont(section_font)
        painter.drawText(
            QRectF(margin, y, usable_width, 24),
            Qt.AlignLeft,
            "Краткая таблица по спуску",
        )
        y += 30

        table_rows = [
            ("Где был спуск", summary["location"]),
            ("Когда был спуск", summary["when"]),
            ("Температура", summary["temperature"]),
            ("Влажность", summary["humidity"]),
            ("Время спуска", summary["descent_time"]),
            ("Длина спуска", summary["descent_length"]),
            ("Макс. скорость", summary["max_speed"]),
            ("Координаты геопозиций", summary["geopositions"]),
        ]

        y = self._draw_summary_table(
            painter=painter,
            writer=writer,
            start_y=y,
            margin=margin,
            usable_width=usable_width,
            rows=table_rows,
            font=text_font,
            page_height=page_height,
        )

        y += 16
        painter.setFont(small_font)
        note = (
            "Поля 'Где был спуск' и 'Координаты геопозиций' заполняются из метаданных, "
            "если они есть в выгруженном файле. Для импортированного CSV без таких "
            "метаданных в отчёте выводится 'Не указано'."
        )
        painter.drawText(
            QRectF(margin, y, usable_width, 80),
            int(Qt.TextWordWrap),
            note,
        )

    def _draw_summary_table(
            self,
            painter: QPainter,
            writer: QPdfWriter,
            start_y: int,
            margin: int,
            usable_width: int,
            rows: list[tuple[str, str]],
            font: QFont,
            page_height: int,
    ) -> int:
        painter.setFont(font)

        label_w = int(usable_width * 0.30)
        value_w = usable_width - label_w

        cell_padding_x = 8
        cell_padding_y = 7
        min_row_h = 34

        y = start_y

        for label, value in rows:
            label_text = self._normalize_cell_text(label)
            value_text = self._normalize_cell_text(value)

            label_text_h = self._measure_wrapped_text_height(
                painter=painter,
                width=label_w - 2 * cell_padding_x,
                text=label_text,
            )
            value_text_h = self._measure_wrapped_text_height(
                painter=painter,
                width=value_w - 2 * cell_padding_x,
                text=value_text,
            )

            row_h = max(min_row_h, max(label_text_h, value_text_h) + 2 * cell_padding_y)

            if y + row_h > page_height - margin:
                writer.newPage()
                y = margin
                painter.setFont(font)

            painter.drawRect(margin, y, label_w, row_h)
            painter.drawRect(margin + label_w, y, value_w, row_h)

            label_rect = QRectF(
                margin + cell_padding_x,
                y + cell_padding_y,
                label_w - 2 * cell_padding_x,
                row_h - 2 * cell_padding_y,
                )
            value_rect = QRectF(
                margin + label_w + cell_padding_x,
                y + cell_padding_y,
                value_w - 2 * cell_padding_x,
                row_h - 2 * cell_padding_y,
                )

            painter.drawText(
                label_rect,
                int(Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap),
                label_text,
            )
            painter.drawText(
                value_rect,
                int(Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap),
                value_text,
            )

            y += row_h

        return y

    def _measure_wrapped_text_height(
            self,
            painter: QPainter,
            width: int,
            text: str,
    ) -> int:
        rect = painter.boundingRect(
            0,
            0,
            max(1, width),
            10000,
            int(Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap),
            text,
        )
        return rect.height()

    @staticmethod
    def _normalize_cell_text(value: Any) -> str:
        if value is None:
            return "Не указано"

        text = str(value).strip()
        if not text:
            return "Не указано"

        return text

    def _draw_graph_page(
            self,
            painter: QPainter,
            writer: QPdfWriter,
            graph_image: QImage,
            title: str,
    ) -> None:
        page_width = writer.width()
        page_height = writer.height()
        margin = 60
        usable_width = page_width - 2 * margin
        usable_height = page_height - 2 * margin

        title_font = QFont("Segoe UI", 14)
        title_font.setBold(True)

        painter.setFont(title_font)
        painter.drawText(
            QRectF(margin, margin, usable_width, 28),
            Qt.AlignLeft,
            title,
        )

        image_rect = QRectF(margin, margin + 40, usable_width, usable_height - 40)
        scaled = graph_image.scaled(
            int(image_rect.width()),
            int(image_rect.height()),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        x = image_rect.x() + (image_rect.width() - scaled.width()) / 2
        y = image_rect.y() + (image_rect.height() - scaled.height()) / 2

        painter.drawImage(QRectF(x, y, scaled.width(), scaled.height()), scaled)

    def _build_descent_summary(self, dataset: LoadedDataset, plot_data) -> dict[str, str]:
        metadata = dataset.metadata or {}

        duration_s = float(plot_data.time_s[-1]) if len(plot_data.time_s) else 0.0
        distance_m = self._compute_path_length(plot_data.coord_x_m, plot_data.coord_z_m)
        max_speed_ms = float(np.max(plot_data.speed_ms)) if len(plot_data.speed_ms) else 0.0
        max_speed_kmh = max_speed_ms * 3.6

        temperature_lines = []
        for key in ("temperature", "temperature2", "temperature3"):
            value = metadata.get(key)
            if value not in (None, "", "None"):
                temperature_lines.append(f"{key} = {value} °C")

        humidity_value = metadata.get("humidity")
        humidity = (
            f"{humidity_value} %"
            if humidity_value not in (None, "", "None")
            else "Не указано"
        )

        return {
            "location": self._pick_first(
                metadata,
                ["location", "place", "track", "slope", "where"],
            )
                        or "Не указано",
            "when": self._pick_first(metadata, ["timestamp", "date", "datetime"])
                    or self._fallback_when(dataset),
            "temperature": "\n".join(temperature_lines) if temperature_lines else "Не указано",
            "humidity": humidity,
            "descent_time": self._format_seconds(duration_s),
            "descent_length": f"{distance_m:.2f} м",
            "max_speed": f"{max_speed_ms:.2f} м/с ({max_speed_kmh:.2f} км/ч)",
            "geopositions": self._extract_geopositions(metadata),
        }

    @staticmethod
    def _pick_first(metadata: dict[str, Any], keys: list[str]) -> str | None:
        for key in keys:
            value = metadata.get(key)
            if value not in (None, "", "None"):
                return str(value)
        return None

    @staticmethod
    def _fallback_when(dataset: LoadedDataset) -> str:
        return dataset.source_path.stem or "Не указано"

    @staticmethod
    def _extract_geopositions(metadata: dict[str, Any]) -> str:
        lat = metadata.get("latitude") or metadata.get("lat")
        lon = metadata.get("longitude") or metadata.get("lon")

        start_lat = metadata.get("start_lat")
        start_lon = metadata.get("start_lon")
        end_lat = metadata.get("end_lat")
        end_lon = metadata.get("end_lon")

        if lat not in (None, "", "None") and lon not in (None, "", "None"):
            return f"lat={lat}, lon={lon}"

        if (
                start_lat not in (None, "", "None")
                and start_lon not in (None, "", "None")
                and end_lat not in (None, "", "None")
                and end_lon not in (None, "", "None")
        ):
            return f"start=({start_lat}, {start_lon}), end=({end_lat}, {end_lon})"

        return "Не указано"

    @staticmethod
    def _compute_path_length(x: np.ndarray, z: np.ndarray) -> float:
        if len(x) < 2 or len(z) < 2:
            return 0.0
        dx = np.diff(x)
        dz = np.diff(z)
        return float(np.sum(np.sqrt(dx * dx + dz * dz)))

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        minutes = total // 60
        sec = total % 60
        return f"{minutes:02d}:{sec:02d}"

    def _render_graphs_to_image(self, plot_data) -> QImage:
        figure = Figure(figsize=(11.5, 8.0), constrained_layout=True)
        grid = figure.add_gridspec(
            3,
            2,
            height_ratios=[1.0, 1.0, 1.15],
            hspace=0.22,
            wspace=0.18,
        )

        ax_accel = figure.add_subplot(grid[0, 0])
        ax_velocity = figure.add_subplot(grid[0, 1])
        ax_coord_x = figure.add_subplot(grid[1, 0])
        ax_coord_z = figure.add_subplot(grid[1, 1])
        ax_traj = figure.add_subplot(grid[2, :])

        ax_accel.plot(plot_data.time_s, plot_data.accel_x_ms2, label="a_x(t)")
        ax_accel.plot(plot_data.time_s, plot_data.accel_z_ms2, label="a_z(t)")
        ax_accel.set_title("1. Ускорение от времени")
        ax_accel.set_xlabel("t, с")
        ax_accel.set_ylabel("a, м/с²")
        ax_accel.grid(True, alpha=0.3)
        ax_accel.legend(fontsize=8)

        ax_velocity.plot(plot_data.time_s, plot_data.velocity_x_ms, label="V_x(t)")
        ax_velocity.plot(plot_data.time_s, plot_data.velocity_z_ms, label="V_z(t)")
        ax_velocity.plot(plot_data.time_s, plot_data.speed_ms, label="|V|(t)")
        ax_velocity.set_title("2. Скорости от времени")
        ax_velocity.set_xlabel("t, с")
        ax_velocity.set_ylabel("V, м/с")
        ax_velocity.grid(True, alpha=0.3)
        ax_velocity.legend(fontsize=8)

        ax_coord_x.plot(plot_data.time_s, plot_data.coord_x_m)
        ax_coord_x.set_title("3. Координата x(t)")
        ax_coord_x.set_xlabel("t, с")
        ax_coord_x.set_ylabel("x, м")
        ax_coord_x.grid(True, alpha=0.3)

        ax_coord_z.plot(plot_data.time_s, plot_data.coord_z_m)
        ax_coord_z.set_title("4. Координата z(t)")
        ax_coord_z.set_xlabel("t, с")
        ax_coord_z.set_ylabel("z, м")
        ax_coord_z.grid(True, alpha=0.3)

        x = plot_data.coord_x_m
        z = plot_data.coord_z_m
        points = np.column_stack([x, z]).reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1) if len(points) > 1 else []

        if len(segments) > 0:
            line_collection = LineCollection(segments, cmap="viridis")
            color_source = getattr(plot_data, "trajectory_color_speed_ms", None)
            if color_source is None or len(color_source) < 2:
                color_source = plot_data.speed_ms
            line_collection.set_array(color_source[:-1])
            line_collection.set_linewidth(2.0)
            ax_traj.add_collection(line_collection)
            colorbar = figure.colorbar(line_collection, ax=ax_traj, shrink=0.85, pad=0.02)
            colorbar.set_label("|v|, м/с")

        ax_traj.scatter(x[:1], z[:1], s=35, label="Старт")
        ax_traj.scatter(x[-1:], z[-1:], s=35, label="Финиш")
        ax_traj.autoscale()
        ax_traj.set_title("5. Траектория z(x) с раскраской по |v|")
        ax_traj.set_xlabel("x, м")
        ax_traj.set_ylabel("z, м")
        ax_traj.grid(True, alpha=0.3)
        ax_traj.legend(fontsize=8)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            figure.savefig(tmp_path, dpi=170, bbox_inches="tight")
            image = QImage(str(tmp_path))
            if image.isNull():
                raise ReportExportError(
                    "Не удалось подготовить изображение графиков для PDF."
                )
            return image
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass