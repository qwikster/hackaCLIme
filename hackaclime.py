import requests
import json
from datetime import datetime
import os
import sys
import random
import time
import threading
import shutil
import math
import configparser
from pathlib import Path
import schedule

config = configparser.ConfigParser()
home = Path.home()

if sys.platform.startswith("win"):
    config_path = home / ".wakatime.cfg"
else:
    config_path = home / ".wakatime.cfg"
    config.read(config_path)

api_url = config["settings"]["api_url"]
api_key = config["settings"]["api_key"]

print(f"url {api_url} key {api_key}")

if sys.platform.startswith("win"):
    import msvcrt

    def key_listener(callback):
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8", errors="ignore")
                callback(key)

else:
    import termios
    import tty
    import select
    
    def key_listener(callback): # i have no idea how this works tbh don't ask me, thanks internet
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                dr, _, _ = select.select([sys.stdin], [], [], 0.05)
                if dr: 
                    key = sys.stdin.read(1)
                    callback(key)
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class color:
    MAIN = "\033[91m" # don't forget to add, may add more later (?)
    ERROR = ""
    DIALOG = ""
    KEYPRESS = ""
    BACKGROUND = ""

class api_response:
    ALLTIME = "unset"
    TODAY = "unset"

def get_alltime():
    alltime_response = requests.get("https://hackatime.hackclub.com/api/v1/users/my/stats", headers={"Authorization": f"Bearer {api_key}"})
    return alltime_response.json()

def get_today():
    date = datetime.today().strftime('%Y-%m-%d')
    today_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/my/stats?start_date={date}", headers={"Authorization": f"Bearer {api_key}"})
    return today_response.json()

def read(data, path, default="Error: could not find parameter"):
    keys = path.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def handle_key(key: str):
    if key == "o":
        print("yay it fuckin uhhhhhhh worked")
    elif key == "q":
        sys.exit(0)
    else:
        print(f"Pressed {key}")

def request():
    api_response.ALLTIME = get_alltime()
    api_response.TODAY = get_today()
    print("set data")

listener_thread = threading.Thread(target=key_listener, args=(handle_key,), daemon = True)
listener_thread.start()

schedule.every(20).seconds.do(request)

while True:
    cols, lines = shutil.get_terminal_size((20, 20))
    schedule.run_pending()

    if api_response.ALLTIME == "unset":
        request()
        print(f"{api_response.TODAY}")

    if lines <= 8:
        print("Terminal is smaller than 8 lines!")
        print("Please increase your terminal window size")
        break
    if cols <= 32:
        print("Terminal smaller than 32 cols!")
        print("Please increase your size.")
        break

    print("╔", end="")
    if cols % 2 == 0:
        for x in range(1, cols-3):
            print("═", end="")
        print("╗")
    else:
        for x in range(1, cols-4):
            print("═", end="")
        print("╗")

    print("║", end = "")
    for x in range(1, math.floor((cols-12)/2)):
        print(" ", end = "")
    print("HackaCLIme", end = "")
    for x in range(1, math.floor((cols-12)/2)):
        print(" ", end = "")
    print("║")

    print(read(api_response.TODAY, "data.total_seconds"))

    time.sleep(0.5) # bruh why isnt it in ms
