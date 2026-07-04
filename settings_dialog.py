from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QCheckBox, QComboBox, QGroupBox,
    QColorDialog, QPushButton, QFormLayout, QLineEdit, QSlider,
    QScrollArea, QSizeGrip
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QSettings


THEME_NAMES = [
    ("default", "Зелёный (по умолчанию)"),
    ("dark_blue", "Тёмно-синий"),
    ("cyberpunk", "Киберпанк"),
    ("nordic", "Nordic"),
    ("solarized", "Solarized"),
    ("matrix", "Matrix"),
    ("dracula", "Dracula"),
    ("synthwave", "Synthwave"),
    ("amoled", "AMOLED (чёрный)"),
    ("inferno", "Inferno (огонь)"),
    ("ice", "Ice (лёд)"),
    ("gold", "Gold (золото)"),
    ("mint", "Mint (мята)"),
    ("crimson", "Crimson (багровый)"),
    ("purple_haze", "Purple Haze"),
    ("clean_light", "Clean Light (светлая)"),
]

BAR_STYLE_NAMES = [
    ("rounded", "Закруглённые"),
    ("square", "Квадратные"),
    ("thin", "Тонкие линии"),
]


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("FPSMonitor", "FPSMonitor")
        self.setWindowTitle("Настройки")
        # Адекватный стартовый размер + маленький минимум, чтобы окно
        # можно было свободно растягивать и сжимать.
        self.setMinimumSize(420, 320)
        self.resize(560, 600)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # Каждую вкладку оборачиваем в прокручиваемую область, чтобы
        # содержимое не задавало огромную минимальную высоту окна.
        tabs.addTab(self._scroll(self._tab_general()), "Общие")
        tabs.addTab(self._scroll(self._tab_overlay()), "Оверлей")
        tabs.addTab(self._scroll(self._tab_visual()), "Визуализация")
        tabs.addTab(self._scroll(self._tab_metrics()), "Метрики")
        tabs.addTab(self._scroll(self._tab_logging()), "Логирование")

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("Применить")
        btn_ok.clicked.connect(self._apply_and_save)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        # Уголовой захват для удобного растягивания.
        btn_layout.addWidget(QSizeGrip(self))
        layout.addLayout(btn_layout)

    def _scroll(self, inner: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setWidget(inner)
        return area

    # --- General tab ---
    def _tab_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group = QGroupBox("Обновление")
        form = QFormLayout(group)
        self.cb_interval = QSpinBox()
        self.cb_interval.setRange(50, 1000)
        self.cb_interval.setSingleStep(50)
        self.cb_interval.setSuffix(" мс")
        form.addRow("Интервал опроса:", self.cb_interval)

        group2 = QGroupBox("Запуск")
        form2 = QFormLayout(group2)
        self.cb_minimize_tray = QCheckBox("Сворачивать в трей при запуске")
        self.cb_overlay_start = QCheckBox("Запускать оверлей сразу")
        self.cb_always_on_top = QCheckBox("Главное окно поверх всех окон")
        form2.addRow(self.cb_minimize_tray)
        form2.addRow(self.cb_overlay_start)
        form2.addRow(self.cb_always_on_top)

        layout.addWidget(group)
        layout.addWidget(group2)
        layout.addStretch()
        return w

    # --- Overlay tab ---
    def _tab_overlay(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group = QGroupBox("Позиция и размер")
        form = QFormLayout(group)
        self.cb_position = QComboBox()
        for pos in ["Топ-Лево", "Топ-Центр", "Топ-Право",
                    "Центр", "Бот-Лево", "Бот-Центр", "Бот-Право"]:
            self.cb_position.addItem(pos)
        form.addRow("Позиция:", self.cb_position)

        self.cb_font_size = QSpinBox()
        self.cb_font_size.setRange(8, 48)
        self.cb_font_size.setSuffix(" px")
        form.addRow("Размер шрифта:", self.cb_font_size)

        layout.addWidget(group)

        group_theme = QGroupBox("Цветовая тема")
        form_theme = QFormLayout(group_theme)
        self.cb_theme = QComboBox()
        for key, label in THEME_NAMES:
            self.cb_theme.addItem(label, key)
        self.cb_theme.currentIndexChanged.connect(self._on_theme_changed)
        form_theme.addRow("Тема:", self.cb_theme)

        self.cb_use_custom_colors = QCheckBox("Использовать свои цвета вместо темы")
        self.cb_use_custom_colors.toggled.connect(self._toggle_custom_colors)
        form_theme.addRow(self.cb_use_custom_colors)

        btn_fg = QPushButton("Выбрать цвет текста")
        btn_fg.clicked.connect(lambda: self._pick_color('overlay_fg', btn_fg))
        self.lbl_fg = QLabel("\u25A0")
        self.lbl_fg.setStyleSheet("font-size: 16px; color: #00FF00;")
        h_fg = QHBoxLayout()
        h_fg.addWidget(btn_fg)
        h_fg.addWidget(self.lbl_fg)
        form_theme.addRow("Текст:", h_fg)

        btn_bg = QPushButton("Выбрать цвет фона")
        btn_bg.clicked.connect(lambda: self._pick_color('overlay_bg', btn_bg))
        self.lbl_bg = QLabel("\u25A0")
        self.lbl_bg.setStyleSheet("font-size: 16px; color: #000000;")
        self.cb_bg_alpha = QSpinBox()
        self.cb_bg_alpha.setRange(0, 255)
        self.cb_bg_alpha.setSuffix(" (\u03B1)")
        h_bg = QHBoxLayout()
        h_bg.addWidget(btn_bg)
        h_bg.addWidget(self.lbl_bg)
        h_bg.addWidget(QLabel("Прозрачность:"))
        h_bg.addWidget(self.cb_bg_alpha)
        form_theme.addRow("Фон:", h_bg)

        layout.addWidget(group_theme)

        group_custom_names = QGroupBox("Названия в оверлее")
        form_names = QFormLayout(group_custom_names)
        self.txt_custom_cpu = QLineEdit()
        self.txt_custom_cpu.setPlaceholderText("Оставить пустым для авто-определения")
        self.txt_custom_gpu = QLineEdit()
        self.txt_custom_gpu.setPlaceholderText("Оставить пустым для авто-определения")
        form_names.addRow("Название CPU:", self.txt_custom_cpu)
        form_names.addRow("Название GPU:", self.txt_custom_gpu)
        layout.addWidget(group_custom_names)

        group_metrics = QGroupBox("Метрики в оверлее")
        form_metrics = QFormLayout(group_metrics)
        self.cb_show_fps = QCheckBox("Показывать FPS")
        self.cb_show_cpu = QCheckBox("Показывать CPU загрузку")
        self.cb_show_ram = QCheckBox("Показывать RAM")
        self.cb_show_gpu = QCheckBox("Показывать GPU загрузку")
        self.cb_show_vram = QCheckBox("Показывать VRAM (видеопамять)")
        self.cb_show_gpu_power = QCheckBox("Показывать энергопотребление GPU (Вт)")
        self.cb_show_gpu_voltage = QCheckBox("Показывать напряжение GPU (В)")
        self.cb_show_gpu_mem_freq = QCheckBox("Показывать частоту памяти GPU")
        self.cb_show_app_name = QCheckBox("Показывать имя приложения")
        form_metrics.addRow(self.cb_show_fps)
        form_metrics.addRow(self.cb_show_cpu)
        form_metrics.addRow(self.cb_show_ram)
        form_metrics.addRow(self.cb_show_gpu)
        form_metrics.addRow(self.cb_show_vram)
        form_metrics.addRow(self.cb_show_gpu_power)
        form_metrics.addRow(self.cb_show_gpu_voltage)
        form_metrics.addRow(self.cb_show_gpu_mem_freq)
        form_metrics.addRow(self.cb_show_app_name)
        layout.addWidget(group_metrics)

        group_temps = QGroupBox("Температуры")
        form_temps = QFormLayout(group_temps)
        self.cb_show_cpu_temp = QCheckBox("Температура CPU")
        self.cb_show_gpu_temp = QCheckBox("Температура GPU")
        self.cb_show_mb_temp = QCheckBox("Температура материнки")
        self.cb_show_vrm_temp = QCheckBox("Температура VRM")
        form_temps.addRow(self.cb_show_cpu_temp)
        form_temps.addRow(self.cb_show_gpu_temp)
        form_temps.addRow(self.cb_show_mb_temp)
        form_temps.addRow(self.cb_show_vrm_temp)
        layout.addWidget(group_temps)

        group_freqs = QGroupBox("Частоты")
        form_freqs = QFormLayout(group_freqs)
        self.cb_show_cpu_freq = QCheckBox("Частота CPU")
        self.cb_show_gpu_freq = QCheckBox("Частота GPU")
        form_freqs.addRow(self.cb_show_cpu_freq)
        form_freqs.addRow(self.cb_show_gpu_freq)
        layout.addWidget(group_freqs)

        group_advanced = QGroupBox("Расширенные метрики FPS")
        form_adv = QFormLayout(group_advanced)
        self.cb_show_1low = QCheckBox("1% low FPS")
        self.cb_show_01low = QCheckBox("0.1% low FPS")
        self.cb_show_frametime = QCheckBox("Frametime (мс)")
        form_adv.addRow(self.cb_show_1low)
        form_adv.addRow(self.cb_show_01low)
        form_adv.addRow(self.cb_show_frametime)
        layout.addWidget(group_advanced)

        layout.addStretch()
        return w

    # --- Visual (Visualization) tab ---
    def _tab_visual(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group_graph = QGroupBox("График")
        form_graph = QFormLayout(group_graph)
        self.cb_history = QSpinBox()
        self.cb_history.setRange(5, 300)
        self.cb_history.setSuffix(" сек")
        form_graph.addRow("История графика:", self.cb_history)

        self.cb_graph_fill = QCheckBox("Заливка под графиком")
        self.cb_graph_frametime = QCheckBox("График Frametime (отдельный)")
        self.cb_graph_grid_x = QCheckBox("Сетка по X")
        self.cb_graph_grid_y = QCheckBox("Сетка по Y")
        self.cb_graph_legend = QCheckBox("Легенда")
        self.cb_graph_smooth = QCheckBox("Сглаживание линий")
        form_graph.addRow(self.cb_graph_fill)
        form_graph.addRow(self.cb_graph_frametime)
        form_graph.addRow(self.cb_graph_grid_x)
        form_graph.addRow(self.cb_graph_grid_y)
        form_graph.addRow(self.cb_graph_legend)
        form_graph.addRow(self.cb_graph_smooth)
        layout.addWidget(group_graph)

        group_colors = QGroupBox("Цвета графика")
        form_colors = QFormLayout(group_colors)

        btn_graph_fps = QPushButton("Выбрать")
        btn_graph_fps.clicked.connect(lambda: self._pick_color('graph_fps_color', btn_graph_fps))
        self.lbl_graph_fps = QLabel("\u25A0")
        self.lbl_graph_fps.setStyleSheet("font-size: 16px; color: #2BD576;")
        h_fps = QHBoxLayout(); h_fps.addWidget(btn_graph_fps); h_fps.addWidget(self.lbl_graph_fps)
        form_colors.addRow("FPS:", h_fps)

        btn_graph_cpu = QPushButton("Выбрать")
        btn_graph_cpu.clicked.connect(lambda: self._pick_color('graph_cpu_color', btn_graph_cpu))
        self.lbl_graph_cpu = QLabel("\u25A0")
        self.lbl_graph_cpu.setStyleSheet("font-size: 16px; color: #FF8A3D;")
        h_cpu = QHBoxLayout(); h_cpu.addWidget(btn_graph_cpu); h_cpu.addWidget(self.lbl_graph_cpu)
        form_colors.addRow("CPU:", h_cpu)

        btn_graph_gpu = QPushButton("Выбрать")
        btn_graph_gpu.clicked.connect(lambda: self._pick_color('graph_gpu_color', btn_graph_gpu))
        self.lbl_graph_gpu = QLabel("\u25A0")
        self.lbl_graph_gpu.setStyleSheet("font-size: 16px; color: #38BDF8;")
        h_gpu = QHBoxLayout(); h_gpu.addWidget(btn_graph_gpu); h_gpu.addWidget(self.lbl_graph_gpu)
        form_colors.addRow("GPU:", h_gpu)

        layout.addWidget(group_colors)

        group_bar = QGroupBox("Прогресс-бары в оверлее")
        form_bar = QFormLayout(group_bar)
        self.cb_show_progress_bars = QCheckBox("Показывать прогресс-бары")
        self.cb_show_frametime_bar = QCheckBox("Показывать bar frametime")
        self.cb_bar_style = QComboBox()
        for key, label in BAR_STYLE_NAMES:
            self.cb_bar_style.addItem(label, key)
        form_bar.addRow(self.cb_show_progress_bars)
        form_bar.addRow(self.cb_show_frametime_bar)
        form_bar.addRow("Стиль баров:", self.cb_bar_style)

        self.cb_border_radius = QSpinBox()
        self.cb_border_radius.setRange(0, 30)
        self.cb_border_radius.setSuffix(" px")
        form_bar.addRow("Радиус скругления:", self.cb_border_radius)

        self.cb_overlay_border = QCheckBox("Показывать рамку")
        self.cb_overlay_gradient = QCheckBox("Градиентный фон")
        form_bar.addRow(self.cb_overlay_border)
        form_bar.addRow(self.cb_overlay_gradient)

        self.cb_overlay_opacity = QSlider()
        self.cb_overlay_opacity.setRange(20, 100)
        lbl_opacity = QLabel("100%")
        self.cb_overlay_opacity.valueChanged.connect(lambda v: lbl_opacity.setText(f"{v}%"))
        h_op = QHBoxLayout(); h_op.addWidget(self.cb_overlay_opacity); h_op.addWidget(lbl_opacity)
        form_bar.addRow("Непрозрачность:", h_op)

        layout.addWidget(group_bar)
        layout.addStretch()
        return w

    # --- Metrics tab ---
    def _tab_metrics(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group = QGroupBox("Сбор метрик")
        form = QFormLayout(group)
        self.cb_collect_cpu = QCheckBox("CPU")
        self.cb_collect_gpu = QCheckBox("GPU")
        self.cb_collect_ram = QCheckBox("RAM")
        self.cb_collect_temp = QCheckBox("Температуры")
        form.addRow(self.cb_collect_cpu)
        form.addRow(self.cb_collect_gpu)
        form.addRow(self.cb_collect_ram)
        form.addRow(self.cb_collect_temp)
        layout.addWidget(group)

        group_thresh = QGroupBox("Пороги температур (C)")
        form_thresh = QFormLayout(group_thresh)
        self.cb_cpu_warn = QSpinBox(); self.cb_cpu_warn.setRange(30, 100); self.cb_cpu_warn.setSuffix(" C")
        self.cb_cpu_crit = QSpinBox(); self.cb_cpu_crit.setRange(50, 120); self.cb_cpu_crit.setSuffix(" C")
        self.cb_gpu_warn = QSpinBox(); self.cb_gpu_warn.setRange(30, 100); self.cb_gpu_warn.setSuffix(" C")
        self.cb_gpu_crit = QSpinBox(); self.cb_gpu_crit.setRange(50, 120); self.cb_gpu_crit.setSuffix(" C")
        form_thresh.addRow("CPU предупреждение:", self.cb_cpu_warn)
        form_thresh.addRow("CPU критично:", self.cb_cpu_crit)
        form_thresh.addRow("GPU предупреждение:", self.cb_gpu_warn)
        form_thresh.addRow("GPU критично:", self.cb_gpu_crit)
        layout.addWidget(group_thresh)

        layout.addStretch()
        return w

    # --- Logging tab ---
    def _tab_logging(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group = QGroupBox("CSV-логирование")
        form = QFormLayout(group)
        self.cb_csv_enabled = QCheckBox("Включить логирование в CSV")
        self.cb_csv_interval = QSpinBox()
        self.cb_csv_interval.setRange(1, 60)
        self.cb_csv_interval.setSuffix(" сек")
        form.addRow(self.cb_csv_enabled)
        form.addRow("Интервал записи:", self.cb_csv_interval)

        info = QLabel(
            "Файлы сохраняются в папку logs/ рядом со скриптом.\n"
            "Имя файла: fps_monitor_дата_время.csv\n\n"
            "Формат: timestamp, FPS, min/max/avg, 1% low, 0.1% low,\n"
            "frametime, CPU, RAM, GPU, температуры и т.д."
        )
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        form.addRow(info)

        layout.addWidget(group)
        layout.addStretch()
        return w

    # -- Helpers --
    def _on_theme_changed(self):
        key = self.cb_theme.currentData()
        from overlay import THEMES
        theme = THEMES.get(key, THEMES['default'])
        self.lbl_fg.setStyleSheet(f"font-size: 16px; color: {theme['fg']};")
        self.lbl_bg.setStyleSheet(f"font-size: 16px; color: {theme['bg']};")

    def _toggle_custom_colors(self, checked):
        pass

    def _pick_color(self, key, btn):
        current = self.settings.value(key, '#00FF00')
        color = QColorDialog.getColor(QColor(current), self, "Выберите цвет")
        if color.isValid():
            self.settings.setValue(key, color.name())
            if key == 'overlay_fg':
                self.lbl_fg.setStyleSheet(f"font-size: 16px; color: {color.name()};")
            elif key == 'overlay_bg':
                self.lbl_bg.setStyleSheet(f"font-size: 16px; color: {color.name()};")
            elif key == 'graph_fps_color':
                self.lbl_graph_fps.setStyleSheet(f"font-size: 16px; color: {color.name()};")
            elif key == 'graph_cpu_color':
                self.lbl_graph_cpu.setStyleSheet(f"font-size: 16px; color: {color.name()};")
            elif key == 'graph_gpu_color':
                self.lbl_graph_gpu.setStyleSheet(f"font-size: 16px; color: {color.name()};")

    def _load_settings(self):
        self.cb_interval.setValue(int(self.settings.value("interval_ms", 100)))
        self.cb_minimize_tray.setChecked(self.settings.value("minimize_tray", False, type=bool))
        self.cb_overlay_start.setChecked(self.settings.value("overlay_start", False, type=bool))
        self.cb_always_on_top.setChecked(self.settings.value("always_on_top", False, type=bool))

        pos_map = ["Топ-Лево", "Топ-Центр", "Топ-Право", "Центр", "Бот-Лево", "Бот-Центр", "Бот-Право"]
        pos_idx = int(self.settings.value("overlay_position", 0))
        self.cb_position.setCurrentIndex(min(pos_idx, len(pos_map) - 1))
        self.cb_font_size.setValue(int(self.settings.value("overlay_font_size", 14)))
        self.cb_bg_alpha.setValue(int(self.settings.value("overlay_bg_alpha", 128)))

        theme_key = self.settings.value("overlay_theme", "default")
        for i in range(self.cb_theme.count()):
            if self.cb_theme.itemData(i) == theme_key:
                self.cb_theme.setCurrentIndex(i)
                break

        self.cb_use_custom_colors.setChecked(self.settings.value("overlay_use_custom_colors", False, type=bool))

        fg = self.settings.value("overlay_fg", "#00FF00")
        self.lbl_fg.setStyleSheet(f"font-size: 16px; color: {fg};")
        bg = self.settings.value("overlay_bg", "#000000")
        self.lbl_bg.setStyleSheet(f"font-size: 16px; color: {bg};")

        self.cb_show_fps.setChecked(self.settings.value("show_fps", True, type=bool))
        self.cb_show_cpu.setChecked(self.settings.value("show_cpu", True, type=bool))
        self.cb_show_ram.setChecked(self.settings.value("show_ram", True, type=bool))
        self.cb_show_gpu.setChecked(self.settings.value("show_gpu", True, type=bool))
        self.cb_show_vram.setChecked(self.settings.value("show_vram", True, type=bool))
        self.cb_show_gpu_power.setChecked(self.settings.value("show_gpu_power", True, type=bool))
        self.cb_show_gpu_voltage.setChecked(self.settings.value("show_gpu_voltage", True, type=bool))
        self.cb_show_gpu_mem_freq.setChecked(self.settings.value("show_gpu_mem_freq", True, type=bool))
        self.cb_show_cpu_temp.setChecked(self.settings.value("show_cpu_temp", True, type=bool))
        self.cb_show_gpu_temp.setChecked(self.settings.value("show_gpu_temp", True, type=bool))
        self.cb_show_mb_temp.setChecked(self.settings.value("show_mb_temp", True, type=bool))
        self.cb_show_vrm_temp.setChecked(self.settings.value("show_vrm_temp", True, type=bool))
        self.cb_show_cpu_freq.setChecked(self.settings.value("show_cpu_freq", True, type=bool))
        self.cb_show_gpu_freq.setChecked(self.settings.value("show_gpu_freq", True, type=bool))
        self.cb_show_1low.setChecked(self.settings.value("show_1low", True, type=bool))
        self.cb_show_01low.setChecked(self.settings.value("show_01low", True, type=bool))
        self.cb_show_frametime.setChecked(self.settings.value("show_frametime", True, type=bool))
        self.cb_show_app_name.setChecked(self.settings.value("show_app_name", True, type=bool))

        self.txt_custom_cpu.setText(self.settings.value("custom_cpu_name", ""))
        self.txt_custom_gpu.setText(self.settings.value("custom_gpu_name", ""))

        self.cb_collect_cpu.setChecked(self.settings.value("collect_cpu", True, type=bool))
        self.cb_collect_gpu.setChecked(self.settings.value("collect_gpu", True, type=bool))
        self.cb_collect_ram.setChecked(self.settings.value("collect_ram", True, type=bool))
        self.cb_collect_temp.setChecked(self.settings.value("collect_temp", True, type=bool))
        self.cb_history.setValue(int(self.settings.value("graph_history", 60)))

        self.cb_graph_fill.setChecked(self.settings.value("graph_fill", True, type=bool))
        self.cb_graph_frametime.setChecked(self.settings.value("graph_frametime", False, type=bool))
        self.cb_graph_grid_x.setChecked(self.settings.value("graph_grid_x", False, type=bool))
        self.cb_graph_grid_y.setChecked(self.settings.value("graph_grid_y", True, type=bool))
        self.cb_graph_legend.setChecked(self.settings.value("graph_legend", True, type=bool))
        self.cb_graph_smooth.setChecked(self.settings.value("graph_smooth", True, type=bool))

        defaults = {'graph_fps_color': '#2BD576', 'graph_cpu_color': '#FF8A3D', 'graph_gpu_color': '#38BDF8'}
        for key, lbl in [('graph_fps_color', self.lbl_graph_fps),
                        ('graph_cpu_color', self.lbl_graph_cpu),
                        ('graph_gpu_color', self.lbl_graph_gpu)]:
            c = self.settings.value(key, defaults[key])
            lbl.setStyleSheet(f"font-size: 16px; color: {c};")

        self.cb_show_progress_bars.setChecked(self.settings.value("show_progress_bars", True, type=bool))
        self.cb_show_frametime_bar.setChecked(self.settings.value("show_frametime_bar", True, type=bool))
        bar_style = self.settings.value("overlay_bar_style", "rounded")
        for i in range(self.cb_bar_style.count()):
            if self.cb_bar_style.itemData(i) == bar_style:
                self.cb_bar_style.setCurrentIndex(i)
                break

        self.cb_border_radius.setValue(int(self.settings.value("overlay_border_radius", 12)))
        self.cb_overlay_border.setChecked(self.settings.value("overlay_show_border", True, type=bool))
        self.cb_overlay_gradient.setChecked(self.settings.value("overlay_show_gradient", True, type=bool))
        self.cb_overlay_opacity.setValue(int(self.settings.value("overlay_opacity", 100)))

        self.cb_cpu_warn.setValue(int(self.settings.value("cpu_warn_temp", 60)))
        self.cb_cpu_crit.setValue(int(self.settings.value("cpu_crit_temp", 80)))
        self.cb_gpu_warn.setValue(int(self.settings.value("gpu_warn_temp", 65)))
        self.cb_gpu_crit.setValue(int(self.settings.value("gpu_crit_temp", 85)))

        self.cb_csv_enabled.setChecked(self.settings.value("csv_enabled", False, type=bool))
        self.cb_csv_interval.setValue(int(self.settings.value("csv_interval", 1)))

    def _apply_and_save(self):
        self._save_settings()
        if self.parent():
            self.parent().apply_settings(self.get_settings())
        self.close()

    def _save_settings(self):
        self.settings.setValue("interval_ms", self.cb_interval.value())
        self.settings.setValue("minimize_tray", self.cb_minimize_tray.isChecked())
        self.settings.setValue("overlay_start", self.cb_overlay_start.isChecked())
        self.settings.setValue("always_on_top", self.cb_always_on_top.isChecked())
        self.settings.setValue("overlay_position", self.cb_position.currentIndex())
        self.settings.setValue("overlay_font_size", self.cb_font_size.value())
        self.settings.setValue("overlay_bg_alpha", self.cb_bg_alpha.value())

        self.settings.setValue("overlay_theme", self.cb_theme.currentData())
        self.settings.setValue("overlay_use_custom_colors", self.cb_use_custom_colors.isChecked())

        self.settings.setValue("show_fps", self.cb_show_fps.isChecked())
        self.settings.setValue("show_cpu", self.cb_show_cpu.isChecked())
        self.settings.setValue("show_ram", self.cb_show_ram.isChecked())
        self.settings.setValue("show_gpu", self.cb_show_gpu.isChecked())
        self.settings.setValue("show_vram", self.cb_show_vram.isChecked())
        self.settings.setValue("show_gpu_power", self.cb_show_gpu_power.isChecked())
        self.settings.setValue("show_gpu_voltage", self.cb_show_gpu_voltage.isChecked())
        self.settings.setValue("show_gpu_mem_freq", self.cb_show_gpu_mem_freq.isChecked())
        self.settings.setValue("show_cpu_temp", self.cb_show_cpu_temp.isChecked())
        self.settings.setValue("show_gpu_temp", self.cb_show_gpu_temp.isChecked())
        self.settings.setValue("show_mb_temp", self.cb_show_mb_temp.isChecked())
        self.settings.setValue("show_vrm_temp", self.cb_show_vrm_temp.isChecked())
        self.settings.setValue("show_cpu_freq", self.cb_show_cpu_freq.isChecked())
        self.settings.setValue("show_gpu_freq", self.cb_show_gpu_freq.isChecked())
        self.settings.setValue("show_1low", self.cb_show_1low.isChecked())
        self.settings.setValue("show_01low", self.cb_show_01low.isChecked())
        self.settings.setValue("show_frametime", self.cb_show_frametime.isChecked())
        self.settings.setValue("show_app_name", self.cb_show_app_name.isChecked())

        self.settings.setValue("custom_cpu_name", self.txt_custom_cpu.text())
        self.settings.setValue("custom_gpu_name", self.txt_custom_gpu.text())
        self.settings.setValue("collect_cpu", self.cb_collect_cpu.isChecked())
        self.settings.setValue("collect_gpu", self.cb_collect_gpu.isChecked())
        self.settings.setValue("collect_ram", self.cb_collect_ram.isChecked())
        self.settings.setValue("collect_temp", self.cb_collect_temp.isChecked())
        self.settings.setValue("graph_history", self.cb_history.value())

        self.settings.setValue("graph_fill", self.cb_graph_fill.isChecked())
        self.settings.setValue("graph_frametime", self.cb_graph_frametime.isChecked())
        self.settings.setValue("graph_grid_x", self.cb_graph_grid_x.isChecked())
        self.settings.setValue("graph_grid_y", self.cb_graph_grid_y.isChecked())
        self.settings.setValue("graph_legend", self.cb_graph_legend.isChecked())
        self.settings.setValue("graph_smooth", self.cb_graph_smooth.isChecked())

        self.settings.setValue("show_progress_bars", self.cb_show_progress_bars.isChecked())
        self.settings.setValue("show_frametime_bar", self.cb_show_frametime_bar.isChecked())
        self.settings.setValue("overlay_bar_style", self.cb_bar_style.currentData())
        self.settings.setValue("overlay_border_radius", self.cb_border_radius.value())
        self.settings.setValue("overlay_show_border", self.cb_overlay_border.isChecked())
        self.settings.setValue("overlay_show_gradient", self.cb_overlay_gradient.isChecked())
        self.settings.setValue("overlay_opacity", self.cb_overlay_opacity.value())

        self.settings.setValue("cpu_warn_temp", self.cb_cpu_warn.value())
        self.settings.setValue("cpu_crit_temp", self.cb_cpu_crit.value())
        self.settings.setValue("gpu_warn_temp", self.cb_gpu_warn.value())
        self.settings.setValue("gpu_crit_temp", self.cb_gpu_crit.value())

        self.settings.setValue("csv_enabled", self.cb_csv_enabled.isChecked())
        self.settings.setValue("csv_interval", self.cb_csv_interval.value())

    def get_settings(self) -> dict:
        return {
            'interval_ms': self.cb_interval.value(),
            'minimize_tray': self.cb_minimize_tray.isChecked(),
            'overlay_start': self.cb_overlay_start.isChecked(),
            'always_on_top': self.cb_always_on_top.isChecked(),
            'overlay_position': self.cb_position.currentIndex(),
            'overlay_font_size': self.cb_font_size.value(),
            'overlay_fg': self.settings.value("overlay_fg", "#00FF00"),
            'overlay_bg': self.settings.value("overlay_bg", "#000000"),
            'overlay_bg_alpha': self.cb_bg_alpha.value(),
            'overlay_theme': self.cb_theme.currentData() if hasattr(self, 'cb_theme') and self.cb_theme.currentIndex() >= 0 else "default",
            'overlay_use_custom_colors': self.cb_use_custom_colors.isChecked() if hasattr(self, 'cb_use_custom_colors') else False,
            'show_fps': self.cb_show_fps.isChecked(),
            'show_cpu': self.cb_show_cpu.isChecked(),
            'show_ram': self.cb_show_ram.isChecked(),
            'show_gpu': self.cb_show_gpu.isChecked(),
            'show_vram': self.cb_show_vram.isChecked(),
            'show_gpu_power': self.cb_show_gpu_power.isChecked(),
            'show_gpu_voltage': self.cb_show_gpu_voltage.isChecked(),
            'show_gpu_mem_freq': self.cb_show_gpu_mem_freq.isChecked(),
            'show_cpu_temp': self.cb_show_cpu_temp.isChecked(),
            'show_gpu_temp': self.cb_show_gpu_temp.isChecked(),
            'show_mb_temp': self.cb_show_mb_temp.isChecked(),
            'show_vrm_temp': self.cb_show_vrm_temp.isChecked(),
            'show_cpu_freq': self.cb_show_cpu_freq.isChecked(),
            'show_gpu_freq': self.cb_show_gpu_freq.isChecked(),
            'show_1low': self.cb_show_1low.isChecked(),
            'show_01low': self.cb_show_01low.isChecked(),
            'show_frametime': self.cb_show_frametime.isChecked(),
            'show_app_name': self.cb_show_app_name.isChecked(),
            'custom_cpu_name': self.txt_custom_cpu.text(),
            'custom_gpu_name': self.txt_custom_gpu.text(),
            'graph_history': self.cb_history.value(),
            'graph_fill': self.cb_graph_fill.isChecked(),
            'graph_frametime': self.cb_graph_frametime.isChecked(),
            'graph_grid_x': self.cb_graph_grid_x.isChecked(),
            'graph_grid_y': self.cb_graph_grid_y.isChecked(),
            'graph_legend': self.cb_graph_legend.isChecked(),
            'graph_smooth': self.cb_graph_smooth.isChecked(),
            'graph_fps_color': self.settings.value("graph_fps_color", "#2BD576"),
            'graph_cpu_color': self.settings.value("graph_cpu_color", "#FF8A3D"),
            'graph_gpu_color': self.settings.value("graph_gpu_color", "#38BDF8"),
            'show_progress_bars': self.cb_show_progress_bars.isChecked(),
            'show_frametime_bar': self.cb_show_frametime_bar.isChecked(),
            'overlay_bar_style': self.cb_bar_style.currentData(),
            'overlay_border_radius': self.cb_border_radius.value(),
            'overlay_show_border': self.cb_overlay_border.isChecked(),
            'overlay_show_gradient': self.cb_overlay_gradient.isChecked(),
            'overlay_opacity': self.cb_overlay_opacity.value() / 100.0,
            'cpu_warn_temp': self.cb_cpu_warn.value(),
            'cpu_crit_temp': self.cb_cpu_crit.value(),
            'gpu_warn_temp': self.cb_gpu_warn.value(),
            'gpu_crit_temp': self.cb_gpu_crit.value(),
            'csv_enabled': self.cb_csv_enabled.isChecked(),
            'csv_interval': self.cb_csv_interval.value(),
        }
