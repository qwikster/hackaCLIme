import requests
import json
from datetime import datetime
import os
import sys
import random
import time
import threading

api_key = "YOUR_API_KEY"
state = "main"

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

class col:
    MAIN = "\033[91m" # don't forget to add, may add more later (?)
    ERROR = ""
    DIALOG = ""
    KEYPRESS = ""
    BACKGROUND = ""

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

listener_thread = threading.Thread(target=key_listener, args=(handle_key,), daemon = True)
listener_thread.start()

while True:
    size = os.get_terminal_size()
    print(f"{col.MAIN}Main loop running fine :thumbsup:")
    time.sleep(0.5) # bruh why isnt it in ms

if False: # DISABLED DO NOT FORGET TO ENABLE
    print(f"{col.MAIN} TEST COLOR (should be red)")
    print(read(get_today(), "data.username"))