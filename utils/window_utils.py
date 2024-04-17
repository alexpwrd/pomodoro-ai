# window_utils.py

import tkinter as tk

def set_window_icon(master, icon_path):
    icon = tk.PhotoImage(file=icon_path)
    master.iconphoto(False, icon)
