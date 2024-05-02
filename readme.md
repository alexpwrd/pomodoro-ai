# Pomodoro AI 

![Pomodoro AI Application Preview](resources/app-preview.png)

Enhance productivity with the Pomodoro Timer featuring AI integration and a voice assistant. Developed with Python and Tkinter, it helps manage work and break intervals and motivates with quotes from OpenAI.

## Key Features

- Discuss tasks with AI to plan work sessions
- Customize work and break durations
- Displays inspirational quotes from OpenAI
- User-friendly interface with audible alerts

## Prerequisites

- macOS (tested on 14.4.1)
- Python 3.11 or higher
- Tkinter (included with Python on macOS)
- OpenAI Python package
- Valid OpenAI API key
- Stable internet connection

## Setup Instructions

### 1. Install Python
Download and install Python 3.11 or higher from [python.org](https://www.python.org/downloads/).

### 2. Clone the Repository
Clone and navigate to the repository:
```bash
git clone https://github.com/alexpwrd/pomodoro-ai.git
cd pomodoro-ai
```

### 3. Create a Virtual Environment (Optional)
Creating a virtual environment is optional but recommended to manage dependencies separately from your global Python installation. If you choose to create one, use Python's `venv` and name it `pomodoro-ai-env`:
```bash
python -m venv pomodoro-ai-env
source pomodoro-ai-env/bin/activate # Use pomodoro-ai-env\Scripts\activate on Windows
```

### 4. Install Dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```
### 5. Install PortAudio
Install PortAudio. This is required by the sounddevice library to stream audio from your computer's microphone.

#### For macOS:
```bash
brew install portaudio
```

#### For Debian / Ubuntu Linux:

```bash
sudo apt-get install portaudio19-dev
```

#### Windows:
Windows may work without having to install PortAudio explicitly (it will get installed with sounddevice).

### 6. Run the Application
Start the application with:
```bash
python pomodoro.py # or python3 pomodoro.py
```

### 7. Obtain an OpenAI API Key
Get an OpenAI API key by signing up at [OpenAI](https://www.openai.com/).

### 8. Configure Application Settings & Set API Keys

After launching the Pomodoro AI application, personalize and configure your settings through the application's settings interface:

1. **Access Settings**: Open the settings menu from the main interface of the application.
2. **User Information**:
   - **User Name**: Enter your name to personalize the interaction with the AI.
   - **Profession**: Provide your profession to help the AI tailor motivational messages and suggestions.
3. **OpenAI API Key**:
   - **Enter API Key**: Input your valid OpenAI API key in the designated field. This key enables the AI functionalities within the app.
5. **Save Changes**: Click the 'Save' button to apply your settings.

![Application Settings Interface](resources/settings.png)

## Reopening the Application 

After setting up and configuring the application, you can start using it by following these steps:

1. **Open Terminal**: Navigate to the terminal or command prompt on your device.
2. **Activate the Virtual Environment** (if you created one during setup):
   - On macOS or Linux:
     ```bash
     source pomodoro-ai-env/bin/activate
     ```
   - On Windows:
     ```bash
     pomodoro-ai-env\Scripts\activate
     ```

3. **Navigate to the Project Directory**:
   ```bash
   cd path/to/pomodoro-ai
   ```

4. **Run the Application**:
   ```bash
   python pomodoro.py # or python3 pomodoro.py if python3 is the specific command on your system
   ```

This will launch the Pomodoro AI application, and you can start using the features such as the AI voice assistant and the customizable Pomodoro timer.

## Using the Application

### Voice Assistant
- **Activate**: Click "Talk to AI" in the main interface.
- **Command**: Speak clearly into your microphone.
- **Feedback**: Receive guidance directly in the app.

### Pomodoro Timer
- **Setup**: Ensure you're in the project directory and the virtual environment is active.
- **Start**: Run the application and use the interface to set durations and control the timer.
- **Motivation**: Get motivational quotes during breaks and audible alerts for session transitions.

Enjoy a more productive workflow with your AI-enhanced Pomodoro Timer!
