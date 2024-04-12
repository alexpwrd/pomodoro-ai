import openai
from dotenv import load_dotenv
import os

def create_speech(text, voice="alloy", audio_format="mp3", speed=1.0):
    """
    Generates spoken audio from text using OpenAI's TTS API.

    Args:
    text (str): The text to convert to speech, up to 4096 characters.
    voice (str): The TTS voice to use. Options include 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'.
    audio_format (str): The audio file format. Options include 'mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'.
    speed (float): The speed of the speech. Can range from 0.25 to 4.0.

    Returns:
    The path to the generated audio file.
    """
    # Load environment variables
    load_dotenv()

    # Get the API key from .env file
    api_key = os.getenv("OPENAI_API_KEY")

    # Configure the API client
    openai.api_key = api_key

    # Generate the speech
    response = openai.Audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format=audio_format,
        speed=speed
    )

    # Define the path for the audio file
    file_path = f"output_speech.{audio_format}"

    # Stream the audio content to a file
    with open(file_path, "wb") as audio_file:
        audio_file.write(response.content)

    return file_path

# Example usage
if __name__ == "__main__":
    text_to_speak = "Hello, this is a test of OpenAI's text to speech conversion."
    audio_file = create_speech(text_to_speak, voice="alloy", audio_format="mp3", speed=1.0)
    print(f"Generated audio file: {audio_file}")
