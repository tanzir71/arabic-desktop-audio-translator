# Arabic Audio Transcriber & Translator for macOS

A real-time Arabic audio transcription and translation tool designed specifically for macOS. Captures desktop audio or microphone input, transcribes Arabic speech, and translates it to English using PyAudio for optimal macOS compatibility.

## Features

### 🎤 Audio Capture
- **Desktop Audio**: Capture system audio (YouTube, music, calls, etc.) using BlackHole
- **Microphone Input**: Capture from any connected microphone
- **Device Selection**: Interactive device selector with auto-detection
- **Device Persistence**: Remembers your preferred audio device
- **Multi-Output Support**: Listen to audio while capturing it simultaneously

### 🗣️ Speech Processing
- **Real-time Transcription**: Live Arabic speech-to-text using Google Speech Recognition
- **High-Quality Translation**: Arabic to English translation using Helsinki-NLP models
- **Continuous Processing**: Processes audio in 3-second chunks for real-time results

### ⌨️ Keyboard Shortcuts
- **Cmd+D**: Change audio device during transcription
- **Cmd+C**: Stop transcription
- **Dynamic Device Switching**: Change devices without losing your session

### 💾 Session Management
- **Auto-save Transcripts**: Automatically saves all transcriptions when program closes
- **Readable Format**: Saves transcripts as formatted text files
- **Session Tracking**: Includes timestamps, device info, and session duration
- **Organized Storage**: Saves transcripts in dedicated `transcripts/` folder

## Installation

### Prerequisites
- **macOS 10.14 or higher**
- **Python 3.7 or higher**
- **Xcode Command Line Tools**: `xcode-select --install`
- **Internet connection** (for speech recognition and first-time model download)

### Step 1: Clone or Download
```bash
# Download the project files to your desired directory
git clone [repository-url]
cd arabic-desktop-audio-translator-main
```

### Step 2: Install Dependencies
```bash
# Install Xcode Command Line Tools (if not already installed)
xcode-select --install

# Install required Python packages
python3 -m pip install -r requirements.txt
```

### Step 3: Install BlackHole (Required for Desktop Audio)

BlackHole is essential for capturing desktop audio on macOS:

```bash
# Install via Homebrew (recommended)
brew install blackhole-2ch

# Or download manually from: https://github.com/ExistentialAudio/BlackHole
```

### Step 4: Create Multi-Output Device (Essential Setup)

**This step is crucial for hearing audio while capturing it simultaneously.**

1. **Open Audio MIDI Setup**:
   - Press `Cmd + Space` and search for "Audio MIDI Setup"
   - Or go to Applications > Utilities > Audio MIDI Setup

2. **Create Multi-Output Device**:
   - Click the "+" button in the bottom-left corner
   - Select "Create Multi-Output Device"

3. **Configure the Multi-Output Device**:
   - Check the boxes for:
     - ✅ **BlackHole 2ch** (for audio capture)
     - ✅ **Your speakers/headphones** (e.g., "MacBook Pro Speakers" or "AirPods")
   - **Important**: Make sure your speakers/headphones are listed **first** (drag to reorder if needed)
   - Right-click the Multi-Output Device and select "Use This Device For Sound Output"

4. **Set as System Output**:
   - Go to System Preferences > Sound > Output
   - Select your newly created "Multi-Output Device"

5. **Verify Setup**:
   - Play some audio (YouTube, Spotify, etc.)
   - You should hear the audio through your speakers/headphones
   - The application will be able to capture this audio through BlackHole

### Step 5: Grant macOS Permissions

#### Required Permissions
1. **Microphone Access**:
   - Go to System Preferences > Security & Privacy > Privacy
   - Click "Microphone" in the left sidebar
   - Enable access for Terminal (or your Python IDE)

2. **Accessibility Access** (for keyboard shortcuts):
   - Go to System Preferences > Security & Privacy > Privacy
   - Click "Accessibility" in the left sidebar
   - Enable access for Terminal (or your Python IDE)

### Step 6: First Run
```bash
python3 main.py
```

## Usage

### Initial Setup
1. **Ensure Multi-Output Device is Active**:
   - Check that your Multi-Output Device is selected in System Preferences > Sound > Output
   - Play some test audio to verify you can hear it

2. **Run the Application**:
   ```bash
   python3 main.py
   ```

3. **Select Audio Device**:
   - **For desktop audio**: Choose "BlackHole 2ch" from the device list
   - **For microphone**: Choose your microphone device
   - Your selection is automatically saved as the default

### Daily Usage
1. **Activate Multi-Output Device** (if capturing desktop audio):
   - Ensure your Multi-Output Device is selected in Sound preferences
   - Start playing the audio you want to transcribe

2. **Run the Application**:
   ```bash
   python3 main.py
   ```

3. **Start Transcription**:
   - Press **Enter** to use your saved default device, or select a different one
   - The program will start transcribing and translating in real-time
   - You'll hear the audio through your speakers while it's being transcribed

4. **Use Keyboard Shortcuts**:
   - **Cmd+D**: Change device during transcription
   - **Cmd+C**: Stop and save transcripts

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
Audio Device: BlackHole 2ch
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
name = BlackHole 2ch
```

### Customization
You can modify these settings in the code:
- `chunk_duration`: Audio processing interval (default: 3 seconds)
- `sample_rate`: Audio sample rate (default: 16kHz)
- `energy_threshold`: Voice detection sensitivity (default: 300)

## Troubleshooting

### 🔊 No Audio Output While Capturing

**Problem**: You can't hear audio when the application is capturing desktop audio.

**Solution**: Ensure you've created and activated the Multi-Output Device:
1. Open Audio MIDI Setup
2. Verify your Multi-Output Device includes both BlackHole and your speakers
3. Set the Multi-Output Device as your system output in Sound preferences
4. Test by playing audio - you should hear it while the app can capture it

### 🎤 "No Audio Devices Found"

**Solutions**:
1. **Check PyAudio Installation**:
   ```bash
   python3 -c "import pyaudio; print('PyAudio working')"
   ```
2. **Verify BlackHole Installation**:
   - Open Audio MIDI Setup
   - Look for "BlackHole 2ch" in the device list
3. **Check Permissions**:
   - Ensure microphone access is granted in System Preferences

### 🚫 "Speech Recognition Error"

**Solutions**:
- Check your internet connection
- Ensure the audio is clear and in Arabic
- Try adjusting the system volume
- Verify the Multi-Output Device is working correctly

### ⌨️ "Keyboard Shortcuts Not Working"

**Solutions**:
- Grant accessibility permissions to Terminal in System Preferences > Security & Privacy > Privacy > Accessibility
- Restart Terminal after granting permissions
- Ensure no other applications are capturing global hotkeys

### 🔄 "Translation Model Loading Slowly"

**Solutions**:
- First-time model download can take several minutes
- Subsequent runs will be faster
- Ensure stable internet connection
- Models are cached locally after first download

### 🎵 Poor Transcription Quality

**Solutions**:
- Ensure clear audio input
- Adjust system volume levels (not too loud, not too quiet)
- Try different audio sources
- For desktop audio: Ensure the Multi-Output Device is properly configured
- For microphone: Position microphone closer and speak clearly in Arabic

## Technical Details

### Dependencies
- **pyaudio**: Audio device access and recording (macOS optimized)
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
- **macOS Optimized**: Uses PyAudio for better macOS compatibility

### Supported Languages
- **Input**: Arabic (ar-AR)
- **Output**: English (en)
- **Translation Model**: Helsinki-NLP opus-mt-ar-en

## Advanced Setup

### Multiple Audio Sources
You can create multiple Multi-Output Devices for different scenarios:
1. **Desktop + Speakers**: BlackHole + MacBook Speakers
2. **Desktop + Headphones**: BlackHole + AirPods
3. **Conference Calls**: BlackHole + External Speakers

### Automation
Create a shell script to quickly switch audio setups:
```bash
#!/bin/bash
# Switch to transcription setup
osascript -e "tell application \"System Preferences\" to set current pane to pane \"com.apple.preference.sound\""
echo "Please select your Multi-Output Device and run the transcriber"
```

## License

This project is open source. Feel free to modify and distribute.

## Contributing

Contributions are welcome! Areas for improvement:
- Additional language support
- Better audio preprocessing
- GUI interface
- Offline translation models
- Enhanced macOS integration

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Ensure Multi-Output Device is properly configured
3. Verify all dependencies are properly installed
4. Test with clear Arabic audio input
5. Check that BlackHole is installed and working

---

**Note**: This application is specifically optimized for macOS and takes advantage of macOS-specific audio routing capabilities through BlackHole and Multi-Output Devices.