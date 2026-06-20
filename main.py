from pynput import mouse, keyboard
from datetime import datetime
from time import time
from os import makedirs
import yaml

makedirs("macros", exist_ok=True)

monitoring = False
buffer: list[str] = []

last_command_time = time()
last_command = ""

pressed_keys = []

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def parse_key(key_name):
    if len(key_name) == 1:
        return keyboard.KeyCode.from_char(key_name)
    else:
        if hasattr(keyboard.Key, key_name):
            return getattr(keyboard.Key, key_name)
        else:
            raise ValueError(f"Invalid keybind in config.yaml: '{key_name}'")

# this jumbled up thing gets keys from the config
start_recording_keys = [parse_key(k) for k in config["keybinds"]["start_recording"].lower().replace(" ", "").split("+")]
stop_recording_keys = [parse_key(k) for k in config["keybinds"]["stop_recording"].lower().replace(" ", "").split("+")]
close_program_keys = [parse_key(k) for k in config["keybinds"]["close_program"].lower().replace(" ", "").split("+")]

def save_macro():
    global buffer

    macro_path = f"macros/{str(datetime.now()).replace(":", ".")}.bmacro"

    with open(macro_path, "w") as f:
        f.writelines(buffer)

    # also save as latest
    with open("macros/latest.bmacro", "w") as f_latest:
        f_latest.writelines(buffer)

    print(f"Wrote macro to '{macro_path}' and 'macros/latest.bmacro'")

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
    global last_command_time, last_command, buffer, monitoring

    pressed_keys.append(key)

    if monitoring and stop_recording_keys == pressed_keys:
        monitoring = False

        if buffer[0].split(" ")[0] == "WAIT":
            buffer = buffer[1:]

        save_macro()
        return

    if monitoring:
        wait_time = time() - last_command_time

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command_time = time()

        buffer.append(f"PRESS {key}\n")
        last_command = "PRESS"

    elif not monitoring and start_recording_keys == pressed_keys:
        monitoring = True
        buffer = []

        print("Started recording macro.")


    if close_program_keys == pressed_keys:
        if monitoring:
            save_macro()

        mouse_listener.stop()
        return False



def on_release(key):
    global monitoring, buffer, last_command_time, last_command

    pressed_keys.remove(key)

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