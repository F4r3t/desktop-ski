from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.exceptions import DeviceConnectionError, DeviceDownloadError
from core.models import ConnectionInfo, DownloadResult
from infrastructure.esp32.pyboard_downloader import PyboardFolderDownloader
from infrastructure.esp32.serial_connector import SerialConnector


class DeviceService:
    def __init__(
            self,
            serial_connector: SerialConnector | None = None,
            downloader: PyboardFolderDownloader | None = None,
            remote_dir: str = "/data/",
    ):
        self.serial_connector = serial_connector or SerialConnector()
        self.downloader = downloader or PyboardFolderDownloader()
        self.remote_dir = remote_dir
        self.connection_info: ConnectionInfo | None = None

    @property
    def is_connected(self) -> bool:
        return self.connection_info is not None

    def connect_usb(self, port: str | None = None) -> ConnectionInfo:
        self.connection_info = self.serial_connector.connect(port=port)
        return self.connection_info

    def ensure_connected(self) -> ConnectionInfo:
        if not self.connection_info:
            raise DeviceConnectionError(
                "ESP32 не подключен. Сначала выполните подключение по USB."
            )
        return self.connection_info

    def download_data(self, base_local_dir: Path) -> DownloadResult:
        connection_info = self.ensure_connected()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_dir = base_local_dir / timestamp
        downloaded_files = self.downloader.download_folder(
            port=connection_info.port,
            remote_dir=self.remote_dir,
            local_dir=target_dir,
            recursive=True,
        )

        if not downloaded_files:
            raise DeviceDownloadError("С ESP32 не было выгружено ни одного файла.")

        txt_files = sorted(
            [path for path in downloaded_files if path.suffix.lower() == ".txt"],
            key=lambda path: path.name,
        )
        selected_raw_file = txt_files[-1] if txt_files else None

        return DownloadResult(
            local_directory=target_dir,
            downloaded_files=downloaded_files,
            selected_raw_file=selected_raw_file,
        )