from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMainWindow

from core.exceptions import AppError
from core.models import LoadedDataset
from design import Ui_MainWindow
from services.data_service import DataService
from services.device_service import DeviceService
from services.plot_processing_service import PlotProcessingService
from services.report_service import ReportService
from ui.plot_widget import SensorPlotWidget


class MainWindow(QMainWindow):
    STATUS_STYLES = {
        "neutral": {"color": "#334155", "background": "#ffffff"},
        "success": {"color": "#15803d", "background": "#ecfdf3"},
        "error": {"color": "#b91c1c", "background": "#fef2f2"},
        "progress": {"color": "#1d4ed8", "background": "#eff6ff"},
    }

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.project_dir = Path(__file__).resolve().parent.parent
        self.app_data_dir = self.project_dir / "data" / "downloads"
        self.app_data_dir.mkdir(parents=True, exist_ok=True)

        self.device_service = DeviceService()
        self.data_service = DataService()
        self.plot_processing_service = PlotProcessingService()
        self.report_service = ReportService()
        self.dataset: LoadedDataset | None = None

        self._status_label = QLabel()
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.ui.statusbar.addPermanentWidget(self._status_label, 1)

        self.plot_widget = SensorPlotWidget(self.ui.chartPlaceholderFrame)
        self.ui.matplotlibLayout.addWidget(self.plot_widget)

        self._bind_events()
        self._refresh_data_actions()
        self._show_chart_placeholder(
            "Данные ещё не загружены.\n"
            "Подключите ESP32 и выполните выгрузку либо импортируйте CSV."
        )
        self._set_status("Программа готова к работе.", kind="neutral")

    def _bind_events(self) -> None:
        # Меню
        if hasattr(self.ui, "actionConnectUsb"):
            self.ui.actionConnectUsb.triggered.connect(self._handle_connect_usb)
        if hasattr(self.ui, "actionConnectWifi"):
            self.ui.actionConnectWifi.triggered.connect(self._handle_connect_wifi)
        if hasattr(self.ui, "actionImportData"):
            self.ui.actionImportData.triggered.connect(self._handle_import_data)
        if hasattr(self.ui, "actionExportData"):
            self.ui.actionExportData.triggered.connect(self._handle_export_data)
        if hasattr(self.ui, "actionExportReport"):
            self.ui.actionExportReport.triggered.connect(self._handle_export_report)

        # Основные кнопки, если они есть в UI
        self._connect_if_exists("pushButtonDownloadFromController", self._handle_download_from_controller)
        self._connect_if_exists("pushButtonShowGraph", self._handle_show_graph)

        # Кнопки на вкладках / в UI, если они уже созданы в design_2.py
        self._connect_if_exists("pushButtonImportData", self._handle_import_data)
        self._connect_if_exists("pushButtonExportData", self._handle_export_data)
        self._connect_if_exists("pushButtonExportReport", self._handle_export_report)

        # Дополнительные возможные имена, если у тебя кнопки названы иначе
        self._connect_if_exists("pushButtonImportCsv", self._handle_import_data)
        self._connect_if_exists("pushButtonExportCsv", self._handle_export_data)
        self._connect_if_exists("pushButtonExportPdf", self._handle_export_report)

    def _connect_if_exists(self, attr_name: str, handler) -> None:
        button = getattr(self.ui, attr_name, None)
        if button is not None:
            button.clicked.connect(handler)

    def _set_enabled_if_exists(self, attr_name: str, enabled: bool) -> None:
        widget = getattr(self.ui, attr_name, None)
        if widget is not None:
            widget.setEnabled(enabled)

    def _handle_connect_usb(self) -> None:
        self._run_ui_action(self._connect_usb)

    def _handle_connect_wifi(self) -> None:
        self._set_status("Подключение по Wi-Fi пока не реализовано.", kind="error")

    def _handle_download_from_controller(self) -> None:
        self._run_ui_action(self._download_from_controller)

    def _handle_import_data(self) -> None:
        self._run_ui_action(self._import_data)

    def _handle_export_data(self) -> None:
        self._run_ui_action(self._export_data)

    def _handle_export_report(self) -> None:
        self._run_ui_action(self._export_report)

    def _handle_show_graph(self) -> None:
        self._run_ui_action(self._render_graphs)

    def _run_ui_action(self, action) -> None:
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            action()
        except AppError as exc:
            self._set_status(str(exc), kind="error")
        except Exception as exc:
            self._set_status(f"Непредвиденная ошибка: {exc}", kind="error")
        finally:
            QApplication.restoreOverrideCursor()

    def _connect_usb(self) -> None:
        self._set_status("Подключение к ESP32 по USB...", kind="progress")
        connection = self.device_service.connect_usb()
        self._set_status(
            f"ESP32 успешно подключен: {connection.port} @ {connection.baudrate} baud.",
            kind="success",
        )

    def _download_from_controller(self) -> None:
        if not self.device_service.is_connected:
            self._set_status(
                "Соединение не установлено. Выполняется автоматическое подключение к ESP32...",
                kind="progress",
            )
            self.device_service.connect_usb()

        self._set_status("Выгрузка данных с ESP32...", kind="progress")
        download_result = self.device_service.download_data(self.app_data_dir)
        self.dataset = self.data_service.load_dataset_from_download(download_result)

        converted_count = len(self.dataset.conversions)
        latest_raw_name = (
            download_result.selected_raw_file.name
            if download_result.selected_raw_file
            else "TXT-файл не выбран"
        )

        self._refresh_data_actions()
        self._show_chart_placeholder(
            "Данные выгружены и обработаны.\n"
            f"Последний файл: {latest_raw_name}\n"
            f"Загружен обработанный CSV: {self.dataset.source_path.name}\n"
            f"Сконвертировано TXT -> CSV: {converted_count}\n"
            f"Строк после обработки: {self.dataset.row_count}\n"
            "Нажмите «Показать график», чтобы построить графики Matplotlib."
        )

        self._set_status(
            f"Выгрузка завершена. TXT -> CSV: {converted_count} файлов. "
            f"Для показа загружен последний файл: {latest_raw_name}.",
            kind="success",
        )

    def _import_data(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт CSV",
            str(self.project_dir / "data"),
            "CSV files (*.csv)",
        )
        if not file_name:
            self._set_status("Импорт данных отменён пользователем.", kind="error")
            return

        imported_path = Path(file_name)
        self.dataset = self.data_service.import_csv(imported_path)
        self._refresh_data_actions()

        processed_in_app = (
                self.dataset.processing_artifacts is not None
                and self.dataset.source_path != imported_path
        )

        if processed_in_app:
            placeholder_text = (
                "CSV успешно импортирован и обработан.\n"
                f"Исходный CSV: {imported_path.name}\n"
                f"Загружен обработанный CSV: {self.dataset.source_path.name}\n"
                f"Строк после обработки: {self.dataset.row_count}\n"
                "Нажмите «Показать график», чтобы построить графики Matplotlib."
            )
            status_text = (
                f"Импорт выполнен: {imported_path.name}. "
                f"CSV был обработан и сохранён как {self.dataset.source_path.name}."
            )
        else:
            placeholder_text = (
                "CSV успешно импортирован.\n"
                f"Файл: {self.dataset.source_path.name}\n"
                f"Строк: {self.dataset.row_count}\n"
                "Нажмите «Показать график», чтобы построить графики Matplotlib."
            )
            status_text = f"Импорт выполнен успешно: {self.dataset.source_path.name}."

        self._show_chart_placeholder(placeholder_text)
        self._set_status(status_text, kind="success")

    def _export_data(self) -> None:
        dataset = self._require_dataset()
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт данных в CSV",
            str(self.project_dir / "data" / "exported_data.csv"),
            "CSV files (*.csv)",
        )
        if not file_name:
            self._set_status("Экспорт CSV отменён пользователем.", kind="error")
            return

        target_path = Path(file_name)
        if target_path.suffix.lower() != ".csv":
            target_path = target_path.with_suffix(".csv")

        self.data_service.export_csv(dataset, target_path)
        self._set_status(f"CSV успешно сохранён: {target_path.name}.", kind="success")

    def _export_report(self) -> None:
        dataset = self._require_dataset()
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт отчёта в PDF",
            str(self.project_dir / "data" / "report.pdf"),
            "PDF files (*.pdf)",
        )
        if not file_name:
            self._set_status("Экспорт PDF отменён пользователем.", kind="error")
            return

        target_path = Path(file_name)
        if target_path.suffix.lower() != ".pdf":
            target_path = target_path.with_suffix(".pdf")

        self.report_service.export_pdf_report(dataset, target_path, created_by="Султангареев Алан")
        self._set_status(
            f"PDF-отчёт успешно сохранён: {target_path.name}.",
            kind="success",
        )

    def _render_graphs(self) -> None:
        dataset = self._require_dataset()
        plot_data = self.plot_processing_service.prepare_plot_data(dataset)
        self.plot_widget.plot_data(plot_data)
        self._set_status(
            "Графики построены успешно: a_x(t), a_z(t), V(t), x(t), z(t), траектория z(x).",
            kind="success",
        )

    def _require_dataset(self) -> LoadedDataset:
        if self.dataset is None or not self.dataset.has_data:
            raise AppError(
                "Нет загруженных данных. Сначала выполните выгрузку с ESP32 или импорт CSV."
            )
        return self.dataset

    def _refresh_data_actions(self) -> None:
        has_data = self.dataset is not None and self.dataset.has_data

        # Меню
        if hasattr(self.ui, "actionImportData"):
            self.ui.actionImportData.setEnabled(True)
        if hasattr(self.ui, "actionExportData"):
            self.ui.actionExportData.setEnabled(has_data)
        if hasattr(self.ui, "actionExportReport"):
            self.ui.actionExportReport.setEnabled(has_data)

        # Кнопки в интерфейсе / вкладках
        self._set_enabled_if_exists("pushButtonShowGraph", has_data)
        self._set_enabled_if_exists("pushButtonImportData", True)
        self._set_enabled_if_exists("pushButtonExportData", has_data)
        self._set_enabled_if_exists("pushButtonExportReport", has_data)

        self._set_enabled_if_exists("pushButtonImportCsv", True)
        self._set_enabled_if_exists("pushButtonExportCsv", has_data)
        self._set_enabled_if_exists("pushButtonExportPdf", has_data)

    def _show_chart_placeholder(self, text: str) -> None:
        self.plot_widget.show_placeholder(text)

    def _set_status(self, message: str, *, kind: str) -> None:
        style = self.STATUS_STYLES[kind]
        self.ui.statusbar.showMessage(message, 8000)
        self.ui.statusbar.setStyleSheet(
            "QStatusBar {"
            f"background-color: {style['background']};"
            f"color: {style['color']};"
            "border-top: 1px solid #d9deea;"
            "}"
        )
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"color: {style['color']}; font-weight: 700; padding-right: 8px;"
        )