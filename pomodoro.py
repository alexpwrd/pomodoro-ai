import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from openai import OpenAI
import os
from dotenv import load_dotenv
import platform
import threading

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PomodoroApp:
    def __init__(self, master):
        self.master = master
        master.title("Pomodoro Timer")

        # Timer display
        self.time_var = tk.StringVar(master, value="25:00")
        self.timer_display = tk.Label(master, textvariable=self.time_var, font=("Helvetica", 48))
        self.timer_display.pack()

        # Quote display
        self.quote_var = tk.StringVar(master, value="Get ready to be motivated!")
        self.quote_display = tk.Label(master, textvariable=self.quote_var, font=("Helvetica", 14), wraplength=400)
        self.quote_display.pack()

        # Progress Bar
        self.progress = ttk.Progressbar(master, orient="horizontal", length=300, mode="determinate")
        self.progress.pack()

        # Dropdown for selecting focus time
        self.focus_options = [15, 25, 50]  # in minutes
        self.selected_focus_length = tk.IntVar(master)
        self.selected_focus_length.set(self.focus_options[1])  # default to 25 minutes
        self.focus_dropdown = tk.OptionMenu(master, self.selected_focus_length, *self.focus_options, command=self.update_focus_length)
        self.focus_dropdown.pack()

        # Buttons
        self.start_button = tk.Button(master, text="Start", command=self.start_pomodoro)
        self.start_button.pack()
        self.pause_button = tk.Button(master, text="Pause", command=self.pause_pomodoro, state=tk.DISABLED)
        self.pause_button.pack()
        self.reset_button = tk.Button(master, text="Reset", command=self.reset_pomodoro, state=tk.DISABLED)
        self.reset_button.pack()
        self.break_button = tk.Button(master, text="Take a Break", command=self.start_break)
        self.break_button.pack()

        # Initialize variables
        self.focus_length = self.selected_focus_length.get() * 60  # Convert minutes to seconds
        self.short_break = 5 * 60  # 5 minutes
        self.remaining_time = self.focus_length
        self.cycles = 4
        self.current_cycle = 0
        self.is_focus_time = True
        self.running = False

        # Initialize progress bar
        self.progress["maximum"] = self.focus_length
        self.progress["value"] = 0

    def update_focus_length(self, *args):
        self.focus_length = self.selected_focus_length.get() * 60  # Convert minutes to seconds
        self.progress["maximum"] = self.focus_length
        if not self.running:
            self.remaining_time = self.focus_length
            self.update_display(self.remaining_time)
            self.progress["value"] = 0

    def start_break(self):
        self.running = True
        self.remaining_time = self.short_break  # 5 minutes
        self.update_display(self.remaining_time)
        self.fetch_motivational_quote(for_break=True)
        self.progress["maximum"] = self.short_break
        self.progress["value"] = 0
        self.pomodoro_timer()

    def fetch_motivational_quote(self, for_break=False):
        print("Fetching idea...")
        try:
            if not for_break:
                prompt = 'Give me one brief motivational quote for a coding project, use inspirational builders and coders throughout time to encourage Alex to succeed. Start your message with, "Alex... before we start remember: "Quote", do not include who said the quote, end the message appropriately given the context."'
            else:
                prompt = "Alex just did a pomodory 15 or 25 minute coding session. Now its time to take a 5 minute break. Suggest one activity to Alex for a 5-minute break after coding for a block of time based on self improvement or scientific research. Start by quickly acknowledging the hard work Alex has done, then suggest a relaxing activity. Address the user by Name, Alex, and be brief."
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant to a coder named Alex."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4-turbo",
            )
            message = chat_completion.choices[0].message.content.strip()
            if for_break:
                self.quote_var.set(f"Break Idea: {message}")
            else:
                self.quote_var.set(message)
            print("Idea fetched successfully.")
            
            # Temporarily update a label or button to indicate speaking
            self.start_button.config(text="Speaking...", state=tk.DISABLED)
            
            # Start a new thread to speak the quote without blocking the GUI
            speaking_thread = threading.Thread(target=self.speak_quote, args=(message,))
            speaking_thread.start()
            
        except Exception as e:
            self.quote_var.set("Failed to fetch idea. Check your internet connection.")
            print(f"Error fetching idea: {e}")

    def speak_quote(self, message):
        # Use macOS's say command to read the quote aloud
        os.system(f'say -v Samantha "{message}"')
        # Reset the button text back to normal after speaking
        self.start_button.config(text="Start", state=tk.NORMAL)

    def update_display(self, remaining_time):
        mins, secs = divmod(remaining_time, 60)
        self.time_var.set(f"{mins:02d}:{secs:02d}")

    def start_pomodoro(self):
        if not self.running:
            self.running = True
            self.pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
            self.fetch_motivational_quote()  # Fetch a new quote each time the timer is started
            print("Pomodoro started.")
            self.progress["maximum"] = self.focus_length
            self.progress["value"] = 0
            self.pomodoro_timer()

    def pause_pomodoro(self):
        self.running = False
        self.start_button.config(text="Resume", command=self.start_pomodoro)
        self.pause_button.config(state=tk.DISABLED)
        print("Pomodoro paused.")

    def reset_pomodoro(self):
        self.running = False
        self.current_cycle = 0
        self.is_focus_time = True
        self.remaining_time = self.focus_length
        self.update_display(self.remaining_time)
        self.start_button.config(text="Start", command=self.start_pomodoro)
        self.pause_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        print("Pomodoro reset.")
        self.progress["value"] = 0

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
        if self.is_focus_time:
            self.current_cycle += 1
            if self.current_cycle >= self.cycles:
                messagebox.showinfo("Pomodoro Finished", "All cycles complete! Great job.")
                self.reset_pomodoro()
            else:
                self.is_focus_time = False
                messagebox.showinfo("Break Time", "Time for a short break! Relax a bit.")
                self.remaining_time = self.short_break
                self.play_sound(for_break=True)  # Play break time sound
                self.pomodoro_timer()
        else:
            self.is_focus_time = True
            if self.current_cycle < self.cycles:
                messagebox.showinfo("Focus Time", "Back to work! Stay focused.")
            self.remaining_time = self.focus_length
            self.play_sound(for_break=False)  # Play work time sound
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
                os.system('say "Time to start a new work timer."')
            else:
                os.system('say "Time to take a break."')

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()