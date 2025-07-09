# cat_overlay_gui.py
import tkinter as tk
from tkinter import messagebox, colorchooser
from PIL import Image, ImageTk, ImageGrab
import asyncio
import websockets
import threading
import os
import listening
from tkinter.filedialog import askopenfilename
import time
from help_window import open_help_window

IMAGE_FILES = ["idle.png", "leftslap.png", "rightslap.png", "bothslap.png", "talking.png"]

class BongoOverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bongo Cat Overlay")
        self.root.configure(bg="lime")
        self.root.geometry("600x1000")
        self.root.resizable(True, True)
        self.customize_visible = False

        # --- cat display & drawing surface ---
        self.cat_canvas = tk.Canvas(self.root, bg="lime", highlightthickness=0)
        self.cat_canvas.pack(side="top", fill="both", expand=True, pady=10)
        self.cat_canvas.bind("<Configure>", self._center_cat)
        self.cat_canvas.bind("<Motion>", self._on_canvas_motion)

        # load base images
        self.images = {}
        self.load_images()
        self.current_base = "idle"
        photo = self.images["idle"]
        self.cat_image_id = self.cat_canvas.create_image(
            0, 0, anchor="center", image=photo)
        self.cat_canvas.image = photo


        self.cat_canvas.tag_bind(self.cat_image_id, "<ButtonPress-1>", self._on_start_move)
        self.cat_canvas.tag_bind(self.cat_image_id, "<B1-Motion>",   self._on_move)
        
        # initial cat size state

        # start the cat at 75% of its full size
        orig_w, orig_h = 500, 500
        self.cat_scale = .75
        self.cat_width  = int(orig_w * self.cat_scale)
        self.cat_height = int(orig_h * self.cat_scale)
        self.show_cat("idle", talking=False)

        # bind shift-drag to resize the cat
        self.cat_canvas.tag_bind(self.cat_image_id, "<Shift-ButtonPress-1>",
                                 self._on_cat_resize_start)
        self.cat_canvas.tag_bind(self.cat_image_id, "<Shift-B1-Motion>",
                                 self._on_cat_resize)
        self._cat_resize_data = {"start_x": 0, "start_y": 0,
                                 "orig_w": self.cat_width, "orig_h": self.cat_height}

        # --- drawing state ---
        self.selected_color    = "#000000"
        self.coloring_mode_var = tk.BooleanVar(value=False)
        self.drawings          = []
        self.last_draw_pos     = None
        self.eraser_mode       = False

        # --- imported-image & delete-button state ---
        self.imported_images = []
        self._drag_data      = {"item": None, "x": 0, "y": 0}
        self._resize_data    = {
            "item":     None,
            "pil_orig": None,
            "orig_w":   0,
            "orig_h":   0,
            "start_x":  0,
            "start_y":  0
        }
        self.delete_widgets  = {}

        # --- settings panel ---
        self.settings_frame = tk.Frame(
            self.root, bg="#ffdde8", pady=5,
            highlightbackground="black", highlightthickness=5
        )
        self.settings_frame.pack(side="bottom", fill=tk.X, padx=10)

        # key variables
        self.sensitivity_var     = tk.DoubleVar()
        self.applied_sensitivity = tk.DoubleVar()
        self.random_hand_var     = tk.BooleanVar()
        self.alternate_tap_var   = tk.BooleanVar()
        self.audio_input_var     = tk.BooleanVar()
        self.full_keyboard_var   = tk.BooleanVar()
        self.both_paws_var       = tk.BooleanVar()
        self.custom_keys_var     = tk.BooleanVar()
        self.background_color_var= tk.StringVar(value="lime")
        # ——— instruction for resizing imported images ———
        tk.Label(
            self.settings_frame,
            text="Click and drag an image to move it around\n To resize an image: hold shift, click on the image, and drag left or right",
            bg="#ffdde8",
            justify="center"
        ).pack(pady=(5,2))

        # key variables
        self.left_key_var        = tk.StringVar()
        self.right_key_var       = tk.StringVar()
        # keybind inputs
        key_frame = tk.Frame(self.settings_frame, bg="#ffdde8")
        key_frame.pack(pady=5)


        tk.Label(key_frame, text="Left Paw:",  bg="#ffdde8")\
          .grid(row=0, column=0, padx=5)
        tk.Entry(key_frame, textvariable=self.left_key_var, width=5)\
          .grid(row=0, column=1, padx=5)
        tk.Label(key_frame, text="Right Paw:", bg="#ffdde8")\
          .grid(row=0, column=2, padx=5)
        tk.Entry(key_frame, textvariable=self.right_key_var, width=5)\
          .grid(row=0, column=3, padx=5)

        # microphone sensitivity slider
        tk.Frame(self.settings_frame, height=15, bg="#ffdde8").pack()
        tk.Label(self.settings_frame,
                 text="Microphone Sensitivity Slider:", bg="#ffdde8")\
          .pack()
        slider_frame = tk.Frame(self.settings_frame, bg="#ffdde8")
        slider_frame.pack(pady=5)
        self.dot_canvas = tk.Canvas(slider_frame, width=20, height=20,
                                    bg="#ffdde8", highlightthickness=0)
        self.dot_canvas.pack(side="left", padx=(10,0))
        self.dot = self.dot_canvas.create_oval(2,2,18,18, fill="red", outline="red")
        tk.Scale(slider_frame, from_=0.25, to=10.0, resolution=0.25,
                 orient=tk.HORIZONTAL,
                 variable=self.sensitivity_var, length=300)\
          .pack(side="left", padx=10)
        self.slider_current_label = tk.Label(self.settings_frame,
                                             text="", bg="#ffdde8")
        self.slider_current_label.pack()
        self.volume_bar = tk.Canvas(self.settings_frame,
                                    width=300, height=15,
                                    bg="#dddddd", highlightthickness=1,
                                    highlightbackground="#888")
        self.volume_bar.pack()
        self.volume_fill = self.volume_bar.create_rectangle(
            0,0,0,15, fill="#66cc66")

        # --- mode checkboxes (must bind to self.xxx_check) ---
        tk.Frame(self.settings_frame, height=15, bg="#ffdde8").pack()
        mode_frame = tk.Frame(self.settings_frame, bg="#ffdde8")
        mode_frame.pack()
        left_col  = tk.Frame(mode_frame, bg="#ffdde8")
        left_col.pack(side="left", padx=10)
        right_col = tk.Frame(mode_frame, bg="#ffdde8")
        right_col.pack(side="left", padx=10)

        self.random_check = tk.Checkbutton(left_col, text="Random Hand Mode",
                                           variable=self.random_hand_var,
                                           bg="#ffdde8",
                                           command=self.toggle_conflicts)
        self.random_check.pack(anchor="w")

        self.alternate_check = tk.Checkbutton(left_col, text="Alternate Tap Mode",
                                              variable=self.alternate_tap_var,
                                              bg="#ffdde8",
                                              command=self.toggle_conflicts)
        self.alternate_check.pack(anchor="w")

        self.both_paws_check = tk.Checkbutton(left_col, text="Both Paws Mode",
                                              variable=self.both_paws_var,
                                              bg="#ffdde8",
                                              command=self.toggle_conflicts)
        self.both_paws_check.pack(anchor="w")

        self.full_keyboard_check = tk.Checkbutton(
            right_col, text="Enable Full Keyboard Input",
            variable=self.full_keyboard_var,
            bg="#ffdde8", command=self.toggle_conflicts
        )
        self.full_keyboard_check.pack(anchor="w")

        # custom-keys + audio
        cframe = tk.Frame(right_col, bg="#ffdde8")
        cframe.pack(anchor="w")
        self.custom_keys_check = tk.Checkbutton(
            cframe, text="Enable Custom Keys Input",
            variable=self.custom_keys_var,
            bg="#ffdde8", command=self.toggle_conflicts
        )
        self.custom_keys_check.pack(side="left")
        tk.Button(cframe, text="☰", font=("Arial",8), width=2, height=1,
                  command=self.open_custom_keys_window)\
          .pack(side="left", padx=(5,0))
        tk.Checkbutton(self.settings_frame, text="Enable Audio Input",
                       variable=self.audio_input_var, bg="#ffdde8")\
          .pack()

        # apply & help
        tk.Frame(self.settings_frame, height=15, bg="#ffdde8").pack()
        br = tk.Frame(self.settings_frame, bg="#ffdde8"); br.pack(pady=5)
        tk.Button(br, text="Apply", command=self.apply_settings)\
          .pack(side="left", padx=(0,10))
        tk.Button(br, text="Help", command=open_help_window)\
          .pack(side="left", padx=(0,10))
        tk.Button(br, text="Reset", command=self.reset_all)\
          .pack(side="left")
        tk.Label(self.settings_frame,
                 text="Make sure to press 'Apply' for your settings to be saved.",
                 bg="#ffdde8")\
          .pack(pady=(0,5))

        # customization toggler + section
        self.customize_toggle = tk.Button(
            self.settings_frame, text="▶ Customization",
            bg="#ffdde8", anchor="w",
            command=self.toggle_customization_section
        )
        self.customize_toggle.pack(fill="x", padx=10, pady=(5,0))

        self.customize_section = tk.Frame(self.settings_frame, bg="#ffdde8")

        # --- coloring controls inside customize_section ---
        color_frame = tk.Frame(self.customize_section, bg="#ffdde8")
        color_frame.pack(fill="x", padx=20, pady=2)
        tk.Button(color_frame, text="Import Image",
                  command=self.import_image).pack(side="left", padx=(10,0))
        tk.Checkbutton(color_frame, text="Enable Coloring Mode",
                       variable=self.coloring_mode_var,
                       bg="#ffdde8",
                       command=self.toggle_coloring_mode).pack(side="left")
        self.clear_btn = tk.Button(color_frame, text="Clear Drawing",
                                   command=self.clear_drawings)
        self.clear_btn.pack(side="left", padx=(10,0))
        self.color_display = tk.Button(color_frame, width=2, height=1,
                                       bg=self.selected_color,
                                       command=self.choose_color,
                                       state="disabled")
        self.color_display.pack(side="left", padx=(5,0))

        # eraser button
        self.eraser_border = tk.Frame(
            color_frame, bg="#ffdde8", highlightthickness=2,
            highlightbackground="red")
        self.eraser_border.pack(side="left", padx=(10,0))
        eraser_img = Image.open("eraser.jpg").resize((24,24))
        self.eraser_icon = ImageTk.PhotoImage(eraser_img)
        self.eraser_btn = tk.Button(self.eraser_border,
                                    image=self.eraser_icon,
                                    command=self.toggle_eraser,
                                    state="disabled",
                                    bd=0, highlightthickness=0)
        self.eraser_btn.pack(side="left")

        # background color radios
        tk.Label(self.customize_section, text="Select Background Color:",
                 bg="#ffdde8").pack(anchor="w", padx=20)
        for label, color in [("lime","lime"),("blue","#00f"),("magenta","#f0f")]:
            tk.Radiobutton(self.customize_section, text=label,
                           variable=self.background_color_var, value=color,
                           bg="#ffdde8",
                           command=self.change_background_color)\
              .pack(anchor="w", padx=40)

        # start customization open
        self.customize_section.pack(fill="x", padx=10, pady=(0,5))
        self.customize_toggle.config(text="▼ Customization")
        self.customize_visible = True


        # wire up rest
        self.load_settings()
        self.ws_thread = threading.Thread(
            target=self.start_websocket_client, daemon=True)
        self.ws_thread.start()
        self.toggle_conflicts()

        # finally, center the cat image in whatever size the canvas actually is
        self.root.update_idletasks()






    def open_custom_keys_window(self):
        top = tk.Toplevel(self.root)
        top.title("Custom Keys Input")
        top.geometry("350x200")
        top.configure(bg="#ffdde8")

        example = tk.Message(top, text="Example: a,s,d,f,g or left,right,middle (for mouse clicks)\nNote: 'unknown' works for anything else, including mouse4,mouse5,etc.", 
                             bg="#ffdde8", width=300, justify="center")
        example.pack(pady=10)


        self.custom_keys_entry = tk.Text(top, height=5, width=30)
        self.custom_keys_entry.pack(pady=5)
        
        if os.path.exists("custom_keys.txt"):
            with open("custom_keys.txt", "r") as f:
                self.custom_keys_entry.insert("1.0", f.read())


        save_btn = tk.Button(top, text="Save", command=self.save_custom_keys)
        save_btn.pack(pady=5)
        
    def save_custom_keys(self):
        try:
            keys = self.custom_keys_entry.get("1.0", "end").strip()
            with open("custom_keys.txt", "w") as f:
                f.write(keys)
                messagebox.showinfo("Saved", "Custom keys saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save custom keys: {e}")

    def toggle_conflicts(self):
        both = self.both_paws_var.get()
        random = self.random_hand_var.get()
        alternate = self.alternate_tap_var.get()

        if both or random or alternate:
            self.full_keyboard_check.config(state="normal")
            self.custom_keys_check.config(state="normal")
        else:
            self.full_keyboard_check.config(state="disabled")
            self.full_keyboard_var.set(False)
            self.custom_keys_check.config(state="disabled")
            self.custom_keys_var.set(False)

        if both:
            self.random_check.config(state="disabled")
            self.alternate_check.config(state="disabled")
        else:
            self.random_check.config(state="normal")
            self.alternate_check.config(state="normal")
            if random:
                self.alternate_check.config(state="disabled")
            elif alternate:
                self.random_check.config(state="disabled")

        if random or alternate:
            self.both_paws_check.config(state="disabled")
        else:
            self.both_paws_check.config(state="normal")

        # force one or the other: full keyboard vs custom keys
        if self.custom_keys_var.get():
            self.full_keyboard_check.config(state="disabled")
            self.full_keyboard_var.set(False)
        elif self.full_keyboard_var.get():
            self.custom_keys_check.config(state="disabled")
            self.custom_keys_var.set(False)

            


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
            with open("full_keyboard_mode.txt", "w") as f:
                f.write(str(self.full_keyboard_var.get()).lower())
            with open("both_paws_mode.txt", "w") as f:
                f.write(str(self.both_paws_var.get()).lower())
            with open("custom_keys_mode.txt", "w") as f:
                f.write(str(self.custom_keys_var.get()).lower())

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

        for name, var in [
            ("random_hand_mode.txt", self.random_hand_var),
            ("alternate_tap_mode.txt", self.alternate_tap_var),
            ("audio_input_enabled.txt", self.audio_input_var),
            ("full_keyboard_mode.txt", self.full_keyboard_var),
            ("both_paws_mode.txt", self.both_paws_var),
            ("custom_keys_mode.txt", self.custom_keys_var)
        ]:
            if os.path.exists(name):
                with open(name, "r") as f:
                    var.set(f.read().strip().lower() == "true")

    def update_volume_bar(self, level):
        level = max(0.0, min(level, 1.0))
        width = int(300 * level)
        self.volume_bar.coords(self.volume_fill, 0, 0, width, 15)

    def update_mic_dot(self, active):
        new_color = "#ff0000" if active else "#ffaaaa"
        current = self.dot_canvas.itemcget(self.dot, "fill")
        if current != new_color:
            self.dot_canvas.itemconfigure(self.dot, fill=new_color, outline=new_color)
            



            



    def toggle_customization_section(self):
        if self.customize_visible:
            self.customize_section.pack_forget()
            self.customize_toggle.config(text="▶ customization")
        else:
            self.customize_section.pack(fill="x", padx=10, pady=(0,5))
            self.customize_toggle.config(text="▼ customization")

        self.customize_visible = not self.customize_visible









    def show_cat(self, state, talking):
        if self.current_base == state and talking == getattr(self, "last_talking", None):
            return
        self.current_base = state
        self.last_talking = talking

        # always resize the PIL to your saved cat_width/height
        base = self.images[state + "_rgba"]
        resized = base.resize((self.cat_width, self.cat_height),
                              Image.Resampling.LANCZOS)
        if talking:
            mouth = self.images["talking_rgba"].resize(
                        (self.cat_width, self.cat_height),
                        Image.Resampling.LANCZOS)
            resized = Image.alpha_composite(resized, mouth)

        photo = ImageTk.PhotoImage(resized)
        self.cat_canvas.itemconfig(self.cat_image_id, image=photo)
        self.cat_canvas.image = photo


    def load_images(self):
        for name in IMAGE_FILES:
            key = name.replace(".png", "")
            path = os.path.join(os.getcwd(), name)
            pil = Image.open(path).convert("RGBA")
            self.images[key + "_rgba"] = pil
            self.images[key] = ImageTk.PhotoImage(pil)   # initial PhotoImage at native size
    
    def change_background_color(self):
        selected = self.background_color_var.get()
        self.root.configure(bg=selected)
        self.cat_canvas.configure(bg=selected)

        
    def clear_drawings(self):
        # turn eraser off if active
        if self.eraser_mode:
            self.toggle_eraser()
        # then clear strokes
        for item in self.drawings:
            self.cat_canvas.delete(item)
        self.drawings.clear()

    def choose_color(self):
        # turn eraser off if active
        if self.eraser_mode:
            self.toggle_eraser()
        # now open picker
        _, hexcode = colorchooser.askcolor(
            title="pick a drawing color",
            initialcolor=self.selected_color
        )
        if hexcode:
            self.selected_color = hexcode
            self.color_display.config(bg=hexcode)


    def toggle_coloring_mode(self):
        # turn off eraser if needed
        if self.eraser_mode:
            self.toggle_eraser()

        if self.coloring_mode_var.get():
            self.clear_btn.config(state="normal")    # stays enabled
            self.eraser_btn.config(state="normal")
            self.color_display.config(state="normal")    # enable picker
            self.cat_canvas.bind("<ButtonPress-1>", self.start_draw)
            self.cat_canvas.bind("<B1-Motion>",    self.draw_motion)
        else:
            # self.clear_btn.config(state="disabled")
            self.eraser_btn.config(state="disabled")
            self.color_display.config(state="disabled")   # disable picker
            self.cat_canvas.unbind("<ButtonPress-1>")
            self.cat_canvas.unbind("<B1-Motion>")


            
            
                
    def toggle_eraser(self):
        self.eraser_mode = not self.eraser_mode
        # switch the highlight border color
        color = "green" if self.eraser_mode else "red"
        self.eraser_border.config(highlightbackground=color)
        if self.eraser_mode:
            self.cat_canvas.unbind("<ButtonPress-1>")
            self.cat_canvas.unbind("<B1-Motion>")
            self.cat_canvas.bind("<ButtonPress-1>", self.erase_motion)
            self.cat_canvas.bind("<B1-Motion>",    self.erase_motion)
        else:
            self.cat_canvas.unbind("<ButtonPress-1>")
            self.cat_canvas.unbind("<B1-Motion>")
            self.cat_canvas.bind("<ButtonPress-1>", self.start_draw)
            self.cat_canvas.bind("<B1-Motion>",    self.draw_motion)


                
            
            
    def erase_motion(self, event):
        # remove any stroke items near the cursor
        x, y = event.x, event.y
        hits = self.cat_canvas.find_overlapping(x-5, y-5, x+5, y+5)
        for item in hits:
            if item in self.drawings:
                self.cat_canvas.delete(item)
                self.drawings.remove(item)
            
            


    def _on_start_move(self, event):
        # don’t start a drag if we’re in coloring mode
        if self.coloring_mode_var.get():  
            return
        item = self.cat_canvas.find_withtag("current")[0]
        self._drag_data["item"] = item
        self._drag_data["x"], self._drag_data["y"] = event.x, event.y

    def _on_move(self, event):
        # block any dragging while coloring
        if self.coloring_mode_var.get():
            return
        item = self._drag_data["item"]
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.cat_canvas.move(item, dx, dy)
        self._drag_data["x"], self._drag_data["y"] = event.x, event.y

        # reposition delete “✕” if it’s showing
        if item in self.delete_widgets:
            _, win = self.delete_widgets[item]
            x1,y1,x2,y2 = self.cat_canvas.bbox(item)
            self.cat_canvas.coords(win, x2, y1)
        
    def _on_start_resize(self, event):
        # record the exact state at the moment Shift-click begins
        item = self.cat_canvas.find_withtag("current")[0]
        for img in self.imported_images:
            if img["item"] == item:
                self._resize_data = {
                    "item":     item,
                    "pil_orig": img["pil_orig"],      # pristine original
                    "orig_w":   img["width"],         # current width
                    "orig_h":   img["height"],        # current height
                    "start_x":  event.x,              # where you clicked
                }
                break

    def _on_resize(self, event):
        rd = self._resize_data
        if rd["item"] is None:
            return

        # how far have we dragged horizontally?
        dx = event.x - rd["start_x"]

        # new width is original width + that delta
        new_w = rd["orig_w"] + dx
        # maintain aspect
        new_h = int(rd["orig_h"] * new_w / rd["orig_w"])

        # enforce your limits
        new_w = max(20, min(1500, new_w))
        new_h = max(20, min(1500, new_h))

        # resize with LANCZOS
        pil2  = rd["pil_orig"].resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil2)
        self.cat_canvas.itemconfig(rd["item"], image=photo)

        # update our record so future drags/deletes know the new size
        for img in self.imported_images:
            if img["item"] == rd["item"]:
                img["width"]  = new_w
                img["height"] = new_h
                img["photo"]  = photo
                break

        # keep the little “✕” in the right place if it’s visible
        if rd["item"] in self.delete_widgets:
            _, win = self.delete_widgets[rd["item"]]
            x1, y1, x2, y2 = self.cat_canvas.bbox(rd["item"])
            self.cat_canvas.coords(win, x2, y1)













    def start_draw(self, event):
        # remember where the user started
        self.last_draw_pos = (event.x, event.y)

    def draw_motion(self, event):
        # draw a line segment and record its ID
        x0, y0 = self.last_draw_pos
        line = self.cat_canvas.create_line(x0, y0, event.x, event.y,
                                           fill=self.selected_color,
                                           width=4, capstyle="round")
        self.drawings.append(line)
        self.last_draw_pos = (event.x, event.y)

    def import_image(self):
        path = askopenfilename(filetypes=[("PNG files","*.png")])
        if not path:
            return

        # load & auto‐resize
        pil = Image.open(path).convert("RGBA")
        max_dim = 500
        scale = min(max_dim / pil.width, max_dim / pil.height, 1.0)
        new_size = (int(pil.width * scale), int(pil.height * scale))
        # use LANCZOS resampling instead of the removed ANTIALIAS
        pil = pil.resize(new_size, Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(pil)
        # create a brand-new canvas item for _this_ imported image,
        # and stash its ID in a local variable called `item`
        item = self.cat_canvas.create_image(
            0, 0,
            anchor="center",
            image=photo
        )

        # now append it to your list of imported-images so you can
        # show/move/delete it later
        self.imported_images.append({
            "item":     item,
            "pil_orig": pil,
            "width":    pil.width,
            "height":   pil.height,
            "photo":    photo
        })


        # bind move, resize, hover/delete
        self.cat_canvas.tag_bind(item, "<ButtonPress-1>",   self._on_start_move)
        self.cat_canvas.tag_bind(item, "<B1-Motion>",       self._on_move)
        self.cat_canvas.tag_bind(item, "<Shift-ButtonPress-1>", self._on_start_resize)
        self.cat_canvas.tag_bind(item, "<Shift-B1-Motion>",     self._on_resize)
        # show delete‐button when pointer enters the image
        self.cat_canvas.tag_bind(item, "<Enter>",
            lambda e, i=item: self._show_delete(i))





    def _show_delete(self, item):
        if item in self.delete_widgets:
            return

        x1, y1, x2, y2 = self.cat_canvas.bbox(item)
        # create a real Button with a command
        btn = tk.Button(self.cat_canvas,
                        text="✕", bg="red", fg="white", bd=0,
                        font=("Arial",8,"bold"),
                        command=lambda i=item: self._remove_image(i))
        win = self.cat_canvas.create_window(x2, y1,
                                            anchor="ne", window=btn)
        self.delete_widgets[item] = (btn, win)

        # now bind the button itself to hide once the cursor actually leaves the button
        btn.bind("<Leave>", lambda e, i=item: self._hide_delete(i))

    def _hide_delete(self, item):
        if item not in self.delete_widgets: return
        btn, win = self.delete_widgets.pop(item)
        btn.destroy()
        self.cat_canvas.delete(win)

    def _remove_image(self, item):
        # first: unhook every tag-bind on that canvas‐item
        print(f"→ _remove_image start for item {item}")
        for seq in ("<Enter>", "<Leave>",
                    "<ButtonPress-1>", "<B1-Motion>",
                    "<Shift-ButtonPress-1>", "<Shift-B1-Motion>"):
            self.cat_canvas.tag_unbind(item, seq)

        # now delete it and its little delete-button
        self.cat_canvas.delete(item)
        if item in self.delete_widgets:
            btn, win = self.delete_widgets.pop(item)
            btn.destroy()
            self.cat_canvas.delete(win)

        # and drop it from your list so the PhotoImage can be GC’d
        self.imported_images = [
            img for img in self.imported_images
            if img["item"] != item
        ]
        print(f"← _remove_image end for item {item}")


    def _on_canvas_motion(self, event):
        hits = set(self.cat_canvas.find_overlapping(
            event.x, event.y, event.x, event.y))

        # show new ones
        for img in self.imported_images:
            item = img["item"]
            if item in hits and item not in self.delete_widgets:
                self._show_delete(item)

        # hide old ones
        for item in list(self.delete_widgets):
            if item not in hits:
                self._hide_delete(item)


    def _on_cat_resize_start(self, event):
        # remember where we clicked and the original dimensions
        self._cat_resize_data["start_x"] = event.x
        self._cat_resize_data["start_y"] = event.y
        self._cat_resize_data["orig_w"] = self.cat_width
        self._cat_resize_data["orig_h"] = self.cat_height

    def _on_cat_resize(self, event):
        rd = self._cat_resize_data
        dx = event.x - rd["start_x"]
        scale = 1 + dx / 50.0

        # compute new size off those stored original dims
        new_w = int(rd["orig_w"] * scale)
        new_h = int(rd["orig_h"] * scale)
        # snap to 7px grid (round to nearest multiple)
        new_w = int(round(new_w / 7.0)) * 7
        new_h = int(round(new_h / 7.0)) * 7

        # clamp to [75,1500]
        new_w = max(75, min(1500, new_w))
        new_h = max(75, min(1500, new_h))

        base = self.images[self.current_base + "_rgba"]
        resized = base.resize((new_w, new_h), Image.Resampling.LANCZOS)

        if getattr(self, "last_talking", False):
            mouth = self.images["talking_rgba"].resize((new_w, new_h),
                                                       Image.Resampling.LANCZOS)
            resized = Image.alpha_composite(resized, mouth)

        photo = ImageTk.PhotoImage(resized)
        self.cat_canvas.itemconfig(self.cat_image_id, image=photo)
        self.cat_canvas.image = photo

        self.cat_width, self.cat_height = new_w, new_h


    def reset_all(self):
        # 1) Clear any freehand drawings
        self.clear_drawings()

        # 2) Remove all imported images
        for img in list(self.imported_images):
            self._remove_image(img["item"])

        # 3) Reset background color to default ("lime")
        self.background_color_var.set("lime")
        self.change_background_color()

        # 4) Reset all hand/key/audio modes
        self.random_hand_var.set(False)
        self.alternate_tap_var.set(False)
        self.both_paws_var.set(False)
        self.full_keyboard_var.set(False)
        self.custom_keys_var.set(False)
        self.audio_input_var.set(False)      # ← turn audio input off
        self.toggle_conflicts()

        # 5) Reset mic sensitivity slider to 3.2
        self.sensitivity_var.set(3.2)
        self.applied_sensitivity.set(3.2)
        self.slider_current_label.config(text="Applied Sensitivity: 3.2")

        # 6) Reset left/right paw keybinds
        self.left_key_var.set("s")
        self.right_key_var.set("d")

        # 7) Clear custom‐keys file
        with open("custom_keys.txt", "w"):
            pass

        # 8) Turn off coloring mode
        self.coloring_mode_var.set(False)
        self.eraser_btn.config(state="disabled")
        self.color_display.config(state="disabled")
        self.cat_canvas.unbind("<ButtonPress-1>")
        self.cat_canvas.unbind("<B1-Motion>")

        # 9) Reset the cat’s size back to 75% of 500×500
        orig_w, orig_h = 500, 500
        self.cat_width  = int(orig_w * 0.75)
        self.cat_height = int(orig_h * 0.75)

        # 10) Clear show_cat cache so it redraws
        self.current_base = None
        self.last_talking = None

        # 11) Actually write & apply those new settings
        self.apply_settings()

        # 12) Redraw & re-center the cat immediately
        self.show_cat("idle", talking=False)
        self._cat_resize_data["orig_w"] = self.cat_width
        self._cat_resize_data["orig_h"] = self.cat_height
        self._center_cat()










    def _center_cat(self, event=None):
        # get the current canvas size
        cw = self.cat_canvas.winfo_width()
        ch = self.cat_canvas.winfo_height()
        # move the cat image to center
        self.cat_canvas.coords(self.cat_image_id, cw//2, ch//2)


    async def listen_ws(self):
        async with websockets.connect("ws://localhost:8770") as websocket:
            async for message in websocket:
                try:
                    parts = message.split("|")
                    state_part = parts[0]
                    talking_part = parts[1]
                    volume = float(parts[2]) if len(parts) > 2 else (1.0 if talking_part == "true" else 0.0)
                    talking = talking_part == "True"
                    base_state = {"s": "leftslap", "d": "rightslap", "sd": "bothslap", "idle": "idle"}.get(state_part, "idle")
                    self.root.after(0, lambda: (
                        self.show_cat(base_state, talking),
                        self.update_mic_dot(talking),
                        # self.update_volume_bar(volume)
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
    server_thread = threading.Thread(target=listening.main, daemon=True)
    server_thread.start()
    time.sleep(1)

    root = tk.Tk()
    app = BongoOverlayApp(root)
    root.mainloop()
