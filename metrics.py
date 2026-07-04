import time
import re
import winreg
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


def read_vram_total_gb():
    """
    Реальный объём видеопамяти из реестра (qwMemorySize, 64-бит).

    Win32_VideoController.AdapterRAM — 32-битное значение, обрезается на ~4 ГБ
    и врёт для современных карт, поэтому берём значение из ключа драйвера.
    """
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    best = 0
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(root, sub) as k:
                        val, _ = winreg.QueryValueEx(k, "HardwareInformation.qwMemorySize")
                        best = max(best, int(val))
                except OSError:
                    continue
    except OSError:
        return None
    return round(best / (1024 ** 3), 2) if best else None


def read_cpu_base_mhz():
    """Базовая (номинальная) частота CPU в МГц из реестра (~MHz).

    Используется как опора для расчёта живой частоты:
        live = base_mhz * PercentProcessorPerformance / 100
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as k:
            val, _ = winreg.QueryValueEx(k, "~MHz")
            return float(val)
    except Exception:
        return None


class MetricsWorker(QThread):
    """Поток сбора системных метрик."""
    metrics_ready = pyqtSignal(dict)

    def __init__(self, interval_ms=100):
        super().__init__()
        self.interval = interval_ms / 1000.0
        self._running = True
        self._wmi = None

        # Названия по умолчанию
        self.cpu_name = "CPU"
        self.gpu_name = "GPU"

        # Реальный объём VRAM (из реестра, один раз при старте).
        self.vram_total_gb = read_vram_total_gb()

        # Базовая частота CPU (опора для расчёта живой частоты).
        self._cpu_base_mhz = read_cpu_base_mhz()

        # Названия CPU/GPU читаем ЛОКАЛЬНЫМ WMI-объектом в главном потоке.
        # Нельзя оставлять self._wmi из __init__ — этот COM-объект создан в
        # главном потоке, а в run()/_loop используется в рабочем. Кросс-поточное
        # COM-подключение ВИСНЕТ намертво. Рабочее подключение создаётся в run().
        if WMI_AVAILABLE:
            try:
                w = wmi.WMI()
                # Точное название CPU
                cpus = w.Win32_Processor()
                if cpus:
                    self.cpu_name = cpus[0].Name.strip()
                    # Базовая частота = MaxClockSpeed (именно её Диспетчер
                    # задач показывает как «Базовая скорость»). Реестровый
                    # ~MHz завышен — это замер на момент загрузки (часто
                    # буст-частота), из-за него живая частота уезжала вверх.
                    mcs = getattr(cpus[0], 'MaxClockSpeed', None)
                    if mcs:
                        self._cpu_base_mhz = float(mcs)

                # Точное название GPU (пропускаем виртуальные адаптеры)
                gpus = w.Win32_VideoController()
                for g in gpus:
                    if g.Name and "Microsoft Basic Display Adapter" not in g.Name:
                        self.gpu_name = g.Name.strip()
                        break
            except Exception:
                pass

    def run(self):
        # COM и WMI инициализируем именно в ЭТОМ потоке. Иначе часть WMI-
        # запросов молча падает с COM-ошибкой кросс-потока — именно поэтому
        # раньше не читалась живая частота и температура CPU.
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        # Кэш WMI-подключений по namespace. Создаётся ОДИН РАЗ здесь, а не
        # в каждой итерации _loop. Раньше было self._wmi(namespace=...) — это
        # падало с TypeError под Python 3.14. Наивная замена на
        # wmi.WMI(namespace=...) в каждой итерации тоже плоха: каждый вызов
        # открывает новое COM-подключение, а для НЕсуществующих namespace'ов
        # (root\OpenHardwareMonitor, если OHM не установлен) виснет на
        # несколько секунд. Поэтому подключаемся один раз и запоминаем, что
        # недоступно.
        self._wmi = None
        self._wmi_ns_cache = {}
        self._wmi_ns_unavailable = set()
        if WMI_AVAILABLE:
            try:
                self._wmi = wmi.WMI()
            except Exception:
                self._wmi = None
            # Предварительно пробуем нужные namespace'ы один раз. Недоступные
            # помечаем — в _loop они будут мгновенно пропускаться.
            for ns in ("root\\cimv2", "root\\OpenHardwareMonitor",
                       "root\\WMI", "root\\HWiNFO"):
                self._get_wmi_ns(ns)

        # Источники датчиков создаём в этом же потоке.
        from sensors import NvmlGpu, LhmSensors
        from hwinfo import HwInfoSensors
        gpu = NvmlGpu()
        lhm = LhmSensors()
        hwinfo = HwInfoSensors()
        # Запоминаем доступность NVML один раз: если он есть, GPU-метрики
        # берём через него, а медленные WMI-счётчики GPU пропускаем.
        self._gpu_ok = gpu.ok
        if gpu.ok:
            nm = gpu.name()
            if nm:
                self.gpu_name = nm

        try:
            self._loop(gpu, lhm, hwinfo)
        finally:
            gpu.shutdown()
            lhm.close()
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def _get_wmi_ns(self, namespace: str):
        """Возвращает кэшированное WMI-подключение к namespace или None.

        Недоступные namespace'ы запоминаются — повторные запросы мгновенно
        возвращают None без попытки подключения.
        """
        if namespace in self._wmi_ns_unavailable:
            return None
        if namespace in self._wmi_ns_cache:
            return self._wmi_ns_cache[namespace]
        try:
            conn = wmi.WMI(namespace=namespace)
            self._wmi_ns_cache[namespace] = conn
            return conn
        except Exception:
            self._wmi_ns_unavailable.add(namespace)
            return None

    def _loop(self, gpu, lhm, hwinfo):
        while self._running:
            metrics = {}

            # === CPU ===
            try:
                metrics['cpu_percent_total'] = psutil.cpu_percent(interval=None)
                metrics['cpu_percent_per_core'] = psutil.cpu_percent(interval=None, percpu=True)
            except Exception:
                metrics['cpu_percent_total'] = None
                metrics['cpu_percent_per_core'] = None

            # Живая частота CPU.
            # psutil.cpu_freq() на Windows возвращает БАЗОВУЮ частоту и залипает
            # (например, вечные 3600 МГц). Реальную частоту считаем через счётчик
            # производительности Windows — так же, как Диспетчер задач:
            #   live = base_mhz * PercentProcessorPerformance / 100
            # (PercentProcessorPerformance может быть > 100 при буст-режиме).
            #
            # НО: Win32_PerfFormattedData_Counters_ProcessorInformation на этой
            # системе отдаётся ~0.6с (тянет все ядра). Поэтому кэшируем результат
            # и обновляем не чаще раза в секунду — частота меняется медленно, а
            # интервал опроса по умолчанию 100мс. Между обновлениями держим
            # последнее значение вместо того, чтобы тормозить каждый кадр.
            metrics['cpu_freq'] = getattr(self, "_cpu_freq_cached", None)
            now = time.time()
            if now - getattr(self, "_cpu_freq_ts", 0) >= 1.0:
                cpu_perf_pct = None
                cimv2 = self._get_wmi_ns("root\\cimv2")
                if cimv2 is not None:
                    try:
                        perf = cimv2.Win32_PerfFormattedData_Counters_ProcessorInformation()
                        total = None
                        for p in perf:
                            nm = getattr(p, 'Name', '') or ''
                            if nm == '_Total':
                                total = p
                                break
                            if nm.endswith('_Total') and total is None:
                                total = p
                        if total is not None:
                            v = getattr(total, 'PercentProcessorPerformance', None)
                            if v is not None:
                                cpu_perf_pct = float(v)
                    except Exception:
                        cpu_perf_pct = None
                if cpu_perf_pct is not None and self._cpu_base_mhz:
                    raw = self._cpu_base_mhz * cpu_perf_pct / 100.0
                    # PercentProcessorPerformance — мгновенный снимок, он скачет
                    # (113 → 118 → 105 за секунду) и ловит буст-пики. Диспетчер
                    # задач показывает сглаженное значение, поэтому усредняем
                    # экспоненциально, чтобы не мигать на всплесках.
                    prev = getattr(self, "_cpu_freq_ema", None)
                    ema = raw if prev is None else prev * 0.6 + raw * 0.4
                    self._cpu_freq_ema = ema
                    metrics['cpu_freq'] = round(ema)
                elif metrics['cpu_freq'] is None:
                    try:
                        freq = psutil.cpu_freq()
                        metrics['cpu_freq'] = round(freq.current) if freq else None
                    except Exception:
                        metrics['cpu_freq'] = None
                self._cpu_freq_cached = metrics['cpu_freq']
                self._cpu_freq_ts = now

            # CPU температура
            metrics['cpu_temp'] = None
            ohm = self._get_wmi_ns("root\\OpenHardwareMonitor")
            if ohm is not None:
                try:
                    sensors = ohm.Sensor()
                    for s in sensors:
                        if s.SensorType == "Temperature" and "CPU" in s.Name:
                            metrics['cpu_temp'] = round(s.Value, 1)
                            break
                except Exception:
                    pass
            if metrics['cpu_temp'] is None:
                wmins = self._get_wmi_ns("root\\WMI")
                if wmins is not None:
                    try:
                        # Fallback: MSAcpi_ThermalZoneTemperature живёт в root\WMI,
                        # а не в cimv2. Требует прав администратора.
                        temps = wmins.MSAcpi_ThermalZoneTemperature()
                        if temps:
                            kelvin10 = temps[0].CurrentTemperature
                            metrics['cpu_temp'] = round(kelvin10 / 10.0 - 273.15, 1)
                    except Exception:
                        pass

            # === RAM ===
            try:
                mem = psutil.virtual_memory()
                metrics['ram_percent'] = mem.percent
                metrics['ram_used_gb'] = round(mem.used / (1024**3), 2)
                metrics['ram_total_gb'] = round(mem.total / (1024**3), 2)
            except Exception:
                metrics['ram_percent'] = None
                metrics['ram_used_gb'] = None
                metrics['ram_total_gb'] = None

            # === Материнская плата и VRM ===
            metrics['motherboard_temp'] = None
            metrics['vrm_temp'] = None
            ohm = self._get_wmi_ns("root\\OpenHardwareMonitor")
            if ohm is not None:
                try:
                    # Температура материнской платы через OpenHardwareMonitor (более надежно)
                    sensors = ohm.Sensor()
                    for s in sensors:
                        if s.SensorType == "Temperature" and any(x in s.Name for x in ["Motherboard", "Mainboard", "System"]):
                            metrics['motherboard_temp'] = round(s.Value, 1)
                            break
                except Exception:
                    pass

                # Fallback на стандартный WMI, если OHM не нашел
                if metrics['motherboard_temp'] is None and self._wmi:
                    try:
                        for sensor in self._wmi.Win32_TemperatureProbe():
                            if sensor.Name and sensor.CurrentReading:
                                metrics['motherboard_temp'] = int(sensor.CurrentReading)
                                break
                    except Exception:
                        pass

                try:
                    # Температура VRM через OpenHardwareMonitor
                    sensors = ohm.Sensor()
                    for s in sensors:
                        if s.SensorType == "Temperature" and "VRM" in s.Name:
                            metrics['vrm_temp'] = round(s.Value, 1)
                            break
                except Exception:
                    pass

            # === GPU ===
            metrics['gpu_load'] = None
            metrics['gpu_mem_used'] = None
            metrics['gpu_mem_total'] = None
            metrics['gpu_temp'] = None
            metrics['gpu_freq'] = None
            metrics['cpu_fan_rpm'] = None
            metrics['gpu_fan_rpm'] = None

            # Реальный объём VRAM (из реестра).
            metrics['gpu_mem_total'] = self.vram_total_gb

            # NVML отдаёт gpu_load / gpu_mem / gpu_temp / gpu_freq быстрее и
            # надёжнее WMI. Медленные WMI-счётчики GPU (GPUEngine ~3.3с,
            # GPUProcessMemory ~0.3с на этой системе) дёргаем ТОЛЬКО если NVML
            # недоступен — иначе _loop вместо 100мс крутится по 4-6 секунд и
            # оверлей "зависает". gpu_ok фиксируем один раз в run().
            gpu_via_nvml = getattr(self, "_gpu_ok", False)

            ohm = self._get_wmi_ns("root\\OpenHardwareMonitor")

            if gpu_via_nvml:
                # Минимальный путь: имя/VRAM из реестра уже есть, остальное
                # добавит NVML в блоке overlay ниже. Температуру через OHM
                # всё же пробуем — NVML её перебьёт, но на не-NVIDIA это запас.
                pass
            elif WMI_AVAILABLE and self._wmi:
                cimv2 = self._get_wmi_ns("root\\cimv2")

                # Частота ядра (часто не отдаётся драйвером — тогда останется None).
                try:
                    gpus = self._wmi.Win32_VideoController()
                    for g in gpus:
                        if g.Name and "Microsoft Basic Display Adapter" not in g.Name:
                            if metrics['gpu_mem_total'] is None and getattr(g, 'AdapterRAM', None):
                                metrics['gpu_mem_total'] = round(g.AdapterRAM / (1024**3), 2)
                            if getattr(g, 'CurrentClockSpeed', None):
                                metrics['gpu_freq'] = int(g.CurrentClockSpeed)
                            break
                except Exception:
                    pass

                # GPU загрузка: суммируем по типам движков (3D, Compute, Copy…)
                # и берём максимум — так же, как Диспетчер задач.
                if cimv2 is not None:
                    try:
                        gpu_counters = cimv2.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine()
                        if gpu_counters:
                            by_engtype = {}
                            for c in gpu_counters:
                                util = getattr(c, 'UtilizationPercentage', None)
                                if not util:
                                    continue
                                m = re.search(r'engtype_(\w+)', c.Name or '')
                                engtype = m.group(1) if m else 'other'
                                by_engtype[engtype] = by_engtype.get(engtype, 0) + int(util)
                            if by_engtype:
                                metrics['gpu_load'] = round(min(100.0, max(by_engtype.values())), 1)
                    except Exception:
                        pass

                # Использовано VRAM: сумма выделенной памяти по всем процессам.
                if cimv2 is not None:
                    try:
                        mem_counters = cimv2.Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory()
                        if mem_counters:
                            dedicated = 0
                            for c in mem_counters:
                                used = getattr(c, 'DedicatedUsage', None)
                                if used:
                                    dedicated += int(used)
                            if dedicated > 0:
                                metrics['gpu_mem_used'] = round(dedicated / (1024**3), 2)
                    except Exception:
                        pass

            # GPU температура / память через OpenHardwareMonitor (только если
            # OHM есть — иначе _get_wmi_ns мгновенно вернёт None).
            if ohm is not None:
                try:
                    sensors = ohm.Sensor()
                    for s in sensors:
                        if s.SensorType == "Temperature" and "GPU" in s.Name:
                            metrics['gpu_temp'] = round(s.Value, 1)
                            break
                except Exception:
                    pass
                if metrics['gpu_mem_used'] is None:
                    try:
                        sensors = ohm.Sensor()
                        for s in sensors:
                            if s.SensorType == "Data" and "GPU Memory" in s.Name:
                                metrics['gpu_mem_used'] = round(s.Value, 2)
                                break
                    except Exception:
                        pass

            # Скорости вентиляторов.
            if WMI_AVAILABLE and self._wmi:
                try:
                    for fan in self._wmi.Win32_Fan():
                        if fan.Name and fan.DesiredSpeed:
                            name = fan.Name.lower()
                            if 'cpu' in name:
                                metrics['cpu_fan_rpm'] = int(fan.DesiredSpeed)
                            elif 'gpu' in name or 'video' in name:
                                metrics['gpu_fan_rpm'] = int(fan.DesiredSpeed)
                except Exception:
                    pass

            # === Приоритетные источники: HWiNFO → LHM → NVML ===
            # Порядок наложения обратный приоритету: HWiNFO первым, т.к. у него
            # свой подписанный драйвер, читающий SMU AMD там, где WinRing0 у LHM
            # молча не стартует на свежих Windows. NVML — только для GPU NVIDIA.
            # Для частот/температур/мощностей 0 — это не валидное значение, а
            # признак того, что источник не смог прочитать датчик (так ведёт
            # себя LHM при заблокированном Ring0). Таких нулей не накладываем,
            # чтобы не затирать живое значение, полученное через WMI.
            _POSITIVE_ONLY = {
                "cpu_freq", "cpu_temp", "cpu_power",
                "gpu_freq", "gpu_temp", "gpu_power",
            }
            def _overlay(source):
                if source is None:
                    return
                for k, v in source.read().items():
                    if v is None:
                        continue
                    if k in _POSITIVE_ONLY and v <= 0:
                        continue
                    metrics[k] = v

            _overlay(hwinfo)
            _overlay(lhm)
            _overlay(gpu)

            self.metrics_ready.emit(metrics)
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        self.wait()

    def set_interval(self, interval_ms: int):
        self.interval = interval_ms / 1000.0
