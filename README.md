# Arabic Audio Transcriber & Translator

A real-time Arabic audio transcription and translation tool that captures desktop audio or microphone input, transcribes Arabic speech, and translates it to English.

## Features

### 🎤 Audio Capture
- **Desktop Audio**: Capture system audio (YouTube, music, calls, etc.) using loopback devices
- **Microphone Input**: Capture from any connected microphone
- **Device Selection**: Interactive device selector with auto-detection
- **Device Persistence**: Remembers your preferred audio device

### 🗣️ Speech Processing
- **Real-time Transcription**: Live Arabic speech-to-text using Google Speech Recognition
- **High-Quality Translation**: Arabic to English translation using Helsinki-NLP models
- **Continuous Processing**: Processes audio in 3-second chunks for real-time results

### ⌨️ Keyboard Shortcuts
- **Ctrl+D**: Change audio device during transcription
- **Ctrl+C**: Stop transcription
- **Dynamic Device Switching**: Change devices without losing your session

### 💾 Session Management
- **Auto-save Transcripts**: Automatically saves all transcriptions when program closes
- **Readable Format**: Saves transcripts as formatted text files
- **Session Tracking**: Includes timestamps, device info, and session duration
- **Organized Storage**: Saves transcripts in dedicated `transcripts/` folder

## Installation

### Prerequisites
- Python 3.7 or higher
- Windows operating system (for current audio capture implementation)
- Internet connection (for speech recognition and first-time model download)

### Step 1: Clone or Download
```bash
# Download the main.py file to your desired directory
```

### Step 2: Install Dependencies
```bash
# Install required packages
pip install -r requirements.txt
```

### Step 3: First Run
```bash
python main.py
```

## Usage

### Initial Setup
1. Run the program: `python main.py`
2. Select your audio device from the interactive menu:
   - **For desktop audio**: Choose a loopback device
   - **For microphone**: Choose a microphone device
3. Your selection is automatically saved as the default

### Daily Usage
1. Run the program: `python main.py`
2. Press **Enter** to use your saved default device, or select a different one
3. The program will start transcribing and translating in real-time
4. Use keyboard shortcuts as needed:
   - **Ctrl+D**: Change device
   - **Ctrl+C**: Stop and save transcripts

### Device Management
- **First time**: Select and confirm your preferred device
- **Startup**: Press Enter to use saved device, or choose a new one
- **During transcription**: Press Ctrl+D to change devices on-the-fly
- **Auto-save**: Any newly selected device becomes your new default

## Output Format

### Console Output
```
🎤 Arabic: مرحبا كيف حالك
🔤 English: Hello, how are you
--------------------------------------------------
```

### Saved Transcripts
Transcripts are saved as `transcript_YYYYMMDD_HHMMSS.txt` in the `transcripts/` folder:

```
============================================================
ARABIC AUDIO TRANSCRIPTION SESSION
============================================================
Session Start: 2025-01-06 20:51:08
Session End: 2025-01-06 21:15:32
Audio Device: Desktop Audio
Total Entries: 5
============================================================

[001] 20:52:15
----------------------------------------
🎤 Arabic:  مرحبا كيف حالك
🔤 English: Hello, how are you

[002] 20:53:22
----------------------------------------
🎤 Arabic:  أهلا وسهلا
🔤 English: Welcome
```

## Configuration

### Config File
Device preferences are stored in `config.ini`:
```ini
[DEVICE]
name = Your Selected Device Name
```

### Customization
You can modify these settings in the code:
- `chunk_duration`: Audio processing interval (default: 3 seconds)
- `sample_rate`: Audio sample rate (default: 16kHz)
- `energy_threshold`: Voice detection sensitivity (default: 300)

## Troubleshooting

### Common Issues

**"No audio devices found"**
- Ensure your audio devices are properly connected
- Try running as administrator
- Check Windows audio settings

**"Speech recognition error"**
- Check your internet connection
- Ensure the audio is clear and in Arabic
- Try adjusting the microphone volume

**"Translation model loading slowly"**
- First-time model download can take several minutes
- Subsequent runs will be faster
- Ensure stable internet connection

**"Keyboard shortcuts not working"**
- Try running as administrator
- Ensure no other applications are capturing global hotkeys

### Audio Device Issues

**Desktop audio not capturing**
- Select a "loopback" device, not a regular microphone
- Ensure the application you want to capture is playing audio
- Check Windows sound settings

**Poor transcription quality**
- Ensure clear audio input
- Adjust system volume levels
- Try different audio devices
- Speak clearly in Arabic

## Technical Details

### Dependencies
- **soundcard**: Audio device access and recording
- **numpy**: Audio data processing
- **SpeechRecognition**: Google Speech Recognition API
- **transformers**: Helsinki-NLP translation models
- **torch**: Machine learning backend
- **keyboard**: Global keyboard shortcuts
- **configparser**: Configuration file management

### Architecture
- **Multi-threaded**: Separate threads for audio capture and processing
- **Real-time**: Continuous 3-second audio chunk processing
- **Persistent**: Device preferences and transcript storage
- **Modular**: Clean separation of concerns

### Supported Languages
- **Input**: Arabic (ar-AR)
- **Output**: English (en)
- **Translation Model**: Helsinki-NLP opus-mt-ar-en

## License

This project is open source. Feel free to modify and distribute.

## Contributing

Contributions are welcome! Areas for improvement:
- Additional language support
- Better audio preprocessing
- GUI interface
- Cross-platform compatibility
- Offline translation models

## Support

For issues or questions:
1. Check the troubleshooting section
2. Ensure all dependencies are properly installed
3. Verify your audio device setup
4. Test with clear Arabic audio input