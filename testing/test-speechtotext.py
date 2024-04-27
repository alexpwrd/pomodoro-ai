import os
import tkinter as tk
from tkinter import messagebox
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
import threading
from dotenv import load_dotenv
import logging
import numpy as np
import webrtcvad

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize OpenAI client with API key
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# Define the path to the audiofiles directory
audiofiles_dir = os.path.join(os.path.dirname(__file__), 'audiofiles')


# Global variable to store conversation history
conversation_history = [
    {"role": "system", "content": "You are a helpful voice assistant, your response will be read aloud so write it in a way that can be read by a text to speech model. Be extremely brief and friendly in your response with a touch of humor and irony. "}
]

# Create the directory if it does not exist
if not os.path.exists(audiofiles_dir):
    os.makedirs(audiofiles_dir)

def list_audio_devices():
    devices = sd.query_devices()
    logging.info(f"Available audio devices: {devices}")
    print(devices)

def record_audio_vad(filename="output.wav", fs=48000, vad_mode=3, frame_duration=30, silence_duration=1000):
    # Include the directory in the filename path
    filename = os.path.join(audiofiles_dir, filename)
    logging.info("Starting recording with VAD...")
    vad = webrtcvad.Vad(vad_mode)
    device_info = sd.query_devices(kind='input')
    logging.debug(f"Device Info: {device_info}")
    max_channels = device_info['max_input_channels']
    if max_channels < 1:
        logging.error("Default device does not support the required number of channels.")
        raise ValueError("Default device does not support the required number of channels.")
    
    try:
        with sd.InputStream(samplerate=fs, channels=1, dtype='int16') as stream:
            audio_data = []
            silent_frames = 0
            num_silent_frames_to_stop = int(silence_duration / frame_duration)
            while True:
                frame, overflowed = stream.read(int(fs * frame_duration / 1000))
                logging.debug(f"Read frame: {frame}")
                is_speech = vad.is_speech(frame.tobytes(), fs)
                logging.debug(f"Is speech: {is_speech}")
                if is_speech:
                    audio_data.extend(frame)
                    silent_frames = 0
                else:
                    silent_frames += 1
                if silent_frames > num_silent_frames_to_stop:
                    break
        sf.write(filename, np.array(audio_data), fs)
        # Calculate and log the duration of the recorded audio
        duration_seconds = len(audio_data) / fs
        logging.info(f"Recording stopped and saved to file. Duration: {duration_seconds:.2f} seconds.")
    except Exception as e:
        logging.error(f"Error during recording: {e}")

def transcribe_audio(filename="output.wav"):
    # Include the directory in the filename path
    filename = os.path.join(audiofiles_dir, filename)
    """Use OpenAI's Whisper model to transcribe audio."""
    try:
        with open(filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        logging.info(f"Transcription result: {transcription.text}")
        return transcription.text
    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        return ""

def generate_response(text):
    """Generate a response using GPT-4 Turbo based on the transcribed text, including prior conversation history."""
    global conversation_history
    try:
        # Append the new user message to the conversation history
        conversation_history.append({"role": "user", "content": text})
        
        # Generate the response using the accumulated conversation history
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation_history
        )
        
        # Extract the generated response and append it to the conversation history
        generated_response = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": generated_response})
        
        logging.info(f"Generated response: {generated_response}")
        return generated_response
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        return ""

def text_to_speech(text):
    """Converts text to speech and saves as an audio file using the user's preferred voice."""
    user_voice = "onyx"  # Example voice, adjust as needed
    valid_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
    if user_voice not in valid_voices:
        logging.warning(f"Invalid voice setting '{user_voice}'. Using default 'onyx'.")
        user_voice = "onyx"
    # Define the path for the speech output file within the audiofiles directory
    speech_file_path = os.path.join(audiofiles_dir, 'speech_output.opus')
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=user_voice,
            input=text,
            response_format="opus"
        )
        response.stream_to_file(speech_file_path)
        logging.info(f"Text to speech conversion successful, saved to {speech_file_path}")
        play_audio(speech_file_path)
    except Exception as e:
        logging.error(f"Error in text-to-speech conversion: {e}")

def play_audio(file_path):
    """Plays the specified audio file."""
    try:
        data, fs = sf.read(file_path, dtype='float32')
        sd.play(data, samplerate=fs)
        sd.wait()
        logging.info("Audio playback completed.")
    except Exception as e:
        logging.error(f"Error playing audio file: {e}")

def handle_record():
    """Handle the recording and processing pipeline using VAD, including managing conversation history."""
    global conversation_history
    filename = os.path.join(audiofiles_dir, "output.wav")
    try:
        record_audio_vad(filename)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            text = transcribe_audio(filename)
            if text:
                response = generate_response(text)
                text_to_speech(response)
            else:
                logging.error("Failed to transcribe audio.")
                conversation_history = []  # Reset conversation history if transcription fails
        else:
            logging.error("Recording failed or produced an empty file.")
            conversation_history = []  # Reset conversation history if recording fails
    except Exception as e:
        logging.error(f"Unhandled error in handle_record: {e}")
        conversation_history = []  # Reset conversation history on any unhandled error

def setup_gui():
    """Setup the GUI for the application."""
    root = tk.Tk()
    root.title("Speech to Text Test")

    # Status label to give feedback to the user
    status_label = tk.Label(root, text="Press 'Talk to AI' to start", wraplength=400)
    status_label.pack(pady=10)

    def update_status(message):
        """Update the status label with the given message."""
        status_label.config(text=message)
        root.update()

    def handle_record_thread():
        """Thread target for handling the record process with status updates."""
        global conversation_history
        filename = os.path.join(audiofiles_dir, "output.wav")
        try:
            update_status("Recording... Speak now.")
            record_audio_vad(filename)
            update_status("Transcribing audio...")
            text = transcribe_audio(filename)
            if text:
                update_status("Generating response...")
                response = generate_response(text)
                update_status("Converting response to speech...")
                text_to_speech(response)
                update_status("Response ready. Press 'Talk to AI' to start again.")
            else:
                update_status("Failed to transcribe audio. Try again.")
                conversation_history = []  # Reset on failure
        except Exception as e:
            logging.error(f"Unhandled error in handle_record_thread: {e}")
            update_status(f"Error: {e}")
            conversation_history = []  # Reset on error

    record_button = tk.Button(root, text="Talk to AI", command=lambda: threading.Thread(target=handle_record_thread).start())
    record_button.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    setup_gui()