# listening.py
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

clients = set()
keys_down = set()
pressed_keys = set()
handled_keys = set()
is_talking = False
last_message = None
keybinds = {"left": "s", "right": "d"}
sensitivity = 2.0
random_hand_mode = False
alternate_tap_mode = False
audio_input_enabled = True
alternate_toggle = True

# load settings
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

def load_random_mode():
    global random_hand_mode
    if os.path.exists("random_hand_mode.txt"):
        with open("random_hand_mode.txt", "r") as f:
            random_hand_mode = f.read().strip().lower() == "true"

def load_alternate_mode():
    global alternate_tap_mode
    if os.path.exists("alternate_tap_mode.txt"):
        with open("alternate_tap_mode.txt", "r") as f:
            alternate_tap_mode = f.read().strip().lower() == "true"

def load_audio_input_mode():
    global audio_input_enabled
    if os.path.exists("audio_input_enabled.txt"):
        with open("audio_input_enabled.txt", "r") as f:
            audio_input_enabled = f.read().strip().lower() == "true"

def audio_callback(indata, frames, time, status):
    global is_talking
    if audio_input_enabled:
        volume = np.linalg.norm(indata)
        is_talking = volume > sensitivity
    else:
        is_talking = False

# websocket + logic

async def send_state():
    global last_message, alternate_toggle
    last_input_time = time.time()
    idle_delay = 0.3  # time (in seconds) to wait before switching to idle

    while True:
        left = keybinds.get("left", "s")
        right = keybinds.get("right", "d")

        new_keys = keys_down - handled_keys
        state = "idle"

        # update last_input_time if there is new input
        if new_keys or keys_down or is_talking:
            last_input_time = time.time()

        if random_hand_mode and not alternate_tap_mode:
            if new_keys:
                state = random.choice(["s", "d"])
                handled_keys.update(new_keys)
            elif keys_down:
                state = last_message.split("|")[0] if last_message else "idle"
        elif alternate_tap_mode and not random_hand_mode:
            if new_keys:
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

        # handle idle timeout
        if not keys_down and not is_talking and time.time() - last_input_time > idle_delay:
            state = "idle"

        message = f"{state}|{is_talking}"
        if message != last_message:
            last_message = message
            print("state:", message)
            for ws in clients.copy():
                try:
                    await ws.send(message)
                except websockets.exceptions.ConnectionClosed:
                    clients.discard(ws)

        handled_keys.intersection_update(keys_down)
        await asyncio.sleep(0.01)

async def handler(websocket):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.discard(websocket)

# keyboard hooks
def on_press(key):
    try:
        char = key.char.lower()
        if char not in pressed_keys:
            pressed_keys.add(char)
            keys_down.add(char)
    except AttributeError:
        pass

def on_release(key):
    try:
        char = key.char.lower()
        keys_down.discard(char)
        pressed_keys.discard(char)
        handled_keys.discard(char)
    except AttributeError:
        pass

# file watcher
class SettingsChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("keybinds.txt"):
            load_keybinds()
        elif event.src_path.endswith("sensitivity.txt"):
            load_sensitivity()
        elif event.src_path.endswith("random_hand_mode.txt"):
            load_random_mode()
        elif event.src_path.endswith("alternate_tap_mode.txt"):
            load_alternate_mode()
        elif event.src_path.endswith("audio_input_enabled.txt"):
            load_audio_input_mode()

def start_watchdog():
    event_handler = SettingsChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=False)
    observer.start()

def start_keyboard_listener():
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

def start_mic_listener():
    return sd.InputStream(callback=audio_callback)

# main entry point
def main():
    load_keybinds()
    load_sensitivity()
    load_random_mode()
    load_alternate_mode()
    load_audio_input_mode()
    start_keyboard_listener()
    start_watchdog()
    mic_stream = start_mic_listener()
    mic_stream.start()

    async def runner():
        async with websockets.serve(handler, "localhost", 8770, ping_interval=None):
            await send_state()

    asyncio.run(runner())

if __name__ == "__main__":
    main()
