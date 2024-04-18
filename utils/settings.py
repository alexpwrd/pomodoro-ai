import tkinter as tk
from tkinter import ttk, simpledialog
from pathlib import Path
from cryptography.fernet import Fernet
import logging
from utils.ui import UIConfig
import json

logger = logging.getLogger(__name__)

class APIKeyManager:
    def __init__(self, key_path="api_key.key", api_key_file='encrypted_api_key.bin'):
        self.key_path = Path(key_path)
        self.api_key_file = Path(api_key_file)  # Initialize the api_key_file attribute here
        if not self.key_path.exists():
            self.initialize_key()
        self.cipher = Fernet(self.load_key())

    def api_key_exists(self):
        # Check if the encrypted API key file exists
        return self.api_key_file.exists()

    def initialize_key(self):
        # Generate and save a new encryption key
        key = Fernet.generate_key()
        with self.key_path.open('wb') as key_file:
            key_file.write(key)

    def load_key(self):
        return self.key_path.read_bytes()

    def set_api_key(self, api_key):
        try:
            encrypted_api_key = self.cipher.encrypt(api_key.encode())
            with self.api_key_file.open('wb') as key_file:
                key_file.write(encrypted_api_key)
            logger.info("API key updated successfully.")
        except Exception as e:
            logger.error(f"Failed to update API key: {e}")
            return False
        return True

    def get_api_key(self):
        try:
            with self.api_key_file.open('rb') as key_file:
                encrypted_api_key = key_file.read()
            return self.cipher.decrypt(encrypted_api_key).decode()
        except FileNotFoundError:
            logger.error("API key file not found.")
            return None
        except InvalidToken:
            logger.error("Failed to decrypt API key. The key file might be corrupted.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error accessing the API key: {e}")
            return None
        
class SettingsManager:
    def __init__(self, settings_file='settings.json', callback=None):
        self.settings_file = Path(settings_file)
        self.settings = {}  # Initialize as an empty dictionary
        self.load_settings()  # Load settings immediately upon initialization
        self.callback = callback

    def settings_exist(self):
        return self.settings_file.exists()

    def create_default_settings(self):
        # Set the default settings and save them to the file
        self.settings = self.default_settings()
        self.save_settings()

    def load_settings(self):
        if not self.settings_file.exists():
            logger.info("Settings file not found, creating default settings.")
            self.create_default_settings()
        try:
            with self.settings_file.open('r') as file:
                self.settings = json.load(file)
                logger.info("Settings loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load settings, reverting to defaults: {e}")
            self.create_default_settings()

    def validate_settings(self):
        valid_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        if self.settings['AI_VOICE'] not in valid_voices:
            logger.error(f"Invalid AI_VOICE setting: {self.settings['AI_VOICE']}")
            return False
        return True

    def save_settings(self, callback=None):
        if not self.validate_settings():
            logger.error("Settings validation failed. Aborting save.")
            return False
        try:
            with self.settings_file.open('w') as file:
                json.dump(self.settings, file, indent=4)
                logger.info("Settings saved successfully.")
            if callback:
                callback()  # Execute the callback function if provided
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get_setting(self, key, default=None):
        if self.settings is None:
            logger.error("Settings not loaded or initialized correctly.")
            return default
        return self.settings.get(key, default)

    def update_setting(self, key, value):
        """Update a single setting in the in-memory settings dictionary."""
        self.settings[key] = value

    def default_settings(self):
        return {
            "USER_NAME": "Default User",
            "PROFESSION": "Default Profession",
            "AI_VOICE": "alloy"
        }


class SettingsWindow:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        self.ui = app.ui  # Assume UIConfig is initialized in the main app class
        self.window = tk.Toplevel(master)
        self.create_widgets()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        frame = ttk.Frame(self.window, style="TFrame")
        frame.pack(padx=40, pady=40)

        settings = {
            "User Name": "USER_NAME",
            "Profession": "PROFESSION",
            "AI Voice": "AI_VOICE",
            "OpenAI API Key": "api_key"
        }
        self.entries = {}

        for i, (label, setting_key) in enumerate(settings.items()):
            label_widget = self.ui.create_label(frame, text=f"{label}:")
            label_widget.grid(row=i, column=0, padx=10, pady=10)
            current_value = self.app.settings_manager.get_setting(setting_key, "")

            if setting_key == "api_key":
                entry_widget = self.ui.create_entry(frame)
                if self.app.api_key_manager.api_key_exists():
                    entry_widget.insert(0, "**********************")
                else:
                    entry_widget.insert(0, current_value)
                entry_widget.bind("<FocusIn>", lambda event, e=entry_widget: e.delete(0, tk.END) if e.get() == "**********************" else None)
                entry_widget.bind("<FocusOut>", lambda event, e=entry_widget: e.insert(0, "**********************") if not e.get() else None)
                entry_widget.grid(row=i, column=1, padx=10, pady=10)
                self.entries[setting_key] = entry_widget
            elif setting_key == "AI_VOICE":
                voice_combobox = ttk.Combobox(frame, values=["alloy", "echo", "fable", "onyx", "nova", "shimmer"], state="readonly", style="TCombobox")
                voice_combobox.set(current_value)
                voice_combobox.grid(row=i, column=1, padx=10, pady=10)
                self.entries[setting_key] = voice_combobox
            else:
                entry_widget = self.ui.create_entry(frame)
                entry_widget.insert(0, current_value)
                entry_widget.grid(row=i, column=1, padx=10, pady=10)
                self.entries[setting_key] = entry_widget

        save_button = self.ui.create_modern_button(frame, text="Save", command=self.apply_and_save_settings)
        save_button.grid(row=len(settings), column=0, columnspan=2, pady=20)

    def on_close(self):
        # Handle any necessary cleanup or final actions
        logger.info("Closing settings window.")
        self.window.destroy()  # Ensure the window is properly closed

    def apply_and_save_settings(self):
        placeholder = "**********************"
        for key, entry in self.entries.items():
            value = entry.get()
            if key == "api_key":
                # Skip updating the API key if the placeholder text is present
                if value != placeholder and value:  # Ensure the field is not empty or just the placeholder
                    self.app.api_key_manager.set_api_key(value)
            else:
                self.app.settings_manager.update_setting(key, value)

        # Pass the reinitialize_ai_utils method as a callback
        success = self.app.settings_manager.save_settings(callback=self.app.reinitialize_ai_utils)
        if success:
            logger.info("Settings saved successfully.")
        else:
            logger.error("Failed to save settings (apply_and_save_settings)")

        self.window.destroy()  # Close the settings window regardless of the result