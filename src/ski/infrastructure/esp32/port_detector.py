from __future__ import annotations

from typing import Iterable

from serial.tools import list_ports

ESP32_MARKERS = (
    "ch340",
    "usb-serial",
    "wch",
    "cp210",
    "silicon labs",
    "uart",
    "ttyusb",
    "ttyacm",
)


def _describe_port(port) -> str:
    return " ".join(
        str(value) for value in (port.device, port.description, port.manufacturer) if value
    ).lower()


def iter_candidate_ports() -> Iterable[str]:
    for port in list_ports.comports():
        description = _describe_port(port)
        if any(marker in description for marker in ESP32_MARKERS):
            yield port.device


def find_esp32_port() -> str | None:
    return next(iter(iter_candidate_ports()), None)