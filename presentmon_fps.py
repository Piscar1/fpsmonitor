"""
Реальный источник FPS на базе PresentMon (Intel GameTechDev).

PresentMon через ETW перехватывает вызовы Present() у DirectX/Vulkan/OpenGL
и выдаёт по строке CSV на каждый показанный кадр. Это тот же механизм, что
используют MSI Afterburner / CapFrameX. Чистым Python настоящий FPS игр
получить нельзя — поэтому здесь запускается PresentMon.exe и парсится его вывод.

ВАЖНО: ETW-трассировка требует прав администратора.
"""

import os
import ctypes
import collections
import subprocess
from ctypes import wintypes

from PyQt6.QtCore import QThread, pyqtSignal

PRESENTMON_EXE = "PresentMon-1.10.0-x64.exe"

# Процессы-композиторы/служебные, которые не являются «игрой».
EXCLUDED_PROCESSES = {
    "dwm.exe", "explorer.exe", "applicationframehost.exe",
    "searchhost.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "textinputhost.exe", "presentmon-1.10.0-x64.exe", "presentmon.exe",
    "python.exe", "pythonw.exe",
}

CREATE_NO_WINDOW = 0x08000000

_user32 = ctypes.windll.user32


def is_admin() -> bool:
    """True, если процесс запущен с правами администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_foreground_pid() -> int:
    """PID процесса активного (переднего) окна."""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return 0
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def find_presentmon() -> str | None:
    """Ищет PresentMon.exe рядом с проектом (папка bin) или в каталоге скрипта."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "bin", PRESENTMON_EXE),
        os.path.join(base, PRESENTMON_EXE),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


class PresentMonFPS(QThread):
    """
    Фоновый поток: запускает PresentMon, парсит CSV и вычисляет реальный FPS
    активной игры. Эмитит fps_updated(fps, имя_процесса) и status_changed(текст).
    """

    fps_updated = pyqtSignal(float, str)   # fps, имя приложения ('' если игры нет)
    status_changed = pyqtSignal(str)

    # Окно усреднения FPS (секунды трейс-времени) и период выдачи результата.
    FPS_WINDOW = 1.0
    EMIT_PERIOD = 0.25
    # Если по процессу давно не было кадров — считаем его неактивным.
    STALE_AFTER = 1.5

    def __init__(self, exe_path: str | None = None, parent=None):
        super().__init__(parent)
        self._exe = exe_path or find_presentmon()
        self._proc = None
        self._running = True

        # pid -> deque[float]  (TimeInSeconds каждого кадра)
        self._events: dict[int, collections.deque] = {}
        self._names: dict[int, str] = {}
        self._last_seen: dict[int, float] = {}
        self._latest_t = 0.0
        self._last_emit = 0.0
        self._last_target = None

    # ------------------------------------------------------------------ #
    def run(self):
        if self._exe is None:
            self.status_changed.emit(
                "PresentMon.exe не найден — положите его в папку bin/")
            return
        if not is_admin():
            self.status_changed.emit(
                "Нужны права администратора — запустите программу от имени админа")
            return

        cmd = [
            self._exe,
            "-output_stdout",
            "-stop_existing_session",
            "-no_top",
            "-no_track_display",   # меньше нагрузка, для FPS не нужно
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=1,
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as e:
            self.status_changed.emit(f"Не удалось запустить PresentMon: {e}")
            return

        self.status_changed.emit("Ожидание игры…")

        col = None  # индексы колонок по заголовку
        try:
            for line in self._proc.stdout:
                if not self._running:
                    break
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")

                if col is None:
                    if line.startswith("Application,"):
                        col = self._parse_header(parts)
                    continue

                self._handle_row(parts, col)
        except Exception:
            pass
        finally:
            self._terminate_proc()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_header(parts: list[str]) -> dict:
        idx = {name: i for i, name in enumerate(parts)}
        return {
            "app": idx.get("Application", 0),
            "pid": idx.get("ProcessID", 1),
            "dropped": idx.get("Dropped", 6),
            "time": idx.get("TimeInSeconds", 7),
        }

    def _handle_row(self, parts: list[str], col: dict):
        try:
            pid = int(parts[col["pid"]])
            t = float(parts[col["time"]])
            app = parts[col["app"]]
        except (ValueError, IndexError):
            return

        if app.lower() in EXCLUDED_PROCESSES:
            return

        self._latest_t = t
        self._names[pid] = app
        self._last_seen[pid] = t

        dq = self._events.get(pid)
        if dq is None:
            dq = collections.deque()
            self._events[pid] = dq
        dq.append(t)

        # Чистим всё старше 2 секунд, чтобы не копить память.
        cutoff = t - 2.0
        while dq and dq[0] < cutoff:
            dq.popleft()

        if t - self._last_emit >= self.EMIT_PERIOD:
            self._last_emit = t
            self._emit_fps()

    def _emit_fps(self):
        target = self._pick_target()
        if target is None:
            if self._last_target is not None:
                self.status_changed.emit("Ожидание игры…")
            self._last_target = None
            self.fps_updated.emit(0.0, "")
            return

        fps = self._fps_for(target)
        name = self._names.get(target, "")
        if target != self._last_target:
            self.status_changed.emit(f"Измерение: {name}")
            self._last_target = target
        self.fps_updated.emit(fps, name)

    def _pick_target(self) -> int | None:
        """Активная игра: процесс переднего окна, иначе самый «активный» по кадрам."""
        active = [
            pid for pid, last in self._last_seen.items()
            if self._latest_t - last <= self.STALE_AFTER and self._events.get(pid)
        ]
        if not active:
            return None

        fg = get_foreground_pid()
        if fg in active:
            return fg

        # Иначе — процесс с наибольшим числом кадров за последнюю секунду.
        return max(active, key=lambda p: self._frame_count(p))

    def _frame_count(self, pid: int) -> int:
        dq = self._events.get(pid)
        if not dq:
            return 0
        cutoff = self._latest_t - self.FPS_WINDOW
        return sum(1 for t in dq if t >= cutoff)

    def _fps_for(self, pid: int) -> float:
        dq = self._events.get(pid)
        if not dq:
            return 0.0
        cutoff = self._latest_t - self.FPS_WINDOW
        recent = [t for t in dq if t >= cutoff]
        if len(recent) < 2:
            return 0.0
        span = recent[-1] - recent[0]
        if span <= 0:
            return 0.0
        # (кадров - 1) интервалов за span секунд.
        return (len(recent) - 1) / span

    # ------------------------------------------------------------------ #
    def stop(self):
        self._running = False
        self._terminate_proc()
        self.wait(2000)

    def _terminate_proc(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
