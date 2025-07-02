# cat_overlay_gui.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import sys
import asyncio
import websockets
import threading
import os
import listening
import time
from help_window import open_help_window

IMAGE_FILES = ["idle.png", "leftslap.png", "rightslap.png", "bothslap.png", "talking.png"]

class BongoOverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bongo Cat Overlay")
        self.root.configure(bg="lime")
        self.root.geometry("600x850")
        self.root.resizable(False, False)

        # --- cat display ---
        self.cat_label = tk.Label(self.root, bg="lime")
        self.cat_label.pack()

        self.images = {}
        self.load_images()
        self.current_base = "idle"
        self.show_cat("idle", talking=False)

        # --- pink settings frame ---
        self.settings_frame = tk.Frame(self.root, bg="#ffdde8", pady=5, highlightbackground="black", highlightthickness=5)
        self.settings_frame.pack(fill=tk.X, padx=10)


        # --- variable declarations ---
        self.left_key_var = tk.StringVar()
        self.right_key_var = tk.StringVar()
        self.sensitivity_var = tk.DoubleVar()
        self.applied_sensitivity = tk.DoubleVar()
        self.random_hand_var = tk.BooleanVar()
        self.alternate_tap_var = tk.BooleanVar()
        self.audio_input_var = tk.BooleanVar()

        # --- keybind section ---
        key_frame = tk.Frame(self.settings_frame, bg="#ffdde8")
        key_frame.pack(pady=5)

        tk.Label(key_frame, text="Left Paw:", bg="#ffdde8").grid(row=0, column=0, padx=5)
        self.left_entry = tk.Entry(key_frame, textvariable=self.left_key_var, width=5)
        self.left_entry.grid(row=0, column=1, padx=5)

        tk.Label(key_frame, text="Right Paw:", bg="#ffdde8").grid(row=0, column=2, padx=5)
        self.right_entry = tk.Entry(key_frame, textvariable=self.right_key_var, width=5)
        self.right_entry.grid(row=0, column=3, padx=5)

        # --- spacer between keybinds and sensitivity ---
        tk.Frame(self.settings_frame, height=15, bg="#ffdde8").pack()

        # --- mic sensitivity section ---
        tk.Label(self.settings_frame, text="Microphone Sensitivity Slider:", bg="#ffdde8").pack()

        slider_frame = tk.Frame(self.settings_frame, bg="#ffdde8")
        slider_frame.pack(pady=5)

        self.canvas = tk.Canvas(slider_frame, width=20, height=20, bg="#ffdde8", highlightthickness=0)
        self.dot = self.canvas.create_oval(2, 2, 18, 18, fill="red", outline="red")
        self.canvas.pack(side="left", padx=(10, 0))

        self.slider = tk.Scale(slider_frame, from_=0.25, to=10.0, resolution=0.25,
                               orient=tk.HORIZONTAL, variable=self.sensitivity_var,
                               length=300)
        self.slider.pack(side="left", padx=10)

        self.slider_current_label = tk.Label(self.settings_frame, text="", bg="#ffdde8")
        self.slider_current_label.pack()

        # --- spacer between sensitivity and checkboxes ---
        tk.Frame(self.settings_frame, height=15, bg="#ffdde8").pack()

        # --- mode checkboxes ---
        self.random_check = tk.Checkbutton(self.settings_frame, text="Random Hand Mode",
                                           variable=self.random_hand_var, bg="#ffdde8",
                                           command=self.toggle_conflicts)
        self.random_check.pack()

        self.alternate_check = tk.Checkbutton(self.settings_frame, text="Alternate Tap Mode",
                                              variable=self.alternate_tap_var, bg="#ffdde8",
                                              command=self.toggle_conflicts)
        self.alternate_check.pack()

        self.audio_check = tk.Checkbutton(self.settings_frame, text="Enable Audio Input",
                                          variable=self.audio_input_var, bg="#ffdde8")
        self.audio_check.pack()

        # --- spacer between checkboxes and apply button ---
        tk.Frame(self.settings_frame, height=15, bg="#ffdde8").pack()

        # --- apply + help buttons side by side ---
        button_row = tk.Frame(self.settings_frame, bg="#ffdde8")
        button_row.pack(pady=5)

        self.apply_btn = tk.Button(button_row, text="Apply", command=self.apply_settings)
        self.apply_btn.pack(side="left", padx=(0, 10))

        self.help_btn = tk.Button(button_row, text="Help", command=open_help_window)
        self.help_btn.pack(side="left")

        # --- reminder label below buttons ---
        self.reminder_label = tk.Label(self.settings_frame,
                                       text="Make sure to press 'Apply' for your settings to be saved.",
                                       bg="#ffdde8")
        self.reminder_label.pack(pady=(0, 5))


        # --- finish setup ---
        self.load_settings()
        self.ws_thread = threading.Thread(target=self.start_websocket_client, daemon=True)
        self.ws_thread.start()




    def load_images(self):
        for name in IMAGE_FILES:
            key = name.replace(".png", "")
            path = os.path.join(os.getcwd(), name)
            img = Image.open(path).resize((500, 500))
            self.images[key] = ImageTk.PhotoImage(img)
            self.images[key + "_rgba"] = img.convert("RGBA")

    def show_cat(self, state, talking):
        if self.current_base == state and talking == getattr(self, "last_talking", None):
            return

        self.current_base = state
        self.last_talking = talking

        if talking:
            base_rgba = self.images.get(state + "_rgba")
            mouth_rgba = self.images.get("talking_rgba")
            if base_rgba and mouth_rgba:
                combined = Image.alpha_composite(base_rgba.copy(), mouth_rgba.copy())
                photo = ImageTk.PhotoImage(combined)
                self.cat_label.config(image=photo)
                self.cat_label.image = photo
        else:
            base = self.images.get(state, self.images["idle"])
            self.cat_label.config(image=base)
            self.cat_label.image = base

    def update_mic_dot(self, active):
        new_color = "#ff0000" if active else "#ffaaaa"
        current = self.canvas.itemcget(self.dot, "fill")
        if current != new_color:
            self.canvas.itemconfigure(self.dot, fill=new_color, outline=new_color)

    def toggle_conflicts(self):
        if self.random_hand_var.get():
            self.alternate_check.config(state="disabled")
        else:
            self.alternate_check.config(state="normal")

        if self.alternate_tap_var.get():
            self.random_check.config(state="disabled")
        else:
            self.random_check.config(state="normal")

    # apply_settings method
    def apply_settings(self):
        left = self.left_key_var.get().strip().lower()
        right = self.right_key_var.get().strip().lower()
        sens = self.sensitivity_var.get()
        try:
            with open("keybinds.txt", "w") as f:
                f.write(f"left:{left}\n")
                f.write(f"right:{right}\n")
            with open("sensitivity.txt", "w") as f:
                f.write(str(sens))
            with open("random_hand_mode.txt", "w") as f:
                f.write(str(self.random_hand_var.get()).lower())
            with open("alternate_tap_mode.txt", "w") as f:
                f.write(str(self.alternate_tap_var.get()).lower())
            with open("audio_input_enabled.txt", "w") as f:
                f.write(str(self.audio_input_var.get()).lower())

            self.applied_sensitivity.set(sens)
            self.slider_current_label.config(text=f"Applied Sensitivity: {sens}")
            self.left_key_var.set(left[:1])
            self.right_key_var.set(right[:1])
            self.root.focus()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")


    def load_settings(self):
        if os.path.exists("keybinds.txt"):
            with open("keybinds.txt", "r") as f:
                for line in f:
                    if ":" in line:
                        action, key = line.strip().split(":")
                        if action == "left":
                            self.left_key_var.set(key)
                        elif action == "right":
                            self.right_key_var.set(key)

        if os.path.exists("sensitivity.txt"):
            with open("sensitivity.txt", "r") as f:
                try:
                    val = float(f.read().strip())
                    self.sensitivity_var.set(val)
                    self.applied_sensitivity.set(val)
                    self.slider_current_label.config(text=f"Applied Sensitivity: {val}")
                except ValueError:
                    pass

        if os.path.exists("random_hand_mode.txt"):
            with open("random_hand_mode.txt", "r") as f:
                self.random_hand_var.set(f.read().strip().lower() == "true")

        if os.path.exists("alternate_tap_mode.txt"):
            with open("alternate_tap_mode.txt", "r") as f:
                self.alternate_tap_var.set(f.read().strip().lower() == "true")

        if os.path.exists("audio_input_enabled.txt"):
            with open("audio_input_enabled.txt", "r") as f:
                self.audio_input_var.set(f.read().strip().lower() == "true")


    async def listen_ws(self):
        async with websockets.connect("ws://localhost:8770") as websocket:
            async for message in websocket:
                try:
                    state_part, talking_part = message.split("|")
                    base_state = {"s": "leftslap", "d": "rightslap", "sd": "bothslap", "idle": "idle"}.get(state_part, "idle")
                    talking = talking_part.lower() == "true"
                    self.root.after(0, lambda: (
                        self.show_cat(base_state, talking),
                        self.update_mic_dot(talking)
                    ))
                except Exception as e:
                    print("Failed to parse message:", message, e)

    def start_websocket_client(self):
        while True:
            try:
                asyncio.run(self.listen_ws())
            except Exception as e:
                print("ws client error, retrying:", e)
                time.sleep(1)

if __name__ == "__main__":
    import threading
    server_thread = threading.Thread(target=listening.main, daemon=True)
    server_thread.start()
    time.sleep(1)

    root = tk.Tk()
    app = BongoOverlayApp(root)
    root.mainloop()
