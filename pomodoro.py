# pomodoro.py is the main file that runs the pomodoro application

import os
import platform
import threading
import warnings
import random
from pathlib import Path

import sounddevice as sd
import soundfile as sf
import tkinter as tk
from dotenv import load_dotenv
from openai import OpenAI
from tkinter import ttk
from ui import UIConfig

# Ignore DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PomodoroApp:
    def __init__(self, master):
        self.master = master
        master.title("Pomodoro AI")

        # Initialize UIConfig and use its colors
        self.ui = UIConfig()
        master.configure(bg=self.ui.colors["background"])  # Use background color from UIConfig

        # Set the initial size of the window
        window_width = 600
        window_height = 600

        # Get screen width and height
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()

        # Calculate position for window to be at the top center
        x = (screen_width / 2) - (window_width / 2)
        y = 0  # Set y position to 0 to position the window at the very top

        # Set the window's position
        master.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))

        self.speech_file_path = Path(__file__).parent / "quote.mp3"

        # User customization
        self.user_name = os.getenv("USER_NAME", "Generic User")
        self.profession = os.getenv("PROFESSION", "Generic Profession")
        self.company = os.getenv("COMPANY", "Self Employed")

        # Initialize counters and limits for work and break sessions
        self.work_sessions_completed = 0
        self.break_sessions_completed = 0
        self.max_work_sessions = 4  # Maximum work sessions per cycle
        self.max_break_sessions = 4  # Maximum break sessions per cycle

        # Dropdown for selecting focus time
        self.focus_options = [1, 15, 25, 50, 90]
        self.selected_focus_length = tk.IntVar(master)
        self.selected_focus_length.set(self.focus_options[1])

        # Break time options
        self.break_options = [1, 5, 10, 15]  # Break times in minutes
        self.selected_break_length = tk.IntVar(master)
        self.selected_break_length.set(self.break_options[1])  # Default to 5 minutes

        # Initialize variables
        self.focus_length = self.selected_focus_length.get() * 60
        self.short_break = self.selected_break_length.get() * 60  # Convert minutes to seconds
        self.remaining_time = self.focus_length
        self.cycles = 4
        self.total_session_limit = 8  # Define the total session limit here
        self.current_cycle = 0
        self.is_focus_time = True
        self.running = False
        self.is_muted = False 
        self.is_resuming = False 

        # Progress Bar - Repositioned and resized
        self.progress = ttk.Progressbar(master, orient="horizontal", mode="determinate", maximum=self.focus_length)
        self.progress.pack(pady=(10, 20), fill=tk.X, padx=10)  # Adjust pady for padding, fill=tk.X to stretch across the window
        self.progress.config(style="green.Horizontal.TProgressbar")

        # Timer display - Make it responsive to window resizing
        self.time_var = tk.StringVar(master, value="15:00")
        self.timer_display = tk.Label(master, textvariable=self.time_var, font=("Helvetica", 48), bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.timer_display.pack(expand=True)

        # Quote display
        self.quote_var = tk.StringVar(master, value="Welcome to AI Pomodoro, click start to begin!!")
        self.quote_display = tk.Label(master, textvariable=self.quote_var, font=("Helvetica", 14), wraplength=400, bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.quote_display.pack()

        # Status message display
        self.status_var = tk.StringVar(master, value="")
        self.status_display = tk.Label(master, textvariable=self.status_var, font=("Helvetica", 12), bg=self.ui.colors["background"], fg=self.ui.colors["text"])
        self.status_display.pack()

        # Define the size of the circle
        circle_diameter = 40  # This will be the diameter of the circle

        # Calculate the canvas size to include the circle with some padding
        canvas_size = circle_diameter + 20  # Add 20 pixels of padding around the circle

        # State Indicator Canvas - Adjust the size of the canvas
        self.state_indicator_canvas = tk.Canvas(master, width=canvas_size, height=canvas_size, bg=self.ui.colors["background"], highlightthickness=0)
        self.state_indicator_canvas.pack(pady=(10, 10))  # Add some padding around the canvas

        # Calculate the coordinates for the circle within the canvas
        circle_x0 = (canvas_size - circle_diameter) / 2
        circle_y0 = circle_x0
        circle_x1 = circle_x0 + circle_diameter
        circle_y1 = circle_y0 + circle_diameter

        # Create the circle with the new dimensions
        self.state_indicator = self.state_indicator_canvas.create_oval(circle_x0, circle_y0, circle_x1, circle_y1, fill=self.ui.colors["state_indicator"]["default"])

        # Frame for focus time selection
        focus_frame = tk.Frame(master, bg=self.ui.colors["background"])
        focus_frame.pack(pady=(10, 0))  # This will center the frame in the packing order
        focus_label = self.ui.create_label(focus_frame, "Focus Time (min):")
        focus_label.pack(side=tk.LEFT, padx=(0, 10))
        self.focus_dropdown = self.ui.create_option_menu(focus_frame, self.selected_focus_length, self.focus_options, self.update_focus_length)
        self.focus_dropdown.pack(side=tk.LEFT)

        # Frame for break time selection
        break_frame = tk.Frame(master, bg=self.ui.colors["background"])
        break_frame.pack(pady=(10, 0))  # This will center the frame in the packing order
        break_label = self.ui.create_label(break_frame, "Break Time (min):")
        break_label.pack(side=tk.LEFT, padx=(0, 10))
        self.break_dropdown = self.ui.create_option_menu(break_frame, self.selected_break_length, self.break_options, self.update_break_length)
        self.break_dropdown.pack(side=tk.LEFT)

        # Updated labels to display session counters with limits
        self.work_session_label = self.ui.create_label(self.master, f"Work Sessions: {self.work_sessions_completed}/{self.max_work_sessions}")
        self.break_session_label = self.ui.create_label(self.master, f"Break Sessions: {self.break_sessions_completed}/{self.max_break_sessions}")

        # Adjust label packing
        self.work_session_label.pack(side=tk.TOP, pady=(0, 5))
        self.break_session_label.pack(side=tk.TOP, pady=(0, 10))

        # Create a frame for buttons to keep them centered at the bottom
        self.buttons_frame_outer = tk.Frame(master, bg=self.ui.colors["background"])
        self.buttons_frame_outer.pack(side=tk.BOTTOM, fill=tk.X, expand=True)  # This frame expands

        # Create another inner frame that will actually hold the buttons
        self.buttons_frame = tk.Frame(self.buttons_frame_outer, bg=self.ui.colors["background"])
        self.buttons_frame.pack(pady=10)  # Center this frame within the outer frame

        # In the __init__ method where buttons are being created
        self.start_button = self.ui.create_modern_button(self.buttons_frame, "Start", self.start_pomodoro)
        self.pause_button = self.ui.create_modern_button(self.buttons_frame, "Pause", self.pause_pomodoro, state=tk.DISABLED)
        self.reset_button = self.ui.create_modern_button(self.buttons_frame, "Reset", self.reset_pomodoro, state=tk.DISABLED)
        self.break_button = self.ui.create_modern_button(self.buttons_frame, "Take a Break", self.start_break)
        self.mute_button = self.ui.create_modern_button(self.buttons_frame, "Mute", self.toggle_mute)

        # Adjust button packing to center them within the inner frame
        self.start_button.pack(side=tk.LEFT, padx=5, expand=False)
        self.pause_button.pack(side=tk.LEFT, padx=5, expand=False)
        self.reset_button.pack(side=tk.LEFT, padx=5, expand=False)
        self.break_button.pack(side=tk.LEFT, padx=5, expand=False)
        self.mute_button.pack(side=tk.LEFT, padx=5, expand=False)

        # Initialize progress bar
        self.progress["maximum"] = self.focus_length
        self.progress["value"] = 0

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

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        # Update the button style using the new method from UIConfig
        self.ui.update_mute_button_style(self.is_muted)
        if self.is_muted:
            self.mute_button.config(text="Unmute")
        else:
            self.mute_button.config(text="Mute")
        print("Muted" if self.is_muted else "Unmuted")

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
            print("Work session paused for a break.")
        
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

    import random

    def fetch_motivational_quote(self, for_break=False):
        print("Fetching idea...")
        try:
            themes = [
                "perseverance",  # Emphasizes the importance of persistence and resilience in achieving goals.
                "efficiency",  # Focuses on optimizing processes and maximizing output with minimal wasted effort.
                "teamwork",  # Highlights the benefits of collaborative work and mutual support.
                "leadership",  # Stresses the role of guiding and inspiring others.
                "learning",  # Encourages continual growth and acquisition of new skills.
                "growth",  # Focuses on personal and professional development.
                "adaptability",  # Emphasizes flexibility and the ability to adjust to new conditions.
                "focus",  # Concentrates on the ability to maintain attention and avoid distractions.
                "productivity",  # Relates to maximizing output and effectiveness in work tasks.
                "balance",  # Stresses the importance of maintaining a healthy work-life balance.
                "well-being",  # Focuses on overall mental and physical health.
                "mental clarity",  # Highlights the importance of clear thinking and decision-making.
                "optimism",  # Encourages a positive outlook and expectation of good outcomes.
                "resilience",  # Focuses on the ability to recover quickly from difficulties.
                "innovation",  # Stresses creativity and the introduction of new ideas.
                "success",  # General theme celebrating achievements and accomplishments.
                "energy",  # Discusses maintaining high levels of enthusiasm and vigor.
                "motivation",  # Encourages finding reasons and incentives to perform well.
                "happiness",  # Focuses on achieving a state of well-being and contentment.
                "do what you love"  # Encourages passion-driven work and finding joy in professional activities.
            ]
            theme = random.choice(themes)
            print(f"Selected theme: {theme}")

            if not for_break:
                prompt = (
                    f"Generate a motivational quote related to {theme} from a successful individual in the {self.profession} industry. This quote should inspire {self.user_name}, who is about to start a work session at {self.company}. "
                    f"Begin the message with {self.user_name}'s name to grab their attention immediately. Follow with the quote and conclude with a brief, encouraging statement that incorporates humor and irony. "
                    f"Design this message to be concise, engaging, and easily readable aloud by a voice assistant. The entire message should be a single, impactful paragraph that subtly blends humor/irony with motivation ,without directly attributing the quote to a specific person."
                )
            else:
                activities = [
                    "deep breathing",  # A quick way to relax and reduce stress
                    "quick stretches",  # Helps relieve muscle tension and improve circulation
                    "a short walk",  # Boosts mood and energy
                    "listening to music",  # Reduces stress and improves mood
                    "drinking a glass of water",  # Keeps you hydrated and refreshes your mind
                    "doing a few yoga poses",  # Enhances flexibility and mental clarity
                    "meditating for a few minutes",  # Improves focus and reduces anxiety
                    "doodling or sketching",  # Stimulates creativity and relaxation
                    "reading a page of a book",  # A brief escape that relaxes the mind
                    "enjoying a healthy snack",  # Provides energy and stabilizes blood sugar levels
                    "stepping outside for fresh air",  # Refreshes and reinvigorates
                    "practicing a quick mindfulness exercise",  # Helps center thoughts and reduce stress
                    "performing a brief body scan meditation",  # Increases bodily awareness and relaxes
                    "writing down three things you're grateful for"  # Boosts positivity and mental well-being
                ]
                activity = random.choice(activities)
                print(f"Selected theme: {activity}") 
                prompt = (
                    f"Compose a concise, unique, and creative short message for {self.user_name}, who has just finished a work session as a {self.profession} at {self.company}. "
                    f"Suggest a simple 5 or 10 minute break activity like {activity}. "
                    f"Keep the suggestion brief, easy to understand, and suitable for being read aloud by a voice assistant. "
                    f"Focus on activities that are scientifically proven to reduce stress and enhance focus. "
                    f"Add a touch of humor or irony to lighten the mood—because even serious break activities can have a fun side."
                )

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are a motivational AI assistant to a {self.profession} at {self.company} named {self.user_name}. Aim for uniqueness, creativity, humour, and scientific grounding in your messages. Your messages will be read out loud to the user to format them in a way that would be easy for an apple OS voice to say out loud. "},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4-turbo",
                temperature=0.8,  # Set the creativity/variability of the response
                max_tokens=200,  # Limit the response length
            )
            message = chat_completion.choices[0].message.content.strip()
            if for_break:
                self.quote_var.set(f"Break Idea: {message}")
            else:
                self.quote_var.set(message)
            print("Idea fetched successfully.")
            
            # Temporarily update that it's speaking
            self.status_var.set("Speaking...")

            # Start a new thread to speak the quote without blocking the GUI
            speaking_thread = threading.Thread(target=self.speak_quote, args=(message,))
            speaking_thread.start()
            
        except Exception as e:
            self.quote_var.set("Failed to fetch idea. Check your internet connection.")
            print(f"Error fetching idea: {e}")

    def text_to_speech(self, text):
        """Converts text to speech and saves as an MP3 file using the user's preferred voice."""
        # Fetch the user's preferred voice setting from environment variables with 'onyx' as the default
        user_voice = os.getenv("USER_VOICE", "onyx")
        
        # Define valid voice options for error checking
        valid_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        
        # Check if the provided voice setting is valid
        if user_voice not in valid_voices:
            print(f"Invalid voice setting '{user_voice}'. Using default 'onyx'.")
            user_voice = "onyx"

        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice=user_voice,
                input=text,
                response_format="opus"
            )
            response.stream_to_file(self.speech_file_path)
            self.play_audio(self.speech_file_path)
        except Exception as e:
            print(f"Error in text-to-speech conversion: {e}")


    def play_audio(self, file_path):
        try:
            data, samplerate = sf.read(file_path, dtype='float32')
            sd.play(data, samplerate)
            sd.wait()  # Wait until the file has finished playing
        except Exception as e:
            print(f"Error playing audio file: {e}")


    def speak_quote(self, message):
        """Modified to use text_to_speech if not muted."""
        if not self.is_muted:
            self.text_to_speech(message)
        # Clears the "Speaking..." status and adjusts button states.
        self.status_var.set("")

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
            print("Pomodoro started.")

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
        print("Timer paused.")

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
        print("Timer reset.")

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
            self.play_sound(for_break=True)
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
            self.play_sound(for_break=False)
            self.break_sessions_completed += 1
            if self.break_sessions_completed >= self.max_break_sessions:
                self.reset_pomodoro()  # Reset if maximum break sessions are reached
                return
            self.is_focus_time = True
            self.remaining_time = self.focus_length
            self.update_state_indicator("focus")
            self.break_session_label.config(text=f"Break Sessions: {self.break_sessions_completed}/{self.max_break_sessions}")
            self.start_pomodoro()  # Start the focus session

    def play_sound(self, for_break=False):
        if platform.system() == "Windows":
            import winsound
            if for_break:
                winsound.Beep(440, 1000)  # Example frequency and duration for break
            else:
                winsound.Beep(550, 1000)  # Example frequency and duration for work
        else:  # macOS and Linux
            if for_break:
                os.system('say "Break time."')
            else:
                os.system('say "Focus time."')

    def update_state_indicator(self, state):
        color = self.ui.colors["state_indicator"].get(state, self.ui.colors["state_indicator"]["default"])
        self.state_indicator_canvas.itemconfig(self.state_indicator, fill=color)

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()
