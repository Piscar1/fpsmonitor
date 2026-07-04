import sys
import os
import ctypes
import traceback


def _fatal_error(exc_text: str):
    """Записывает ошибку в crash.log рядом с программой и показывает окно."""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(exc_text)
    except OSError:
        pass
    # Показываем ошибку: сначала пробуем Qt, потом нативный MessageBox
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None, "FPS Monitor — ошибка запуска",
            f"Программа не смогла запуститься.\n\n{exc_text}\n\nЛог сохранён: {log_path}",
        )
    except Exception:
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                f"Ошибка запуска:\n\n{exc_text}\n\nЛог: {log_path}",
                "FPS Monitor — ошибка запуска",
                0x10,
            )
        except Exception:
            print(exc_text, file=sys.stderr)


try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QSettings
    from main_window import MainWindow
    from tray import TrayIcon
    from presentmon_fps import is_admin
    import theme
except Exception:
    _fatal_error(traceback.format_exc())
    sys.exit(1)


def _maybe_elevate(app) -> bool:
    """
    PresentMon (ETW) требует прав администратора. Если их нет — предлагаем
    перезапустить программу с повышением. Возвращает True, если запущен
    перезапуск (и текущий процесс должен завершиться).
    """
    if is_admin():
        return False

    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Нужны права администратора")
    box.setText(
        "Для измерения реального FPS игр нужны права администратора.\n\n"
        "Перезапустить программу от имени администратора?"
    )
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.button(QMessageBox.StandardButton.Yes).setText("Перезапустить")
    box.button(QMessageBox.StandardButton.No).setText("Продолжить без FPS")
    if box.exec() != QMessageBox.StandardButton.Yes:
        return False

    try:
        params = " ".join(f'"{a}"' for a in sys.argv)
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        # >32 — успех (запущен новый, уже elevated, процесс).
        return rc > 32
    except Exception:
        return False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.apply(app)

    if _maybe_elevate(app):
        sys.exit(0)

    # Создаём главное окно
    window = MainWindow()

    # Создаём системный трей
    tray = TrayIcon(window)
    tray.show()

    # Загружаем настройки
    settings = QSettings("FPSMonitor", "FPSMonitor")
    window.apply_settings(window.settings_dialog.get_settings())

    # Автозапуск оверлея если включено
    if settings.value("overlay_start", False, type=bool):
        window.overlay.show()
        window.btn_overlay.setChecked(True)

    # Показываем главное окно (если не включено сворачивание в трей)
    if not settings.value("minimize_tray", False, type=bool):
        window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        _fatal_error(traceback.format_exc())
        sys.exit(1)
