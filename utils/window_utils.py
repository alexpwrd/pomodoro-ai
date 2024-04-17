# window_utils.py
import tkinter as tk
import os
import logging

logger = logging.getLogger(__name__)

def set_window_icon(master, icon_filename):
    # Get the directory of the current script
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # Construct the path to the icon in the resources folder
    icon_path = os.path.join(dir_path, '..', 'resources', icon_filename)
    try:
        icon = tk.PhotoImage(file=icon_path)
        master.iconphoto(False, icon)
    except Exception as e:
        logger.error(f"Failed to load window icon from {icon_path}: {e}")