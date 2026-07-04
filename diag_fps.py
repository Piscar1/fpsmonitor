"""Тест настоящего PresentMonFPS: что он эмитит и какой статус шлёт."""
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from presentmon_fps import PresentMonFPS

app = QApplication(sys.argv)
pm = PresentMonFPS()

fps_events = []
status_events = []


def on_fps(fps, name):
    fps_events.append((round(fps, 1), name))


def on_status(text):
    status_events.append(text)
    print(f"  [STATUS] {text}")


pm.fps_updated.connect(on_fps)
pm.status_changed.connect(on_status)

print("Запуск PresentMonFPS на 12 секунд...")
print("  Откройте игру/CS2 или помашите окном, если запущено")
print()
pm.start()
print(f"Поток запущен? {pm.isRunning()}")


def finish():
    print()
    print(f"FPS событий: {len(fps_events)}")
    print(f"Статусов: {len(status_events)}")
    if fps_events:
        print()
        print("Последние FPS:")
        for fps, name in fps_events[-15:]:
            print(f"  {fps:>6} FPS  {name}")
    else:
        print(">>> НЕТ НИ ОДНОГО FPS-события!")
    pm.stop()
    app.quit()


QTimer.singleShot(12000, finish)
app.exec()
