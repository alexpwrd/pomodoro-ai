# Pomodoro Timer with Motivational Quotes

Enhance your productivity with this straightforward desktop application, the Pomodoro Timer. Developed using Python and Tkinter, it not only assists in managing your work and break intervals efficiently but also keeps you motivated with uplifting quotes.

## Key Features

- Tailor work and break periods to your preference
- Inspirational quotes displayed, courtesy of OpenAI
- User-friendly graphical interface
- Audible alerts signaling the start and end of sessions

## Prerequisites

- macOS operating system - tested on 14.4.1
- Python version 3.11 or above
- Tkinter library (usually comes with Python installations on macOS)
- openai and dotenv Python packages
- Valid OpenAI API key
- Stable internet connection

## Note for Windows and Linux Users

The audible alerts feature uses the `say` command, which is specific to macOS. Windows users can replace this with the `pyttsx3` library for text-to-speech functionality, or the `winsound` module for simple beeps. Linux users might consider using `espeak` or similar for text-to-speech. Example adaptations for these platforms can be found in the documentation or comments within the `pomodoro.py` script.

## Setting Up

1. Verify Python 3 is installed on your device. It's recommended to use a virtual environment such as Miniconda to manage your Python versions and packages. This helps in avoiding conflicts between package versions and requirements for different projects.

2. If you're using Miniconda or another virtual environment tool, create a new environment for this project:
   ```
   conda create --name pomodoro python=3.11
   conda activate pomodoro
   ```
   Adjust the `python=3.11` to your preferred Python version (3.11 or above).

3. Execute the following command to install necessary Python packages:
   ```
   pip install openai python-dotenv
   ```

4. Obtain the `pomodoro.py` script by either cloning the repository or downloading it directly.

5. In the script's directory, create a `.env` file and insert your OpenAI API key as shown below:
   ```
   OPENAI_API_KEY=<your_openai_api_key_here>
   ```
   Ensure the `.env` file is secured and not shared publicly, as it contains sensitive information.

## How to Use

To start the Pomodoro Timer, open your terminal, change to the directory containing the `pomodoro.py` script, and execute the following command:

python pomodoro.py


This will launch the Pomodoro Timer application. Through its graphical interface, you can:

- Set your desired focus and break durations using the dropdown menu.
- Start, pause, or reset the timer with the corresponding buttons.
- During breaks, the application will fetch and display an inspirational quote from OpenAI, and an audible alert will signal the start and end of each session.

Enjoy enhanced productivity and motivation with your AI Pomodoro Timer!
