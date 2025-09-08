from datetime import datetime
import os
import sys
import time
import threading
import shutil
import configparser
from pathlib import Path

# 3rd-party modules
import schedule 
import requests


try:
    wakatime_config = configparser.ConfigParser()
    wakatime_config.read([Path.home() / ".wakatime.cfg"], encoding="utf-8-sig")
    api_url = wakatime_config["settings"]["api_url"]
    api_key = wakatime_config["settings"]["api_key"]
except:  # noqa: E722
    print("Could not read your \nconfig file. Do you have \nHackatime installed? It \nshould be under your user \nfolder, then .wakatime.cfg")

try:
    themes = configparser.ConfigParser() 
    theme_path = f"{os.path.dirname(os.path.abspath(__file__))}/hackaclime.cfg"
    themes.read(theme_path)
except:  # noqa: E722
    print("Could not read your \ntheme file. If you downloaded \nthis file from GitHub, STOP! \nGet the package from pip instead")

theme = themes["DEFAULT"]["currenttheme"]


doquit = False
active = True
other_user = False
listening = True

old_settings = None
fd = None
req_user = "my"

actual_print = print
buffer = ""

def print_buffer() -> None: # Avoid the stupid scrolling issue Windows' terminal has, i guess its too slow? or microsoft thinks it looks cool??
    global buffer
    
    actual_print(buffer, end="")
    buffer = ""

def print(*v, sep=" ", end="\n", flush=False) -> None:
    global buffer
    
    buffer += sep.join(v) + end
    if flush:
        print_buffer()

if sys.platform.startswith("win"):
    import msvcrt

    def key_listener(callback):
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode("utf-8", errors="ignore")
                callback(key)

else: # UNIX / LINUX only make sure it doesn't call these functions on a windows client
    import termios
    import tty
    import select
    
    def key_listener(callback): # mm yummy archaic terminal settings
        global fd
        global old_settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setcbreak(fd)
            
            while True:
                global listening
                
                if listening:
                    dr, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if dr: 
                        key = sys.stdin.read(1)
                        callback(key)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def safe_input(prompt = "> "):
    global listening
    listening = False
    
    if not sys.platform.startswith("win"):
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    try:
        return input(prompt)
    finally:
        if not sys.platform.startswith("win"):
            tty.setcbreak(fd)
        listening = True

def handle_exception(exc_type, exc_value, exc_traceback): # don't forget anything called from here will be in the listener thread
    if exc_type is KeyboardInterrupt:
        print("goodbye :(")
        print_buffer()
        
        sys.exit(0)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

class api_response: # Probably poor form to set up classes like this but I don't care it makes it easier to access, guess what PEP 8 can do :)
    ALLTIME = "unset"
    TODAY = "unset"
    PROJECT = "unset"

class color: # \x1b[38;2;RED;GREEN;BLUEm (store as tuple and convert with .split)
    TIME = "\x1b[38;2;9;230;169m"
    TEXT = "\x1b[38;2;55;120;169m"
    TITLE = "\x1b[38;2;237;198;69m"
    ERROR = "\x1b[38;2;214;64;69m"
    BORDER = "\x1b[38;2;101;169;205m"
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"

def load_theme(themes, theme_in): 
    global theme
    theme = theme_in
    
    themes["DEFAULT"]["currenttheme"] = theme
    time = themes[theme]["time"].split(", ")
    text = themes[theme]["text"].split(", ")
    title = themes[theme]["title"].split(", ")
    error = themes[theme]["error"].split(", ")
    border = themes[theme]["border"].split(", ")
    color.TIME = f"\x1b[38;2;{time[0]};{time[1]};{time[2]}m"
    color.TEXT = f"\x1b[38;2;{text[0]};{text[1]};{text[2]}m"
    color.TITLE = f"\x1b[38;2;{title[0]};{title[1]};{title[2]}m"
    color.ERROR = f"\x1b[38;2;{error[0]};{error[1]};{error[2]}m"
    color.BORDER = f"\x1b[38;2;{border[0]};{border[1]};{border[2]}m"

def get_alltime(): # could have combined these four to one function but it works and i'm too lazy to fix
    global req_user # re ^, add if you still have time to round up hackatime with
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

def read(data, path, default=f"{color.ERROR}response parser brokey"): # this is some recursive janky shit don't look at it wrong
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

def handle_key(key: str): # also in the listener thread!!! set > global active = False
    global active
    if key == "t":
        active = False
        theme_menu()
        active = True
        
    elif key == "q":
        global doquit # if you call sys.exit it'll just quit the listener
        doquit = True
        sys.exit(0)
        
    elif key == "u":
        global req_user
        active = False
        req_user = get_user()
        request()
        if read(api_response.TODAY, "data.username") == f"{color.ERROR}response parser brokey":
            print(f"{color.ERROR}Invalid user!")
            print_buffer()
            time.sleep(3)
            req_user = "my"
            request()
        active = True
    else:
        pass # other functions might need to go here?
             
def request(): # yeah this could def be one function
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
    print("\033[2J\033[H", end="") # clear
    
    print(f"{color.BORDER}╭──────────────────────────────╮")
    
    username = read(api_response.TODAY, "data.username")
    username = username[:18]
    print(f"│{color.TITLE}HackaCLIme: {color.TEXT}{username:>18}{color.BORDER}│")
    
    print("╞══════════════════════════════╡")
    
    if read(api_response.TODAY, "data.human_readable_total") != "":
        print(f"│{color.TITLE}Time Today: {color.TIME}{read(api_response.TODAY, "data.human_readable_total"): <15}{color.TITLE}of {color.BORDER}│")
    else:
        print(f"│{color.TITLE}Time Today: {color.ERROR}No time today!    {color.BORDER}│")
        
    print(f"│{color.TITLE}Total Time: {color.TIME}{read(api_response.ALLTIME, "data.human_readable_total"): <18}{color.BORDER}│")
    print("╞═════════════╤═══════╤════════╡")
    print(f"│   {color.TITLE}Language  {color.BORDER}│ {color.TITLE}Today {color.BORDER}│ {color.TITLE}Total  {color.BORDER}│")
    print("├┄┄┄┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┄┤")

    rows = get_language_times(api_response.ALLTIME, api_response.TODAY)
    for lang_name, lang_alltime, lang_today in rows:
        if int(lang_alltime.translate(str.maketrans("", "", "hm "))) > 10:
            lang_name = lang_name[:13]
            print(f"│{color.TEXT}{lang_name:^13}{color.BORDER}│{color.TIME}{lang_today:^7}{color.BORDER}│{color.TIME}{lang_alltime:^8}{color.BORDER}│")

    print("╞═════════════╧═══════╧════════╡")
    print(f"│{color.TITLE}Top Projects                  {color.BORDER}│")
    
    proj_name = "error?"
    proja_name = "error?"
    if read(api_response.TODAYPROJ, "data.projects.0.text") != "No work today!":
        proj_name = read(api_response.TODAYPROJ, "data.projects.0.name")
        proj_name = proj_name[:14]
        print(f"│{color.TITLE}today: {color.TEXT}{proj_name:>14}  {color.TIME}{read(api_response.TODAYPROJ, "data.projects.0.text"):>7}{color.BORDER}│")
    else:
        print(f"│{color.TITLE}today:    {color.ERROR}No work done today! {color.BORDER}│")
        
    proja_name = read(api_response.ALLPROJ, "data.projects.0.name")
    proja_name = proja_name[:14]
    print(f"│{color.TITLE}total: {color.TEXT}{proja_name:>14} {color.TIME}{read(api_response.ALLPROJ, 'data.projects.0.text'):>8}{color.BORDER}│")
    
    print("╰──────────────────────────────╯\n")
    print(f"{color.TITLE}Type {color.TEXT}\"my\" {color.TITLE}for your profile.")
    
    print_buffer()
    
    try:
        user = safe_input(f"{color.ERROR}Slack member ID? ")
    except:  # noqa: E722
        print("Invalid user,\ndid you use special chars?")
        print_buffer()
        return "my"
    
    return user

def theme_menu():
    global themes
    global theme_path
    
    while(1): 
        print("\033[2J\033[H", end="")
        print(f"{color.BORDER}╭──────────────────────────────╮")
        print(f"│ {color.TITLE}HackaCLIme:     {color.TEXT}Change Theme{color.BORDER} │")
        print("╞══════════════════════════════╡")

        i = 0
        themelist = []
        for index in themes:
            themelist.append(index)
            if index != "DEFAULT":
                if index == themes["DEFAULT"]["currenttheme"]:
                    print(f"│{color.TIME}{i:>2} {color.TITLE}(Current): {color.TEXT}{themes["DEFAULT"]["currenttheme"]:>15} {color.BORDER}│")
                else:
                    print(f"│{color.TIME}{i:>2}: {color.TEXT}{index:>25} {color.BORDER}│")
            i += 1
        
        print("╞═══════════╤═══════════╤══════╡")
        print(f"│{color.TITLE}Type number{color.BORDER}│{color.TITLE}[{color.ERROR}{color.UNDERLINE}{color.BOLD}n{color.RESET}{color.TITLE}]ew theme{color.BORDER}│{color.TITLE}[{color.ERROR}{color.UNDERLINE}{color.BOLD}b{color.RESET}{color.TITLE}]ack{color.BORDER}│")
        print("╰───────────┴───────────┴──────╯")
        
        print_buffer()
        
        num = safe_input(f"{color.TITLE}> ")
        if num == "n":
            create_theme()
            break
        elif num == "b":
            break
        elif num.isdigit():
            if (int(num) > len(themelist) - 1) or (int(num) < 1):
                print(f"{color.ERROR}Not an option, learn to count!")
                print_buffer()
                time.sleep(2)
                
                break
            pass
        else:
            print(f"{color.ERROR}Invalid input!")
            print_buffer()
            time.sleep(2)
            break

        theme = themelist[int(num)]
        times = themes[theme]["time"].split(", ")
        text = themes[theme]["text"].split(", ")
        title = themes[theme]["title"].split(", ")
        error = themes[theme]["error"].split(", ")
        border = themes[theme]["border"].split(", ")

        print("\033[2J\033[H", end="")
        print(f"{color.BORDER}╭──────────────────────────────╮")
        print(f"{color.BORDER}│ {color.TITLE}Theme: {color.TEXT}{theme:>21}{color.BORDER} │")
        print(f"{color.BORDER}╞══════════════════════════════╡")
        print(f"{color.BORDER}│ {color.TITLE}Numbers and time: \x1b[38;2;{times[0]};{times[1]};{times[2]}m69h 42m 0s{color.BORDER} │")
        print(f"{color.BORDER}│ {color.TITLE}Variable text fields: \x1b[38;2;{text[0]};{text[1]};{text[2]}mabc123{color.BORDER} │")
        print(f"{color.BORDER}│ {color.TITLE}Titles and prompts: \x1b[38;2;{title[0]};{title[1]};{title[2]}mTitle123{color.BORDER} │")
        print(f"{color.BORDER}│ {color.TITLE}Error/bad messages: \x1b[38;2;{error[0]};{error[1]};{error[2]}m Oopsies{color.BORDER} │")
        print(f"{color.BORDER}│ {color.TITLE}Program box borders: \x1b[38;2;{border[0]};{border[1]};{border[2]}m╞╪╡░▒▓█{color.BORDER} │")
        print(f"{color.BORDER}╞════════════╤═════╤════╤══════╡")
        print(f"{color.BORDER}│ {color.TITLE}Use theme? {color.BORDER}│{color.TITLE}[{color.ERROR}{color.UNDERLINE}{color.BOLD}y{color.RESET}{color.TITLE}]es{color.BORDER}│{color.TITLE}[{color.ERROR}{color.UNDERLINE}{color.BOLD}n{color.RESET}{color.TITLE}]o{color.BORDER}│{color.TITLE}[{color.ERROR}{color.UNDERLINE}{color.BOLD}b{color.RESET}{color.TITLE}]ack{color.BORDER}│")
        print("╰────────────┴─────┴────┴──────╯")
        
        print_buffer()
        
        choice = safe_input(f"{color.TITLE}> ")
        if choice == "y":
            load_theme(themes, theme)
            themes["DEFAULT"]["currenttheme"] = theme
            with open(theme_path, 'w') as configfile:
                themes.write(configfile)
            print("Success!")
            print_buffer()
            break
        elif choice == "b":
            break
        elif choice == "n":
            pass
        else:
            print(f"{color.ERROR}Invalid input!")
            print_buffer()
            time.sleep(2)
            
            break

def create_theme():
    global theme_path
    global themes
    
    print("\033[2J\033[H", end="")
    print(f"{color.TITLE}Creating new theme...")
    print(f"{color.TITLE}Input {color.ERROR}r, g, b{color.TITLE} / {color.ERROR}hex{color.TITLE} only. (No {color.ERROR}#{color.TITLE})")
    print(f"{color.TITLE}(Don't forget commas for RGB!)\n")
    print(f"{color.TITLE}Choose a name for your theme")
    print(f"{color.TITLE}(lowercase, alphanumeric)\n")
    
    print_buffer()
    
    name = safe_input("> ")
    name = name.translate(str.maketrans('', '', "!@#$%^&*()[]\"\'/}{"))
    themes[name] = {}
    
    for index in ["time", "text", "title", "error", "border"]:
        while(1):
            print(f"{color.TITLE}Input color for {index}s...")
            
            print_buffer()
            
            choice = safe_input(f"{color.TITLE}> ")
            if "," in choice:
                try:
                    col = choice.split(", ")
                    print(f"\x1b[38;2;{col[0]};{col[1]};{col[2]}mIs this the correct color? ░▒▓█")
                    print_buffer()
                    yn = safe_input("y/n > ")
                    
                    if yn == "y":
                        break
                    else:
                        pass
                    
                except ValueError:
                    print("Invalid value, try again...")
                    print_buffer()
                    time.sleep(2)
                    pass
            elif len(choice) == 6:
                try:
                    col = tuple(int(choice[i:i+2], 16) for i in (0, 2, 4))  
                    r, g, b = col
                    col = f"{r}, {g}, {b}"
                    
                    print(f"\x1b[38;2;{r};{g};{b}mIs this the correct color? ░▒▓█")
                    
                    print_buffer()
                    
                    yn = safe_input("y/n > ")
                    if yn == "y":
                        break
                    else:
                        pass
                    
                except ValueError:
                    print("Invalid value, try again...")
                    print_buffer()
                    time.sleep(2)
            else:
                print("Invalid string? Try again")
                print_buffer()
        themes[name][index] = col
        
        with open(theme_path, 'w') as configfile:
            themes.write(configfile)

def main():
    global listener_thread, fd, old_settings, listening

    sys.excepthook = handle_exception

    listener_thread = threading.Thread(target=key_listener, args=(handle_key,), daemon=True)
    listener_thread.start()

    schedule.every(20).seconds.do(request)

    load_theme(themes, themes["DEFAULT"]["currenttheme"])

    try:
        while True: # main loop
            cols, lines = shutil.get_terminal_size((20, 20))
            schedule.run_pending()

            if api_response.ALLTIME == "unset":
                request()

            if doquit:
                sys.exit(0)

            if lines < 16:
                print("Terminal is smaller than 16 lines!")
                print("Please increase your terminal window size")
                print_buffer()
                time.sleep(5)
                continue

            if cols < 32:
                print("Terminal smaller than 32 cols!")
                print("Please increase your size.")
                print_buffer()
                time.sleep(5)
                continue

            if active:
                print("\033[2J\033[H", end="") #clear
                print(f"{color.BORDER}╭──────────────────────────────╮")
                
                username = read(api_response.TODAY, "data.username")
                username = username[:18]
                print(f"│{color.TITLE}HackaCLIme: {color.TEXT}{username:>18}{color.BORDER}│")
                
                print("╞══════════════════════════════╡")
                
                if read(api_response.TODAY, "data.human_readable_total") != "":
                    print(f"│{color.TITLE}Time Today: {color.TIME}{read(api_response.TODAY, 'data.human_readable_total'): <15}{color.TITLE}of {color.BORDER}│")
                else:
                    print(f"│{color.TITLE}Time Today: {color.ERROR}No time today!    {color.BORDER}│")
                print(f"│{color.TITLE}Total Time: {color.TIME}{read(api_response.ALLTIME, 'data.human_readable_total'): <18}{color.BORDER}│")
                
                print("╞═════════════╤═══════╤════════╡")
                print(f"│   {color.TITLE}Language  {color.BORDER}│ {color.TITLE}Today {color.BORDER}│ {color.TITLE}Total  {color.BORDER}│")
                print("├┄┄┄┄┄┄┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┼┄┄┄┄┄┄┄┄┤")

                rows = get_language_times(api_response.ALLTIME, api_response.TODAY)

                for lang_name, lang_alltime, lang_today in rows:
                    if int(lang_alltime.translate(str.maketrans("", "", "hm "))) > 10:
                        lang_name = lang_name[:13]
                        print(f"│{color.TEXT}{lang_name:^13}{color.BORDER}│{color.TIME}{lang_today:^7}{color.BORDER}│{color.TIME}{lang_alltime:^8}{color.BORDER}│")

                print("╞═════════════╧═══════╧════════╡")
                
                print(f"│{color.TITLE}Top Projects                  {color.BORDER}│")
                
                if read(api_response.TODAYPROJ, "data.projects.0.text") != "No work today!":
                    proj_name = read(api_response.TODAYPROJ, "data.projects.0.name")[:14]
                    print(f"│{color.TITLE}today: {color.TEXT}{proj_name:>14}  {color.TIME}{read(api_response.TODAYPROJ, 'data.projects.0.text'):>7}{color.BORDER}│")
                else:
                    print(f"│{color.TITLE}today:    {color.ERROR}No work done today! {color.BORDER}│")
                proja_name = read(api_response.ALLPROJ, "data.projects.0.name")[:14]
                
                print(f"│{color.TITLE}total: {color.TEXT}{proja_name:>14} {color.TIME}{read(api_response.ALLPROJ, 'data.projects.0.text'):>8}{color.BORDER}│")
                print("╞══════════╤════════╤══════════╡")
                print(f"│ {color.TITLE}[{color.BOLD}{color.UNDERLINE}{color.ERROR}t{color.RESET}{color.TITLE}]hemes {color.BORDER}│ {color.TITLE}[{color.BOLD}{color.UNDERLINE}{color.ERROR}u{color.RESET}{color.TITLE}]ser {color.BORDER}│ {color.TITLE}[{color.BOLD}{color.UNDERLINE}{color.ERROR}q{color.RESET}{color.TITLE}]uit {color.ERROR}:({color.BORDER}│")
                print("╰──────────┴────────┴──────────╯")
                
                print_buffer()

            time.sleep(1)

    finally:
        # clean up in terminal? probably not required but linux be linux
        if not sys.platform.startswith("win") and 'old_settings' in globals() and old_settings is not None:
            try:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass


if __name__ == "__main__": # in case someone is stupid enough to import this
    main()