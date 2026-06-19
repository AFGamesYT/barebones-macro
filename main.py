from pynput import mouse, keyboard
from datetime import datetime
from time import time
from os import makedirs

makedirs("macros", exist_ok=True)

monitoring = False
buffer: list[str] = []
last_command = time()

def get_same_command_indexes(buffer_list: list[str], i: int) -> int:
    try:
        if buffer_list[i].split(" ")[0] != buffer_list[i+1].split(" ")[0]:
            return i
            pass
        else:
            get_same_command_indexes(buffer_list, i+1)
            pass
    except IndexError:
        return i
        pass


def on_move(x, y):
    global last_command

    if monitoring:
        wait_time = time()-last_command

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command = time()

        buffer.append(f"MOVE {x} {y}\n")

def on_click(x, y, button, pressed):
    global last_command

    if monitoring:
        wait_time = time() - last_command

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command = time()

        buffer.append(f"CLICK {x} {y} {button} {pressed}\n")

def on_scroll(x, y, dx, dy):
    global last_command

    if monitoring:
        wait_time = time() - last_command

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command = time()

        buffer.append(f"SCROLL {x} {y} {dy}\n")


mouse_listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click,
    on_scroll=on_scroll
)


def on_press(key):
    global last_command

    if monitoring and key != keyboard.Key.page_down:
        wait_time = time() - last_command

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command = time()

        buffer.append(f"PRESS {key}\n")

def on_release(key):
    global monitoring, buffer, last_command

    if not monitoring and key == keyboard.Key.page_up:
        monitoring = True
        buffer = []

        print("Reset buffer and started recording macro.")

        return

    if not monitoring and key == keyboard.Key.f10:
        mouse_listener.stop()
        return False

    if monitoring and key == keyboard.Key.page_down:
        monitoring = False

        if buffer[0].split(" ")[0] == "WAIT":
            buffer = buffer[1:]

        marco_path = f"macros/{str(datetime.now()).replace(":", ".")}.bmacro"

        with open(marco_path, "w") as f:
            f.writelines(buffer)

        print(f"Wrote macro to {marco_path}")
        return

    if monitoring:
        wait_time = time() - last_command

        if wait_time > 0.02:
            buffer.append(f"WAIT {wait_time}\n")

        last_command = time()

        buffer.append(f"RELEASE {key}\n")


keyboard_listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release
)

keyboard_listener.start()
mouse_listener.start()

keyboard_listener.join()
mouse_listener.join()