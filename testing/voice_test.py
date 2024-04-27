from openai import OpenAI
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import os
from dotenv import load_dotenv
import warnings

# Ignore DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load environment variables
load_dotenv()

# Initialize the OpenAI client with an API key from the environment variables
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_poem():
    # Generate a poem using the chat completions API
    completion = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Ты поэтический помощник, умело объясняющий сложные концепции программирования с творческим подходом."},
            {"role": "user", "content": "Составь короткое четырехстрочное стихотворение на тему кайтсерфинга."}
        ]
    )
    return completion.choices[0].message.content

def text_to_speech(text, file_path):
    # Convert text to speech and save as an audio file
    response = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=text,
        response_format="opus",
        speed=1.0
    )
    response.stream_to_file(file_path)

def play_audio(file_path):
    # Play an opus file using soundfile and sounddevice
    data, samplerate = sf.read(file_path, dtype='float32')
    sd.play(data, samplerate)
    sd.wait()  # Wait until the file has finished playing

def main():
    poem_text = generate_poem()
    print("Generated Poem:", poem_text)
    speech_file_path = Path(__file__).parent / "voice.opus"
    text_to_speech(poem_text, speech_file_path)
    play_audio(speech_file_path)

if __name__ == "__main__":
    main()
