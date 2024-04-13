import tkinter as tk
from tkinter import ttk

class UIConfig:
    def __init__(self):
        self.colors = {
            "background": '#2D2D2D',
            "text": '#F0F0F0',
            "progress_bar": '#505050',
            "button": {
                'bg': '#505050',
                'fg': '#F0F0F0',
                'hover_bg': '#686868',
                'hover_fg': '#FFFFFF',
                'disabled_bg': '#3A3A3A',
                'disabled_fg': '#A6A6A6'
            },
            "entry": {
                "bg": '#FFFFFF',
                "fg": '#000000',
                "field_bg": '#333333'
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
                "default": '#9E9E9E'  # Grey
            }
        }
        self.configure_styles()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('default')
        self.global_font = ("Helvetica", 14)

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
        style.configure("MuteButton.TButton",
                        background=self.colors['mute_button']['bg'],
                        foreground=self.colors['mute_button']['fg'])
        style.map("MuteButton.TButton",
                  background=[('active', self.colors['mute_button']['hover_bg']),
                              ('disabled', self.colors['mute_button']['disabled_bg'])],
                  foreground=[('active', self.colors['mute_button']['hover_fg']),
                              ('disabled', self.colors['mute_button']['disabled_fg'])])

        # Configure label and entry styles
        style.configure(
            "TLabel",
            background=self.colors["background"],
            foreground=self.colors["text"],
            font=self.global_font
        )
        style.configure(
            "TEntry",
            fieldbackground=self.colors["entry"]["field_bg"],
            background=self.colors["entry"]["bg"],
            foreground=self.colors["entry"]["fg"],
            borderwidth=0,
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

    def create_entry(self, master, textvariable=None, placeholder=None):
        entry = ttk.Entry(master, textvariable=textvariable, style="TEntry")
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind("<FocusIn>", lambda event: entry.delete(0, tk.END) if entry.get() == placeholder else None)
            entry.bind("<FocusOut>", lambda event: entry.insert(0, placeholder) if not entry.get() else None)
        return entry

    def create_option_menu(self, master, variable, options, command=None):
        option_menu = tk.OptionMenu(master, variable, *options, command=command)
        option_menu.config(bg=self.colors["background"], fg=self.colors["text"], font=self.global_font)
        option_menu["menu"].config(bg=self.colors["background"], fg=self.colors["text"])
        return option_menu
