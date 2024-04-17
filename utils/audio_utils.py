# audio_utils.py
import os
import platform

def play_sound(for_break=False):
    """Plays a sound indicating the end of a work or break period based on the OS."""
    if platform.system() == "Windows":
        import winsound
        if for_break:
            winsound.Beep(440, 1000)  # Example frequency and duration for break
        else:
            winsound.Beep(550, 1000)  # Example frequency and duration for work
    else:  # macOS and Linux
        if for_break:
            os.system('say -v Tessa "Break time."')
        else:
            os.system('say -v Tessa "Focus time."')

def toggle_mute(is_muted, update_button_style, mute_button):
    is_muted = not is_muted
    update_button_style(is_muted)
    if is_muted:
        mute_button.config(text="Unmute")
    else:
        mute_button.config(text="Mute")
    print("Muted" if is_muted else "Unmuted")
    return is_muted  # Return the new state

