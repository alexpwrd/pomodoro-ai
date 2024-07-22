import os
import threading
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
import numpy as np
import webrtcvad
import logging
from utils.settings import APIKeyManager
import mss
from PIL import Image
import base64
import io
from datetime import datetime
import time
from utils.database import ConversationDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
        return result
    return wrapper

class VoiceAssistant:
    def __init__(self, app):
        self.app = app
        self.audiofiles_dir = os.path.join(os.path.dirname(__file__), '..', 'audiofiles')
        self.client = OpenAI(api_key=APIKeyManager().get_api_key())
        self.db = ConversationDatabase()
        self.max_history_length = 10
        self.load_conversation_history()

    def load_conversation_history(self):
        history = self.db.get_conversation_history(self.max_history_length)
        self.conversation_history = [
            {"role": "system", "content": (
                "As a personal productivity coach AI, your primary role is to assist the user in enhancing "
                "their productivity and time management skills to successfully complete their tasks while being brief and conversational in your response. "
                "When seeing a screenshot of what they see on their main screen, you can use this information to help them complete their tasks more efficiently. If you see destractions like social media, be sure to remind them to focus on their main task. "
                "Your responses should be brief in the same way a conversation would be brief between two humans. When greeting the user, ask what they would like to work on today? "
                "Feel free to ask for the user's name, "
                "and use this information to personalize the conversation based on prior interactions stored in the conversational history. "
                "You are not limited to offering general advice; you are also equipped to engage in detailed planning based on the user's specific goals. "
                "Proactively ask insightful questions about their current projects, upcoming tasks, and their approach to tackling them, "
                "tailoring your suggestions to their previous responses and progress. "
                "You appear as a clickable button within a Pomodoro AI app, which the user uses to initiate conversations with you. "
                "This app also features a timer for 25-minute focused work sessions followed by 5-minute breaks, aiming for the user "
                "to complete four sessions to achieve a full work cycle of 2 hours. "
                "Your interactions should guide the user in planning their work sessions effectively. Offer tangible, proven productivity strategies "
                "and tailor your suggestions to fit within the framework of the Pomodoro technique. "
                "Ensure your responses are clear, concise, and conversational. Maintain a tone that is friendly, funny, playful, and supportive, "
                "encouraging a productive and enjoyable work experience. Always remember to keep your responses brief and to the point, "
                "and do not hesitate to ask the user questions that will aid in their task completion."
            )}
        ]
        for role, content in reversed(history):
            self.conversation_history.append({"role": role, "content": content})

        if not os.path.exists(self.audiofiles_dir):
            os.makedirs(self.audiofiles_dir)

    @timer
    def capture_screenshot(self):
        try:
            with mss.mss() as sct:
                # Get all monitors
                monitors = sct.monitors

                # Find the primary monitor (usually the one with left and top coordinates as 0)
                primary_monitor = next((m for m in monitors if m["left"] == 0 and m["top"] == 0), monitors[1])

                screenshot = sct.grab(primary_monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Calculate new dimensions while maintaining aspect ratio
                max_width = 3840  # 4K resolution width
                max_height = 2160  # 4K resolution height
                
                if img.width > max_width or img.height > max_height:
                    aspect_ratio = img.width / img.height
                    if img.width > img.height:
                        new_width = max_width
                        new_height = int(new_width / aspect_ratio)
                    else:
                        new_height = max_height
                        new_width = int(new_height * aspect_ratio)
                    
                    # Resize image
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to base64
                buffered = io.BytesIO()
                img.save(buffered, format="PNG", compress_level=1)  # Use minimum compression
                screenshot_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                logging.info(f"Screenshot captured. Size: {len(screenshot_base64)} bytes, Dimensions: {img.size}")
                return screenshot_base64
        except Exception as e:
            logging.error(f"Error capturing screenshot: {e}")
            return None

    @timer
    def record_audio_vad(self, filename="output.wav", fs=48000, vad_mode=3, frame_duration=10, silence_duration=500, max_duration=20000):
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
                speech_frames = 0
                num_silent_frames_to_stop = int(silence_duration / frame_duration)
                max_frames = int(max_duration / frame_duration)
                frames_recorded = 0
                
                while frames_recorded < max_frames:
                    frame, overflowed = stream.read(int(fs * frame_duration / 1000))
                    frames_recorded += 1
                    is_speech = vad.is_speech(frame.tobytes(), fs)
                    if is_speech:
                        audio_data.extend(frame)
                        silent_frames = 0
                        speech_frames += 1
                    else:
                        silent_frames += 1
                        if speech_frames > 0:  # Only add silence after we've detected speech
                            audio_data.extend(frame)
                    if silent_frames > num_silent_frames_to_stop and speech_frames > 0:
                        logging.info(f"Silence detected after speech, stopping recording.")
                        break
                    if frames_recorded % 100 == 0:  # Log every second
                        logging.info(f"Recording in progress... {frames_recorded * frame_duration / 1000:.1f} seconds")
                
                if frames_recorded >= max_frames:
                    logging.info("Maximum recording duration reached.")
                elif speech_frames == 0:
                    logging.info("No speech detected, stopping recording.")
            
            if speech_frames > 0:
                sf.write(filename, np.array(audio_data), fs)
                logging.info(f"Recording stopped and saved to file. Duration: {len(audio_data) / fs:.2f} seconds")
                return True
            else:
                logging.info("No audio saved as no speech was detected.")
                return False
        except Exception as e:
            logging.error(f"Error during recording: {e}")
            return False

    @timer
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

    @timer
    def generate_response(self, text, screenshot_base64=None):
        try:
            # Start with the system message
            messages = [self.conversation_history[0]]  # System message
            
            # Add the most recent messages from the conversation history
            messages.extend(self.conversation_history[1:self.max_history_length])
            
            # Add the new user message
            user_message = {"role": "user", "content": text}
            self.db.add_message("user", text)
            messages.append(user_message)

            logging.info(f"Sending request to AI with {len(messages)} messages")
            
            # Include screenshot in the current request if available, but don't save it in history
            if screenshot_base64:
                current_message = messages[-1].copy()
                current_message["content"] = [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}",
                            "detail": "auto"
                        }
                    }
                ]
                messages[-1] = current_message
                logging.info("Screenshot included in the current request")
            else:
                logging.info("No screenshot included in the request")

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=2000
            )
            
            generated_response = response.choices[0].message.content
            self.db.add_message("assistant", generated_response)
            self.conversation_history.append({"role": "assistant", "content": generated_response})
            
            # Trim the in-memory conversation history if it exceeds the max length
            if len(self.conversation_history) > self.max_history_length + 1:  # +1 for the system message
                self.conversation_history = self.conversation_history[:1] + self.conversation_history[-(self.max_history_length):]
            
            logging.info("Response generated successfully")
            
            return generated_response
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return ""

    @timer
    def text_to_speech(self, text):
        if not text:
            logging.warning("Empty text provided for text-to-speech conversion. Skipping.")
            return

        user_voice = self.app.settings_manager.get_setting("AI_VOICE", "onyx")
        valid_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

        if user_voice not in valid_voices:
            logging.error(f"Invalid voice setting '{user_voice}'. Using default 'onyx'.")
            user_voice = "onyx"

        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=user_voice,
                input=text,
                response_format="opus"
            )
            audio_stream = io.BytesIO(response.content)
            logging.info("Text to speech conversion successful")
            self.play_audio_from_stream(audio_stream)
        except Exception as e:
            logging.error(f"Error in text-to-speech conversion: {e}")

    @timer
    def play_audio_from_stream(self, audio_stream):
        try:
            data, fs = sf.read(audio_stream, dtype='float32')
            sd.play(data, samplerate=fs, device=sd.default.device['output'])
            sd.wait()
            logging.info("Audio playback completed.")
        except Exception as e:
            logging.error(f"Error playing audio stream: {e}")

    @timer
    def handle_voice_command(self):
        def background_task():
            try:
                start_time = time.time()
                self.app.update_user_feedback("Listening...")
                speech_detected = self.record_audio_vad()
                
                if not speech_detected:
                    self.app.update_user_feedback("No speech detected. Try again.")
                    return

                self.app.update_user_feedback("Thinking...")
                transcription = self.transcribe_audio()
                
                if transcription:
                    screenshot_base64 = None
                    if self.app.settings_manager.get_setting("AI_SCREEN_VISION", False):
                        self.app.update_user_feedback("Looking at screen...")
                        logging.info("AI Screen Vision is enabled. Looking at screen...")
                        screenshot_base64 = self.capture_screenshot()
                        if screenshot_base64:
                            logging.info("Screenshot captured successfully")
                        else:
                            logging.warning("Failed to capture screenshot")
                    else:
                        logging.info("AI Screen Vision is disabled. No screenshot captured.")
                    
                    response = self.generate_response(transcription, screenshot_base64)
                    
                    self.app.update_user_feedback("Speaking...")
                    self.text_to_speech(response)
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    logging.info(f"Total voice command process time: {total_time:.2f} seconds")
                    
                    self.app.master.after(1000, lambda: self.app.update_user_feedback("Press to Talk"))
                else:
                    logging.error("No transcription result.")
                    self.app.update_user_feedback("Try speaking again.")
            except Exception as e:
                logging.error(f"Error handling voice command: {e}")
                self.app.update_user_feedback("Error. Check log.")
            finally:
                self.app.master.after(0, lambda: self.app.user_feedback_var.set("Press to Talk"))
                self.app.enable_talk_to_ai_button()

        thread = threading.Thread(target=background_task)
        thread.start()