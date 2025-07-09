import tkinter as tk

def open_help_window():
    help_win = tk.Toplevel()
    help_win.title("FAQ")
    help_win.geometry("325x400")

    faq_text = """Frequently asked questions that have never been asked because nobody has messaged me about this program:

Note: If any modes are checked but don't seem to be working, uncheck them and click apply, wait a second, and then check them and hit apply again.
Note2: If you have any problem first restart the program and see if that fixes it for you

1. How do I add this to OBS?
Add a Window Capture into your OBS sources and select this application. Crop out the user settings. Then under filters add a chroma key and set the color to green. Change settings as you wish.

2. The mouth isn't moving, why is that?
Firstly, ensure you have enabled audio input and pressed apply. The red dot to the left of the microphone sensitivity slider will light up when audio is detected from your microphone. Make sure it is on and transmitting audio. Try different values of sensitivity. Higher values require more noise and lower values require less noise.

3. The OBS overlay disappears when I minimize it — how do I fix that?
Minimized windows are hidden from screen capture. Other applications may be on top of it, but don't minimize it. There are probably programs out there that will let you minimize it while still being captured but I have no clue what they are so good luck.

4. The cat is doing literally nothing man. This isn't even a question it's just a statement.
There's probably a million ways this could happen, but the most likely culprit is the websocket disconnecting. Try closing and reopening the program (classic advice). If that doesn't work make sure listening.py is running before the gui opens and port 8770 is unused on your computer... and then restart the program again x)

5. How do I resize an image?
Hold shift and click on the image, dragging left or right. Dragging to the right should increase its size and to the left should decrease it.

6. All my changes have mucked things up... what can I do?
Hit the reset button! That should reset all the settings you fucked up, you stupid idiot. At least I hope it does.

6. I'm having another issue that isn't listed here/I am very confused, what should I do?
Give up or message me on discord under the username 'kmkt'. I'll try to get back to you as quickly as possible but I might be, you know, doing anything but coding.
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
