"""Прямой запуск PresentMon через Python: что он реально выводит?"""
import subprocess
import time
import os

pm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin",
                  "PresentMon-1.10.0-x64.exe")
print(f"PresentMon: {pm}")
print(f"Существует: {os.path.isfile(pm)}")
print()

cmd = [pm, "-output_stdout", "-stop_existing_session", "-no_top",
       "-no_track_display"]
print("Запуск на 6 секунд (по таймеру)...")
print("Команда:", " ".join(cmd))
print()

try:
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, creationflags=0x08000000,
    )
except Exception as e:
    print(f"Не удалось запустить: {e}")
    raise SystemExit

lines = []
start = time.time()
try:
    while time.time() - start < 6:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.05)
            continue
        lines.append(line.rstrip())
        if len(lines) <= 25:
            print(f"  {len(lines):3}: {line.rstrip()}")
except Exception as e:
    print(f"Ошибка чтения: {e}")

# Принудительно убиваем
try:
    proc.terminate()
    proc.wait(timeout=2)
except Exception:
    try:
        proc.kill()
    except Exception:
        pass
print()
print(f"Всего строк: {len(lines)}")
if lines:
    print()
    print("Заголовок:", lines[0])
    # Уникальные процессы
    apps = set()
    for ln in lines[1:]:
        apps.add(ln.split(",")[0])
    print(f"Уникальных процессов в выводе: {len(apps)}")
    for a in sorted(apps):
        print(f"   {a}")

# stderr
err = proc.stderr.read() if proc.stderr else ""
if err.strip():
    print()
    print("STDERR:", err[:500])
