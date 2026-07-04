import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QToolBar, QGroupBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction, QColor

import pyqtgraph as pg
import theme
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
        layout.setContentsMargins(12, 8, 12, 10)
        self.lbl_value = QLabel("---")
        self.lbl_value.setFont(QFont(theme.MONO, 14, QFont.Weight.DemiBold))
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_value.setWordWrap(True)
        layout.addWidget(self.lbl_value)

    def set_value(self, text: str):
        self.lbl_value.setText(text)

    def set_temp_color(self, temp, warn, crit):
        state = 'ok' if temp < warn else ('warn' if temp < crit else 'crit')
        value_col = theme.OK if state == 'ok' else (theme.WARN if state == 'warn' else theme.CRIT)
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
        self._graph_fps_color = theme.GRAPH_FPS
        self._graph_cpu_color = theme.GRAPH_CPU
        self._graph_gpu_color = theme.GRAPH_GPU
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

        # App title on the left
        lbl_title = QLabel("FPS MONITOR")
        lbl_title.setStyleSheet(
            f"color: {theme.TEXT}; font-size: 13px; font-weight: 800;"
            "letter-spacing: 2px; padding: 0 10px 0 4px; background: transparent;"
        )
        tb.addWidget(lbl_title)
        tb.addSeparator()

        self.btn_overlay = QAction("Оверлей", self)
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.toggled.connect(self.overlay.toggle)
        tb.addAction(self.btn_overlay)

        btn_settings = QAction("Настройки", self)
        btn_settings.triggered.connect(self._open_settings)
        tb.addAction(btn_settings)

        btn_reset = QAction("Сброс", self)
        btn_reset.triggered.connect(self._reset)
        tb.addAction(btn_reset)

        btn_tray = QAction("В трей", self)
        btn_tray.triggered.connect(self.hide)
        tb.addAction(btn_tray)

        # Status indicator pinned to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        tb.addWidget(spacer)

        self.lbl_status_dot = QLabel("\u25CF")
        self.lbl_status_dot.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 10px; padding-right: 4px; background: transparent;"
        )
        tb.addWidget(self.lbl_status_dot)

        self.lbl_status = QLabel("Запуск…")
        self.lbl_status.setObjectName("statusText")
        self.lbl_status.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 12px; padding-right: 8px; background: transparent;"
        )
        tb.addWidget(self.lbl_status)

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # --- Top: hero FPS card + stats card ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(20, 14, 20, 16)
        hero_l.setSpacing(2)
        cap_fps = QLabel("ТЕКУЩИЙ FPS")
        cap_fps.setProperty("class", "caption")
        hero_l.addWidget(cap_fps)
        self.lbl_fps = QLabel("--")
        self.lbl_fps.setObjectName("fpsValue")
        self.lbl_fps.setFont(QFont(theme.MONO, 56, QFont.Weight.Bold))
        self.lbl_fps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fps.setStyleSheet(f"color: {theme.OK};")
        hero_l.addWidget(self.lbl_fps, stretch=1)
        top_layout.addWidget(hero, stretch=3)

        stats = QFrame()
        stats.setObjectName("statsCard")
        stats_grid = QGridLayout(stats)
        stats_grid.setContentsMargins(18, 14, 18, 14)
        stats_grid.setHorizontalSpacing(28)
        stats_grid.setVerticalSpacing(10)

        stat_items = [
            ("MIN", "lbl_min"), ("MAX", "lbl_max"),
            ("AVG", "lbl_avg"), ("1% LOW", "lbl_1low"),
            ("0.1% LOW", "lbl_01low"), ("FRAMETIME", "lbl_frametime"),
        ]
        for i, (cap_text, attr) in enumerate(stat_items):
            lbl_cap = QLabel(cap_text)
            lbl_cap.setProperty("class", "statLabel")
            lbl_val = QLabel("---")
            lbl_val.setProperty("class", "statValue")
            setattr(self, attr, lbl_val)
            box = QVBoxLayout()
            box.setSpacing(1)
            box.addWidget(lbl_cap)
            box.addWidget(lbl_val)
            row, col = divmod(i, 2)
            stats_grid.addLayout(box, row, col)
        top_layout.addWidget(stats, stretch=2)

        main_layout.addLayout(top_layout)

        # --- Center: FPS Graph ---
        cap_perf = QLabel("ПРОИЗВОДИТЕЛЬНОСТЬ")
        cap_perf.setProperty("class", "caption")
        main_layout.addWidget(cap_perf)

        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        self._style_plot(self.plot, 'FPS / %', 'Время (с)')
        self.fps_curve = self.plot.plot([], [], pen=pg.mkPen(theme.GRAPH_FPS, width=2), name="FPS")
        self.cpu_curve = self.plot.plot([], [], pen=pg.mkPen(theme.GRAPH_CPU, width=1), name="CPU %")
        self.gpu_curve = self.plot.plot([], [], pen=pg.mkPen(theme.GRAPH_GPU, width=1), name="GPU %")
        main_layout.addWidget(self.plot, stretch=2)

        # Frametime graph (optional)
        self.ft_plot = pg.PlotWidget()
        self._style_plot(self.ft_plot, 'ms', 'Время (с)')
        self.ft_curve = self.ft_plot.plot([], [], pen=pg.mkPen(theme.GRAPH_GPU, width=2), name="Frametime")
        self.ft_plot.setVisible(False)
        main_layout.addWidget(self.ft_plot, stretch=1)

        # --- Bottom: Metric cards ---
        cap_sensors = QLabel("ДАТЧИКИ")
        cap_sensors.setProperty("class", "caption")
        main_layout.addWidget(cap_sensors)

        self.cards_widget = QWidget()
        cards_layout = QGridLayout(self.cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(10)
        cards_layout.setVerticalSpacing(8)

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

    def _style_plot(self, plot, left_label: str, bottom_label: str):
        """Apply the app theme to a pyqtgraph PlotWidget."""
        plot.setBackground(theme.BG_1)
        for name in ('left', 'bottom'):
            ax = plot.getAxis(name)
            ax.setPen(pg.mkPen(theme.BORDER))
            ax.setTextPen(pg.mkPen(theme.TEXT_DIM))
        label_style = {'color': theme.TEXT_DIM, 'font-size': '11px'}
        plot.setLabel('left', left_label, **label_style)
        plot.setLabel('bottom', bottom_label, **label_style)

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
        color = theme.CRIT if problem else theme.TEXT_DIM
        dot_color = theme.CRIT if problem else theme.OK
        self.lbl_status.setStyleSheet(
            f"color: {color}; font-size: 12px; padding-right: 8px; background: transparent;"
        )
        self.lbl_status_dot.setStyleSheet(
            f"color: {dot_color}; font-size: 10px; padding-right: 4px; background: transparent;"
        )

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
            col = theme.OK if fps >= 60 else (theme.WARN if fps >= 30 else theme.CRIT)
            self.lbl_fps.setStyleSheet(f"color: {col};")
        self.lbl_min.setText(str(self.fps_counter.minimum or '---'))
        self.lbl_max.setText(str(self.fps_counter.maximum or '---'))
        self.lbl_avg.setText(str(self.fps_counter.average or '---'))
        self.lbl_1low.setText(str(self.fps_counter.one_pct_low or '---'))
        self.lbl_01low.setText(str(self.fps_counter.zero_one_pct_low or '---'))
        ft = self.fps_counter.frametime_avg
        if ft > 0:
            self.lbl_frametime.setText(f"{ft:.2f} ms")
        else:
            self.lbl_frametime.setText("--- ms")

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
                pen = pg.mkPen(theme.GRAPH_GPU, width=2)
                self.ft_curve.setData(x, y, pen=pen)
                self.ft_curve.setFillLevel(0)
                ft_fill = QColor(theme.GRAPH_GPU)
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
        self._graph_fps_color = settings.get('graph_fps_color', theme.GRAPH_FPS)
        self._graph_cpu_color = settings.get('graph_cpu_color', theme.GRAPH_CPU)
        self._graph_gpu_color = settings.get('graph_gpu_color', theme.GRAPH_GPU)

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
