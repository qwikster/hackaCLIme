import requests
import json
from datetime import datetime
import os
import random
import time
import curses

api_key = "YOUR_API_KEY"
date = datetime.today().strftime('%Y-%m-%d')
active = True

class col:
    MAIN = "\033[91m"

def get_alltime():
    alltime_response = requests.get("https://hackatime.hackclub.com/api/v1/users/my/stats", headers={"Authorization": f"Bearer {api_key}"})
    return alltime_response.json()
    

def get_today():
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

def heartbeat():
    size = os.get_terminal_size()
    print(f"{col.MAIN} TEST COLOR (should be red)")
    print(read(get_today(), "data.username"))
    print(random.random())
    # print('\x1b[2J')
    print("sleep")

while(active):
    heartbeat()