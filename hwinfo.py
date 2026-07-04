"""
Источник сенсоров через HWiNFO.

HWiNFO — бесплатная утилита с собственным подписанным драйвером,
который корректно работает на Windows 11 24H2/26200 (в отличие от
WinRing0 в LibreHardwareMonitor). Через её WMI provider можно читать
температуру, частоту и мощность CPU/GPU без установки своих драйверов.

Важно: HWiNFO должна быть запущена, и в её настройках включён
"Sensors → WMI Provider" (по умолчанию он ВЫКЛЮЧЕН — это частая причина,
почему значения не появляются).

WMI-namespace HWiNFO: root\\HWiNFO
Классы:
    HWiNFO.CPU0   — поля вида cpu_temp, cpu_power, ... (как их называет сам HWiNFO)
    HWiNFO.Sensor — полный список сенсоров (строки: Value, Label, SensorClass...)

Каждый класс-провайдер имеет специфичную структуру полей и зависит от версии
HWiNFO, поэтому здесь перебираем все свойства динамически и сопоставляем
по ключевым словам в имени.
"""

import re

try:
    import wmi
    _WMI_OK = True
except ImportError:
    wmi = None
    _WMI_OK = False

try:
    import win32com.client
    _COM_WMI_OK = True
except ImportError:
    win32com = None
    _COM_WMI_OK = False

# Namespace HWiNFO. Используем root\\HWiNFO — именно туда HWiNFO кладёт
# свой WMI-провайдер, когда опция "Sensors → WMI Provider" включена.
_HWINFO_NS = r"root\HWiNFO"


class HwInfoSensors:
    """Температура/частота/мощность CPU и GPU через запущенный HWiNFO."""

    def __init__(self):
        self.ok = False
        self._w = None
        self._backend = None
        if _WMI_OK:
            try:
                self._w = wmi.WMI(namespace=_HWINFO_NS)
                # Триггер: пробуем получить хоть один класс — если namespace
                # существует, WMI не выбросит исключение при создании объекта.
                self.ok = True
                self._backend = "wmi"
                return
            except Exception:
                pass

        # Запасной путь без стороннего пакета WMI. pywin32 уже нужен проекту,
        # а через COM можно читать тот же namespace root\HWiNFO напрямую.
        if _COM_WMI_OK:
            try:
                locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                self._w = locator.ConnectServer(".", _HWINFO_NS)
                self.ok = True
                self._backend = "com"
            except Exception:
                # Namespace недоступен: HWiNFO не запущен или WMI-провайдер
                # выключен в её настройках.
                self.ok = False

    def read(self) -> dict:
        """Возвращает словарь с cpu_temp, cpu_freq, cpu_power, gpu_temp.

        Поля, которые не удалось прочитать, в словарь не попадают — это
        позволяет вызывающему коду отличать «нет значения» от «ноль».
        """
        if not self.ok:
            return {}

        out = {}

        # ---- Подход 1: классы HWiNFO.CPU0 / HWiNFO.GPU0 ----
        # У них поля называются предсказуемо: cpu_temp, cpu_power,
        # cpu_clock, gpu_temp и т.п. Эти классы появляются, только если
        # HWiNFO запущена в режиме "Sensors" (окно сенсоров открыто).
        try:
            for cls_name in ("CPU0", "GPU0"):
                try:
                    # wmi.WMI монkey-patches классы как атрибуты, но
                    # имена с цифрами нельзя обратиться через точку,
                    # поэтому используем .instances().
                    instances = self._instances(cls_name)
                except Exception:
                    continue
                if not instances:
                    continue
                self._read_typed(instances[0], cls_name, out)
        except Exception:
            pass

        # ---- Подход 2: класс HWiNFO.Sensor — универсальный ----
        # Появляется всегда, даже без открытого окна сенсоров. Каждый
        # инстанс — один датчик с полями Label / Value / SensorClass.
        # Это основной и самый надёжный путь.
        try:
            sensors = self._read_sensor_class()
            if sensors:
                out = {**sensors, **out}
        except Exception:
            pass

        # Чистим: нули для температур и мощностей исключаем — HWiNFO
        # реально не отдаёт нулевую температуру, это признак пропуска.
        for k in ("cpu_temp", "gpu_temp"):
            if out.get(k) is not None and out[k] <= 0:
                out.pop(k, None)
        for k in ("cpu_power", "gpu_power"):
            if out.get(k) is not None and out[k] <= 0:
                out.pop(k, None)

        return out

    # ------------------------------------------------------------------
    #  Универсальный провайдер HWiNFO.Sensor
    # ------------------------------------------------------------------
    def _read_sensor_class(self) -> dict:
        """Читает все строки HWiNFO.Sensor и сопоставляет их по имени.

        HWiNFO хранит все датчики в одном классе. Каждая запись имеет:
            Label         — читаемое имя ("CPU Package", "Core 0", ...)
            Value         — значение
            SensorClass   — категория ("Temperature", "Clock", "Power"...)
            SensorDevice  — устройство ("AMD Ryzen 5 5500", "NVIDIA RTX ...")

        Сопоставление сделано жадным по приоритету: первое совпадение
        по ключевому имени выигрывает.
        """
        out = {}

        try:
            sensors = self._instances("Sensor")  # HWiNFO.Sensor
        except Exception:
            return out

        # Приоритеты для температуры CPU: предпочитаем "Tctl/Tdie" / "Package",
        # затем "CPU" по имени устройства.
        cpu_temp_candidates = []
        gpu_temp_candidates = []

        for s in sensors:
            try:
                stype = (getattr(s, "SensorClass", "") or "").strip()
                label = (getattr(s, "Label", "") or "").strip()
                value = getattr(s, "Value", None)
                device = (getattr(s, "SensorDevice", "") or "").strip()
                unit = (getattr(s, "SensorUnit", "") or "").strip()

                if value is None:
                    continue
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue

                label_low = label.lower()
                device_low = device.lower()
                unit_low = unit.lower()

                # ---------- Температуры ----------
                if stype.lower() == "temperature" or "c" in unit_low or "°c" in unit_low:
                    is_cpu = ("cpu" in device_low
                              or "ryzen" in device_low
                              or "intel" in device_low
                              or "amd" in device_low
                              or "core" in label_low
                              or "package" in label_low
                              or "tctl" in label_low
                              or "tdie" in label_low
                              or "ccd" in label_low
                              or "cpu" in label_low)
                    is_gpu = ("gpu" in device_low
                              or "geforce" in device_low
                              or "radeon" in device_low)

                    if is_cpu:
                        # Приоритет: Tctl/Tdie > Package > Core
                        prio = 0
                        if "tctl" in label_low or "tdie" in label_low:
                            prio = 0
                        elif "package" in label_low:
                            prio = 1
                        elif "ccd" in label_low:
                            prio = 2
                        elif "core" in label_low:
                            prio = 3
                        else:
                            prio = 4
                        if value > 0:
                            cpu_temp_candidates.append((prio, value))
                    elif is_gpu:
                        if value > 0:
                            gpu_temp_candidates.append((0, value))

                # ---------- Частоты (Clock) ----------
                elif stype.lower() == "clock":
                    is_cpu = ("cpu" in device_low
                              or "ryzen" in device_low
                              or "intel" in device_low
                              or "amd" in device_low
                              or re.search(r"\bcore\b", label_low)
                              or "core" in device_low)
                    if is_cpu and value > 0:
                        # Берём максимум по ядрам — это то же, что показывает
                        # Диспетчер задач как "скорость".
                        cur = out.get("cpu_freq")
                        if cur is None or value > cur:
                            out["cpu_freq"] = round(value)

                # ---------- Мощность ----------
                elif stype.lower() == "power":
                    is_cpu = ("cpu" in device_low
                              or "ryzen" in device_low
                              or "intel" in device_low
                              or "amd" in device_low
                              or "package" in label_low)
                    is_gpu = ("gpu" in device_low
                              or "geforce" in device_low)
                    if is_cpu and "package" in label_low and value > 0:
                        out["cpu_power"] = round(value, 1)
                    elif is_gpu and ("power" in label_low or "pwr" in label_low) and value > 0:
                        out["gpu_power"] = round(value, 1)

            except Exception:
                continue

        # Финализируем температуры: выбираем кандидат с наивысшим приоритетом.
        if cpu_temp_candidates and "cpu_temp" not in out:
            cpu_temp_candidates.sort(key=lambda t: (t[0], -t[1]))
            out["cpu_temp"] = round(cpu_temp_candidates[0][1], 1)
        if gpu_temp_candidates and "gpu_temp" not in out:
            gpu_temp_candidates.sort(key=lambda t: (t[0], -t[1]))
            out["gpu_temp"] = round(gpu_temp_candidates[0][1], 1)

        return out

    def _instances(self, cls_name: str):
        if self._backend == "wmi":
            return self._w.instances(cls_name)
        if self._backend == "com":
            return list(self._w.ExecQuery(f"SELECT * FROM {cls_name}"))
        return []

    # ------------------------------------------------------------------
    #  Типизированные классы (CPU0/GPU0) — запасной путь
    # ------------------------------------------------------------------
    def _read_typed(self, instance, cls_name: str, out: dict):
        """Читает типизированные поля HWiNFO.CPU0 / HWiNFO.GPU0.

        Имена полей в этих классах фиксированы (cpu_temp, cpu_power,
        cpu_clock, gpu_temp, ...), но доступны только если окно сенсоров
        открыто. Поэтому это лишь дополнение к универсальному провайдеру.
        """
        # Имя поля -> (ключ в нашем словаре, минимум валидного значения)
        mapping = {
            "cpu_temp":     ("cpu_temp", 1),
            "cpu_clock":    ("cpu_freq", 1),
            "cpu_power":    ("cpu_power", 1),
            "gpu_temp":     ("gpu_temp", 1),
            "gpu_clock":    ("gpu_freq", 1),
            "gpu_power":    ("gpu_power", 1),
        }
        prefix = "cpu_" if cls_name == "CPU0" else "gpu_"
        for prop_name in wmi_to_props(instance):
            if not prop_name.startswith(prefix):
                continue
            if prop_name not in mapping:
                continue
            out_key, min_val = mapping[prop_name]
            try:
                val = float(getattr(instance, prop_name))
                if val >= min_val:
                    out[out_key] = round(val) if out_key.endswith("_freq") else round(val, 1)
            except Exception:
                continue


def wmi_to_props(instance) -> list:
    """Возвращает список имён WMI-свойств объекта (wmi не даёт .properties
    напрямую в старых версиях — перебираем через .properties_ если есть)."""
    try:
        # pythonnet-обёрнутый объект
        return [p.Name for p in instance.Properties_]
    except Exception:
        pass
    try:
        return list(instance.properties.keys())
    except Exception:
        return []


def is_available() -> bool:
    """Быстрая проверка: запущен ли HWiNFO с включённым WMI-провайдером."""
    if _WMI_OK:
        try:
            wmi.WMI(namespace=_HWINFO_NS)
            return True
        except Exception:
            pass
    if _COM_WMI_OK:
        try:
            locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            locator.ConnectServer(".", _HWINFO_NS)
            return True
        except Exception:
            pass
    return False
