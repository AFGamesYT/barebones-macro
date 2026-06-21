import sys

from pynput import mouse, keyboard
from datetime import datetime
from time import time, sleep
from os import makedirs
import yaml
from threading import Thread
from pathlib import Path

makedirs("macros", exist_ok=True)

monitoring = False
macro_playing = False
buffer: list[str] = []

last_command_time = time()
last_command = ""

pressed_keys = set()

k_controller = keyboard.Controller()
m_controller = mouse.Controller()

if Path("config.yaml").exists():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
else:
    raise FileNotFoundError("Config file wasn't found. Check, if it's in the same directory as main.py")


def parse_key(key_name):
    if len(key_name) == 1:
        return keyboard.KeyCode.from_char(key_name)
    else:
        if hasattr(keyboard.Key, key_name):
            return getattr(keyboard.Key, key_name)
        else:
            raise ValueError(f"Invalid keybind in config.yaml: '{key_name}'")

# this jumbled up thing gets keys from the config
record_keys = {parse_key(k) for k in config["keybinds"]["record"].lower().replace(" ", "").split("+")}
close_program_keys = {parse_key(k) for k in config["keybinds"]["close_program"].lower().replace(" ", "").split("+")}
play_latest_keys = {parse_key(k) for k in config["keybinds"]["play_latest_macro"].lower().replace(" ", "").split("+")}
play_selected_keys = {parse_key(k) for k in config["keybinds"]["play_selected_macro"].lower().replace(" ", "").split("+")}
stop_macro_keys = {parse_key(k) for k in config["keybinds"]["stop_macro"].lower().replace(" ", "").split("+")}

selected_macro_path = config["selected_macro"]
loop = config["loop"]

def save_macro():
    global buffer

    macro_path = f"macros/{str(datetime.now()).replace(":", ".")}.bmacro"

    with open(macro_path, "w") as f:
        f.writelines(buffer)

    # also save as latest
    with open("macros/latest.bmacro", "w") as f_latest:
        f_latest.writelines(buffer)

    print(f"Wrote macro to '{macro_path}' and 'macros/latest.bmacro'")

def play_macro(path):
    global macro_playing

    with open(path, "r") as f:
        lines = f.readlines()

    while True:
        for l in lines:
            line = l.replace("\n", "")
            command = line.split(" ")[0]

            if not macro_playing: break

            match command:
                case "WAIT":
                    sleep(float(line.split(" ")[1]))
                case "MOVE":
                    m_controller.position = (line.split(" ")[1], line.split(" ")[2])
                case "CLICK":
                    if line.split(" ")[4] == "True":
                        m_controller.press(getattr(mouse.Button, line.split(" ")[3].replace("Button.", "")))
                    else:
                        m_controller.release(getattr(mouse.Button, line.split(" ")[3].replace("Button.", "")))
                case "SCROLL":
                    m_controller.scroll(0, int(line.split(" ")[3]))
                case "PRESS":
                    if "'" in line.split(" ")[1]: k_controller.press(line.split(" ")[1].replace("'", ""))
                    if "Key." in line.split(" ")[1]: k_controller.press(getattr(keyboard.Key, line.split(" ")[1].replace("Key.", "")))
                case "RELEASE":
                    if "'" in line.split(" ")[1]: k_controller.release(line.split(" ")[1].replace("'", ""))
                    if "Key." in line.split(" ")[1]: k_controller.release(getattr(keyboard.Key, line.split(" ")[1].replace("Key.", "")))
                case _:
                    raise Exception("Something unexpected happened!")
        if not loop: break

    print("Macro finished playing.")
    macro_playing = False

def on_move(x, y):
    global last_command_time, last_command

    if monitoring:
        wait_time = time()-last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")
        elif last_command == "MOVE":
            return

        last_command_time = time()

        buffer.append(f"MOVE {x} {y}\n")
        last_command = "MOVE"

def on_click(x, y, button, pressed):
    global last_command_time, last_command

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"CLICK {x} {y} {button} {pressed}\n")
        last_command = "CLICK"

def on_scroll(x, y, dx, dy):
    global last_command_time, last_command

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"SCROLL {x} {y} {dy}\n")
        last_command = "SCROLL"


mouse_listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click,
    on_scroll=on_scroll
)


def on_press(key):
    global last_command_time, last_command, buffer, monitoring, macro_playing

    pressed_keys.add(key)

    if not macro_playing:
        if monitoring and record_keys == pressed_keys:
            monitoring = False

            if buffer[0].split(" ")[0] == "WAIT":
                buffer = buffer[1:]

            for k in pressed_keys:
                buffer.append(f"RELEASE {k}\n")

            save_macro()
            return

        if monitoring:
            wait_time = time() - last_command_time

            if wait_time > 0.02:
                buffer.append(f"WAIT {wait_time}\n")

            last_command_time = time()

            buffer.append(f"PRESS {key}\n")
            last_command = "PRESS"

        elif not monitoring and record_keys == pressed_keys:
            monitoring = True
            buffer = []

            print("Started recording macro.")


    if not monitoring and not macro_playing:
        if play_latest_keys == pressed_keys:

            print("Playing latest macro.")
            macro_playing = True
            Thread(target=play_macro, args=["macros/latest.bmacro"], daemon=True).start()

        elif play_selected_keys == pressed_keys:

            print("Playing latest macro.")
            macro_playing = True

            if "macros/" in selected_macro_path:
                path = selected_macro_path
            else:
                if ".bmacro" in selected_macro_path:
                    path = f"macros/{selected_macro_path}"
                else:
                    path = f"macros/{selected_macro_path}.bmacro"

            Thread(target=play_macro, args=[path], daemon=True).start()

    if stop_macro_keys == pressed_keys:
        macro_playing = False
        print("Stopped macro")

    if close_program_keys == pressed_keys:
        print("Exiting program.", end="")
        macro_playing = False

        if monitoring:
            save_macro()
            print(" The current recording is saved.")
        else:
            print("")

        keyboard_listener.stop()
        mouse_listener.stop()
        sys.exit()


def on_release(key):
    global monitoring, buffer, last_command_time, last_command, pressed_keys

    pressed_keys = set()

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"RELEASE {key}\n")
        last_command = "RELEASE"


keyboard_listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release
)

keyboard_listener.start()
mouse_listener.start()

keyboard_listener.join()
mouse_listener.join()