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
        self.initialize_managers()
        self.check_and_initialize_settings()  # New method to handle first-time setup and loading
        self.load_api_settings()
        self.load_user_settings() 
        self.initialize_timing()
        self.initialize_state_flags()
        self.setup_window_layout()
        self.setup_sidebar()
        self.initialize_ui_elements()

        self.load_api_settings()
        # Make sure to only initialize AIUtils if client is set
        if self.client is not None:
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession, self.company)
        else:
            self.ai_utils = None

    def initialize_managers(self):
        self.api_key_manager = APIKeyManager()
        self.settings_manager = SettingsManager(callback=self.handle_settings_change)

    def handle_settings_change(self, key, value):
        if key == "API_KEY":
            self.load_api_settings()  # Reload API settings which will reinitialize the AIUtils with new API key

    def check_and_initialize_settings(self):
        # Check for the existence of settings and initialize if necessary
        settings_exist = self.settings_manager.settings_exist()

        if not settings_exist:
            logger.info("First-time setup required. Initializing default settings.")
            self.settings_manager.create_default_settings()
        
        # Load settings without checking for API key
        self.load_user_settings()

    def prompt_for_api_key(self):
        # Prompt the user to enter their OpenAI API key if not set
        api_key = simpledialog.askstring("API Key Required", "Enter your OpenAI API key:", parent=self.master)
        if api_key:
            self.api_key_manager.set_api_key(api_key)
            logger.info("API key set successfully.")
        else:
            logger.warning("No API key provided; some functionalities will be restricted.")
            messagebox.showinfo("API Key", "You can set the API key later via Settings.")

    def load_api_settings(self):
        self.openai_api_key = self.api_key_manager.get_api_key()
        self.client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        if self.client:
            self.ai_utils = AIUtils(self.client, self.user_name, self.profession, self.company)
        else:
            logger.error("API Key is not set or invalid. AI functionalities will be limited.")
            self.ai_utils = None

    def load_user_settings(self):
        self.user_name = self.settings_manager.get_setting("USER_NAME", "Default User")
        self.profession = self.settings_manager.get_setting("PROFESSION", "Default Profession")
        self.company = self.settings_manager.get_setting("COMPANY", "Default Company")
        self.ai_voice = self.settings_manager.get_setting("AI_VOICE", "alloy")  # Correct setting for AI voice

    def initialize_timing(self):
        self.focus_options = [1, 15, 25, 50, 90]  # in minutes
        self.break_options = [1, 5, 10, 15]  # in minutes
        self.selected_focus_length = tk.IntVar(self.master, value=25)  # Default to 25 minutes
        self.selected_break_length = tk.IntVar(self.master, value=5)  # Default to 5 minutes
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
        set_window_icon(self.master, 'tomato_icon.png')
        self.master.configure(bg=self.ui.colors["background"])
        window_width, window_height = 900, 600
        screen_width, screen_height = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))  # Convert to int
        y = 0  # Keep y as an integer
        self.master.geometry(f'{window_width}x{window_height}+{x}+{y}')

    def setup_sidebar(self):
        logging.debug("Setting up sidebar.")

        if hasattr(self, 'sidebar') and self.sidebar.winfo_exists():
            logging.debug("Destroying existing sidebar.")
            self.sidebar.destroy()

        logging.debug("Creating new sidebar.")

        self.sidebar = tk.Frame(self.master, bg=self.ui.colors["sidebar_bg"], width=150, height=600)
        # Create a sidebar frame with a darker background
        self.sidebar = tk.Frame(self.master, bg=self.ui.colors["sidebar_bg"], width=150, height=600)
        self.sidebar.pack(expand=False, fill='y', side='left', anchor='nw')
        self.sidebar.pack_propagate(False)  # Prevent the sidebar from resizing to fit its children

        # Time selection frame
        time_selection_frame = tk.Frame(self.sidebar, bg=self.ui.colors["sidebar_bg"])
        time_selection_frame.pack(pady=10, fill='x')

        # Focus time dropdown
        focus_label = tk.Label(time_selection_frame, text="Focus Time (min):", bg=self.ui.colors["sidebar_bg"], fg=self.ui.colors["text"])
        focus_label.pack(side='top')
        self.focus_dropdown = self.ui.create_option_menu(time_selection_frame, self.selected_focus_length, self.focus_options, self.update_focus_length)
        self.focus_dropdown.pack(side='top')

        # Break time dropdown
        break_label = tk.Label(time_selection_frame, text="Break Time (min):", bg=self.ui.colors["sidebar_bg"], fg=self.ui.colors["text"])
        break_label.pack(side='top')
        self.break_dropdown = self.ui.create_option_menu(time_selection_frame, self.selected_break_length, self.break_options, self.update_break_length)
        self.break_dropdown.pack(side='top')

        # Control buttons frame
        control_buttons_frame = tk.Frame(self.sidebar, bg=self.ui.colors["sidebar_bg"])
        control_buttons_frame.pack(pady=10, fill='x')

        # Adding buttons
        self.start_button = self.ui.create_modern_button(control_buttons_frame, "Start", self.start_pomodoro)
        self.pause_button = self.ui.create_modern_button(control_buttons_frame, "Pause", self.pause_pomodoro, state=tk.DISABLED)
        self.reset_button = self.ui.create_modern_button(control_buttons_frame, "Reset", self.reset_pomodoro, state=tk.DISABLED)
        self.break_button = self.ui.create_modern_button(control_buttons_frame, "Take a Break", self.start_break)
        self.mute_button = self.ui.create_modern_button(control_buttons_frame, "Mute", lambda: self.handle_toggle_mute())
        for button in [self.start_button, self.pause_button, self.reset_button, self.break_button, self.mute_button]:
            button.pack(side='top', pady=5)

        # Session statistics
        session_stats_frame = tk.Frame(self.sidebar, bg=self.ui.colors['sidebar_bg'])
        session_stats_frame.pack(pady=10, fill='x')
        self.work_session_label = tk.Label(session_stats_frame, text=f"Work Sessions: {self.work_sessions_completed}/{self.max_work_sessions}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.work_session_label.pack(side='top')
        self.break_session_label = tk.Label(session_stats_frame, text=f"Break Sessions: {self.break_sessions_completed}/{self.max_break_sessions}", bg=self.ui.colors['sidebar_bg'], fg=self.ui.colors['text'])
        self.break_session_label.pack(side='top')

        # Add Settings Button at the bottom of the sidebar
        self.settings_button = self.ui.create_modern_button(control_buttons_frame, "Settings", self.open_settings_window, style='Modern.TButton')
        self.settings_button.pack(side='bottom', pady=10)

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

        # Frame for chat window and instructions
        self.chat_frame = tk.Frame(self.master, bg=self.ui.colors["background"])
        self.chat_frame.pack(pady=(20, 10), padx=10, fill=tk.X)  # Use fill=tk.X to keep it centered and expand horizontally

        # Instruction label for chat input
        self.chat_instruction_label = tk.Label(self.chat_frame, text="Write down up to 3 tasks and save:", bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.chat_instruction_label.pack(pady=(0, 5))

        # Chat input text box
        self.chat_input = tk.Text(self.chat_frame, height=3, width=50, bg=self.ui.colors["entry"]["field_bg"], fg=self.ui.colors["text"])
        self.chat_input.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10), expand=True, fill=tk.X)  # Expanded to fill the frame horizontally

        # Save Task button
        self.chat_submit_button = self.ui.create_modern_button(self.chat_frame, "Save Tasks", self.save_task, style='Modern.TButton')
        self.chat_submit_button.pack(side=tk.RIGHT, padx=(10, 0), pady=(0, 10))

    def set_api_key(self, api_key):
        self.api_key_manager.set_api_key(api_key)
        logger.info("API Key has been updated successfully.")
    
    def open_settings_window(self):
        SettingsWindow(self.master, self)

    def create_button(self, master, text, command, button_key, state=tk.NORMAL):
        # Retrieve button color configuration using button_key
        button_colors = self.ui.colors[button_key]
        
        # Create a unique style name for this button
        style_name = f"{button_key}.TButton"

        # Configure the style for this button
        button_style = ttk.Style()
        button_style.configure(style_name, background=button_colors['bg'], foreground=button_colors['fg'])

        # Create a button with the specific style
        button = ttk.Button(master, text=text, command=command, style=style_name)
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

    def start_break(self):
        # Stop any ongoing work session before starting the break.
        if self.running and self.is_focus_time:
            self.running = False
            self.is_focus_time = False
        
        # Now start the break.
        self.running = True
        self.remaining_time = self.short_break
        self.update_display(self.remaining_time)
        self.fetch_motivational_quote(for_break=True)
        self.progress["maximum"] = self.short_break
        self.progress["value"] = 0
        self.pomodoro_timer()
        
        # Update button states.
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.reset_button.config(state=tk.DISABLED)
        self.break_button.config(state=tk.DISABLED)

        self.update_state_indicator("break")  # Update state indicator to yellow for break time

    def play_audio(self, file_path):
        try:
            data, samplerate = sf.read(file_path, dtype='float32')
            sd.play(data, samplerate)
            sd.wait()  # Wait until the file has finished playing
            logger.info("Audio playback completed.")
        except Exception as e:
            logger.error(f"Error playing audio file: {e}")

    def fetch_motivational_quote(self, for_break=False):
        if hasattr(self, 'ai_utils'):
            try:
                message = self.ai_utils.fetch_motivational_quote(for_break)
                self.master.after(0, lambda: self.quote_var.set(message if not for_break else f"Break Idea: {message}"))
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

    def start_pomodoro(self):
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.DISABLED)
            self.break_button.config(state=tk.DISABLED)
            self.focus_dropdown.config(state="disabled")
            self.break_dropdown.config(state="disabled")
            if not self.is_resuming:
                threading.Thread(target=self.fetch_motivational_quote).start()  # Run this in a separate thread
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
        self.break_button.config(state=tk.NORMAL)
        self.update_state_indicator("paused")
        self.focus_dropdown.config(state="normal")
        self.break_dropdown.config(state="normal")
        logger.info("Timer paused.")

    def reset_pomodoro(self):
        self.running = False
        self.current_cycle = 0
        self.is_focus_time = True
        self.remaining_time = self.focus_length
        self.update_display(self.remaining_time)
        self.start_button.config(text="Start", command=self.start_pomodoro, state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        self.break_button.config(state=tk.NORMAL)
        self.focus_dropdown.config(state="normal")
        self.break_dropdown.config(state="normal")
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
            self.work_session_label.config(text=f"Work Sessions: {self.work_sessions_completed}/{self.max_work_sessions}")
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
            self.break_session_label.config(text=f"Break Sessions: {self.break_sessions_completed}/{self.max_break_sessions}")
            self.start_pomodoro()  # Start the focus session

    def update_state_indicator(self, state):
        color = self.ui.colors["state_indicator"].get(state, self.ui.colors["state_indicator"]["default"])
        self.state_indicator_canvas.itemconfig(self.state_indicator, fill=color)

    def handle_toggle_mute(self):
        self.is_muted = toggle_mute(self.is_muted, self.ui.update_mute_button_style, self.mute_button)

    def save_task(self):
        # Retrieve text from the chat input
        task_text = self.chat_input.get("1.0", tk.END).strip()
        if task_text:
            # Here you can add the code to save the task to a file or database
            print("Task saved:", task_text)  # Example action: print the task to the console

            # Clear the input field after saving
            self.chat_input.delete("1.0", tk.END)
        else:
            print("No task to save")  # Optionally handle the case where no text was entered


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Pomodoro AI")
    app = PomodoroApp(root)
    root.mainloop()
