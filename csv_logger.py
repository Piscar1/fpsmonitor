import csv
import os
import time
from datetime import datetime


class CSVLogger:
    """
    Логирование метрик в CSV-файл.

    Файл создаётся в папке logs/ рядом со скриптом.
    Имя файла: fps_monitor_YYYY-MM-DD_HH-MM-SS.csv
    """

    BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

    def __init__(self):
        self._file = None
        self._writer = None
        self._fieldnames = [
            "timestamp", "fps", "fps_min", "fps_max", "fps_avg",
            "fps_1_low", "fps_0_1_low", "frametime_ms",
            "cpu_percent", "cpu_temp", "cpu_freq",
            "ram_percent", "ram_used_gb", "ram_total_gb",
            "gpu_load", "gpu_temp", "gpu_freq", "gpu_mem_freq",
            "gpu_mem_used", "gpu_mem_total", "gpu_power", "gpu_voltage",
            "motherboard_temp", "vrm_temp",
        ]
        self._enabled = False
        self._interval = 1.0
        self._last_write = 0.0

    def start(self):
        if not self._enabled:
            return
        os.makedirs(self.BASE_DIR, exist_ok=True)
        filename = f"fps_monitor_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        path = os.path.join(self.BASE_DIR, filename)
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self._fieldnames)
        self._writer.writeheader()
        self._last_write = time.perf_counter()

    def set_enabled(self, enabled: bool):
        if enabled and not self._enabled:
            self._enabled = True
            self.start()
        elif not enabled and self._enabled:
            self._enabled = False
            self.stop()

    def set_interval(self, seconds: float):
        self._interval = max(0.1, seconds)

    def log(self, fps_counter, metrics: dict):
        if not self._enabled or self._writer is None:
            return
        now = time.perf_counter()
        if now - self._last_write < self._interval:
            return
        self._last_write = now

        row = {
            "timestamp": datetime.now().isoformat(),
            "fps": fps_counter.current,
            "fps_min": fps_counter.minimum,
            "fps_max": fps_counter.maximum,
            "fps_avg": fps_counter.average,
            "fps_1_low": fps_counter.one_pct_low,
            "fps_0_1_low": fps_counter.zero_one_pct_low,
            "frametime_ms": fps_counter.frametime_avg,
            "cpu_percent": metrics.get("cpu_percent_total"),
            "cpu_temp": metrics.get("cpu_temp"),
            "cpu_freq": metrics.get("cpu_freq"),
            "ram_percent": metrics.get("ram_percent"),
            "ram_used_gb": metrics.get("ram_used_gb"),
            "ram_total_gb": metrics.get("ram_total_gb"),
            "gpu_load": metrics.get("gpu_load"),
            "gpu_temp": metrics.get("gpu_temp"),
            "gpu_freq": metrics.get("gpu_freq"),
            "gpu_mem_freq": metrics.get("gpu_mem_freq"),
            "gpu_mem_used": metrics.get("gpu_mem_used"),
            "gpu_mem_total": metrics.get("gpu_mem_total"),
            "gpu_power": metrics.get("gpu_power"),
            "gpu_voltage": metrics.get("gpu_voltage"),
            "motherboard_temp": metrics.get("motherboard_temp"),
            "vrm_temp": metrics.get("vrm_temp"),
        }
        self._writer.writerow(row)
        self._file.flush()

    def stop(self):
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
