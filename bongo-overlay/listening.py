import asyncio
import websockets
from pynput import keyboard
import sounddevice as sd
import numpy as np
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import random
import time
from pynput import mouse


clients = set()
keys_down = set()
pressed_keys = set()
handled_keys = set()
is_talking = False
last_message = None
current_volume = 0.0

keybinds = {"left": "s", "right": "d"}
sensitivity = 2.0
random_hand_mode = False
alternate_tap_mode = False
audio_input_enabled = True
alternate_toggle = True
full_keyboard_enabled = False
both_paws_mode = False
custom_keys_enabled = False
custom_keys = set()

def load_keybinds():
    global keybinds
    if os.path.exists("keybinds.txt"):
        with open("keybinds.txt", "r") as f:
            for line in f:
                if ":" in line:
                    action, key = line.strip().split(":")
                    keybinds[action] = key.lower()

def load_sensitivity():
    global sensitivity
    if os.path.exists("sensitivity.txt"):
        with open("sensitivity.txt", "r") as f:
            try:
                sensitivity = float(f.read().strip())
            except ValueError:
                sensitivity = 2.0

def load_bool_setting(filename, varname):
    globals()[varname] = False
    if os.path.exists(filename):
        with open(filename, "r") as f:
            globals()[varname] = f.read().strip().lower() == "true"

def load_custom_keys():
    global custom_keys
    custom_keys = set()
    if os.path.exists("custom_keys.txt"):
        with open("custom_keys.txt", "r") as f:
            keys = f.read().strip().lower().replace(" ", "")
            if keys:
                custom_keys = set(keys.split(","))

def audio_callback(indata, frames, time, status):
    global is_talking, current_volume
    volume = np.linalg.norm(indata)
    current_volume = volume
    is_talking = volume > sensitivity if audio_input_enabled else False
    # print(f"volume: {volume:.2f}, is_talking: {is_talking}")  # debug line


async def send_state():
    global last_message, alternate_toggle
    last_input_time = time.time()
    idle_delay = 0.3

    while True:
        left = keybinds.get("left", "s")
        right = keybinds.get("right", "d")
        new_keys = keys_down - handled_keys
        state = "idle"

        if new_keys or keys_down or is_talking:
            last_input_time = time.time()

        if both_paws_mode:
            valid_keys = keys_down if full_keyboard_enabled or custom_keys_enabled else keys_down & {left, right}
            if valid_keys:
                state = "sd"
        elif random_hand_mode and not alternate_tap_mode:
            if new_keys and (full_keyboard_enabled or custom_keys_enabled or new_keys & {left, right}):
                state = random.choice(["s", "d"])
                handled_keys.update(new_keys)
            elif keys_down:
                state = last_message.split("|")[0] if last_message else "idle"
        elif alternate_tap_mode and not random_hand_mode:
            if new_keys and (full_keyboard_enabled or custom_keys_enabled or new_keys & {left, right}):
                state = "s" if alternate_toggle else "d"
                alternate_toggle = not alternate_toggle
                handled_keys.update(new_keys)
            elif keys_down:
                state = last_message.split("|")[0] if last_message else "idle"
        else:
            if left in keys_down and right in keys_down:
                state = "sd"
            elif left in keys_down:
                state = "s"
            elif right in keys_down:
                state = "d"

        handled_keys.intersection_update(keys_down)

        if not keys_down and not is_talking and time.time() - last_input_time > idle_delay:
            state = "idle"

        norm_volume = min(current_volume / 10.0, 1.0)
        message = f"{state}|{is_talking}|{norm_volume:.3f}"
        if message != last_message:
            last_message = message
            for ws in clients.copy():
                try:
                    await ws.send(message)
                except websockets.exceptions.ConnectionClosed:
                    clients.discard(ws)

        await asyncio.sleep(0.01)

async def handler(websocket):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.discard(websocket)

def on_press(key):
    try:
        if hasattr(key, 'char') and key.char:
            char = key.char.lower()
        elif hasattr(key, 'name'):
            char = key.name.lower()
        else:
            return

        if custom_keys_enabled:
            if char in custom_keys and char not in pressed_keys:
                pressed_keys.add(char)
                keys_down.add(char)
        elif full_keyboard_enabled or char in keybinds.values():
            if char not in pressed_keys:
                pressed_keys.add(char)
                keys_down.add(char)
    except AttributeError:
        pass

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char:
            char = key.char.lower()
        elif hasattr(key, 'name'):
            char = key.name.lower()
        else:
            return
        keys_down.discard(char)
        pressed_keys.discard(char)
        handled_keys.discard(char)
    except AttributeError:
        pass

class SettingsChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("keybinds.txt"):
            load_keybinds()
        elif event.src_path.endswith("sensitivity.txt"):
            load_sensitivity()
        elif event.src_path.endswith("random_hand_mode.txt"):
            load_bool_setting("random_hand_mode.txt", "random_hand_mode")
        elif event.src_path.endswith("alternate_tap_mode.txt"):
            load_bool_setting("alternate_tap_mode.txt", "alternate_tap_mode")
        elif event.src_path.endswith("audio_input_enabled.txt"):
            load_bool_setting("audio_input_enabled.txt", "audio_input_enabled")
        elif event.src_path.endswith("full_keyboard_mode.txt"):
            load_bool_setting("full_keyboard_mode.txt", "full_keyboard_enabled")
        elif event.src_path.endswith("both_paws_mode.txt"):
            load_bool_setting("both_paws_mode.txt", "both_paws_mode")
        elif event.src_path.endswith("custom_keys_mode.txt"):
            load_bool_setting("custom_keys_mode.txt", "custom_keys_enabled")
        elif event.src_path.endswith("custom_keys.txt"):
            load_custom_keys()

def start_watchdog():
    event_handler = SettingsChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=False)
    observer.start()

def start_keyboard_listener():
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

def start_mic_listener():
    return sd.InputStream(callback=audio_callback, channels=1, samplerate=44100)
    
def on_click(x, y, button, pressed):
    name = str(button).replace("Button.", "").lower()  # e.g., 'mouse1'
    if pressed:
        if custom_keys_enabled and name in custom_keys and name not in pressed_keys:
            pressed_keys.add(name)
            keys_down.add(name)
        elif full_keyboard_enabled and name not in pressed_keys:
            pressed_keys.add(name)
            keys_down.add(name)
    else:
        keys_down.discard(name)
        pressed_keys.discard(name)
        handled_keys.discard(name)

def start_mouse_listener():
    listener = mouse.Listener(on_click=on_click)
    listener.start()


def main():
    load_keybinds()
    load_sensitivity()
    load_bool_setting("random_hand_mode.txt", "random_hand_mode")
    load_bool_setting("alternate_tap_mode.txt", "alternate_tap_mode")
    load_bool_setting("audio_input_enabled.txt", "audio_input_enabled")
    load_bool_setting("full_keyboard_mode.txt", "full_keyboard_enabled")
    load_bool_setting("both_paws_mode.txt", "both_paws_mode")
    load_bool_setting("custom_keys_mode.txt", "custom_keys_enabled")
    load_custom_keys()
    start_keyboard_listener()
    start_watchdog()
    mic_stream = start_mic_listener()
    mic_stream.start()
    start_mouse_listener()

    async def runner():
        async with websockets.serve(handler, "localhost", 8770, ping_interval=None):
            await send_state()

    asyncio.run(runner())

if __name__ == "__main__":
    main()
