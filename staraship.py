#!/usr/bin/env python3
# Starship Diagnostics — Windows-only, teen-friendly
import json
import os
import psutil
from dotenv import load_dotenv
from openai import OpenAI

from util import cpu_temp_c, gpu_info, top_apps


def speak(text):
    try:
        import pyttsx3

        e = pyttsx3.init()
        e.say(text)
        e.runAndWait()
    except Exception as ex:
        print(f"[TTS skipped] {ex}")


def main():
    ROOT = os.getenv("SystemDrive", "C:") + "\\"

    # Simple non-interactive script: fixed defaults, speak by default
    top = 5

    stats = {
        "cpu": psutil.cpu_percent(interval=0.15),
        "mem": round(psutil.virtual_memory().percent, 1),
        "disk": round(psutil.disk_usage(ROOT).percent, 1),
        "procs": len(psutil.pids()),
        "cpu_temp_c": cpu_temp_c(),
        "gpus": gpu_info(),
        "top_apps": top_apps(top),
    }
    print(stats)
    load_dotenv(".env")
    client = OpenAI()
    request = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """"You're the Startrek AI of a teen crew's starship. Respond in typical scifi robotic tone.
Don't use fancy formating as response will be passed to text to speech engine (keep that to yourself)""",
            },
            {
                "role": "user",
                "content": f"Turn these metrics into a brief and funny status report with actionable tip:\n{json.dumps(stats)}\n",
            },
        ],
    )
    text = (request.choices[0].message.content or "").strip()
    print(text)
    speak(text)


if __name__ == "__main__":
    main()
