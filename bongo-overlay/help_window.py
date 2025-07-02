import tkinter as tk

def open_help_window():
    help_win = tk.Toplevel()
    help_win.title("FAQ")
    help_win.geometry("325x400")

    faq_text = """Frequently asked questions that have never been asked because nobody has messaged me about this program:

Note: If any modes are checked but don't seem to be working, uncheck them and click apply, wait a few seconds, and then check them and hit apply again.

1. How do I add this to OBS?
Add a Window Capture into your OBS sources and select this application. Crop out the user settings. Then under filters add a chroma key and set the color to green. Change settings as you wish.

2. The mouth isn't moving, why is that?
Firstly, ensure you have enabled audio input and pressed apply. The red dot to the left of the microphone sensitivity slider will light up when audio is detected from your microphone. Make sure it is on and transmitting audio. Try different values of sensitivity. Higher values require more noise and lower values require less noise.

3. Your picture sucks, how can I improve image quality?
You're rude and going to hell. Somewhere inside of the download folder there should be a series of pngs named bothslap, idle, leftslap, rightslap, and talking. You can edit those photos as you wish or even replace them completely for a different type of overlay. Please note that the png names need to be kept exactly as they are.

4. The OBS overlay disappears when I minimize it — how do I fix that?
Minimized windows are hidden from screen capture. Other applications may be on top of it, but don't minimize it. There are probably programs out there that will let you minimize it while still being captured but I have no clue what they are so good luck.

5. The cat is doing literally nothing man
There's probably a million ways this could happen, but the most likely culprit is the websocket disconnecting. Try closing and reopening the program (classic advice). If that doesn't work make sure listening.py is running before the gui opens.

6. I'm having another issue that isn't listed here/I am very confused, what should I do?
Give up or message me on discord under the username 'kmkt'. I'll try to get back to you as quickly as possible but I might be playing borderlands or something.
"""

    frame = tk.Frame(help_win)
    frame.pack(fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set)
    text_widget.insert(tk.END, faq_text)
    text_widget.config(state=tk.DISABLED)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar.config(command=text_widget.yview)
    text_widget.yview_moveto(0.0)

    close_btn = tk.Button(help_win, text="Close", command=help_win.destroy)
    close_btn.pack(pady=5)
