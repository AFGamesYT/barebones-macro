from pynput import mouse, keyboard
from datetime import datetime

monitoring = False
buffer: list[str] = []
last_command = datetime.now()

def get_same_command_indexes(buffer_list: list[str], i: int):
    try:
        if buffer_list[i].split(" ")[0] != buffer_list[i+1].split(" ")[0]:
            # command's different!!!!!!
            pass
        else:
            # command's the same!!!!!!
            pass
    except IndexError:
        # fuck you
        pass


def on_move(x, y):

    if monitoring:
        buffer.append(f"MOVE {x} {y}\n")

def on_click(x, y, button, pressed):

    if monitoring:
        buffer.append(f"CLICK {x} {y} {button} {pressed}\n")

def on_scroll(x, y, dx, dy):

    if monitoring:
        buffer.append(f"SCROLL {x} {y} {dy}\n")


mouse_listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click,
    on_scroll=on_scroll
)


def on_press(key):

    if monitoring and key != keyboard.Key.page_down:
        buffer.append(f"PRESS {key}\n")

def on_release(key):
    global monitoring, buffer

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

        marco_path = f"macros/{str(datetime.now()).replace(":", ".")}.bmacro"
        print(f"Wrote macro to {marco_path}")



        with open(marco_path, "w") as f:
            f.writelines(buffer)

        return

    if monitoring:
        buffer.append(f"RELEASE {key}\n")


keyboard_listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release
)

keyboard_listener.start()
mouse_listener.start()

keyboard_listener.join()
mouse_listener.join()