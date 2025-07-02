import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS  # used by PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_overlay():
    try:
        overlay_path = resource_path("start_overlay.bat")
        subprocess.Popen(["cmd", "/c", overlay_path], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start overlay:\n{e}")

root = tk.Tk()
root.title("Bongo Cat Overlay")
root.geometry("300x150")
root.resizable(False, False)

start_btn = tk.Button(root, text="Start Overlay", font=("Segoe UI", 12), command=start_overlay)
start_btn.pack(expand=True, pady=40)

root.mainloop()
