"""
Источники аппаратных датчиков.

NvmlGpu  — загрузка/температура/частоты/VRAM видеокарты NVIDIA через NVML
           (родная библиотека драйвера, user-mode, надёжно, без админ-прав).
LhmSensors — температуры CPU / материнской платы / VRM через LibreHardwareMonitor
           (DLL грузится из bin/). Требует драйвер Ring0; на части систем он
           заблокирован Windows (блок-лист драйверов), тогда значения недоступны
           и соответствующие карточки просто скрываются.
"""

import os
import warnings

BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")


class NvmlGpu:
    """Метрики GPU NVIDIA через NVML."""

    def __init__(self):
        self.ok = False
        self._n = None
        self._handle = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import pynvml
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                self._n = pynvml
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                self.ok = True
        except Exception:
            self.ok = False

    def name(self):
        if not self.ok:
            return None
        try:
            nm = self._n.nvmlDeviceGetName(self._handle)
            return nm.decode() if isinstance(nm, bytes) else nm
        except Exception:
            return None

    def read(self) -> dict:
        if not self.ok:
            return {}
        n, h, out = self._n, self._handle, {}
        try:
            out['gpu_load'] = float(n.nvmlDeviceGetUtilizationRates(h).gpu)
        except Exception:
            pass
        try:
            m = n.nvmlDeviceGetMemoryInfo(h)
            out['gpu_mem_used'] = round(m.used / 1024 ** 3, 2)
            out['gpu_mem_total'] = round(m.total / 1024 ** 3, 2)
        except Exception:
            pass
        try:
            out['gpu_temp'] = float(n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU))
        except Exception:
            pass
        try:
            out['gpu_freq'] = int(n.nvmlDeviceGetClockInfo(h, n.NVML_CLOCK_GRAPHICS))
        except Exception:
            pass
        try:
            out['gpu_mem_freq'] = int(n.nvmlDeviceGetClockInfo(h, n.NVML_CLOCK_MEM))
        except Exception:
            pass
        # Энергопотребление (Вт)
        try:
            out['gpu_power'] = round(n.nvmlDeviceGetPowerUsage(h) / 1000.0, 1)
        except Exception:
            pass
        # Лимит мощности (Вт)
        try:
            out['gpu_power_limit'] = round(n.nvmlDeviceGetEnforcedPowerLimit(h) / 1000.0, 1)
        except Exception:
            pass
        # Напряжение ядра (В) через поле NVML
        try:
            field_id = getattr(n, 'NVML_FI_DEV_VOLTAGE_BOARD', None)
            if field_id is not None:
                vals = n.nvmlDeviceGetFieldValues(h, [field_id])
                fv = vals[0]
                if getattr(fv, 'nvmlReturn', 0) == 0:
                    mv = fv.value.uiVal
                    if mv:
                        out['gpu_voltage'] = round(mv / 1000.0, 3)
        except Exception:
            pass
        return out

    def shutdown(self):
        if self.ok:
            try:
                self._n.nvmlShutdown()
            except Exception:
                pass


class LhmSensors:
    """Температуры CPU / материнской платы / VRM через LibreHardwareMonitor."""

    def __init__(self):
        self.ok = False
        self._computer = None
        try:
            import clr
            from System import AppDomain
            from System.Reflection import Assembly

            def _resolver(sender, args):
                simple = args.Name.split(",")[0].strip()
                path = os.path.join(BIN_DIR, simple + ".dll")
                return Assembly.LoadFrom(path) if os.path.isfile(path) else None

            # Держим ссылку на обработчик, чтобы его не собрал GC.
            self._resolver = _resolver
            AppDomain.CurrentDomain.AssemblyResolve += _resolver

            clr.AddReference(os.path.join(BIN_DIR, "LibreHardwareMonitorLib.dll"))
            from LibreHardwareMonitor.Hardware import Computer

            c = Computer()
            c.IsCpuEnabled = True
            c.IsMotherboardEnabled = True
            c.IsGpuEnabled = False
            c.Open()
            self._computer = c
            self.ok = True
        except Exception:
            self.ok = False

    def read(self) -> dict:
        if not self.ok:
            return {}
        out = {}
        try:
            for hw in self._computer.Hardware:
                hw.Update()
                for sh in hw.SubHardware:
                    sh.Update()
                self._scan(hw, str(hw.HardwareType), out)
        except Exception:
            return {}
        return out

    def _scan(self, hw, htype: str, out: dict):
        for s in hw.Sensors:
            try:
                stype = str(s.SensorType)
                if s.Value is None:
                    continue
                raw = float(s.Value)
            except Exception:
                continue
            name = str(s.Name)

            htype_low = htype.lower()
            name_low = name.lower()

            if stype == "Temperature":
                val = round(raw, 1)
                if val <= 0:
                    continue
                if "cpu" in htype_low and 'cpu_temp' not in out:
                    if any(k in name_low for k in (
                        "tctl", "tdie", "package", "core", "cpu", "ccd", "die"
                    )):
                        out['cpu_temp'] = val
                if "vrm" in name_low and 'vrm_temp' not in out:
                    out['vrm_temp'] = val
                if "motherboard" in htype_low and 'motherboard_temp' not in out:
                    if any(k in name_low for k in ("system", "motherboard", "mainboard", "board")):
                        out['motherboard_temp'] = val

            elif stype == "Clock" and "cpu" in htype_low:
                # Живая частота ядер CPU. psutil на Windows возвращает
                # базовую (залипает), поэтому берём максимум реальных
                # частот ядер из LHM (исключая Bus Speed).
                if raw > 0 and "core" in name_low and "bus" not in name_low:
                    if raw > out.get('cpu_freq', 0):
                        out['cpu_freq'] = round(raw, 0)

        for sub in hw.SubHardware:
            self._scan(sub, htype, out)

    def close(self):
        if self._computer is not None:
            try:
                self._computer.Close()
            except Exception:
                pass
