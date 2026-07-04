"""
Диагностика источника HWiNFO для температуры/частоты CPU.

Запускать от администратора:
    python diag_hwinfo.py

Если HWiNFO нет — подскажет, что делать дальше.
Если HWiNFO есть — покажет, какие именно датчики приходят и какие
ключи (cpu_temp / cpu_freq / cpu_power) извлекаются.
"""

import subprocess

try:
    import wmi
    _WMI_OK = True
except ImportError:
    _WMI_OK = False

try:
    import win32com.client
    _COM_WMI_OK = True
except ImportError:
    _COM_WMI_OK = False


def _proc_running(name: str) -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}"],
            capture_output=True, text=True, timeout=10,
        )
        return name.lower() in r.stdout.lower() and "PID" in r.stdout
    except Exception:
        return False


def main():
    print("=" * 60)
    print(" ДИАГНОСТИКА HWiNFO WMI")
    print("=" * 60)

    # 1. Запущен ли процесс?
    print("\n[1] Процесс HWiNFO:")
    running_64 = _proc_running("HWiNFO64.EXE")
    running_32 = _proc_running("HWiNFO32.EXE")
    if running_64:
        print("    HWiNFO64.EXE запущен")
    if running_32:
        print("    HWiNFO32.EXE запущен")
    if not (running_64 or running_32):
        print("    >> HWiNFO НЕ запущена.")

    # 2. namespace
    print("\n[2] WMI namespace root\\HWiNFO:")
    ns_ok = False
    if _WMI_OK:
        try:
            wmi.WMI(namespace=r"root\HWiNFO")
            ns_ok = True
            print("    доступен")
        except Exception as e:
            print(f"    >> НЕ доступен: {e}")
    elif _COM_WMI_OK:
        try:
            locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            locator.ConnectServer(".", r"root\HWiNFO")
            ns_ok = True
            print("    доступен через pywin32 COM")
        except Exception as e:
            print(f"    >> НЕ доступен через pywin32 COM: {e}")
    else:
        print("    >> нет ни модуля WMI, ни pywin32 COM")

    if not ns_ok:
        print()
        print("=" * 60)
        print(" HWiNFO НЕ ПОДКЛЮЧЕН — температура CPU недоступна.")
        print("=" * 60)
        print("Что нужно сделать:")
        print()
        print("  1. Скачайте HWiNFO (бесплатно):")
        print("       https://www.hwinfo.com/download/")
        print("     (выбрать Installer для 64-bit Windows)")
        print()
        print("  2. Запустите HWiNFO.")
        print()
        print("  3. Settings -> Safety / Safe Mode:")
        print("       установите галочку 'WMI Provider'")
        print("       (без неё namespace root\\HWiNFO не появится)")
        print()
        print("  4. Перезапустите fps_monitor. Температура/частота CPU")
        print("     подтянутся автоматически.")
        print()
        print("ЧАСТОТА CPU работает и без HWiNFO — через счётчики Windows.")
        return

    # 3. Перечисляем датчики
    print("\n[3] Датчики (HWiNFO.Sensor):")
    try:
        if _WMI_OK:
            w = wmi.WMI(namespace=r"root\HWiNFO")
            sensors = w.Sensor()
        else:
            locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            w = locator.ConnectServer(".", r"root\HWiNFO")
            sensors = list(w.ExecQuery("SELECT * FROM Sensor"))
        print(f"    всего записей: {len(sensors)}")
    except Exception as e:
        print(f"    >> класс Sensor недоступен: {e}")
        return

    temps = clocks = powers = 0
    sample = []
    for s in sensors:
        try:
            stype = (getattr(s, "SensorClass", "") or "").strip()
            label = (getattr(s, "Label", "") or "").strip()
            value = getattr(s, "Value", None)
            device = (getattr(s, "SensorDevice", "") or "").strip()
            if stype == "Temperature":
                temps += 1
            elif stype == "Clock":
                clocks += 1
            elif stype == "Power":
                powers += 1
            if len(sample) < 25:
                sample.append((stype, device, label, value))
        except Exception:
            continue

    print(f"    температурных: {temps}, частот: {clocks}, мощностных: {powers}")
    print("    образцы (первые 25):")
    for stype, device, label, value in sample:
        print(f"      {stype:13} | {device[:22]:22} | {label[:28]:28} = {value}")

    # 4. Что извлечёт наш модуль
    print("\n[4] Результат hwinfo.HwInfoSensors().read():")
    from hwinfo import HwInfoSensors
    h = HwInfoSensors()
    data = h.read()
    print(f"    {data}")

    print("\n" + "=" * 60)
    print(" КОНЕЦ")
    print("=" * 60)


if __name__ == "__main__":
    main()
