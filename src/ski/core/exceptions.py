from __future__ import annotations


class AppError(Exception):
    """Базовое прикладное исключение."""


class DeviceConnectionError(AppError):
    """Ошибка подключения к устройству."""


class DeviceDownloadError(AppError):
    """Ошибка выгрузки данных с устройства."""


class DataOperationError(AppError):
    """Ошибка операций с данными."""


class ReportExportError(AppError):
    """Ошибка экспорта отчета."""