#!/usr/bin/env python3
# Starship Diagnostics — Windows-only, teen-friendly
import os, json, time, argparse, psutil
from pathlib import Path


# New: load .env from project root (search upward from this file)
def load_env_from_project_root(filename=".env", override=False):
    start = Path(__file__).resolve().parent
    cur = start
    while True:
        candidate = cur / filename
        if candidate.exists() and candidate.is_file():
            # Prefer python-dotenv if available
            try:
                from dotenv import load_dotenv as _load_dotenv

                _load_dotenv(dotenv_path=str(candidate), override=override)
                return
            except Exception:
                pass
            # Manual lightweight parser: KEY=VALUE, ignore comments and blank lines
            try:
                with candidate.open(encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        # remove surrounding single/double quotes
                        if len(val) >= 2 and (
                            (val[0] == val[-1]) and val[0] in ('"', "'")
                        ):
                            val = val[1:-1]
                        if override or key not in os.environ:
                            os.environ[key] = val
            except Exception:
                pass
            return
        if cur.parent == cur:
            # reached filesystem root
            return
        cur = cur.parent


# ensure .env is loaded before any getenv calls (e.g. ROOT)
load_env_from_project_root()

ROOT = os.getenv("SystemDrive", "C:") + "\\"


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
            rows.append({"name": name, "cpu": cpu})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    return sorted(rows, key=lambda r: r["cpu"], reverse=True)[:n]


def speak(text):
    try:
        import pyttsx3

        e = pyttsx3.init()
        e.say(text)
        e.runAndWait()
    except Exception as ex:
        print(f"[TTS skipped] {ex}")


def main():
    ap = argparse.ArgumentParser(description="Starship Diagnostics (Windows-only)")
    ap.add_argument("--top", type=int, default=5, help="Top N apps by CPU")
    ap.add_argument(
        "--speak", action="store_true", help="Speak the report", default=True
    )
    args = ap.parse_args()

    stats = {
        "cpu": psutil.cpu_percent(interval=0.15),
        "mem": round(psutil.virtual_memory().percent, 1),
        "disk": round(psutil.disk_usage(ROOT).percent, 1),
        "procs": len(psutil.pids()),
        "cpu_temp_c": cpu_temp_c(),
        "gpus": gpu_info(),
        "top_apps": top_apps(args.top),
    }

    try:
        from openai import OpenAI

        c = OpenAI()
        r = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """"You're the Startrek AI of a teen crew's starship. Respond in typical scifi robotic tone.
Don't use fancy formating as response will be passed to text to speech engine (keep that to yourself)""",
                },
                {
                    "role": "user",
                    "content": f"Turn these metrics into a brief and funny status report with one actionable tip:\n{json.dumps(stats)}\n",
                },
            ],
            temperature=0.7,
        )
        text = (r.choices[0].message.content or "").strip()
    except Exception as ex:
        tip = (
            "Tip: Close a heavy app from the list to free CPU."
            if stats["top_apps"]
            else "Tip: Quick reboot cycles systems."
        )
        gpu_line = (
            ", ".join(
                f'{g["name"]} {g["util"]}% @ {g["temp"]}°C' for g in stats["gpus"]
            )
            if stats["gpus"]
            else "no GPU telemetry"
        )
        text = "\n".join(
            [
                "🛸 Shipboard Pulse nominal.",
                f'CPU {stats["cpu"]}%'
                + (
                    f' | Temp {stats["cpu_temp_c"]}°C'
                    if stats["cpu_temp_c"] is not None
                    else ""
                ),
                f'MEM {stats["mem"]}% | DISK {stats["disk"]}%',
                f"GPU: {gpu_line}",
                tip,
            ]
        )
        print(f"[Local summary used: {ex}]")

    print(text)
    if args.speak:
        speak(text)


if __name__ == "__main__":
    main()
