import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QToolBar, QGroupBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction, QColor

import pyqtgraph as pg
from settings_dialog import SettingsDialog
from metrics import MetricsWorker
from fps_counter import FPSCounter
from overlay import OverlayWindow
from presentmon_fps import PresentMonFPS
from csv_logger import CSVLogger


class MetricCard(QGroupBox):
    """Карточка метрики."""
    def __init__(self, title: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.lbl_value = QLabel("---")
        self.lbl_value.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_value.setWordWrap(True)
        layout.addWidget(self.lbl_value)

    def set_value(self, text: str):
        self.lbl_value.setText(text)

    def set_temp_color(self, temp, warn, crit):
        state = 'ok' if temp < warn else ('warn' if temp < crit else 'crit')
        value_col = '#00E676' if state == 'ok' else ('#FFB020' if state == 'warn' else '#FF5252')
        self.lbl_value.setStyleSheet(f"color: {value_col};")
        if self.property('state') != state:
            self.setProperty('state', state)
            # Re-run the stylesheet so the [state=...] selector applies.
            self.style().unpolish(self)
            self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FPS Monitor")
        self.resize(900, 700)

        self.fps_counter = FPSCounter()
        self.overlay = OverlayWindow()
        self.settings_dialog = SettingsDialog(self)
        self.csv_logger = CSVLogger()
        self._app_name = ""

        self.metrics = {}
        self._graph_history = 60
        self.cpu_history = []
        self.gpu_history = []

        # Visual settings
        self._graph_fill = True
        self._graph_frametime = False
        self._graph_grid_x = False
        self._graph_grid_y = True
        self._graph_legend = True
        self._graph_smooth = True
        self._graph_fps_color = '#00FF00'
        self._graph_cpu_color = '#FF6600'
        self._graph_gpu_color = '#00CCFF'
        self._cpu_warn = 60
        self._cpu_crit = 80
        self._gpu_warn = 65
        self._gpu_crit = 85

        self._init_toolbar()
        self._init_metrics_worker()
        self._init_ui()
        self._init_metrics_ui()
        self._init_fps_source()

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._refresh)
        self.ui_timer.start(250)

    # ------------------------------------------------------------------ #
    def _init_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.btn_overlay = QAction("\U0001F4F7 Оverлей", self)
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.toggled.connect(self.overlay.toggle)
        tb.addAction(self.btn_overlay)

        btn_settings = QAction("\u2699 Настройки", self)
        btn_settings.triggered.connect(self._open_settings)
        tb.addAction(btn_settings)

        btn_reset = QAction("\U0001F5AB Сброс", self)
        btn_reset.triggered.connect(self._reset)
        tb.addAction(btn_reset)

        tb.addSeparator()

        btn_tray = QAction("\U0001F5D6 Скрыть", self)
        btn_tray.triggered.connect(self.hide)
        tb.addAction(btn_tray)

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # --- Top: FPS display + advanced stats ---
        fps_layout = QHBoxLayout()

        # Big FPS number
        self.lbl_fps = QLabel("--")
        self.lbl_fps.setFont(QFont("Consolas", 72, QFont.Weight.Bold))
        self.lbl_fps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fps.setStyleSheet("color: #00FF00;")
        fps_layout.addWidget(self.lbl_fps, stretch=2)

        # Stats panel
        stats_layout = QVBoxLayout()
        self.lbl_min = QLabel("MIN: ---")
        self.lbl_max = QLabel("MAX: ---")
        self.lbl_avg = QLabel("AVG: ---")
        self.lbl_1low = QLabel("1% low: ---")
        self.lbl_01low = QLabel("0.1% low: ---")
        self.lbl_frametime = QLabel("Frametime: --- ms")
        for lbl in (self.lbl_min, self.lbl_max, self.lbl_avg, self.lbl_1low, self.lbl_01low, self.lbl_frametime):
            lbl.setFont(QFont("Consolas", 13))
            stats_layout.addWidget(lbl)
        fps_layout.addLayout(stats_layout, stretch=1)

        main_layout.addLayout(fps_layout)

        # Status bar
        self.lbl_status = QLabel("Запуск…")
        self.lbl_status.setFont(QFont("Consolas", 11))
        self.lbl_status.setStyleSheet("color: #AAAAAA;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.lbl_status)

        # --- Center: FPS Graph ---
        self.plot = pg.PlotWidget(title="FPS Timeline")
        self.plot.setBackground('#13131d')
        self.plot.setLabel('left', 'FPS / %')
        self.plot.setLabel('bottom', 'Время (с)')
        self.fps_curve = self.plot.plot([], [], pen=pg.mkPen('#00FF00', width=2), name="FPS")
        self.cpu_curve = self.plot.plot([], [], pen=pg.mkPen('#FF6600', width=1), name="CPU %")
        self.gpu_curve = self.plot.plot([], [], pen=pg.mkPen('#00CCFF', width=1), name="GPU %")
        main_layout.addWidget(self.plot, stretch=2)

        # Frametime graph (optional)
        self.ft_plot = pg.PlotWidget(title="Frametime (ms)")
        self.ft_plot.setBackground('#13131d')
        self.ft_plot.setLabel('left', 'ms')
        self.ft_plot.setLabel('bottom', 'Время (с)')
        self.ft_curve = self.ft_plot.plot([], [], pen=pg.mkPen('#00CCFF', width=2), name="Frametime")
        self.ft_plot.setVisible(False)
        main_layout.addWidget(self.ft_plot, stretch=1)

        # --- Bottom: Metric cards ---
        self.cards_widget = QWidget()
        cards_layout = QGridLayout(self.cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        self.card_cpu = MetricCard("")
        self.card_cpu_cores = MetricCard("")
        self.card_cpu_freq = MetricCard("")
        self.card_cpu_temp = MetricCard("")
        self.card_ram = MetricCard("")
        self.card_gpu = MetricCard("")
        self.card_gpu_mem = MetricCard("")
        self.card_gpu_freq = MetricCard("")
        self.card_gpu_temp = MetricCard("")
        self.card_gpu_power = MetricCard("GPU — Энергопотребление")
        self.card_gpu_voltage = MetricCard("GPU — Напряжение")
        self.card_gpu_mem_freq = MetricCard("GPU — Частота памяти")
        self.card_motherboard = MetricCard("Материнская плата")
        self.card_vrm = MetricCard("VRM")

        cards = [
            self.card_cpu, self.card_cpu_cores, self.card_cpu_freq, self.card_cpu_temp,
            self.card_ram, self.card_gpu, self.card_gpu_mem, self.card_gpu_freq, self.card_gpu_temp,
            self.card_gpu_power, self.card_gpu_voltage, self.card_gpu_mem_freq,
            self.card_motherboard, self.card_vrm
        ]
        for i, card in enumerate(cards):
            cards_layout.addWidget(card, i // 3, i % 3)

        main_layout.addWidget(self.cards_widget, stretch=1)

    def _init_metrics_worker(self):
        self.worker = MetricsWorker(interval_ms=100)
        self.worker.metrics_ready.connect(self._on_metrics)

    def _init_metrics_ui(self):
        self.card_cpu.setTitle(self.worker.cpu_name)
        self.card_gpu.setTitle(self.worker.gpu_name)
        self.card_cpu_cores.setTitle(f"{self.worker.cpu_name} — Ядра")
        self.card_gpu_mem.setTitle(f"{self.worker.gpu_name} — VRAM")
        self.worker.start()

    def _init_fps_source(self):
        self.fps_source = PresentMonFPS()
        self.fps_source.fps_updated.connect(self._on_fps)
        self.fps_source.status_changed.connect(self._on_fps_status)
        self.fps_source.start()

    # ------------------------------------------------------------------ #
    def _on_fps(self, fps: float, app_name: str):
        self.fps_counter.update(fps)
        self._app_name = app_name

    def _on_fps_status(self, text: str):
        self.lbl_status.setText(text)
        problem = any(w in text.lower() for w in ("админ", "не найден", "не удалось"))
        color = "#FF5555" if problem else "#AAAAAA"
        self.lbl_status.setStyleSheet(f"color: {color};")

    def _on_metrics(self, data: dict):
        self.metrics = data
        self._update_cards()
        self.csv_logger.log(self.fps_counter, self.metrics)

    def _refresh(self):
        self._update_fps_display()
        self._update_graph()
        if self.overlay.isVisible():
            self.overlay.update_data(
                self.fps_counter.current,
                self.fps_counter.minimum,
                self.fps_counter.maximum,
                self.fps_counter.average,
                self.metrics,
                fps_1low=self.fps_counter.one_pct_low,
                fps_01low=self.fps_counter.zero_one_pct_low,
                frametime=self.fps_counter.frametime_avg,
                app_name=self._app_name,
            )

    def _update_fps_display(self):
        fps = self.fps_counter.current
        self.lbl_fps.setText(str(fps) if fps > 0 else "--")
        # Dynamic color for big FPS number
        if fps > 0:
            col = '#00FF00' if fps >= 60 else ('#FFAA00' if fps >= 30 else '#FF5555')
            self.lbl_fps.setStyleSheet(f"color: {col};")
        self.lbl_min.setText(f"MIN: {self.fps_counter.minimum or '---'}")
        self.lbl_max.setText(f"MAX: {self.fps_counter.maximum or '---'}")
        self.lbl_avg.setText(f"AVG: {self.fps_counter.average or '---'}")
        self.lbl_1low.setText(f"1% low: {self.fps_counter.one_pct_low or '---'}")
        self.lbl_01low.setText(f"0.1% low: {self.fps_counter.zero_one_pct_low or '---'}")
        ft = self.fps_counter.frametime_avg
        if ft > 0:
            self.lbl_frametime.setText(f"Frametime: {ft:.2f} ms")
        else:
            self.lbl_frametime.setText("Frametime: --- ms")

    def _update_graph(self):
        # FPS curve with optional fill
        fps_hist = self.fps_counter.history
        if len(fps_hist) > 1:
            x = [t - fps_hist[0][0] for t, _ in fps_hist]
            y = [v for _, v in fps_hist]
            pen = pg.mkPen(self._graph_fps_color, width=2)
            if self._graph_smooth:
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self.fps_curve.setData(x, y, pen=pen)
            if self._graph_fill:
                self.fps_curve.setFillLevel(0)
                fill_color = QColor(self._graph_fps_color)
                fill_color.setAlpha(30)
                self.fps_curve.setFillBrush(pg.mkBrush(fill_color))
            else:
                self.fps_curve.setFillLevel(None)
        else:
            self.fps_curve.setData([], [])

        # CPU curve
        if len(self.cpu_history) > 1:
            x = [t - self.cpu_history[0][0] for t, _ in self.cpu_history]
            y = [v for _, v in self.cpu_history]
            self.cpu_curve.setData(x, y, pen=pg.mkPen(self._graph_cpu_color, width=1))
        else:
            self.cpu_curve.setData([], [])

        # GPU curve
        if len(self.gpu_history) > 1:
            x = [t - self.gpu_history[0][0] for t, _ in self.gpu_history]
            y = [v for _, v in self.gpu_history]
            self.gpu_curve.setData(x, y, pen=pg.mkPen(self._graph_gpu_color, width=1))
        else:
            self.gpu_curve.setData([], [])

        # Grid
        self.plot.showGrid(x=self._graph_grid_x, y=self._graph_grid_y)

        # Legend
        if self._graph_legend and not hasattr(self, '_legend_added'):
            self._legend_added = True
            try:
                legend = self.plot.addLegend()
            except Exception:
                pass

        # Frametime graph
        if self._graph_frametime:
            self.ft_plot.setVisible(True)
            ft_hist = self.fps_counter.frametime_history
            if len(ft_hist) > 1:
                x = [t - ft_hist[0][0] for t, _ in ft_hist]
                y = [v for _, v in ft_hist]
                pen = pg.mkPen('#00CCFF', width=2)
                self.ft_curve.setData(x, y, pen=pen)
                self.ft_curve.setFillLevel(0)
                ft_fill = QColor('#00CCFF')
                ft_fill.setAlpha(30)
                self.ft_curve.setFillBrush(pg.mkBrush(ft_fill))
        else:
            self.ft_plot.setVisible(False)

    # ------------------------------------------------------------------ #
    def _update_cards(self):
        m = self.metrics
        now = time.perf_counter()

        # CPU total
        cpu = m.get('cpu_percent_total')
        if cpu is not None:
            self.card_cpu.set_value(f"{cpu:.1f}%")
            self.cpu_history.append((now, cpu))
            self._prune_history(self.cpu_history, now)
        else:
            self.card_cpu.hide()

        # CPU per core
        cores = m.get('cpu_percent_per_core')
        if cores:
            core_parts = [f"C{i}:{c:.0f}%" for i, c in enumerate(cores[:16])]
            lines = []
            for i in range(0, len(core_parts), 8):
                lines.append("  ".join(core_parts[i:i+8]))
            self.card_cpu_cores.set_value("\n".join(lines))
        else:
            self.card_cpu_cores.hide()

        # CPU freq
        freq = m.get('cpu_freq')
        if freq:
            self.card_cpu_freq.set_value(f"\u26A1 {freq:.0f} MHz")
        else:
            self.card_cpu_freq.hide()

        # CPU temp
        cpu_temp = m.get('cpu_temp')
        if cpu_temp is not None:
            self.card_cpu_temp.show()
            self.card_cpu_temp.set_value(f"\U0001F321\uFE0F {cpu_temp:.1f}C")
            self.card_cpu_temp.set_temp_color(cpu_temp, self._cpu_warn, self._cpu_crit)
        else:
            self.card_cpu_temp.hide()

        # RAM
        ram_pct = m.get('ram_percent')
        ram_used = m.get('ram_used_gb')
        ram_total = m.get('ram_total_gb')
        if ram_pct is not None:
            self.card_ram.set_value(f"{ram_pct:.1f}%\n{ram_used} / {ram_total} GB")
        else:
            self.card_ram.hide()

        # GPU load
        gpu_load = m.get('gpu_load')
        if gpu_load is not None:
            self.card_gpu.set_value(f"{gpu_load:.1f}%")
            self.gpu_history.append((now, gpu_load))
            self._prune_history(self.gpu_history, now)
        else:
            self.card_gpu.hide()

        # GPU memory
        gpu_mem = m.get('gpu_mem_used')
        gpu_mem_total = m.get('gpu_mem_total')
        if gpu_mem is not None:
            total = f" / {gpu_mem_total}" if gpu_mem_total else ""
            self.card_gpu_mem.set_value(f"{gpu_mem:.1f}{total} GB")
        elif gpu_mem_total is not None:
            self.card_gpu_mem.set_value(f"— / {gpu_mem_total} GB")
        else:
            self.card_gpu_mem.hide()

        # GPU freq
        gpu_freq = m.get('gpu_freq')
        if gpu_freq is not None:
            self.card_gpu_freq.set_value(f"\u26A1 {gpu_freq} MHz")
        else:
            self.card_gpu_freq.hide()

        # GPU power
        gpu_power = m.get('gpu_power')
        if gpu_power is not None:
            limit = m.get('gpu_power_limit')
            suffix = f" / {limit:.0f}" if limit else ""
            self.card_gpu_power.set_value(f"{gpu_power:.0f}{suffix} W")
        else:
            self.card_gpu_power.hide()

        # GPU voltage
        gpu_voltage = m.get('gpu_voltage')
        if gpu_voltage is not None:
            self.card_gpu_voltage.set_value(f"{gpu_voltage:.3f} V")
        else:
            self.card_gpu_voltage.hide()

        # GPU memory frequency
        gpu_mem_freq = m.get('gpu_mem_freq')
        if gpu_mem_freq is not None:
            self.card_gpu_mem_freq.set_value(f"{gpu_mem_freq} MHz")
        else:
            self.card_gpu_mem_freq.hide()

        # GPU temp
        gpu_temp = m.get('gpu_temp')
        if gpu_temp is not None:
            self.card_gpu_temp.set_value(f"\U0001F321\uFE0F {gpu_temp}C")
            self.card_gpu_temp.set_temp_color(gpu_temp, self._gpu_warn, self._gpu_crit)
        else:
            self.card_gpu_temp.hide()

        # Motherboard temp
        mb_temp = m.get('motherboard_temp')
        if mb_temp is not None:
            self.card_motherboard.set_value(f"\U0001F321\uFE0F {mb_temp}C")
            self.card_motherboard.set_temp_color(mb_temp, 50, 70)
        else:
            self.card_motherboard.hide()

        # VRM temp
        vrm_temp = m.get('vrm_temp')
        if vrm_temp is not None:
            self.card_vrm.set_value(f"\U0001F321\uFE0F {vrm_temp:.1f}C")
            self.card_vrm.set_temp_color(vrm_temp, 60, 90)
        else:
            self.card_vrm.hide()

    def _prune_history(self, hist: list, now: float):
        cutoff = now - self._graph_history
        while hist and hist[0][0] < cutoff:
            hist.pop(0)

    # ------------------------------------------------------------------ #
    def _open_settings(self):
        self.settings_dialog.show()

    def _reset(self):
        self.fps_counter.reset()
        self.cpu_history.clear()
        self.gpu_history.clear()

    def apply_settings(self, settings: dict):
        self.worker.set_interval(settings.get('interval_ms', 100))
        self.overlay.apply_settings(settings)
        self._graph_history = settings.get('graph_history', 60)
        self.fps_counter.set_history_seconds(self._graph_history)

        # Graph visual
        self._graph_fill = settings.get('graph_fill', True)
        self._graph_frametime = settings.get('graph_frametime', False)
        self._graph_grid_x = settings.get('graph_grid_x', False)
        self._graph_grid_y = settings.get('graph_grid_y', True)
        self._graph_legend = settings.get('graph_legend', True)
        self._graph_smooth = settings.get('graph_smooth', True)
        self._graph_fps_color = settings.get('graph_fps_color', '#00FF00')
        self._graph_cpu_color = settings.get('graph_cpu_color', '#FF6600')
        self._graph_gpu_color = settings.get('graph_gpu_color', '#00CCFF')

        # Update curve colors
        self.fps_curve.setPen(pg.mkPen(self._graph_fps_color, width=2))
        self.cpu_curve.setPen(pg.mkPen(self._graph_cpu_color, width=1))
        self.gpu_curve.setPen(pg.mkPen(self._graph_gpu_color, width=1))

        # Temperature thresholds
        self._cpu_warn = settings.get('cpu_warn_temp', 60)
        self._cpu_crit = settings.get('cpu_crit_temp', 80)
        self._gpu_warn = settings.get('gpu_warn_temp', 65)
        self._gpu_crit = settings.get('gpu_crit_temp', 85)

        # Always on top
        if settings.get('always_on_top', False):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

        # CSV logging
        csv_enabled = settings.get('csv_enabled', False)
        csv_interval = settings.get('csv_interval', 1)
        self.csv_logger.set_interval(float(csv_interval))
        self.csv_logger.set_enabled(csv_enabled)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
