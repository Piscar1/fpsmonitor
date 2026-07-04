"""
Полная интеграция: PresentMonFPS + MetricsWorker + таймер _refresh
как в main_window. Запускай ИГРУ в соседнем окне.
"""
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from presentmon_fps import PresentMonFPS
from fps_counter import FPSCounter

app = QApplication(sys.argv)

pm = PresentMonFPS()
counter = FPSCounter()

overlay_calls = []


def on_fps(fps, name):
    counter.update(fps)


def on_status(text):
    print(f"[STATUS] {text}")


pm.fps_updated.connect(on_fps)
pm.status_changed.connect(on_status)
pm.start()

print("Запуск. Откройте CS2/игру. Тест 15 сек.")


def refresh():
    # Эмулируем _refresh -> overlay.update_data
    overlay_calls.append({
        "fps": counter.current,
        "min": counter.minimum,
        "max": counter.maximum,
        "avg": counter.average,
    })


def finish():
    print()
    print(f"=== Результат ({len(overlay_calls)} обновлений overlay) ===")
    nonzero = [c for c in overlay_calls if c["fps"] > 0]
    print(f"Из них с FPS>0: {len(nonzero)}")
    if nonzero:
        print(f"FPS: {nonzero[-1]['fps']}  AVG={nonzero[-1]['avg']}")
        print(">>> FPS ДОХОДИТ до overlay ✓")
    else:
        print(">>> FPS НЕТ в overlay ✗  (counter.current всегда 0)")
    print()
    print(f"counter.current = {counter.current}")
    print(f"counter.average = {counter.average}")
    pm.stop()
    app.quit()


timer = QTimer()
timer.timeout.connect(refresh)
timer.start(250)
QTimer.singleShot(15000, finish)
app.exec()
