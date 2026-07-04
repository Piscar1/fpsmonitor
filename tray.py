from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QTimer


class TrayIcon(QSystemTrayIcon):
    """Системный трей с динамической иконкой FPS."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._fps = 0
        self._setup_tray()

        # Timer for updating tray icon
        self._icon_timer = QTimer(self)
        self._icon_timer.timeout.connect(self._update_icon)
        self._icon_timer.start(500)

    def _setup_tray(self):
        self._update_icon()
        self.setToolTip("FPS Monitor")

        menu = QMenu()

        action_show = QAction("\U0001F441 Показать", self)
        action_show.triggered.connect(self._show_window)
        menu.addAction(action_show)

        action_overlay = QAction("\U0001F4F7 Оверлей", self)
        action_overlay.setCheckable(True)
        action_overlay.toggled.connect(self.main_window.overlay.toggle)
        menu.addAction(action_overlay)

        menu.addSeparator()

        action_settings = QAction("\u2699 Настройки", self)
        action_settings.triggered.connect(self.main_window._open_settings)
        menu.addAction(action_settings)

        menu.addSeparator()

        action_quit = QAction("\u274C Выход", self)
        action_quit.triggered.connect(self._quit_app)
        menu.addAction(action_quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _update_icon(self):
        """Рисует иконку с текущим FPS."""
        self._fps = self.main_window.fps_counter.current

        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background circle with color based on FPS
        if self._fps > 0:
            color = QColor(0, 255, 0) if self._fps >= 60 else (QColor(255, 170, 0) if self._fps >= 30 else QColor(255, 80, 80))
        else:
            color = QColor(80, 80, 80)

        painter.setBrush(color)
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawEllipse(3, 3, 26, 26)

        # FPS text
        font = QFont("Consolas", 7, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        text = str(self._fps) if self._fps > 0 else "--"
        if self._fps >= 100:
            font.setPointSize(6)
            painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)

        painter.end()
        self.setIcon(QIcon(pixmap))

    def _show_window(self):
        self.main_window.show()
        self.main_window.setWindowState(Qt.WindowState.WindowActive)
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _quit_app(self):
        self.main_window.worker.stop()
        if hasattr(self.main_window, "fps_source"):
            self.main_window.fps_source.stop()
        self.main_window.csv_logger.stop()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()
