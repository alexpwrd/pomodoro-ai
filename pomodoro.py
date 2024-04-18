# pomodoro.py is the main file that runs the pomodoro application

import os
import threading
import warnings
from pathlib import Path
from openai import OpenAI
import sounddevice as sd
import soundfile as sf
import tkinter as tk
from tkinter import ttk, PhotoImage
from utils.ui import UIConfig
from utils.settings import SettingsManager, APIKeyManager, SettingsWindow
from utils.window_utils import set_window_icon
from utils.audio_utils import play_sound, toggle_mute
from utils.ai_utils import AIUtils
import logging
from tkinter import simpledialog


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ignore DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

class PomodoroApp:
    def __init__(self, master):
        self.master = master
        self.ui = UIConfig()
        self.status_var = tk.StringVar(value="Ready")  # Define status_var with a default message
        self.time_var = tk.StringVar()  # Initialize the time_var
        self.initialize_managers()
        self.check_and_initialize_settings()  # New method to handle first-time setup and loading
        self.load_api_settings()
        self.load_user_settings() 
        self.initialize_timing()
        self.initialize_state_flags()
        self.setup_window_layout()
        self.setup_sidebar()
        self.initialize_ui_elements()

        if self.client is not None:
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession)
        else:
            self.ai_utils = None

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
        """Reloads user settings from the settings manager."""
        self.load_user_settings()
        self.initialize_timing()  # Reinitialize timing to update focus and break lengths

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
        settings_exist = self.settings_manager.settings_exist()

        if not settings_exist:
            logger.info("First-time setup required. Initializing default settings.")
            self.settings_manager.create_default_settings()
        
        # Load settings without checking for API key
        self.load_user_settings()

    def load_api_settings(self):
        self.openai_api_key = self.api_key_manager.get_api_key()
        if self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession)
        else:
            self.client = None
            self.ai_utils = None
            logger.info("API Key is not set. Please set your API key for full functionality.")

    def initialize_timing(self):
        self.focus_options = [1, 15, 25, 50, 90]  # in minutes
        self.break_options = [1, 5, 10, 15]  # in minutes
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

    def setup_window_layout(self):
        try:
            # Assuming set_window_icon has been updated to correctly reference the resources folder
            set_window_icon(self.master, 'tomato_icon.png')
        except Exception as e:
            logger.error(f"Failed to set window icon: {e}")
        self.master.configure(bg=self.ui.colors["background"])
        window_width, window_height = 900, 600
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

        # Control buttons frame
        control_buttons_frame = tk.Frame(self.sidebar, bg=self.ui.colors["sidebar_bg"])
        control_buttons_frame.pack(pady=10, fill='x')

        # Adding buttons
        self.start_button = self.ui.create_modern_button(control_buttons_frame, "Start", self.start_pomodoro)
        self.pause_button = self.ui.create_modern_button(control_buttons_frame, "Pause", self.pause_pomodoro, state=tk.DISABLED)
        self.skip_button = self.ui.create_modern_button(control_buttons_frame, "Skip", self.skip_break, state=tk.DISABLED)
        self.reset_button = self.ui.create_modern_button(control_buttons_frame, "Reset", self.reset_pomodoro, state=tk.DISABLED)
        self.mute_button = self.ui.create_modern_button(control_buttons_frame, "Mute", lambda: self.handle_toggle_mute())
        for button in [self.start_button, self.pause_button, self.skip_button, self.reset_button, self.mute_button]:
            button.pack(side='top', pady=5)

        # Session statistics
        session_stats_frame = tk.Frame(self.sidebar, bg=self.ui.colors['sidebar_bg'])
        session_stats_frame.pack(pady=10, fill='x')
        self.work_session_label = tk.Label(session_stats_frame, text=f"Work: {self.work_sessions_completed}/{self.max_work_sessions}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.work_session_label.pack(side='top')
        self.break_session_label = tk.Label(session_stats_frame, text=f"Breaks: {self.break_sessions_completed}/{self.max_break_sessions}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.break_session_label.pack(side='top')

        # Add Settings Button at the bottom of the sidebar
        self.settings_button = self.ui.create_modern_button(self.sidebar, "Settings", self.open_settings_window, style='Modern.TButton')
        self.settings_button.pack(side='bottom', pady=10, fill='x', anchor='s')  # Adjusted to pin to the bottom

    def initialize_ui_elements(self):
        # Progress bar for showing the current session's progress
        self.progress = ttk.Progressbar(self.master, orient="horizontal", mode="determinate", maximum=self.focus_length)
        self.progress.pack(pady=(10, 20), fill=tk.X, padx=10)
        self.progress.config(style="green.Horizontal.TProgressbar")

        # Frame for Circle + Timer Display
        self.center_frame = tk.Frame(self.master, bg=self.ui.colors["background"])
        self.center_frame.pack(expand=True)

        # Circle (State Indicator)
        circle_diameter = 40
        canvas_size = circle_diameter + 20
        self.state_indicator_canvas = tk.Canvas(self.center_frame, width=canvas_size, height=canvas_size, bg=self.ui.colors["background"], highlightthickness=0)
        self.state_indicator_canvas.pack(side=tk.LEFT, pady=(10, 10), padx=(10,0))
        circle_x0 = (canvas_size - circle_diameter) / 2
        circle_y0 = circle_x0
        circle_x1 = circle_x0 + circle_diameter
        circle_y1 = circle_y0 + circle_diameter
        self.state_indicator = self.state_indicator_canvas.create_oval(circle_x0, circle_y0, circle_x1, circle_y1, fill=self.ui.colors["state_indicator"]["default"])

        # Timer Display
        self.time_var = tk.StringVar(self.master, value="25:00")
        self.timer_display = tk.Label(self.center_frame, textvariable=self.time_var, font=("Helvetica", 48), bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.timer_display.pack(side=tk.LEFT, padx=(10,0))

        # Inspirational or motivational quote display
        self.quote_var = tk.StringVar(self.master, value="Welcome to AI Pomodoro, click start to begin!!")
        self.quote_display = tk.Label(self.master, textvariable=self.quote_var, font=("Helvetica", 14), wraplength=400, bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.quote_display.pack(pady=(10, 20))

        # Main Task Frame
        self.task_frame = tk.Frame(self.master, bg=self.ui.colors["background"])
        self.task_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=True, padx=10, pady=10)

        # Task Input Frame
        self.task_input_frame = tk.Frame(self.task_frame, bg=self.ui.colors["background"])
        self.task_input_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Task Input Field
        self.task_input = tk.Entry(self.task_input_frame, width=50)
        self.task_input.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10), expand=True)

        # Add Task Button
        self.add_task_button = tk.Button(self.task_input_frame, text="Add Task", command=self.add_task)
        self.add_task_button.pack(side=tk.RIGHT, padx=(0, 10), pady=(0, 10))

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

        self.completed_frame = tk.Frame(completed_column_frame, bg=self.ui.colors["completed_bg"])
        self.completed_frame.pack(side=tk.TOP, fill=tk.X, expand=True)


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

    def start_break(self):
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
        self.pause_button.config(state=tk.NORMAL)
        self.reset_button.config(state=tk.DISABLED)
        # self.break_button.config(state=tk.DISABLED)
        self.skip_button.config(state=tk.NORMAL)  # Enable the skip button when starting a break

        self.update_state_indicator("break")  # Update state indicator to yellow for break time

    def play_audio(self, file_path):
        if self.is_muted:
            logger.info("Audio playback skipped due to mute state.")
            return
        try:
            data, samplerate = sf.read(file_path, dtype='float32')
            sd.play(data, samplerate)
            sd.wait()  # Wait until the file has finished playing
            logger.info("Audio playback completed.")
        except Exception as e:
            logger.error(f"Error playing audio file: {e}")

    def fetch_motivational_quote(self, for_break=False, current_todo=""):
        if self.ai_utils is not None:  # Check if ai_utils is initialized
            try:
                message = self.ai_utils.fetch_motivational_quote(for_break, current_todo)
                self.master.after(0, lambda: self.quote_var.set(message if not for_break else f"Break Time: {message}"))
                self.master.after(0, lambda: self.status_var.set("Speaking..."))
                speaking_thread = threading.Thread(target=self.speak_quote, args=(message,))
                speaking_thread.start()
            except Exception as e:
                self.quote_var.set("AI functionalities are not currently available due to missing or invalid API Key.")
                logger.error(f"Error fetching idea: {e}")
        else:
            self.master.after(0, lambda: self.quote_var.set("AI functionalities are not available."))
            logger.warning("AI Utils is not initialized or available.")

    def text_to_speech(self, text):
        """Converts text to speech and saves as an audio file using the user's preferred voice."""
        if self.is_muted:
            logger.info("Text-to-speech skipped due to mute state.")
            return
        user_voice = self.settings_manager.get_setting("AI_VOICE", "onyx")
        valid_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

        if user_voice not in valid_voices:
            logger.error(f"Invalid voice setting '{user_voice}'. Using default 'onyx'.")
            user_voice = "onyx"

        script_dir = os.path.dirname(__file__)
        speech_file_path = os.path.join(script_dir, 'speech_output.opus')

        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=user_voice,
                input=text,
                response_format="opus"
            )
            response.stream_to_file(speech_file_path)
            self.play_audio(speech_file_path)  
        except Exception as e:
            logger.error(f"Error in text-to-speech conversion: {e}")
            
    def speak_quote(self, message):
        if not self.is_muted:
            if hasattr(self, 'text_to_speech'):
                self.text_to_speech(message)
            else:
                logger.warning("text_to_speech method is not available.")
        self.master.after(0, lambda: self.status_var.set(""))

    def update_display(self, remaining_time):
        mins, secs = divmod(remaining_time, 60)
        self.time_var.set(f"{mins:02d}:{secs:02d}")

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
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.DISABLED)
            self.skip_button.config(state=tk.DISABLED)  # Disable the skip button when starting a work session
            # self.break_button.config(state=tk.DISABLED)

            # Retrieve all tasks from the todo_frame using the new method
            current_todo = self.collect_current_tasks()  # Combine all tasks into a single string

            if not self.is_resuming:
                threading.Thread(target=self.fetch_motivational_quote, args=(False, current_todo)).start()
            else:
                self.is_resuming = False
            self.progress["maximum"] = self.focus_length
            self.progress["value"] = 0
            self.pomodoro_timer()
            self.update_state_indicator("focus")


    def pause_pomodoro(self):
        self.running = False
        self.is_resuming = True  # Set the flag to indicate resuming
        self.start_button.config(text="Resume", command=self.start_pomodoro, state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.NORMAL)
        # self.break_button.config(state=tk.NORMAL)
        self.update_state_indicator("paused")
        logger.info("Timer paused.")

    def reset_pomodoro(self):
        self.running = False
        self.current_cycle = 0
        self.is_focus_time = True
        self.remaining_time = int(self.focus_length)  # Ensure it's an integer
        logger.debug(f"Updating display with remaining_time: {self.remaining_time} (type: {type(self.remaining_time)})")
        self.update_display(self.remaining_time)
        self.start_button.config(text="Start", command=self.start_pomodoro, state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        # self.break_button.config(state=tk.NORMAL)
        self.skip_button.config(state=tk.DISABLED)  # Disable the skip button when resetting the timer
        self.is_resuming = False 
        self.progress["value"] = 0
        self.update_state_indicator("default")
        self.work_sessions_completed = 0
        self.break_sessions_completed = 0
        logger.info("Timer reset.")

    def pomodoro_timer(self):
        if self.remaining_time > 0 and self.running:
            self.update_display(self.remaining_time)
            self.remaining_time -= 1
            self.progress["value"] = self.progress["maximum"] - self.remaining_time
            self.master.after(1000, self.pomodoro_timer)
        elif self.running:
            self.switch_mode()

    def switch_mode(self):
        self.running = False  # Stop the current timer
        if self.is_focus_time:
            play_sound(for_break=True)
            self.work_sessions_completed += 1
            if self.work_sessions_completed >= self.max_work_sessions:
                self.reset_pomodoro()  # Reset if maximum work sessions are reached
                return
            self.is_focus_time = False
            self.remaining_time = self.short_break
            self.update_state_indicator("break")
            self.work_session_label.config(text=f"Work: {self.work_sessions_completed}/{self.max_work_sessions}")
            self.start_break()  # Start the break session
        else:
            play_sound(for_break=False)
            self.break_sessions_completed += 1
            if self.break_sessions_completed >= self.max_break_sessions:
                self.reset_pomodoro()  # Reset if maximum break sessions are reached
                return
            self.is_focus_time = True
            self.remaining_time = self.focus_length
            self.update_state_indicator("focus")
            self.break_session_label.config(text=f"Breaks: {self.break_sessions_completed}/{self.max_break_sessions}")
            self.start_pomodoro()  # Start the focus session

    def update_state_indicator(self, state):
        color = self.ui.colors["state_indicator"].get(state, self.ui.colors["state_indicator"]["default"])
        self.state_indicator_canvas.itemconfig(self.state_indicator, fill=color)

    def handle_toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            # Stop any ongoing audio playback
            sd.stop()
            self.mute_button.config(text="Unmute")
        else:
            self.mute_button.config(text="Mute")
        # Update the mute button style based on the new mute state
        self.ui.update_mute_button_style(self.is_muted)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Pomodoro AI")
    app = PomodoroApp(root)
    root.mainloop()
