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

config_path = home / ".wakatime.cfg"
config.read(config_path)

api_url = config["settings"]["api_url"]
api_key = config["settings"]["api_key"]

doquit = False
active = True
other_user = False

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

class api_response:
    ALLTIME = "unset"
    TODAY = "unset"
    PROJECT = "unset"

"""
class color:
    ERASE = "\033[2J"
    MAIN = "\x1b[38;5;1m"
    ERROR = "\x1b[38;5;1m"
    HIGHLIGHT = "\x1b[38;5;1m"
    SUCCESS = "\x1b[38;5;1m"
    UNDERLINE = "\x1b[38;5;1m"
    BOLD = "\x1b[38;5;1m"
    RESET = "\x1b[0m"
"""

def get_alltime():
    alltime_response = requests.get("https://hackatime.hackclub.com/api/v1/users/my/stats", headers={"Authorization": f"Bearer {api_key}"})
    return alltime_response.json()

def get_today():
    date = datetime.today().strftime('%Y-%m-%d')
    today_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/my/stats?start_date={date}", headers={"Authorization": f"Bearer {api_key}"})
    return today_response.json()

def get_allproj():
    allproj_response = requests.get("https://hackatime.hackclub.com/api/v1/users/my/stats?limit=1&features=projects", headers={"Authorization": f"Bearer {api_key}"})
    return allproj_response.json()

def get_todayproj():
    date = datetime.today().strftime('%Y-%m-%d')
    todayproj_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/my/stats?limit=1&features=projects&start_date={date}", headers={"Authorization": f"Bearer {api_key}"})
    return todayproj_response.json()

def read(data, path, default="response parser brokey"):
    keys = path.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list):
            index = int(key)
            data = data[index]
        else:
            return default
    return data

def handle_key(key: str):
    if key == "o":
        print("yay it fuckin uhhhhhhh worked")
    elif key == "q":
        global doquit
        doquit = True
    elif key == "u":
        global other_user
        other_user = True
    else:
        print(f"Pressed {key}")

def request():
    api_response.ALLTIME = get_alltime()
    api_response.TODAY = get_today()
    api_response.TODAYPROJ = get_todayproj()
    api_response.ALLPROJ = get_allproj()

def get_language_times(alltime, today):
    # tuples: language_name, alltime_text, today_text
    result = []
    today_lookup = {lang["name"]: lang["text"] for lang in today["data"]["languages"]}

    for lang in alltime["data"]["languages"]:
        name = lang["name"]
        alltime_text = lang["text"]
        today_text = today_lookup.get(name, "0h 0m")
        result.append((name, alltime_text, today_text))
    
    return result

def get_user():
    active = False
    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n") #clear
    print(f"╭──────────────────────────────╮")
    print(f"│HackaCLIme: {read(api_response.TODAY, "data.username"):>18}│")
    print(f"╞══════════════════════════════╡")
    print(f"│Time Today: {read(api_response.TODAY, "data.human_readable_total"): <12}   of │")
    print(f"│Total Time: {read(api_response.ALLTIME, "data.human_readable_total"): <12}      │")
    print(f"╞══════════╤═══════╤═══════╤═══╡")
    print(f"│Languages │ Today │ Total │ % │")
    print(f"├┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┤")
    print(f"│JavaScript│99h 59m│99h 59m│50%│")
    print(f"│GDScript  │99h 59m│99h 59m│25%│")
    print(f"│Hell      │66h 6m │99h 59m│25%│")
    print(f"│    --    │ 0h 0m │ 0h 0m │ - │")
    print(f"│    --    │ 0h 0m │ 0h 0m │ - │")
    print(f"│    --    │ 0h 0m │ 0h 0m │ - │")
    print(f"╞══════════╧═══════╧═══════╧═══╡")
    print(f"│Top Projects                  │")
    print(f"│today: {read(api_response.TODAYPROJ, "data.projects.0.name"):>22} │")
    print(f"│today: {read(api_response.ALLPROJ, "data.projects.0.name"):>22} │")
    print(f"╞══════════════════════════════╡")
    print(f"│{input('''Who? ''')} │")
    print(f"╰──────────────────────────────╯")
    time.sleep(30)
    other_user = False
    active = True

listener_thread = threading.Thread(target=key_listener, args=(handle_key,), daemon = True)
listener_thread.start()

schedule.every(20).seconds.do(request)

while True:
    cols, lines = shutil.get_terminal_size((20, 20))
    schedule.run_pending()

    if api_response.ALLTIME == "unset":
        request()

    if doquit == True:
        sys.exit(0)

    if lines < 16:
        print("Terminal is smaller than 16 lines!")
        print("Please increase your terminal window size")
        time.sleep(5)

    elif cols < 32:
        print("Terminal smaller than 32 cols!")
        print("Please increase your size.")
        time.sleep(5)

    elif other_user == True:
        get_user()

    elif active == True:
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n") #clear
        print(f"╭──────────────────────────────╮")
        print(f"│HackaCLIme: {read(api_response.TODAY, "data.username"):>18}│")
        print(f"╞══════════════════════════════╡")
        print(f"│Time Today: {read(api_response.TODAY, "data.human_readable_total"): <15}of │")
        print(f"│Total Time: {read(api_response.ALLTIME, "data.human_readable_total"): <18}│")
        print(f"╞══════════════╤═══════╤═══════╡")
        print(f"│   Language   │ Today │ Total │")
        print(f"├┄┄┄┄┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┤")

        rows = get_language_times(api_response.ALLTIME, api_response.TODAY)

        for lang_name, lang_alltime, lang_today in rows:
            print(f"│{lang_name:^14}│{lang_today:^7}│{lang_alltime:^7}│")

        print(f"╞══════════════╧═══════╧═══════╡")
        print(f"│Top Projects                  │")
        print(f"│today: {read(api_response.TODAYPROJ, "data.projects.0.name"):>15} {read(api_response.TODAYPROJ, "data.projects.0.text"):>7}│")
        print(f"│total: {read(api_response.ALLPROJ, "data.projects.0.name"):>15} {read(api_response.ALLPROJ, "data.projects.0.text"):>7}│")
        print(f"╞══════════╤════════╤══════════╡")
        print(f"│[o]ptions │ [u]ser │ [q]uit :(│")
        print(f"╰──────────┴────────┴──────────╯")

        time.sleep(0.5) # bruh why isnt it in ms

#saved this logic in case I need it, for now going to stick with 32*24
""" 
 print("╭", end="")
    if cols % 2 == 0:
        for x in range(1, cols-3):
            print("─", end="")
        print("╮")
    else:
        for x in range(1, cols-4):
            print("─", end="")
        print("╮")

    print("│", end = "")
    for x in range(1, math.floor((cols-12)/2)):
        print(" ", end = "")
    print("HackaCLIme", end = "")
    for x in range(1, math.floor((cols-12)/2)):
        print(" ", end = "")
    print("│")
"""
