# testaudio.py

import numpy as np
import sounddevice as sd
import logging
import tkinter as tk
from tkinter import ttk

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_sound_device():
    try:
        sd._terminate()
        sd._initialize()
    except Exception as e:
        logger.error(f"Error initializing sound device: {e}")

def play_tone():
    initialize_sound_device()  # Ensure sound device is initialized
    fs = 44100  # Sample rate in Hz
    duration = 1  # Duration in seconds
    frequency = 110  # Frequency in Hz
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    tone = np.sin(2 * np.pi * frequency * t)

    default_device_index = sd.default.device['output']
    default_device_info = sd.query_devices(default_device_index, 'output')
    device_index = default_device_index
    max_output_channels = default_device_info['max_output_channels']

    logger.info(f"Using audio output device: {default_device_info['name']}, with {max_output_channels} channels")

    if max_output_channels > 1:
        tone = np.column_stack([tone] * max_output_channels)

    try:
        sd.play(tone, samplerate=fs, device=device_index, blocksize=512, latency='high')
        sd.wait()
        logger.info("Audio played successfully.")
    except Exception as e:
        logger.error(f"Error playing audio: {e}")

def create_gui():
    root = tk.Tk()
    root.title("Audio Test Application")

    frame = tk.Frame(root)
    frame.pack(pady=10, padx=10)

    test_button = tk.Button(frame, text="Test", command=play_tone)
    test_button.grid(row=0, column=0, padx=(0, 10))

    root.mainloop()

if __name__ == "__main__":
    create_gui()