from setuptools import setup

APP = ['pomodoro.py']  # Your main Python script
DATA_FILES = []  # Any data files you need included
OPTIONS = {
    'argv_emulation': False,
    'packages': ['numpy', 'sounddevice', 'soundfile', 'openai', 'cryptography'],
    'iconfile': 'tomato_icon.icns',
    'resources': ['/opt/homebrew/lib/libportaudio.dylib', 'tomato_icon.png'],  # Include the icon file here
}

setup(
    app=APP,
    name="pomodoro-ai",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
