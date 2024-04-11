import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from openai import OpenAI
import os
from dotenv import load_dotenv
import platform
import threading
import subprocess


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PomodoroApp:
    def __init__(self, master):
        self.master = master
        master.title("Pomodoro Timer")

        self.colors = {
            "background": '#2D2D2D',  # A deep gray for the background
            "text": '#F0F0F0',  # A bright gray for text, ensuring good readability
            "progress_bar": 'forest green',  
            "start_button": {
                'bg': 'forest green', 'fg': '#F0F0F0',
                'hover_bg': '#333333', 'hover_fg': '#FFFFFF',  # Dark gray for hover, white text
                'disabled_bg': '#2D2D2D', 'disabled_fg': '#A6A6A6'
            },
            "pause_button": {
                'bg': '#3E3E3E', 'fg': '#F0F0F0',
                'hover_bg': '#333333', 'hover_fg': '#FFFFFF',  # Dark gray for hover, white text
                'disabled_bg': '#2D2D2D', 'disabled_fg': '#A6A6A6'
            },
            "reset_button": {
                'bg': '#3E3E3E', 'fg': '#F0F0F0',
                'hover_bg': '#333333', 'hover_fg': '#FFFFFF',  # Dark gray for hover, white text
                'disabled_bg': '#2D2D2D', 'disabled_fg': '#A6A6A6'
            },
            "break_button": {
                'bg': '#3E3E3E', 'fg': '#F0F0F0',
                'hover_bg': '#333333', 'hover_fg': '#FFFFFF',  # Dark gray for hover, white text
                'disabled_bg': '#2D2D2D', 'disabled_fg': '#A6A6A6'
            },
            "mute_button": {
                'bg': '#3E3E3E', 'fg': '#F0F0F0',
                'hover_bg': '#333333', 'hover_fg': '#FFFFFF',  # Dark gray for hover, white text
                'disabled_bg': '#2D2D2D', 'disabled_fg': '#A6A6A6'
            },
            "state_indicator": {
                "focus": 'forest green',  # Green for focus
                "break": 'yellow',  # Blue for break
                "paused": 'goldenrod',  # Yellow for paused
                "default": 'gray'  # Light gray for default
            }
        }

        # Use the centralized background color
        master.configure(bg=self.colors["background"])

        # Set the initial size of the window
        window_width = 500
        window_height = 500

        # Get screen width and height
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()

        # Calculate position for window to be at the top center
        x = (screen_width / 2) - (window_width / 2)
        y = 0  # Set y position to 0 to position the window at the very top

        # Set the window's position
        master.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))

        # User customization
        self.user_name = "Alex"
        self.profession = "Coding Developer"
        self.company = "AGI Trader"

        # Dropdown for selecting focus time
        self.focus_options = [15, 25, 50]
        self.selected_focus_length = tk.IntVar(master)
        self.selected_focus_length.set(self.focus_options[1])

        # Initialize variables
        self.focus_length = self.selected_focus_length.get() * 60
        self.short_break = 5 * 60
        self.remaining_time = self.focus_length
        self.cycles = 4
        self.current_cycle = 0
        self.is_focus_time = True
        self.running = False
        self.is_muted = False 
        self.is_resuming = False  # Add this line

        # Progress Bar - Repositioned and resized
        self.progress = ttk.Progressbar(master, orient="horizontal", mode="determinate", maximum=self.focus_length)
        self.progress.pack(pady=(10, 20), fill=tk.X, padx=10)  # Adjust pady for padding, fill=tk.X to stretch across the window
        self.progress.config(style="green.Horizontal.TProgressbar")

        # Configure the style of the progress bar
        style = ttk.Style(master)
        style.theme_use('default')
        style.configure("green.Horizontal.TProgressbar", background=self.colors["progress_bar"], thickness=20)

        # Timer display - Make it responsive to window resizing
        self.time_var = tk.StringVar(master, value="25:00")
        self.timer_display = tk.Label(master, textvariable=self.time_var, font=("Helvetica", 48), bg=self.colors["background"], fg=self.colors["text"])
        self.timer_display.pack(expand=True)

        # Quote display
        self.quote_var = tk.StringVar(master, value="Welcome to AI Pomodoro, click start to begin!!")
        self.quote_display = tk.Label(master, textvariable=self.quote_var, font=("Helvetica", 14), wraplength=400, bg=self.colors["background"], fg=self.colors["text"])
        self.quote_display.pack()

        # Status message display
        self.status_var = tk.StringVar(master, value="")
        self.status_display = tk.Label(master, textvariable=self.status_var, font=("Helvetica", 12), bg=self.colors["background"], fg=self.colors["text"])
        self.status_display.pack()

        # Define the size of the circle
        circle_diameter = 40  # This will be the diameter of the circle

        # Calculate the canvas size to include the circle with some padding
        canvas_size = circle_diameter + 20  # Add 20 pixels of padding around the circle

        # State Indicator Canvas - Adjust the size of the canvas
        self.state_indicator_canvas = tk.Canvas(master, width=canvas_size, height=canvas_size, bg=self.colors["background"], highlightthickness=0)
        self.state_indicator_canvas.pack(pady=(10, 10))  # Add some padding around the canvas

        # Calculate the coordinates for the circle within the canvas
        circle_x0 = (canvas_size - circle_diameter) / 2
        circle_y0 = circle_x0
        circle_x1 = circle_x0 + circle_diameter
        circle_y1 = circle_y0 + circle_diameter

        # Create the circle with the new dimensions
        self.state_indicator = self.state_indicator_canvas.create_oval(circle_x0, circle_y0, circle_x1, circle_y1, fill=self.colors["state_indicator"]["default"])

        # Dropdown for selecting focus time
        self.focus_dropdown = tk.OptionMenu(master, self.selected_focus_length, *self.focus_options, command=self.update_focus_length)
        self.focus_dropdown.config(bg=self.colors["background"], fg=self.colors["text"], highlightthickness=0, font=("Helvetica", 14, "bold"), borderwidth=0)
        self.focus_dropdown["menu"].config(bg=self.colors["background"], fg=self.colors["text"], font=("Helvetica", 12))  # This changes the dropdown items
        self.focus_dropdown.pack(padx=10, pady=10)  # Add padding around the dropdown

        # Create a frame for buttons to keep them centered and at the bottom
        self.buttons_frame = tk.Frame(master, bg=self.colors["background"])
        self.buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 10))

        # Buttons with hover effects, now added to the buttons_frame
        self.start_button = self.create_button(self.buttons_frame, "Start", self.start_pomodoro, "start_button")
        self.pause_button = self.create_button(self.buttons_frame, "Pause", self.pause_pomodoro, "pause_button", state=tk.DISABLED)
        self.reset_button = self.create_button(self.buttons_frame, "Reset", self.reset_pomodoro, "reset_button", state=tk.DISABLED)
        self.break_button = self.create_button(self.buttons_frame, "Take a Break", self.start_break, "break_button", state=tk.NORMAL)
        self.mute_button = self.create_button(self.buttons_frame, "Mute", self.toggle_mute, "mute_button")

        # Adjust create_button to not pack buttons immediately, allowing for layout control here
        # Pack buttons in the buttons_frame to center them
        self.start_button.pack(side=tk.LEFT, expand=True)
        self.pause_button.pack(side=tk.LEFT, expand=True)
        self.reset_button.pack(side=tk.LEFT, expand=True)
        self.break_button.pack(side=tk.LEFT, expand=True)
        self.mute_button.pack(side=tk.LEFT, expand=True)

        # Initialize progress bar
        self.progress["maximum"] = self.focus_length
        self.progress["value"] = 0

    def create_button(self, master, text, command, button_key, state=tk.NORMAL):
        # Retrieve button color configuration using button_key
        button_colors = self.colors[button_key]
        
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

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.mute_button.config(text="Unmute", bg=self.colors["mute_button"]['bg'], fg='black')  # Lighter gray to indicate muted state
        else:
            self.mute_button.config(text="Mute", bg=self.colors["mute_button"]['bg'], fg=self.colors["mute_button"]['fg'])  # Original gray color
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
        self.reset_button.config(state=tk.NORMAL)
        self.break_button.config(state=tk.DISABLED)

        self.update_state_indicator("break")  # Update state indicator to yellow for break time

    def fetch_motivational_quote(self, for_break=False):
        print("Fetching idea...")
        try:
            if not for_break:
                prompt = (
                    f"Find a unique and original brief motivational quote from a renowned figure in the {self.profession} industry that could inspire {self.user_name}, who is about to start a work session at {self.company}. "
                    "The message should start with {self.user_name}'s name to immediately capture their attention, followed by the quote. "
                    "It should resonate with the challenges and triumphs specific to {self.profession}, encouraging perseverance, innovation, and productivity. "
                    "Conclude with a short encouragement, tailored to {self.user_name}'s journey towards success in their profession. Avoid attributing the quote directly in the message. "
                    "Please ensure each quote is unique, creative, and has not been used before. Be brief."
                    "This message will be read to the user so write it in a way that is brief and easy to read and easy for a voice assistant to read aloud, no longer than a single paragraph."
                )
            else:
                prompt = (
                    f"Compose a concise, unique and creative single-paragraph message for {self.user_name}, who has just finished a work session as a {self.profession} at {self.company}. "
                    "The message should suggest a simple 5-minute break activity that aids relaxatio, physical wellbeing, and mental rejuvenation and grounded in scientific research. "
                    "It should be brief, easy to understand, and suitable for being read aloud by a voice assistant. "
                    "The suggested activity should be beneficial for someone in {self.profession} and not be overly detailed. "
                )
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are a motivational AI assistant to a {self.profession} at {self.company} named {self.user_name}. Aim for uniqueness, creativity, humour, and scientific grounding in your messages. Your messages will be read outloud to the user to format them in a way that would be easy for an apple OS voice to say outloud. "},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4-turbo",
                temperature=0.9,  # Set the creativity/variability of the response
                max_tokens=200,  # Limit the response length
            )
            message = chat_completion.choices[0].message.content.strip()
            if for_break:
                self.quote_var.set(f"Break Idea: {message}")
            else:
                self.quote_var.set(message)
            print("Idea fetched successfully.")
            
            # Temporarily update that its speaking
            self.status_var.set("Speaking...")

            # Start a new thread to speak the quote without blocking the GUI
            speaking_thread = threading.Thread(target=self.speak_quote, args=(message,))
            speaking_thread.start()
            
        except Exception as e:
            self.quote_var.set("Failed to fetch idea. Check your internet connection.")
            print(f"Error fetching idea: {e}")

    def speak_quote(self, message):
        """Speak the quote if not muted."""
        if not self.is_muted:
            try:
                # Use the subprocess module to avoid shell interpretation issues
                command = ['say', '-v', 'Samantha', message]
                print(f"Executing command: {' '.join(command)}")
                subprocess.run(command, check=True)
            except Exception as e:
                print(f"Error executing speech command: {e}")
        # Clear the status message after the speaking action is completed.
        self.status_var.set("")  # Clears the "Speaking..." status.
        # Check if the pomodoro session is running and adjust the "Start" button accordingly.
        if not self.running:
            # Only re-enable the "Start" button if no session is active.
            self.start_button.config(text="Start", state=tk.NORMAL)
        else:
            # Keep the button disabled if a session is running.
            self.start_button.config(text="Start", state=tk.DISABLED)

    def update_display(self, remaining_time):
        mins, secs = divmod(remaining_time, 60)
        self.time_var.set(f"{mins:02d}:{secs:02d}")

    def start_pomodoro(self):
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
            self.break_button.config(state=tk.DISABLED)
            self.focus_dropdown.config(state="disabled")
            if not self.is_resuming:  # Only fetch a new quote if not resuming
                self.fetch_motivational_quote()
            self.is_resuming = False  # Reset the flag
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
        self.is_resuming = False  # Ensure a new session starts fresh
        self.progress["value"] = 0
        self.update_state_indicator("default")
        print("Timer reset.")

    def pomodoro_timer(self):
        if self.remaining_time > 0 and self.running:
            self.update_display(self.remaining_time)
            self.remaining_time -= 1
            self.progress["value"] = self.progress["maximum"] - self.remaining_time
            self.master.after(1000, self.pomodoro_timer)
        elif self.running:
            self.play_sound()
            self.switch_mode()

    def switch_mode(self):
        # Automatically switch between focus and break periods
        if self.is_focus_time:
            self.current_cycle += 1
            if self.current_cycle >= self.cycles:
                self.reset_pomodoro()
            else:
                self.is_focus_time = False
                self.remaining_time = self.short_break
                self.break_button.config(state=tk.NORMAL)
                # Ensure the button says "Start Break" when it's time for a break
                self.start_button.config(text="Start Break", command=self.start_break, state=tk.NORMAL)
        else:
            self.is_focus_time = True
            self.remaining_time = self.focus_length
            self.break_button.config(state=tk.DISABLED)
            # Change the button to say "Start" to indicate it will start a work session
            self.start_button.config(text="Start", command=self.start_pomodoro, state=tk.NORMAL)

        self.pause_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.NORMAL)
        self.pomodoro_timer()

    def play_sound(self, for_break=False):
        if platform.system() == "Windows":
            import winsound
            if for_break:
                winsound.Beep(440, 1000)  # Example frequency and duration for break
            else:
                winsound.Beep(550, 1000)  # Example frequency and duration for work
        else:  # macOS and Linux
            if for_break:
                os.system('say "Time to take a break."')
            else:
                os.system('say "Time to start a new work timer."')

    def update_state_indicator(self, state):
        color = self.colors["state_indicator"].get(state, self.colors["state_indicator"]["default"])
        self.state_indicator_canvas.itemconfig(self.state_indicator, fill=color)

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()