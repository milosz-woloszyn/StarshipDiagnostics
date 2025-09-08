import psutil
import time
import concurrent.futures


def cpu_temp_c():
    try:
        import wmi

        vals = [
            t.CurrentTemperature
            for t in wmi.WMI(namespace="root\\wmi").MSAcpi_ThermalZoneTemperature()
            if getattr(t, "CurrentTemperature", None)
        ]
        return (
            round(sum(v / 10 - 273.15 for v in vals) / len(vals), 1) if vals else None
        )
    except Exception:
        return None


def gpu_info():
    try:
        import pynvml as N

        N.nvmlInit()
        hs = [N.nvmlDeviceGetHandleByIndex(i) for i in range(N.nvmlDeviceGetCount())]
        info = [
            {
                "name": (
                    N.nvmlDeviceGetName(h).decode()
                    if hasattr(N.nvmlDeviceGetName(h), "decode")
                    else str(N.nvmlDeviceGetName(h))
                ),
                "util": N.nvmlDeviceGetUtilizationRates(h).gpu,
                "mem": round(
                    100
                    * N.nvmlDeviceGetMemoryInfo(h).used
                    / max(1, N.nvmlDeviceGetMemoryInfo(h).total),
                    1,
                ),
                "temp": N.nvmlDeviceGetTemperature(h, N.NVML_TEMPERATURE_GPU),
            }
            for h in hs
        ]
        N.nvmlShutdown()
        return info
    except Exception:
        return []


def top_apps(n=5, sample=0.3):
    # Gather current processes once
    procs = list(psutil.process_iter(["name"]))

    rows = []

    def measure(p):
        try:
            # measure CPU over the sample interval for this process
            cpu = p.cpu_percent(interval=sample)
            mem = round(p.memory_percent(), 1)
            name = p.info.get("name") or "unknown"
            return {"name": name, "cpu": cpu, "mem": mem}
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
        except Exception:
            return None

    # Submit all measurements concurrently so total wait ~ sample seconds
    if procs:
        max_workers = min(32, len(procs))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(measure, p) for p in procs]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res:
                    rows.append(res)

    # fallback: no processes or all failed -> empty list
    return sorted(rows, key=lambda r: r["cpu"], reverse=True)[:n]


def top_apps(n=5, sample=0.3):
    # First enumerate and "prime" CPU counters; ignore processes that disappear or are inaccessible
    procs = list(psutil.process_iter(["name"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # process gone or not accessible — skip
            continue
        except Exception:
            continue

    time.sleep(sample)

    # Re-enumerate after the interval to avoid using Process objects that may have gone away
    rows = []
    for p in psutil.process_iter(["name"]):
        try:
            cpu = p.cpu_percent(None)
            name = p.info.get("name") or "unknown"
            if name == "System Idle Process":
                continue
            mem = round(p.memory_percent(), 1)
            return {"name": name, "cpu": cpu, "mem": mem}
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    return sorted(rows, key=lambda r: r["cpu"], reverse=True)[:n]
