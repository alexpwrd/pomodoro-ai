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
import tempfile
from datetime import datetime
import time
from utils.database import ConversationDatabase
from pydub import AudioSegment
from pydub.utils import make_chunks
import queue

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
        self.max_history_length = 30
        self.load_conversation_history()
        self.stream_active = False
        self.volume = 1.0

    def load_conversation_history(self):
        history = self.db.get_conversation_history(self.max_history_length)
        self.conversation_history = [
            {"role": "system", "content": (
                "As a voice-activated personal productivity coach AI within a Pomodoro app, your primary role is to enhance the user's productivity and time management skills with extremely brief, spoken responses. "
                "Limit each response to a single, concise sentence that captures the most crucial point or question. "
                "You can sometimes see the users screen when they include a screen shot in the message, if asked, tell the user what you see on the screen. When shown a screenshot, quickly identify distractions like social media and remind the user to focus on their main task. "
                "Greet users by asking what they'd like to work on today, and feel free to ask for their name to personalize future interactions. "
                "Use the conversation history to tailor your brief suggestions and questions about their projects and tasks. "
                "Guide users in planning effective 25-minute work sessions and 5-minute breaks, aiming for four sessions in a 2-hour cycle. "
                "Offer quick, tangible productivity strategies within the Pomodoro framework. "
                "Don't offer lists, only response as a single conversational sentence."
                "Maintain a friendly, funny, playful, and supportive tone while being incredibly succinct. "
                "If more detail is needed, prompt the user to ask a follow-up question instead of providing a lengthy answer. "
                "Remember, your entire response must fit within one sentence, focusing on the most important aspect of productivity or task completion."
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
    def record_audio_vad(self, filename="output.wav", fs=16000, max_duration=20, vad_sensitivity=3):
        filename = os.path.join(self.audiofiles_dir, filename)
        logging.info("Starting recording with VAD...")

        vad = webrtcvad.Vad(vad_sensitivity)
        chunk_duration = 0.03  # 30 ms
        chunk_size = int(fs * chunk_duration)
        num_silent_chunks = int(0.5 / chunk_duration)  # 0.5 seconds of silence
        silent_chunks = 0
        stop_recording = False

        try:
            recording = []
            start_time = time.time()

            def callback(indata, frames, time_info, status):
                nonlocal silent_chunks, stop_recording
                if status:
                    logging.warning(f"Recording status: {status}")

                # Ensure the audio data is in 16-bit PCM format
                audio_data = indata[:, 0].astype(np.int16).tobytes()

                is_speech = vad.is_speech(audio_data, fs)
                logging.debug(f"is_speech: {is_speech}, silent_chunks: {silent_chunks}")

                if is_speech:
                    silent_chunks = 0
                else:
                    silent_chunks += 1

                recording.append(indata.copy())

                if silent_chunks > num_silent_chunks:
                    logging.info("Silence detected, stopping recording.")
                    stop_recording = True

                if time_info.currentTime - start_time > max_duration:
                    logging.info("Max duration reached, stopping recording.")
                    stop_recording = True

            with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback, blocksize=chunk_size) as stream:
                while not stop_recording:
                    sd.sleep(100)

            recording = np.concatenate(recording, axis=0)
            sf.write(filename, recording, fs)
            logging.info(f"Recording finished and saved to {filename}")
            return True
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
            
            # Add context about conversation history
            if len(self.conversation_history) > 1:
                context_message = {
                    "role": "system",
                    "content": "The following messages are from the previous conversation. Use them as context for your response:"
                }
                messages.append(context_message)
                
                # Add the most recent messages from the conversation history
                messages.extend(self.conversation_history[1:self.max_history_length])
            
            # Add a separator to indicate the start of the new interaction
            messages.append({
                "role": "system",
                "content": "The following is the latest message from the user. Respond to this message while considering the context above:"
            })
            
            # Add the new user message
            user_message = {"role": "user", "content": text}
            self.db.add_message("user", text)
            messages.append(user_message)

            # Include screenshot in the current request if available
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

            # Log the messages being sent to the AI
            print("\n" + "="*50)
            print("Messages being sent to OpenAI:")
            print("="*50)
            for idx, msg in enumerate(messages):
                role = msg['role']
                content = msg['content']
                if isinstance(content, list):
                    text_content = next((item['text'] for item in content if item['type'] == 'text'), "")
                    print(f"{idx + 1}. Role: {role}")
                    print(f"   Content: {text_content[:100]}...")
                    print(f"   [Screenshot data included]")
                else:
                    print(f"{idx + 1}. Role: {role}")
                    print(f"   Content: {content[:100]}...")
                print("-" * 30)

            logging.info(f"Sending request to OpenAI with {len(messages)} messages")

            response = self.client.chat.completions.create(
                model="gpt-4o",
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

    def summarize_messages(self, messages):
        """Summarize the message structure without including full content."""
        return [
            {
                "role": msg["role"],
                "content_type": (
                    "text" if isinstance(msg["content"], str) 
                    else [item["type"] for item in msg["content"]]
                )
            }
            for msg in messages
        ]

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
                response_format="mp3"
            )
            logging.info("Text to speech conversion successful")
            self.play_audio_from_stream(response)
        except Exception as e:
            logging.error(f"Error in text-to-speech conversion: {e}")

    @timer
    def play_audio_from_stream(self, response):
        CHUNK_SIZE = 4096  # 4 KB chunks

        def download_thread():
            try:
                buffer = io.BytesIO()
                total_bytes = 0
                for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                    buffer.write(chunk)
                    total_bytes += len(chunk)
                
                buffer.seek(0)
                audio = AudioSegment.from_mp3(buffer)
                logging.info(f"Download complete. Total bytes: {total_bytes}")
                return audio
            except Exception as e:
                logging.error(f"Error in download thread: {e}")
                return None

        def playback_thread(audio):
            try:
                if audio is None:
                    return

                logging.info("Playback started")
                samples = np.array(audio.get_array_of_samples())
                samples = (samples * self.volume).astype(np.int16)
                
                sd.play(samples, audio.frame_rate)
                sd.wait()
                
                logging.info(f"Audio playback completed. Total samples: {len(samples)}")
            except Exception as e:
                logging.error(f"Error in playback thread: {e}")

        # Download the entire audio stream
        audio = download_thread()

        # Play the audio only after it's fully downloaded
        if audio:
            playback_thread(audio)
        else:
            logging.error("Failed to download audio stream")

    def stop_audio_playback(self):
        self.stream_active = False
        sd.stop()
        logging.info("Audio playback stopped.")

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        logging.info(f"Volume set to {self.volume}")

    @timer
    def handle_voice_command(self):
        def background_task():
            timings = {}
            try:
                self.app.update_user_feedback("Listening...")
                
                # Record audio (don't time this)
                speech_detected = self.record_audio_vad()
                
                if not speech_detected:
                    self.app.update_user_feedback("No speech detected. Try again.")
                    logging.warning("No speech detected during recording.")
                    return

                self.app.update_user_feedback("Thinking...")
                
                # Transcribe audio
                transcribe_start = time.time()
                transcription = self.transcribe_audio()
                timings['transcription'] = time.time() - transcribe_start
                
                if transcription:
                    screenshot_base64 = None
                    if self.app.settings_manager.get_setting("AI_SCREEN_VISION", False):
                        self.app.update_user_feedback("Looking at screen...")
                        logging.info("AI Screen Vision is enabled. Looking at screen...")
                        
                        # Capture screenshot
                        screenshot_start = time.time()
                        screenshot_base64 = self.capture_screenshot()
                        timings['screenshot'] = time.time() - screenshot_start
                        
                        if screenshot_base64:
                            logging.info("Screenshot captured successfully")
                        else:
                            logging.warning("Failed to capture screenshot")
                    else:
                        logging.info("AI Screen Vision is disabled. No screenshot captured.")
                    
                    # Generate response
                    response_start = time.time()
                    response = self.generate_response(transcription, screenshot_base64)
                    timings['response_generation'] = time.time() - response_start
                    
                    self.app.update_user_feedback("Speaking...")
                    
                    # Text to speech conversion (don't include playback time)
                    tts_start = time.time()
                    tts_response = self.client.audio.speech.create(
                        model="tts-1",
                        voice=self.app.settings_manager.get_setting("AI_VOICE", "onyx"),
                        input=response,
                        response_format="mp3"
                    )
                    timings['text_to_speech'] = time.time() - tts_start
                    
                    # Play audio (don't time this)
                    self.play_audio_from_stream(tts_response)
                    
                    self.app.master.after(1000, lambda: self.app.update_user_feedback("Press to Talk"))
                else:
                    logging.error("No transcription result.")
                    self.app.update_user_feedback("Try speaking again.")
            except Exception as e:
                logging.error(f"Error handling voice command: {e}", exc_info=True)
                self.app.update_user_feedback("Error. Check log.")
            finally:
                self.app.master.after(0, lambda: self.app.user_feedback_var.set("Press to Talk"))
                self.app.enable_talk_to_ai_button()
                
                # Log summary of timings
                total_processing_time = sum(timings.values())
                logging.info("\nVoice Command Processing Summary:")
                logging.info(f"Total processing time: {total_processing_time:.2f} seconds")
                for step, duration in timings.items():
                    percentage = (duration / total_processing_time) * 100
                    logging.info(f"  {step:<20}: {duration:6.2f} seconds ({percentage:5.1f}%)")

        thread = threading.Thread(target=background_task)
        thread.start()

    def update_audio_devices(self, input_device, output_device):
        self.input_device = input_device
        self.output_device = output_device
        sd.default.device = (input_device, output_device)
        logging.info(f"Audio devices updated. Input: {input_device}, Output: {output_device}")