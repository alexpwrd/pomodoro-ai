import os
import threading
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
import numpy as np
import webrtcvad
import logging
from utils.settings import APIKeyManager  # Adjust the import path as necessary

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class VoiceAssistant:
    def __init__(self, app):
        self.app = app
        self.audiofiles_dir = os.path.join(os.path.dirname(__file__), '..', 'audiofiles')
        self.client = OpenAI(api_key=APIKeyManager().get_api_key())
        self.conversation_history = [
            {"role": "system", "content": (
                "As a personal productivity coach AI, your primary role is to assist the user in enhancing "
                "their productivity and time management skills to successfully complete their tasks. Feel free to ask for the user's name, "
                "and use this information to personalize the conversation based on prior interactions stored in the conversational history. "
                "You are not limited to offering general advice; you are also equipped to engage in detailed planning based on the user's specific goals. "
                "Proactively ask insightful questions about their current projects, upcoming tasks, and their approach to tackling them, "
                "tailoring your suggestions to their previous responses and progress. "
                "You appear as a clickable button within a Pomodoro AI app, which the user uses to initiate conversations with you. "
                "This app also features a timer for 25-minute focused work sessions followed by 5-minute breaks, aiming for the user "
                "to complete four sessions to achieve a full work cycle of 2 hours. "
                "Your interactions should guide the user in planning their work sessions effectively. Offer tangible, proven productivity strategies "
                "and tailor your suggestions to fit within the framework of the Pomodoro technique. "
                "Ensure your responses are clear, concise, and conversational. Maintain a tone that is friendly, playful, and supportive, "
                "encouraging a productive and enjoyable work experience. Always remember to keep your responses brief and to the point, "
                "and do not hesitate to ask the user questions that will aid in their task completion."
            )}
        ]

        # Ensure the audiofiles directory exists
        if not os.path.exists(self.audiofiles_dir):
            os.makedirs(self.audiofiles_dir)

    def record_audio_vad(self, filename="output.wav", fs=48000, vad_mode=3, frame_duration=30, silence_duration=2000):
        filename = os.path.join(self.audiofiles_dir, filename)
        logging.info("Starting recording with VAD...")
        vad = webrtcvad.Vad(vad_mode)
        device_info = sd.query_devices(kind='input')
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
                    is_speech = vad.is_speech(frame.tobytes(), fs)
                    if is_speech:
                        audio_data.extend(frame)
                        silent_frames = 0
                    else:
                        silent_frames += 1
                    if silent_frames > num_silent_frames_to_stop:
                        break
            sf.write(filename, np.array(audio_data), fs)
            logging.info("Recording stopped and saved to file.")
        except Exception as e:
            logging.error(f"Error during recording: {e}")

    def transcribe_audio(self, filename="output.wav"):
        filename = os.path.join(self.audiofiles_dir, filename)
        try:
            with open(filename, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            logging.info(f"Transcription result: {transcription.text}")
            return transcription.text
        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            return ""

    def generate_response(self, text):
        try:
            self.conversation_history.append({"role": "user", "content": text})
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=self.conversation_history
            )
            generated_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": generated_response})
            logging.info(f"Generated response: {generated_response}")
            return generated_response
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return ""

    def text_to_speech(self, text):
        user_voice = "onyx"  # Example voice, adjust as needed
        speech_file_path = os.path.join(self.audiofiles_dir, 'speech_output.opus')
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=user_voice,
                input=text,
                response_format="opus"
            )
            response.stream_to_file(speech_file_path)
            logging.info(f"Text to speech conversion successful, saved to {speech_file_path}")
            self.play_audio(speech_file_path)
        except Exception as e:
            logging.error(f"Error in text-to-speech conversion: {e}")

    def play_audio(self, file_path):
        try:
            data, fs = sf.read(file_path, dtype='float32')
            sd.play(data, samplerate=fs)
            sd.wait()
            logging.info("Audio playback completed.")
        except Exception as e:
            logging.error(f"Error playing audio file: {e}")

    def handle_voice_command(self):
        """
        Handles a voice command by recording, transcribing, generating a response,
        and converting the response to speech. This method ensures all heavy operations
        are performed in a background thread to keep the GUI responsive.
        """
        def background_task():
            """
            A background task that runs the sequence of operations for handling a voice command.
            This task runs in a separate thread to avoid blocking the main GUI thread.
            """
            try:
                # Update the GUI to inform the user that the system is listening.
                self.app.update_user_feedback("Listening...")
                # Record audio with voice activity detection (VAD) to capture only the necessary audio.
                self.record_audio_vad()
                
                # Update the GUI to inform the user that the system is processing the recorded audio.
                self.app.update_user_feedback("Thinking...")
                # Transcribe the recorded audio to text.
                transcription = self.transcribe_audio()
                
                if transcription:
                    # Generate a response based on the transcribed text.
                    response = self.generate_response(transcription)
                    
                    # Update the GUI to inform the user that the system is speaking the response.
                    self.app.update_user_feedback("Speaking...")
                    # Convert the generated text response to speech and play it.
                    self.text_to_speech(response)
                    
                    # Schedule the GUI to update the feedback to "Press to Talk" after a delay,
                    # indicating the system is ready for another command.
                    self.app.master.after(1000, lambda: self.app.update_user_feedback("Press to Talk"))
                else:
                    # Log an error and update the GUI if no transcription result was obtained.
                    logging.error("No transcription result.")
                    self.app.update_user_feedback("Try speaking again.")
            except Exception as e:
                # Log any exceptions that occur during the process and update the GUI to show an error message.
                logging.error(f"Error handling voice command: {e}")
                self.app.update_user_feedback("Error. Check log.")
            finally:
                # Ensure the "Talk to AI" button is re-enabled and the user feedback is reset,
                # regardless of how the voice command processing concludes.
                self.app.master.after(0, lambda: self.app.user_feedback_var.set("Press to Talk"))
                self.app.enable_talk_to_ai_button()

        # Start the background task in a new thread to prevent blocking the main GUI thread.
        thread = threading.Thread(target=background_task)
        thread.start()