from pynput import mouse, keyboard
from datetime import datetime
from time import time, sleep
from os import makedirs
from threading import Thread

import os, yaml, sys

makedirs("macros", exist_ok=True)

monitoring = False
macro_playing = False
buffer: list[str] = []

last_command_time = time()
last_command = ""

pressed_keys = set()

k_controller = keyboard.Controller()
m_controller = mouse.Controller()

try:
    with open("config.yaml", "r") as cfg:
        config = yaml.safe_load(cfg)

        if not config: raise ValueError("config.yaml is empty.")
except FileNotFoundError:
    raise FileNotFoundError("config.yaml wasn't found. Make sure it exists, and is in the same directory as main.py")


def handles_crash(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            print(f"Error in {func.__name__}: {type(err).__name__}: {err}")

            if monitoring and buffer:
                print("The current recording is saved:")
                save_macro()

            os._exit(1) # noqa

    return wrapper

@handles_crash
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

@handles_crash
def save_macro():
    global buffer

    macro_path = f"macros/{str(datetime.now()).replace(":", ".")}.bmacro"

    with open(macro_path, "w") as f:
        f.writelines(buffer)

    # also save as latest
    with open("macros/latest.bmacro", "w") as f_latest:
        f_latest.writelines(buffer)

    print(f"Wrote macro to '{macro_path}' and 'macros/latest.bmacro'")

@handles_crash
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

@handles_crash
def on_move(x, y, *_):
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

@handles_crash
def on_click(x, y, button, pressed, *_):
    global last_command_time, last_command

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"CLICK {x} {y} {button} {pressed}\n")
        last_command = "CLICK"

@handles_crash
def on_scroll(x, y, dx, dy, *_):
    global last_command_time, last_command

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"SCROLL {x} {y} {dy}\n")
        last_command = "SCROLL"


@handles_crash
def on_press(key, *_):
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
        sys.exit(0)

@handles_crash
def on_release(key, *_):
    global monitoring, buffer, last_command_time, last_command, pressed_keys

    pressed_keys = set()

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"RELEASE {key}\n")
        last_command = "RELEASE"


mouse_listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click,
    on_scroll=on_scroll
)

keyboard_listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release
)


keyboard_listener.start()
mouse_listener.start()

print("Started.")

keyboard_listener.join()
mouse_listener.join()
