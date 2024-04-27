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

def play_tone(device_combobox):
    initialize_sound_device()  # Ensure sound device is initialized
    fs = 44100  # Sample rate in Hz
    duration = 1  # Duration in seconds
    frequency = 110  # Frequency in Hz
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    tone = np.sin(2 * np.pi * frequency * t)

    selected_device_name = device_combobox.get()
    devices = sd.query_devices()
    default_device_index = sd.default.device['output']
    default_device_info = sd.query_devices(default_device_index, 'output')

    # Check if the selected device is still the default device
    if selected_device_name != default_device_info['name']:
        logger.info(f"Default audio device has changed to {default_device_info['name']}. Updating selection.")
        device_combobox.set(default_device_info['name'])
        selected_device_name = default_device_info['name']

    device_candidates = [device for device in devices if device['name'] == selected_device_name and device['max_output_channels'] > 0]

    if not device_candidates:
        logger.error(f"Selected device '{selected_device_name}' not found or has no output channels. Using default device.")
        device_index = default_device_index
        max_output_channels = default_device_info['max_output_channels']
    else:
        device_info = max(device_candidates, key=lambda x: x['max_output_channels'])
        device_index = device_info['index']
        max_output_channels = device_info['max_output_channels']

    logger.info(f"Using audio output device: {selected_device_name}, with {max_output_channels} channels")

    if max_output_channels > 1:
        tone = np.column_stack([tone] * max_output_channels)

    try:
        sd.play(tone, samplerate=fs, device=device_index, blocksize=512, latency='high')
        sd.wait()
        logger.info("Audio played successfully.")
    except Exception as e:
        logger.error(f"Error playing audio: {e}")

def refresh_device_list(device_combobox):
    initialize_sound_device()  # Ensure sound device is initialized
    devices = sd.query_devices()
    unique_devices = {}
    for device in devices:
        if device['max_output_channels'] > 0:
            if device['name'] in unique_devices:
                if device['max_output_channels'] > unique_devices[device['name']]['max_output_channels']:
                    unique_devices[device['name']] = device
            else:
                unique_devices[device['name']] = device

    device_combobox['values'] = list(unique_devices.keys())
    default_device_index = sd.default.device['output']
    default_device_info = sd.query_devices(default_device_index, 'output')
    device_combobox.set(default_device_info['name'])
    logger.info("Device list refreshed.")
    for device in unique_devices.values():
        logger.info(f"Device: {device['name']}, Channels: {device['max_output_channels']}")


def create_gui():
    root = tk.Tk()
    root.title("Audio Test Application")

    frame = tk.Frame(root)
    frame.pack(pady=10, padx=10)

    device_combobox = ttk.Combobox(frame, state="readonly", width=50)
    refresh_device_list(device_combobox)
    device_combobox.grid(row=0, column=0, padx=(0, 10))

    refresh_button = tk.Button(frame, text="Refresh", command=lambda: refresh_device_list(device_combobox))
    refresh_button.grid(row=0, column=1, padx=(0, 10))

    test_button = tk.Button(frame, text="Test", command=lambda: play_tone(device_combobox))
    test_button.grid(row=0, column=2)

    root.mainloop()

if __name__ == "__main__":
    create_gui()