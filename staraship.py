#!/usr/bin/env python3
# Starship Diagnostics — Windows-only, teen-friendly
import os, json, time, argparse, psutil

ROOT = os.getenv('SystemDrive', 'C:') + '\\'

def cpu_temp_c():
    try:
        import wmi
        vals = [t.CurrentTemperature for t in wmi.WMI(namespace="root\\wmi").MSAcpi_ThermalZoneTemperature()
                if getattr(t, "CurrentTemperature", None)]
        return round(sum(v/10 - 273.15 for v in vals)/len(vals), 1) if vals else None
    except Exception:
        return None

def gpu_info():
    try:
        import pynvml as N
        N.nvmlInit()
        hs = [N.nvmlDeviceGetHandleByIndex(i) for i in range(N.nvmlDeviceGetCount())]
        info = [{"name": (N.nvmlDeviceGetName(h).decode()
                          if hasattr(N.nvmlDeviceGetName(h), "decode")
                          else str(N.nvmlDeviceGetName(h))),
                 "util": N.nvmlDeviceGetUtilizationRates(h).gpu,
                 "mem": round(100 * N.nvmlDeviceGetMemoryInfo(h).used /
                              max(1, N.nvmlDeviceGetMemoryInfo(h).total), 1),
                 "temp": N.nvmlDeviceGetTemperature(h, N.NVML_TEMPERATURE_GPU)} for h in hs]
        N.nvmlShutdown()
        return info
    except Exception:
        return []

def top_apps(n=5, sample=0.3):
    procs = list(psutil.process_iter(['name']))
    _ = [p.cpu_percent(None) for p in procs]  # prime
    time.sleep(sample)
    def row(p):
        try: return {"name": p.info.get('name') or 'unknown', "cpu": p.cpu_percent(None)}
        except Exception: return None
    rows = [r for r in (row(p) for p in procs) if r]
    return sorted(rows, key=lambda r: r['cpu'], reverse=True)[:n]

def speak(text):
    try:
        import pyttsx3
        e = pyttsx3.init(); e.say(text); e.runAndWait()
    except Exception as ex:
        print(f"[TTS skipped] {ex}")

def main():
    ap = argparse.ArgumentParser(description="Starship Diagnostics (Windows-only)")
    ap.add_argument("--top", type=int, default=5, help="Top N apps by CPU")
    ap.add_argument("--speak", action="store_true", help="Speak the report")
    args = ap.parse_args()

    stats = {
        "cpu": psutil.cpu_percent(interval=0.15),
        "mem": round(psutil.virtual_memory().percent, 1),
        "disk": round(psutil.disk_usage(ROOT).percent, 1),
        "procs": len(psutil.pids()),
        "cpu_temp_c": cpu_temp_c(),
        "gpus": gpu_info(),
        "top_apps": top_apps(args.top)
    }

    prompt = ("You're the upbeat AI of a teen crew's starship. "
              "Turn these metrics into a 5-line status report with one actionable tip:\n"
              + json.dumps(stats))

    try:
        from openai import OpenAI
        c = OpenAI()
        r = c.chat.completions.create(model="gpt-4o-mini",
              messages=[{"role":"user","content": prompt}], temperature=0.7)
        text = (r.choices[0].message.content or "").strip()
    except Exception as ex:
        tip = ("Tip: Close a heavy app from the list to free CPU."
               if stats["top_apps"] else "Tip: Quick reboot cycles systems.")
        gpu_line = (", ".join(f'{g["name"]} {g["util"]}% @ {g["temp"]}°C' for g in stats["gpus"])
                    if stats["gpus"] else "no GPU telemetry")
        text = "\n".join([
            "🛸 Shipboard Pulse nominal.",
            f'CPU {stats["cpu"]}%'
            + (f' | Temp {stats["cpu_temp_c"]}°C' if stats["cpu_temp_c"] is not None else ""),
            f'MEM {stats["mem"]}% | DISK {stats["disk"]}%',
            f'GPU: {gpu_line}',
            tip
        ])
        print(f"[Local summary used: {ex}]")

    print(text)
    if args.speak: speak(text)

if __name__ == "__main__":
    main()
