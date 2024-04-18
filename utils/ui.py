# ui.py is a module that contains the UIConfig class which is responsible for configuring the styles of the UI elements

import tkinter as tk
from tkinter import ttk, PhotoImage

class UIConfig:
    def __init__(self):
        self.colors = {
            "background": '#333333',  # Dark grey background
            "foreground": "#FFFFFF",  # White text
            "sidebar_bg": '#2D2D2D',  # Slightly darker grey for sidebar
            "text": '#FFFFFF',  # White text for better readability
            "progress_bar": '#4CAF50',  # Green progress bar
            "button": {
                'bg': '#595959',  #  buttons
                'fg': '#FFFFFF',  # White text on buttons
                'hover_bg': '#404040',  # Slightly darker  hover
                'hover_fg': '#FFFFFF',
                'disabled_bg': '#9E9E9E',  # Greyed out for disabled
                'disabled_fg': '#CFD8DC'
            },
            "entry": {
                "bg": '#FFFFFF',
                "fg": '#333333',
                "field_bg": '#BBBBBB'  # Light grey for input fields
            },
            "mute_button": {  # Specific style for mute button
                'bg': '#BDBDBD',
                'fg': '#FFFFFF',
                'hover_bg': '#9E9E9E',
                'hover_fg': '#FFFFFF',
                'disabled_bg': '#2D2D2D',
                'disabled_fg': '#A6A6A6'
            },
            "state_indicator": {
                "focus": '#4CAF50',  # Green
                "break": '#FFEB3B',  # Yellow
                "paused": '#FFC107',  # Amber
                "default": '#BDBDBD'  # Neutral grey
            },
            "todo_bg": '#333333',  # Background for todo tasks
            "completed_bg": '#333333'  # Background for completed tasks
        }
        self.configure_styles()


    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('default')
        self.global_font = ("Helvetica", 15)

        # Configure frame style
        style.configure("TFrame", background=self.colors["background"])

        # Configure entry style
        style.configure("TEntry", 
                        fieldbackground='#2D2D2D',  #  input fields
                        background=self.colors["entry"]["bg"],  # White background (general background, not as critical)
                        foreground='#FFFFFF',  # for contrast
                        font=("Helvetica", 15, "bold")) 

        # Configure combobox style
        style.configure("TCombobox", 
                        fieldbackground='#2D2D2D',  # input fields
                        background='#2D2D2D',  # general background
                        foreground='#FFFFFF',  # text
                        font=self.global_font)
        
        # Map combobox styles for different states and attempt to set arrow color
        style.map('TCombobox',
                fieldbackground=[('readonly', '#2D2D2D'), ('disabled', '#2D2D2D')],
                background=[('readonly', '#2D2D2D'), ('disabled', '#2D2D2D')],
                foreground=[('readonly', '#FFFFFF'), ('disabled', '#BBBBBB')],
                arrowcolor=[('readonly', '#FFFFFF'), ('disabled', '#BBBBBB')])  # Attempt to change arrow color

        # Additional configuration for the dropdown list items
        style.configure("TCombobox.Listbox",
                        background='#2D2D2D',  # Almost black for dropdown list background
                        foreground='#FFFFFF',  # dropdown list items
                        font=self.global_font)
        
        
        # Configure the progress bar style
        style.configure(
            "green.Horizontal.TProgressbar",
            background=self.colors["progress_bar"],
            thickness=20
        )

        # Configure button styles
        style.configure(
            'Modern.TButton',
            font=self.global_font,
            background=self.colors['button']['bg'],
            foreground=self.colors['button']['fg'],
            borderwidth=0,
            highlightthickness=0,
            padding=5,
            relief='flat'
        )
        style.map(
            'Modern.TButton',
            background=[('active', self.colors['button']['hover_bg']), ('disabled', self.colors['button']['disabled_bg'])],
            foreground=[('active', self.colors['button']['hover_fg']), ('disabled', self.colors['button']['disabled_fg'])]
        )

        # Configure mute button specific style
        style.configure(
            "MuteButton.TButton",
            font=self.global_font,
            background=self.colors['mute_button']['bg'],
            foreground=self.colors['mute_button']['fg'],
            borderwidth=0,
            highlightthickness=0,
            padding=5,
            relief='flat'
        )
        style.map(
            "MuteButton.TButton",
            background=[('active', self.colors['mute_button']['hover_bg']), ('disabled', self.colors['mute_button']['disabled_bg'])],
            foreground=[('active', self.colors['mute_button']['hover_fg']), ('disabled', self.colors['mute_button']['disabled_fg'])]
        )

        # Configure label style
        style.configure(
            "TLabel",
            background=self.colors["background"],
            foreground=self.colors["text"],
            font=self.global_font
        )


    def update_mute_button_style(self, muted):
        """ Update the style for the mute button based on the muted state. """
        style = ttk.Style()
        if muted:
            style.configure("MuteButton.TButton",
                            background='#9E9E9E',  # Lighter grey for muted
                            foreground='black')
        else:
            style.configure("MuteButton.TButton",
                            background=self.colors['mute_button']['bg'],
                            foreground=self.colors['mute_button']['fg'])

    def create_modern_button(self, master, text, command, state=tk.NORMAL, style='Modern.TButton'):
        button = ttk.Button(master, text=text, command=command, style=style)
        button.state(["!disabled"])
        if state == tk.DISABLED:
            button.state(["disabled"])
        return button

    def create_label(self, master, text):
        label = ttk.Label(master, text=text, style="TLabel")
        return label

    def create_entry(self, master, textvariable=None, placeholder=None, **options):
        entry = ttk.Entry(master, textvariable=textvariable, style="TEntry", **options)
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind("<FocusIn>", lambda event, e=entry: e.delete(0, tk.END) if e.get() == placeholder else None)
            entry.bind("<FocusOut>", lambda event, e=entry: e.insert(0, placeholder) if not e.get() else None)
        return entry

    def create_option_menu(self, master, variable, options, command=None):
        combobox = ttk.Combobox(master, textvariable=variable, values=options, state="readonly")
        combobox.bind("<<ComboboxSelected>>", command)
        combobox.config(font=self.global_font)  # Set the font
        combobox.set(variable.get())  # Set the current value to the variable's value
        combobox.style = "TCombobox"  # Apply the TCombobox style
        return combobox
    

