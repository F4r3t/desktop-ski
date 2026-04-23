from __future__ import annotations

import ast
from pathlib import Path

from core.exceptions import DeviceDownloadError

try:
    import pyboard
except ImportError:
    pyboard = None

MP_TYPE_DIR = 0x4000


class PyboardFolderDownloader:
    def __init__(self, baudrate: int = 115200, chunk_size: int = 256):
        self.baudrate = baudrate
        self.chunk_size = chunk_size

    def download_folder(
            self,
            port: str,
            remote_dir: str,
            local_dir: Path,
            recursive: bool = True,
    ) -> list[Path]:
        if pyboard is None:
            raise DeviceDownloadError(
                "Модуль pyboard недоступен. Установите pyboard.py из экосистемы MicroPython."
            )

        local_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: list[Path] = []
        pyb = pyboard.Pyboard(port, baudrate=self.baudrate)

        try:
            pyb.enter_raw_repl()
            self._download_remote_dir(
                pyb=pyb,
                remote_dir=remote_dir,
                local_dir=local_dir,
                downloaded_files=downloaded_files,
                recursive=recursive,
            )
        except Exception as exc:
            raise DeviceDownloadError(f"Не удалось выгрузить данные с ESP32: {exc}") from exc
        finally:
            try:
                pyb.exit_raw_repl()
            except Exception:
                pass
            pyb.close()

        return downloaded_files

    def _download_remote_dir(
            self,
            pyb,
            remote_dir: str,
            local_dir: Path,
            downloaded_files: list[Path],
            recursive: bool,
    ) -> None:
        entries = self._list_remote_entries(pyb, remote_dir)
        for entry in entries:
            name = entry["name"]
            if name in (".", ".."):
                continue

            remote_path = self._remote_join(remote_dir, name)
            local_path = local_dir / name

            if entry["is_dir"]:
                if recursive:
                    self._download_remote_dir(
                        pyb=pyb,
                        remote_dir=remote_path,
                        local_dir=local_path,
                        downloaded_files=downloaded_files,
                        recursive=recursive,
                    )
                continue

            local_path.parent.mkdir(parents=True, exist_ok=True)
            pyb.fs_get(remote_path, str(local_path), chunk_size=self.chunk_size)
            downloaded_files.append(local_path)

    @staticmethod
    def _remote_join(parent: str, name: str) -> str:
        if parent == "/":
            return f"/{name}"
        return f"{parent.rstrip('/')}/{name}"

    @staticmethod
    def _normalize_name(name) -> str:
        if isinstance(name, bytes):
            return name.decode("utf-8", errors="replace")
        return str(name)

    def _list_remote_entries(self, pyb, remote_dir: str) -> list[dict[str, object]]:
        try:
            raw = pyb.eval(f"list(__import__('os').ilistdir({remote_dir!r}))")
            entries = ast.literal_eval(raw.decode("utf-8"))
            result = []
            for item in entries:
                name = self._normalize_name(item[0])
                entry_type = item[1] if len(item) > 1 else 0
                is_dir = entry_type == MP_TYPE_DIR
                result.append({"name": name, "is_dir": is_dir})
            return result
        except Exception:
            try:
                raw = pyb.eval(f"__import__('os').listdir({remote_dir!r})")
                names = ast.literal_eval(raw.decode("utf-8"))
                result = []
                for name in names:
                    normalized = self._normalize_name(name)
                    full_path = self._remote_join(remote_dir, normalized)
                    mode_raw = pyb.eval(f"__import__('os').stat({full_path!r})[0]")
                    mode = int(mode_raw.decode("utf-8").strip())
                    is_dir = bool(mode & MP_TYPE_DIR)
                    result.append({"name": normalized, "is_dir": is_dir})
                return result
            except Exception as exc:
                raise DeviceDownloadError(
                    f"Не удалось прочитать содержимое каталога {remote_dir} на ESP32: {exc}"
                ) from exc