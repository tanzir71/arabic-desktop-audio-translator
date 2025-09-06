---
title: "Arabic Audio Transcriber & Translator"
date: 2024-01-15
draft: false
layout: "home"
---

# Real-time Arabic Audio Transcription & Translation

A powerful Python application that captures audio from your system, transcribes Arabic speech in real-time, and provides instant English translations.

<div class="hero-buttons">
    <a href="https://github.com/tanzir71/arabic-desktop-audio-translator" class="btn btn-primary" target="_blank">View on GitHub</a>
    <a href="#features" class="btn btn-secondary">Learn More</a>
</div>

## Key Features

### 🎤 Real-time Audio Capture
- Capture audio from any system device (speakers, microphones)
- Smart device selection with persistent preferences
- Keyboard shortcuts for quick device switching (Ctrl+D)

### 🗣️ Advanced Speech Recognition
- Specialized Arabic speech recognition using Whisper models
- High accuracy transcription with noise filtering
- Support for various Arabic dialects

### 🌐 Instant Translation
- Real-time Arabic to English translation
- Powered by advanced transformer models
- Context-aware translations for better accuracy

### 💾 Session Management
- Automatic transcript saving as text files
- Organized output in timestamped files
- Configuration persistence across sessions

### ⌨️ Keyboard Controls
- **Ctrl+D**: Change audio device during runtime
- **Ctrl+C**: Stop transcription gracefully
- **Enter**: Quick device selection on startup

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python main.py
   ```

3. **Select Audio Device**
   - Choose your preferred audio input device
   - Device preference is automatically saved

4. **Start Transcribing**
   - Speak in Arabic or play Arabic audio
   - View real-time transcription and translation
   - Transcripts are automatically saved

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, Linux
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 2GB free space for models

## Technical Stack

- **Speech Recognition**: OpenAI Whisper
- **Translation**: Hugging Face Transformers
- **Audio Processing**: SoundCard, NumPy
- **UI Controls**: Keyboard shortcuts
- **Configuration**: INI file management

## Output Format

Transcripts are saved as text files in the `transcripts/` directory:

```
transcripts/
├── transcript_2024-01-15_14-30-25.txt
├── transcript_2024-01-15_15-45-12.txt
└── ...
```

Each file contains:
- Original Arabic text
- English translation
- Timestamp information
- Session metadata