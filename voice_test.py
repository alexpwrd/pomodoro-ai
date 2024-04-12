from openai import OpenAI
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play
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
            {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
            {"role": "user", "content": "Compose a short 4 line poem with a kiteboarding/kitesurfing theme."}
        ]
    )
    return completion.choices[0].message.content

def text_to_speech(text, file_path):
    # Convert text to speech and save as an audio file
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx",
        input=text,
        response_format="mp3",
        speed=1.0
    )
    response.stream_to_file(file_path)

def play_audio(file_path):
    # Play an MP3 file using pydub
    song = AudioSegment.from_mp3(file_path)
    play(song)

def main():
    poem_text = generate_poem()
    print("Generated Poem:", poem_text)
    speech_file_path = Path(__file__).parent / "voice.mp3"
    text_to_speech(poem_text, speech_file_path)
    play_audio(speech_file_path)

if __name__ == "__main__":
    main()
