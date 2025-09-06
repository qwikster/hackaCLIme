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
import traceback
import re

config = configparser.ConfigParser()
home = Path.home()

config_path = home / ".wakatime.cfg"
config.read(config_path)

api_url = config["settings"]["api_url"]
api_key = config["settings"]["api_key"]
req_user = "my"

doquit = False
active = True
other_user = False
listening = True

old_settings = None
fd = None

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
        global fd
        fd = sys.stdin.fileno()
        global old_settings
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                global listening
                if listening == True:
                    dr, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if dr: 
                        key = sys.stdin.read(1)
                        callback(key)
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def safe_input(prompt = "> "):
    if not sys.platform.startswith("win"):
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    try:
        return input(prompt)
    finally:
        tty.setcbreak(fd)

def handle_exception(exc_type, exc_value, exc_traceback):
    if exc_type is KeyboardInterrupt:
        print("goodbye :(")
        sys.exit(0)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

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
    global req_user
    alltime_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/{req_user}/stats", headers={"Authorization": f"Bearer {api_key}"})
    return alltime_response.json()

def get_today():
    date = datetime.today().strftime('%Y-%m-%d')
    global req_user
    today_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/{req_user}/stats?start_date={date}", headers={"Authorization": f"Bearer {api_key}"})
    return today_response.json()

def get_allproj():
    global req_user
    allproj_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/{req_user}/stats?limit=1&features=projects", headers={"Authorization": f"Bearer {api_key}"})
    return allproj_response.json()

def get_todayproj():
    global req_user
    date = datetime.today().strftime('%Y-%m-%d')
    todayproj_response = requests.get(f"https://hackatime.hackclub.com/api/v1/users/{req_user}/stats?limit=1&features=projects&start_date={date}", headers={"Authorization": f"Bearer {api_key}"})
    return todayproj_response.json()

def read(data, path, default="response parser brokey"):
    keys = path.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list):
            if key.isdigit():
                index = int(key)
                if 0 <= index < len(data):
                    data = data[index]
                else: 
                    return "No work today!"
            else:
                return default
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
        global active
        active = False
        global listening
        global req_user
        listening = False
        req_user = get_user()
        request()
        if read(api_response.TODAY, "data.username") == "response parser brokey":
            print("Invalid user!")
            time.sleep(3)
            req_user = "my"
        active = True
        listening = True
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
    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n") #clear
    print(f"╭──────────────────────────────╮")
    print(f"│HackaCLIme: {read(api_response.TODAY, "data.username"):>18}│")
    print(f"╞══════════════════════════════╡")
    if read(api_response.TODAY, "data.human_readable_total") != "":
        print(f"│Time Today: {read(api_response.TODAY, "data.human_readable_total"): <15}of │")
    else:
        print(f"│Time Today: No time today!    │")
    print(f"│Total Time: {read(api_response.ALLTIME, "data.human_readable_total"): <18}│")
    print(f"╞═════════════╤═══════╤════════╡")
    print(f"│   Language  │ Today │ Total  │")
    print(f"├┄┄┄┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┄┤")

    rows = get_language_times(api_response.ALLTIME, api_response.TODAY)

    for lang_name, lang_alltime, lang_today in rows:
        if int(lang_alltime.translate(str.maketrans("", "", "hm "))) > 10:
            print(f"│{lang_name:^13}│{lang_today:^7}│{lang_alltime:^8}│")

    print(f"╞═════════════╧═══════╧════════╡")
    print(f"│Top Projects                  │")
    if read(api_response.TODAYPROJ, "data.projects.0.text") != "No work today!":
        print(f"│today: {read(api_response.TODAYPROJ, "data.projects.0.name"):>14}  {read(api_response.TODAYPROJ, "data.projects.0.text"):>7}│")
    else:
        print(f"│today:    No work done today! │")
    print(f"│total: {read(api_response.ALLPROJ, "data.projects.0.name"):>14} {read(api_response.ALLPROJ, "data.projects.0.text"):>8}│")
    print(f"╰──────────────────────────────╯\n")
    print(f"Type \"my\" for your profile -")
    user = safe_input("Slack member ID? ")
    return user

listener_thread = threading.Thread(target=key_listener, args=(handle_key,), daemon = True)
listener_thread.start()

sys.excepthook = handle_exception

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
        listening = False
        req_user = get_user()
        request()
        if read(api_response.TODAY, "data.username") == "response parser brokey":
            print("Invalid user!")
            time.sleep(3)
            req_user = "my"
        other_user = False
        listening = True

    elif active == True:
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n") #clear
        print(f"╭──────────────────────────────╮")
        print(f"│HackaCLIme: {read(api_response.TODAY, "data.username"):>18}│")
        print(f"╞══════════════════════════════╡")
        if read(api_response.TODAY, "data.human_readable_total") != "":
            print(f"│Time Today: {read(api_response.TODAY, "data.human_readable_total"): <15}of │")
        else:
            print(f"│Time Today: No time today!    │")
        print(f"│Total Time: {read(api_response.ALLTIME, "data.human_readable_total"): <18}│")
        print(f"╞═════════════╤═══════╤════════╡")
        print(f"│   Language  │ Today │ Total  │")
        print(f"├┄┄┄┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┄┤")

        rows = get_language_times(api_response.ALLTIME, api_response.TODAY)

        for lang_name, lang_alltime, lang_today in rows:
            if int(lang_alltime.translate(str.maketrans("", "", "hm "))) > 10:
                print(f"│{lang_name:^13}│{lang_today:^7}│{lang_alltime:^8}│")

        print(f"╞═════════════╧═══════╧════════╡")
        print(f"│Top Projects                  │")
        if read(api_response.TODAYPROJ, "data.projects.0.text") != "No work today!":
            print(f"│today: {read(api_response.TODAYPROJ, "data.projects.0.name"):>14}  {read(api_response.TODAYPROJ, "data.projects.0.text"):>7}│")
        else:
            print(f"│today:    No work done today! │")
        print(f"│total: {read(api_response.ALLPROJ, "data.projects.0.name"):>14} {read(api_response.ALLPROJ, "data.projects.0.text"):>8}│")
        print(f"╞══════════╤════════╤══════════╡")
        print(f"│[o]ptions │ [u]ser │ [q]uit :(│")
        print(f"╰──────────┴────────┴──────────╯")

        time.sleep(1) # customize speed?