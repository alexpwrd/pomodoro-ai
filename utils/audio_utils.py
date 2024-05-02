# audio_utils.py
import os
import platform

def play_sound(for_break=False):
    """Indicates the end of a work or break period based on the OS."""
    if platform.system() == "Windows":
        # Removed beep sound for Windows
        print("Break time." if for_break else "Focus time.")
    else:  # macOS and Linux
        # Removed voice commands for macOS and Linux
        print("Break time." if for_break else "Focus time.")

def toggle_mute(is_muted, update_button_style, mute_button):
    is_muted = not is_muted
    update_button_style(is_muted)
    if is_muted:
        mute_button.config(text="Unmute")
    else:
        mute_button.config(text="Mute")
    print("Muted" if is_muted else "Unmuted")
    return is_muted  # Return the new state

