from __future__ import annotations

import serial

from core.exceptions import DeviceConnectionError
from core.models import ConnectionInfo
from infrastructure.esp32.port_detector import find_esp32_port


class SerialConnector:
    def __init__(self, baudrate: int = 115200, timeout: float = 1.0):
        self.baudrate = baudrate
        self.timeout = timeout

    def connect(self, port: str | None = None) -> ConnectionInfo:
        resolved_port = port or find_esp32_port()
        if not resolved_port:
            raise DeviceConnectionError(
                "ESP32 не найден. Проверьте USB-подключение и доступность COM-порта."
            )

        try:
            ser = serial.Serial(
                port=resolved_port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            if not ser.is_open:
                ser.open()
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.close()
        except serial.SerialException as exc:
            raise DeviceConnectionError(
                f"Не удалось подключиться к порту {resolved_port}: {exc}"
            ) from exc

        return ConnectionInfo(port=resolved_port, baudrate=self.baudrate, transport="USB")