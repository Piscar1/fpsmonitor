import time
import collections


class FPSCounter:
    """
    Накапливает статистику FPS из реальных замеров (источник — PresentMon).

    Метод update(fps) вызывается при каждом новом значении FPS. Текущий FPS,
    а также min/max/avg за сессию считаются только по «боевым» кадрам (fps > 0),
    поэтому периоды без игры не портят минимум и среднее.

    Дополнительно считаются:
      - 1% low FPS  (усреднённый FPS 1% самых медленных кадров)
      - 0.1% low   (усреднённый FPS 0.1% самых медленных кадров)
      - frametime  (мс на кадр, среднее и история)

    История хранится по времени (perf_counter), окно настраивается на лету.
    """

    def __init__(self, history_seconds: int = 60):
        self._history = collections.deque()          # (timestamp, fps)
        self._frametime_history = collections.deque() # (timestamp, ms_per_frame)
        self._history_seconds = history_seconds

        self._current = 0.0
        self._min = None
        self._max = 0.0
        self._sum = 0.0
        self._count = 0

        # Для расчёта low-percentile в реальном времени используем
        # ограниченный буфер недавних значений fps.
        self._recent_fps = collections.deque(maxlen=600)  # ~10 сек при 60 FPS

        # Frametime статистика
        self._ft_sum = 0.0
        self._ft_count = 0
        self._ft_min = None
        self._ft_max = 0.0

    def update(self, fps: float, frametime_ms: float = 0.0):
        """Записать новое значение FPS (0 = игра не обнаружена)."""
        now = time.perf_counter()
        self._current = max(0.0, fps)

        if self._current > 0:
            self._min = self._current if self._min is None else min(self._min, self._current)
            self._max = max(self._max, self._current)
            self._sum += self._current
            self._count += 1
            self._recent_fps.append(self._current)

            # Frametime (если не передан, вычисляем из FPS)
            ft = frametime_ms if frametime_ms > 0 else (1000.0 / self._current)
            self._ft_sum += ft
            self._ft_count += 1
            self._ft_min = ft if self._ft_min is None else min(self._ft_min, ft)
            self._ft_max = max(self._ft_max, ft)
            self._frametime_history.append((now, ft))

        self._history.append((now, self._current))
        self._prune(now)

    def _prune(self, now: float):
        cutoff = now - self._history_seconds
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()
        while self._frametime_history and self._frametime_history[0][0] < cutoff:
            self._frametime_history.popleft()

    @property
    def current(self) -> int:
        return int(round(self._current))

    @property
    def minimum(self) -> int:
        return int(round(self._min)) if self._min is not None else 0

    @property
    def maximum(self) -> int:
        return int(round(self._max))

    @property
    def average(self) -> int:
        return int(round(self._sum / self._count)) if self._count else 0

    @property
    def history(self) -> list:
        """[(timestamp, fps), ...] для графика."""
        return list(self._history)

    @property
    def frametime_history(self) -> list:
        """[(timestamp, ms), ...] для графика frametime."""
        return list(self._frametime_history)

    @property
    def frametime_avg(self) -> float:
        return round(self._ft_sum / self._ft_count, 2) if self._ft_count else 0.0

    @property
    def frametime_min(self) -> float:
        return round(self._ft_min, 2) if self._ft_min is not None else 0.0

    @property
    def frametime_max(self) -> float:
        return round(self._ft_max, 2)

    def percentile_low(self, pct: float) -> int:
        """
        Возвращает усреднённый FPS среди pct% самых медленных кадров.
        pct=1 → 1% low, pct=0.1 → 0.1% low.
        """
        if len(self._recent_fps) < 10:
            return 0
        sorted_fps = sorted(self._recent_fps)
        n = max(1, int(len(sorted_fps) * pct / 100.0))
        lowest = sorted_fps[:n]
        return int(round(sum(lowest) / len(lowest)))

    @property
    def one_pct_low(self) -> int:
        return self.percentile_low(1.0)

    @property
    def zero_one_pct_low(self) -> int:
        return self.percentile_low(0.1)

    def set_history_seconds(self, seconds: int):
        self._history_seconds = max(1, int(seconds))
        self._prune(time.perf_counter())

    def reset(self):
        self._history.clear()
        self._frametime_history.clear()
        self._recent_fps.clear()
        self._current = 0.0
        self._min = None
        self._max = 0.0
        self._sum = 0.0
        self._count = 0
        self._ft_sum = 0.0
        self._ft_count = 0
        self._ft_min = None
        self._ft_max = 0.0
