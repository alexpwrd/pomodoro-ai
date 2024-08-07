# pomodoro.py is the main file that runs the pomodoro application

"""
Copyright (c) 2024, Alex Glebov
This code is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.
To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/4.0/
"""

import os
import threading
import warnings
from openai import OpenAI
import sounddevice as sd
import soundfile as sf
import tkinter as tk
import numpy as np
from tkinter import ttk
from utils.ui import UIConfig
from utils.settings import SettingsManager, APIKeyManager, SettingsWindow
from utils.window_utils import set_window_icon
from utils.audio_utils import play_sound, toggle_mute
from utils.ai_utils import AIUtils
import logging
from utils.voice_assistant import VoiceAssistant
from pydub import AudioSegment
from pydub.playback import play


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ignore DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

class PomodoroApp:
    def __init__(self, master):
        self.master = master
        self.ui = UIConfig()
        self.status_var = tk.StringVar(value="Ready")  # Define status_var with a default message
        self.time_var = tk.StringVar()  # Initialize the time_var
        self.user_feedback_var = tk.StringVar(value="Press to Talk")  # Initialize user_feedback_var with a default message
        self.initialize_managers()
        self.check_and_initialize_settings()  # New method to handle first-time setup and loading
        self.load_api_settings()
        self.load_user_settings() 
        self.initialize_timing()
        self.initialize_state_flags()
        self.setup_window_layout()
        self.setup_sidebar()
        self.initialize_ui_elements()
        self.voice_assistant = VoiceAssistant(self)
        self.voice_assistant.set_volume(1.0)  # Set initial volume to maximum
        self.update_audio_devices()
        self.long_break_length = int(self.settings_manager.get_setting("LONG_BREAK_TIME", 15)) * 60  # 15 minutes default


        self.work_cycles_completed = int(self.settings_manager.get_setting("WORK_CYCLES_COMPLETED", 0))

        if self.client is not None:
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession)
        else:
            self.ai_utils = None

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.voice_assistant.db.close()
        self.master.destroy()

    def update_user_feedback(self, message):
        # Schedule the update to be run in the main thread
        self.master.after(0, lambda: self.user_feedback_var.set(message))

    def handle_talk_to_ai(self):
        # Disable the "Talk to AI" button to prevent multiple presses during operation
        self.talk_to_ai_button.config(state=tk.DISABLED)
        # Proceed with handling the voice command
        self.voice_assistant.handle_voice_command()

    def enable_talk_to_ai_button(self):
        # Re-enable the "Talk to AI" button
        self.talk_to_ai_button.config(state=tk.NORMAL)

    def load_user_settings(self):
        # Load user profile settings
        self.user_name = self.settings_manager.get_setting("USER_NAME", "Default User")
        self.profession = self.settings_manager.get_setting("PROFESSION", "Default Profession")
        self.ai_voice = self.settings_manager.get_setting("AI_VOICE", "alloy")  # Correct setting for AI voice

        # Load timer settings
        self.focus_length = int(self.settings_manager.get_setting("FOCUS_TIME", 25)) * 60  # Default is 25 minutes, converted to seconds
        self.short_break = int(self.settings_manager.get_setting("BREAK_TIME", 5)) * 60  # Default is 5 minutes, converted to seconds

        # Update the display to reflect the loaded focus time
        self.update_display(self.focus_length)

    def initialize_managers(self):
        self.api_key_manager = APIKeyManager()
        self.settings_manager = SettingsManager(callback=self.reload_user_settings)

    def reload_user_settings(self):
        """Reloads user settings from the settings manager and updates AIUtils."""
        self.load_user_settings()
        self.initialize_timing()  # Reinitialize timing to update focus and break lengths
        # Reinitialize AIUtils with the new settings
        if self.client is not None:
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession)
        else:
            self.ai_utils = None
            logger.info("AI Utils cannot be initialized due to missing API key.")
        self.update_audio_devices()

    def handle_settings_change(self, key, value):
        if key == "API_KEY":
            self.load_api_settings()  # Reload API settings which will reinitialize the AIUtils with new API key

    def reinitialize_ai_utils(self):
        self.load_api_settings()  # This will set self.client based on the new API key
        if self.client is not None:
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession)
        else:
            self.ai_utils = None
            logger.info("AI Utils cannot be initialized due to missing API key.")

    def check_and_initialize_settings(self):
        # Check for the existence of settings and initialize if necessary
        try:
            settings_exist = self.settings_manager.settings_exist()
            if not settings_exist:
                logger.info("First-time setup required. Initializing default settings.")
                self.settings_manager.create_default_settings()
            else:
                logger.info("Loading existing settings.")
            
            # Load settings without checking for API key
            self.load_user_settings()
            logger.info("User settings loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize or load settings: {e}")

    def load_api_settings(self):
        self.openai_api_key = self.api_key_manager.get_api_key()
        if self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession)
        else:
            self.client = None
            self.ai_utils = None
            logger.info("API Key is not set. Proceeding without AI functionalities.")

    def initialize_timing(self):
        self.focus_options = [1, 15, 25, 50, 90]  # in minutes
        self.break_options = [1,5, 10, 15]  # in minutes
        # Use settings for default values
        focus_length = self.settings_manager.get_setting("FOCUS_TIME", 25)
        break_length = self.settings_manager.get_setting("BREAK_TIME", 5)
        self.selected_focus_length = tk.IntVar(self.master, value=focus_length)  # Use setting value
        self.selected_break_length = tk.IntVar(self.master, value=break_length)  # Use setting value
        self.focus_length = self.selected_focus_length.get() * 60
        self.short_break = self.selected_break_length.get() * 60
        self.remaining_time = self.focus_length  # Start with the focus time
        self.max_work_sessions = 4
        self.max_break_sessions = 4

    def initialize_state_flags(self):
        self.running = False 
        self.is_focus_time = True 
        self.is_muted = False 
        self.is_resuming = False  
        self.work_sessions_completed = 0  
        self.break_sessions_completed = 0  
        self.current_cycle = 0  
        self.work_cycles_completed = int(self.settings_manager.get_setting("WORK_CYCLES_COMPLETED", 0))

    def setup_window_layout(self):
        try:
            # Assuming set_window_icon has been updated to correctly reference the resources folder
            set_window_icon(self.master, 'tomato_icon.png')
        except Exception as e:
            logger.error(f"Failed to set window icon: {e}")
        self.master.configure(bg=self.ui.colors["background"])
        window_width, window_height = 800, 500
        
        screen_width, screen_height = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))  # Center the window horizontally
        y = 0  # Position the window at the top of the screen
        self.master.geometry(f'{window_width}x{window_height}+{x}+{y}')

    def setup_sidebar(self):
        logging.debug("Setting up sidebar.")

        if hasattr(self, 'sidebar') and self.sidebar.winfo_exists():
            logging.debug("Destroying existing sidebar.")
            self.sidebar.destroy()

        logging.debug("Creating new sidebar.")

        self.sidebar = tk.Frame(self.master, bg=self.ui.colors["sidebar_bg"], width=150, height=600)
        self.sidebar.pack(expand=False, fill='y', side='left', anchor='nw')
        self.sidebar.pack_propagate(False)  # Prevent the sidebar from resizing to fit its children

        # Adding Start and Skip buttons directly to the sidebar
        self.start_button = self.ui.create_modern_button(self.sidebar, "Start", self.start_pomodoro)
        self.skip_button = self.ui.create_modern_button(self.sidebar, "Skip", self.skip_break, state=tk.DISABLED)
        for button in [self.start_button, self.skip_button]:
            button.pack(side='top', pady=5)

        # Session statistics
        session_stats_frame = tk.Frame(self.sidebar, bg=self.ui.colors['sidebar_bg'])
        session_stats_frame.pack(pady=10, fill='x')
        self.work_session_label = tk.Label(session_stats_frame, text=f"Work Sessions: {self.work_sessions_completed}/{self.max_work_sessions}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.work_session_label.pack(side='top')
        self.break_session_label = tk.Label(session_stats_frame, text=f"Breaks: {self.break_sessions_completed}/{self.max_break_sessions}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.break_session_label.pack(side='top')
        self.work_cycles_label = tk.Label(self.sidebar, text=f"Work Cycles: {self.work_cycles_completed}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.work_cycles_label.pack(side='top')

        # Bottom control buttons frame for Mute, Reset, and Settings
        bottom_buttons_frame = tk.Frame(self.sidebar, bg=self.ui.colors["sidebar_bg"])
        bottom_buttons_frame.pack(side='bottom', fill='x', pady=10)

        # Mute, Reset, and Settings buttons stacked vertically
        self.mute_button = self.ui.create_modern_button(bottom_buttons_frame, "Mute", lambda: self.handle_toggle_mute())
        self.reset_button = self.ui.create_modern_button(bottom_buttons_frame, "Reset", self.reset_pomodoro, state=tk.DISABLED)
        self.settings_button = self.ui.create_modern_button(bottom_buttons_frame, "Settings", self.open_settings_window, style='Modern.TButton')
        for button in [self.mute_button, self.reset_button, self.settings_button]:
            button.pack(side='top', pady=5)

    def initialize_ui_elements(self):
        # Progress bar for showing the current session's progress
        self.progress = ttk.Progressbar(self.master, orient="horizontal", mode="determinate", maximum=self.focus_length)
        self.progress.pack(pady=(10, 20), fill=tk.X, padx=10)
        self.progress.config(style="green.Horizontal.TProgressbar")

        # Frame for Circle + Timer Display
        self.center_frame = tk.Frame(self.master, bg=self.ui.colors["background"])
        self.center_frame.pack(expand=True, fill=tk.BOTH)

        # Sub-frame for grouping the circle and timer horizontally
        circle_timer_frame = tk.Frame(self.center_frame, bg=self.ui.colors["background"])
        circle_timer_frame.pack(side='top', pady=(10, 0))

        # Circle (State Indicator) within the sub-frame
        circle_diameter = 40
        canvas_size = circle_diameter + 20
        self.state_indicator_canvas = tk.Canvas(circle_timer_frame, width=canvas_size, height=canvas_size, bg=self.ui.colors["background"], highlightthickness=0)
        self.state_indicator_canvas.pack(side=tk.LEFT, padx=(10,0))
        circle_x0 = (canvas_size - circle_diameter) / 2
        circle_y0 = circle_x0
        circle_x1 = circle_x0 + circle_diameter
        circle_y1 = circle_y0 + circle_diameter
        self.state_indicator = self.state_indicator_canvas.create_oval(circle_x0, circle_y0, circle_x1, circle_y1, fill=self.ui.colors["state_indicator"]["default"])

        # Timer Display next to the circle in the same sub-frame
        self.time_var = tk.StringVar(self.master)
        self.update_display(self.focus_length)  # Initial display update
        self.timer_display = tk.Label(circle_timer_frame, textvariable=self.time_var, font=("Helvetica", 48), bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.timer_display.pack(side=tk.LEFT, padx=(10,0))

        # Add Talk to AI button directly under the sub-frame within center_frame
        self.talk_to_ai_button = tk.Button(self.center_frame, text="Talk to AI", command=self.handle_talk_to_ai)
        self.talk_to_ai_button.pack(side='top', pady=(10, 0))

        # Add a label for user feedback directly under the "Talk to AI" button
        self.user_feedback_label = tk.Label(self.center_frame, textvariable=self.user_feedback_var, font=("Helvetica", 14), bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.user_feedback_label.pack(side='top', pady=(5, 0))

        # Inspirational or motivational quote display
        self.quote_var = tk.StringVar(self.master, value="Welcome to AI Pomodoro, click start to begin!!")
        self.quote_display = tk.Label(self.master, textvariable=self.quote_var, font=("Helvetica", 14), wraplength=400, bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.quote_display.pack(pady=(10, 20))

        # Main Task Frame
        self.task_frame = tk.Frame(self.master, bg=self.ui.colors["background"])
        self.task_frame.pack(fill=tk.X, expand=True, padx=10, pady=10)

        # Task Display Frame
        self.tasks_display_frame = tk.Frame(self.task_frame, bg=self.ui.colors["background"])
        self.tasks_display_frame.pack(fill=tk.X, expand=True)

        # To Do Column Setup
        todo_column_frame = tk.Frame(self.tasks_display_frame, bg=self.ui.colors["todo_bg"])
        todo_column_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True, padx=(10, 5), pady=5)
        todo_label = tk.Label(todo_column_frame, text="To Do:", bg=self.ui.colors["todo_bg"], fg="lightgrey", font=("Helvetica", 16, "bold"))
        todo_label.pack(side=tk.TOP, fill=tk.X)
        self.todo_frame = tk.Frame(todo_column_frame, bg=self.ui.colors["todo_bg"])
        self.todo_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

        # Completed Column Setup
        completed_column_frame = tk.Frame(self.tasks_display_frame, bg=self.ui.colors["background"])
        completed_column_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True, padx=(5, 10), pady=5)

        # Completed Label and Clear All Button
        completed_label_frame = tk.Frame(completed_column_frame, bg=self.ui.colors["background"])
        completed_label_frame.pack(side=tk.TOP, fill=tk.X)

        completed_label = tk.Label(completed_label_frame, text="Completed", bg=self.ui.colors["background"], fg="lightgrey", font=("Helvetica", 16, "bold"))
        completed_label.pack(side=tk.LEFT)

        # Clear All Button for Completed Tasks
        clear_all_button = tk.Button(completed_label_frame, text="\u2672", command=self.clear_completed_tasks, fg="#2B2B2B", bg="#2D2D2D")
        clear_all_button.pack(side=tk.RIGHT, padx=10)

        # Create a frame to display completed tasks within the completed column frame.
        # The background color is set to the 'completed_bg' color from the UI configuration.
        self.completed_frame = tk.Frame(completed_column_frame, bg=self.ui.colors["completed_bg"])
        # Pack the completed frame at the top of its parent frame, allow it to fill horizontally,
        # and enable expansion to use any extra space.
        self.completed_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

        # New Task Input Frame pinned to the bottom
        task_input_frame = tk.Frame(self.master, bg=self.ui.colors["background"])
        task_input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(5, 10))

        # Task Input Field with specific style
        self.task_input = self.ui.create_entry(task_input_frame, style="TaskInput.TEntry", width=40)
        self.task_input.pack(side=tk.LEFT, padx=(10, 10), pady=(0, 10), expand=True, fill=tk.X)  # Added horizontal padding on the right

        # Add Task Button using the modern button style
        self.add_task_button = self.ui.create_modern_button(task_input_frame, "Add Task", self.add_task)
        self.add_task_button.pack(side=tk.RIGHT, padx=(10, 10), pady=(0, 10))  # Added horizontal padding on the left

    def add_task(self):
        task_text = self.task_input.get().strip()
        if task_text:
            task_frame = tk.Frame(self.todo_frame, bg=self.ui.colors["background"], borderwidth=0, highlightthickness=0)
            task_frame.pack(pady=2, padx=10, fill=tk.X)

            # Task label
            task_label = tk.Label(task_frame, text=task_text, font=("Helvetica", 16), bg=self.ui.colors["background"], fg=self.ui.colors["text"])
            task_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Complete task button
            complete_button = self.create_button(task_frame, "✔", lambda: self.complete_task(task_label, task_frame), "button")
            complete_button.pack(side=tk.RIGHT, padx=(0, 5))

            # Delete task button
            delete_button = self.create_button(task_frame, "✖", lambda: task_frame.destroy(), "button")
            delete_button.pack(side=tk.RIGHT)

            self.task_input.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "No task to add")

    def complete_task(self, task_label, task_frame):
        # Disable the task label and change its color to indicate completion
        task_label.config(fg="gray")

        # Create a new frame in the completed tasks area with matching background color
        completed_task_frame = tk.Frame(self.completed_frame, bg=self.ui.colors["background"], borderwidth=0, highlightthickness=0)
        completed_task_frame.pack(pady=2, padx=10, fill=tk.X)

        # Recreate the label in the new frame with a suitable color to indicate completion
        completed_task_label = tk.Label(completed_task_frame, text=task_label.cget("text"), font=("Helvetica", 16), fg="green", bg=self.ui.colors["background"])
        completed_task_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Destroy the old frame in the To Do section
        task_frame.destroy()
    
    def clear_completed_tasks(self):
    # This method will destroy all child widgets in the completed_frame,
    # effectively clearing all completed tasks.
        for widget in self.completed_frame.winfo_children():
            widget.destroy()

    def create_button(self, master, text, command, button_key, state=tk.NORMAL):
        # Retrieve button color configuration using button_key
        button_colors = self.ui.colors[button_key]
        
        # Create a unique style name for this button
        style_name = f"{button_key}.TButton"

        # Configure the style for this button
        button_style = ttk.Style()
        button_style.configure(style_name, background=button_colors['bg'], foreground=button_colors['fg'], relief='flat', borderwidth=0, padding=1)

        # Create a button with the specific style
        button = ttk.Button(master, text=text, command=command, style=style_name, width=2)  # width set to 2 to make it square
        button.state(["!disabled"])  # Ensure it starts in enabled state unless specified

        # Change the state based on the 'state' parameter
        if state == tk.DISABLED:
            button.state(["disabled"])

        def on_enter(e):
            if button.instate(["!disabled"]):  # Check if button is not disabled
                button_style.configure(style_name, background=button_colors['hover_bg'], foreground=button_colors['hover_fg'])

        def on_leave(e):
            if button.instate(["!disabled"]):
                button_style.configure(style_name, background=button_colors['bg'], foreground=button_colors['fg'])

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

        return button
    
    def set_api_key(self, api_key):
        self.api_key_manager.set_api_key(api_key)
        logger.info("API Key has been updated successfully.")
    
    def open_settings_window(self):
        SettingsWindow(self.master, self)

    def update_break_length(self, *args):
        self.short_break = self.selected_break_length.get() * 60  # Convert minutes to seconds
        if not self.is_focus_time:  # If currently in break, update the timer display and progress bar maximum
            self.remaining_time = self.short_break
            self.update_display(self.remaining_time)
            self.progress["maximum"] = self.short_break
            self.progress["value"] = 0

    def update_focus_length(self, *args):
        self.focus_length = self.selected_focus_length.get() * 60
        self.progress["maximum"] = self.focus_length
        if not self.running:
            self.remaining_time = self.focus_length
            self.update_display(self.remaining_time)
            self.progress["value"] = 0


    def skip_break(self):
        if not self.is_focus_time and self.running:
            # Stop any ongoing audio playback
            sd.stop()

            # Log skipping the break
            logger.info("Skipping break session.")
            # Reset the break session counter and immediately start a new work session
            self.break_sessions_completed = 0
            self.is_focus_time = True
            self.remaining_time = self.focus_length
            self.update_display(self.remaining_time)
            self.progress["maximum"] = self.focus_length
            self.progress["value"] = 0
            self.update_state_indicator("focus")
            
            # Play sound indicating the start of focus time
            play_sound(for_break=False)  # Ensure this function is defined to play a specific sound for focus time
            
            # Fetch and display a motivational quote for focus time
            current_tasks = self.collect_current_tasks()
            self.fetch_motivational_quote(for_break=False, current_todo=current_tasks)
            
            # Start the pomodoro timer for the new focus session
            self.start_pomodoro()

            # Ensure the skip button is disabled when starting a new focus session
            self.skip_button.config(state=tk.DISABLED)

    def start_break(self):
        self.reload_user_settings()  # Reload settings at the start of the break
        # Stop any ongoing work session before starting the break.
        if self.running and self.is_focus_time:
            self.running = False
            self.is_focus_time = False
        
        # Collect current tasks
        current_tasks = [task_label.cget("text") for task_frame in self.todo_frame.winfo_children() for task_label in task_frame.winfo_children() if isinstance(task_label, tk.Label)]
        current_todo = ', '.join(current_tasks)

        # Now start the break.
        self.running = True
        self.remaining_time = self.short_break
        self.update_display(self.remaining_time)
        self.fetch_motivational_quote(for_break=True, current_todo=current_todo)  # Pass current_todo here
        self.progress["maximum"] = self.short_break
        self.progress["value"] = 0
        self.pomodoro_timer()
        
        # Update button states.
        self.start_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        # self.break_button.config(state=tk.DISABLED)
        self.skip_button.config(state=tk.NORMAL)  # Enable the skip button when starting a break

        self.update_state_indicator("break")  # Update state indicator to yellow for break time

    def update_audio_devices(self):
        input_device = self.settings_manager.get_setting("INPUT_DEVICE")
        output_device = self.settings_manager.get_setting("OUTPUT_DEVICE")
        
        if input_device and input_device != "System Default":
            sd.default.device['input'] = int(input_device) if input_device.isdigit() else input_device
        else:
            sd.default.device['input'] = sd.default.device[0]  # Use system default input

        if output_device and output_device != "System Default":
            sd.default.device['output'] = int(output_device) if output_device.isdigit() else output_device
        else:
            sd.default.device['output'] = sd.default.device[1]  # Use system default output
        
        # Update VoiceAssistant's audio devices
        self.voice_assistant.update_audio_devices(sd.default.device['input'], sd.default.device['output'])
        
        logger.info(f"Audio devices updated. Input: {sd.default.device['input']}, Output: {sd.default.device['output']}")

    def play_audio(self, file_path):
        if self.is_muted:
            logger.info("Audio playback skipped due to mute state.")
            return

        try:
            audio = AudioSegment.from_file(file_path, format="mp3")
            play(audio)
            logger.info("Audio playback completed.")
        except Exception as e:
            logger.error(f"Error playing audio file: {e}")

    def fetch_motivational_quote(self, for_break=False, current_todo="", is_long_break=False):
        if hasattr(self, 'quote_thread') and self.quote_thread.is_alive():
            logger.info("A quote is already being fetched. Skipping this request.")
            return

        def thread_target():
            if self.ai_utils is None:
                self.master.after(0, lambda: self.quote_var.set("AI functionalities are not available without an API key."))
                self.master.after(0, lambda: self.status_var.set("AI features disabled. Set an API key in settings to enable."))
                logger.info("AI functionalities are not available without an API key.")
                return

            try:
                message = self.ai_utils.fetch_motivational_quote(for_break, current_todo, is_long_break)
                break_type = "Long Break" if is_long_break else "Break"
                self.master.after(0, lambda: self.quote_var.set(message if not for_break else f"{break_type} Time: {message}"))
                self.master.after(0, lambda: self.status_var.set("Speaking..."))
                self.voice_assistant.text_to_speech(message)
            except Exception as e:
                self.master.after(0, lambda: self.quote_var.set("Error fetching quote. Please check your connection."))
                logger.error(f"Error fetching motivational quote: {e}")

        self.quote_thread = threading.Thread(target=thread_target)
        self.quote_thread.daemon = True
        self.quote_thread.start()


    def update_display(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        self.time_var.set(f"{minutes:02}:{seconds:02}")

    def update_timer_settings(self):
        # Fetch new settings
        self.focus_length = int(self.settings_manager.get_setting("FOCUS_TIME", 25)) * 60
        self.short_break = int(self.settings_manager.get_setting("BREAK_TIME", 5)) * 60

        # Update the progress bar maximum to reflect the new focus length
        self.progress["maximum"] = self.focus_length

        # Optionally, reset the timer to start with the new settings
        self.reset_pomodoro()

    def collect_current_tasks(self):
        """Collects all tasks from the todo_frame and returns them as a single comma-separated string."""
        return ', '.join(task_label.cget("text") for task_frame in self.todo_frame.winfo_children() for task_label in task_frame.winfo_children() if isinstance(task_label, tk.Label))

    def start_pomodoro(self):
        self.reload_user_settings()  # Ensure the latest settings are loaded
        if not self.running:
            self.running = True
            self.start_button.config(text="Pause", command=self.pause_pomodoro, state=tk.NORMAL)
            self.reset_button.config(state=tk.DISABLED)
            self.skip_button.config(state=tk.DISABLED)  # Disable the skip button when starting a work session

            current_todo = self.collect_current_tasks()  # Combine all tasks into a single string
            if not self.is_resuming:
                threading.Thread(target=self.fetch_motivational_quote, args=(False, current_todo)).start()
            else:
                self.is_resuming = False

            self.progress["maximum"] = self.focus_length
            self.progress["value"] = 0
            self.pomodoro_timer()
            self.update_state_indicator("focus")
            logger.info("Timer started.")

    def pause_pomodoro(self):
        self.running = False
        self.paused_time = self.remaining_time  # Save the remaining time
        self.start_button.config(text="Resume", command=self.resume_pomodoro, state=tk.NORMAL)
        self.reset_button.config(state=tk.NORMAL)
        self.update_state_indicator("paused")
        logger.info("Timer paused.")

    def resume_pomodoro(self):
        self.remaining_time = self.paused_time  # Use the saved paused time to resume
        self.running = True
        self.start_button.config(text="Pause", command=self.pause_pomodoro, state=tk.NORMAL)
        self.reset_button.config(state=tk.NORMAL)
        self.update_state_indicator("focus" if self.is_focus_time else "break")
        self.pomodoro_timer()  # Continue the timer
        logger.info("Timer resumed.")

    def reset_pomodoro(self):
        self.reload_user_settings()
        self.running = False
        self.is_focus_time = True
        self.remaining_time = int(self.focus_length)
        self.update_display(self.remaining_time)
        self.start_button.config(text="Start", command=self.start_pomodoro, state=tk.NORMAL)
        self.reset_button.config(state=tk.DISABLED)
        self.skip_button.config(state=tk.DISABLED)
        self.is_resuming = False 
        self.progress["value"] = 0
        self.update_state_indicator("default")
        self.work_sessions_completed = 0
        self.break_sessions_completed = 0
        self.update_work_cycles_display()
        logger.info("Timer reset.")

    def pomodoro_timer(self):
        if self.remaining_time > 0 and self.running:
            self.update_display(self.remaining_time)
            self.remaining_time -= 1
            self.progress["value"] = self.progress["maximum"] - self.remaining_time
            self.master.after(1000, self.pomodoro_timer)
        elif self.running:
            if not self.is_focus_time:
                if self.work_sessions_completed == 0:  # This indicates the end of a long break
                    self.end_long_break()
                else:
                    self.switch_mode()
            else:
                self.switch_mode()

    def switch_mode(self):
        self.reload_user_settings()
        self.running = False
        if self.is_focus_time:
            play_sound(for_break=True)
            self.work_sessions_completed += 1
            if self.work_sessions_completed >= self.max_work_sessions:
                # Completed a full work cycle
                self.work_cycles_completed += 1
                self.work_sessions_completed = 0  # Reset work sessions counter
                self.settings_manager.update_setting("WORK_CYCLES_COMPLETED", self.work_cycles_completed)
                self.settings_manager.save_settings()
                self.update_work_cycles_display()
                self.start_long_break()
                return
            self.is_focus_time = False
            self.remaining_time = self.short_break
            self.update_state_indicator("break")
            self.work_session_label.config(text=f"Work: {self.work_sessions_completed}/{self.max_work_sessions}")
            self.start_break()
        else:
            play_sound(for_break=False)
            self.break_sessions_completed += 1
            if self.break_sessions_completed >= self.max_break_sessions:
                self.reset_pomodoro()
                return
            self.is_focus_time = True
            self.remaining_time = self.focus_length
            self.update_state_indicator("focus")
            self.break_session_label.config(text=f"Breaks: {self.break_sessions_completed}/{self.max_break_sessions}")
            self.start_pomodoro()

    def start_long_break(self):
        self.is_focus_time = False
        self.remaining_time = self.long_break_length
        self.update_display(self.remaining_time)
        self.progress["maximum"] = self.long_break_length
        self.progress["value"] = 0
        self.update_state_indicator("long_break")

        current_tasks = self.collect_current_tasks()
        self.fetch_motivational_quote(for_break=True, current_todo=current_tasks, is_long_break=True)

        self.start_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        self.skip_button.config(state=tk.NORMAL)

        self.running = True
        self.pomodoro_timer()

    def end_long_break(self):
        self.running = False
        self.is_focus_time = True
        self.remaining_time = self.focus_length
        self.update_display(self.remaining_time)
        self.progress["maximum"] = self.focus_length
        self.progress["value"] = 0
        self.update_state_indicator("default")

        self.start_button.config(text="Start New Cycle", command=self.start_pomodoro, state=tk.NORMAL)
        self.reset_button.config(state=tk.NORMAL)
        self.skip_button.config(state=tk.DISABLED)

        self.work_sessions_completed = 0
        self.break_sessions_completed = 0
        self.update_work_cycles_display()

        # Display a message to the user
        self.quote_var.set("Long break completed. Click 'Start New Cycle' when you're ready to begin the next work session.")

    def update_work_cycles_display(self):
        self.work_cycles_label.config(text=f"Work Cycles: {self.work_cycles_completed}")
        self.work_session_label.config(text=f"Work: {self.work_sessions_completed}/{self.max_work_sessions}")

    
    def update_state_indicator(self, state):
        color = self.ui.colors["state_indicator"].get(state, self.ui.colors["state_indicator"]["default"])
        self.state_indicator_canvas.itemconfig(self.state_indicator, fill=color)
        logger.info(f"State updated to {state}.")

    def handle_toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.stop_audio_playback()
            self.mute_button.config(text="Unmute")
        else:
            self.mute_button.config(text="Mute")
        self.ui.update_mute_button_style(self.is_muted)

    def stop_audio_playback(self):
        self.voice_assistant.stop_audio_playback()

    def update_work_cycles_display(self):
        # Assuming you have a label for displaying work cycles, similar to work_session_label
        self.work_cycles_label.config(text=f"Work Cycles: {self.work_cycles_completed}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Pomodoro AI")
    app = PomodoroApp(root)
    root.mainloop()
