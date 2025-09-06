#!/usr/bin/env python3
"""
Arabic Desktop Audio Transcriber and Translator
Captures desktop audio, transcribes Arabic speech, and translates to English
"""

import soundcard as sc
import numpy as np
import speech_recognition as sr
from transformers import pipeline
import threading
import queue
import time
import warnings
import sys
import json
from datetime import datetime
import os
import atexit
import keyboard
import configparser

# Suppress warnings
warnings.filterwarnings("ignore")

# Configuration file path
CONFIG_FILE = "config.ini"

def load_device_config():
    """Load saved device configuration"""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'DEVICE' in config and 'name' in config['DEVICE']:
            return config['DEVICE']['name']
    return None

def save_device_config(device_name):
    """Save device configuration"""
    config = configparser.ConfigParser()
    config['DEVICE'] = {'name': device_name}
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    print(f"Device '{device_name}' saved as default.")

def find_device_by_name(device_name):
    """Find audio device by name"""
    all_devices = sc.all_microphones(include_loopback=True)
    for device in all_devices:
        if device.name == device_name:
            return device
    return None

class ArabicAudioTranscriber:
    def __init__(self, selected_device=None):
        """Initialize the transcriber with audio capture and translation models"""
        print("\nInitializing Arabic Audio Transcriber...")
        
        # Store selected device
        self.selected_device = selected_device
        
        # Initialize transcript storage
        self.transcripts = []
        self.session_start_time = datetime.now()
        
        # Register cleanup function to save transcripts on exit
        atexit.register(self.save_transcript)
        
        # Keyboard shortcut flag
        self.device_change_requested = False
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        
        # Initialize translation pipeline (Helsinki-NLP)
        print("Loading translation model (this may take a moment on first run)...")
        self.translator = pipeline(
            "translation", 
            model="Helsinki-NLP/opus-mt-ar-en",
            device=-1  # Use CPU (-1) or GPU (0) if available
        )
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for speech recognition
        self.chunk_duration = 3  # Process audio in 3-second chunks
        
        # Threading components
        self.audio_queue = queue.Queue()
        self.running = False
        
        print("Initialization complete!\n")
    
    def capture_audio(self):
        """Continuously capture audio from selected device and add to queue"""
        try:
            if self.selected_device is None:
                raise RuntimeError("No audio device selected")
            
            print(f"Capturing audio from: {self.selected_device.name}")
            print("Press Ctrl+C to stop\n")
            print("-" * 50)
            
            # Open recorder for the selected device
            with self.selected_device.recorder(samplerate=self.sample_rate) as mic:
                while self.running:
                    # Capture audio chunk
                    chunk_size = int(self.sample_rate * self.chunk_duration)
                    audio_data = mic.record(numframes=chunk_size)
                    
                    # Convert stereo to mono if necessary
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    
                    # Add to queue for processing
                    self.audio_queue.put(audio_data)
                    
        except Exception as e:
            print(f"\nError capturing audio: {e}")
            self.running = False
    
    def process_audio(self):
        """Process audio chunks from queue: transcribe and translate"""
        while self.running or not self.audio_queue.empty():
            try:
                # Get audio chunk from queue (timeout prevents hanging)
                audio_data = self.audio_queue.get(timeout=1)
                
                # Convert numpy array to AudioData for speech_recognition
                audio_data_int16 = (audio_data * 32767).astype(np.int16)
                audio = sr.AudioData(
                    audio_data_int16.tobytes(),
                    self.sample_rate,
                    2  # Sample width in bytes
                )
                
                try:
                    # Transcribe Arabic audio
                    print("Listening...", end="\r")
                    arabic_text = self.recognizer.recognize_google(
                        audio, 
                        language="ar-AR",  # Arabic
                        show_all=False
                    )
                    
                    if arabic_text:
                        print(f"\n🎤 Arabic: {arabic_text}")
                        
                        # Translate to English
                        translation = self.translator(
                            arabic_text,
                            max_length=512,
                            truncation=True
                        )
                        english_text = translation[0]['translation_text']
                        print(f"🔤 English: {english_text}")
                        print("-" * 50)
                        
                        # Store transcript entry
                        transcript_entry = {
                            'timestamp': datetime.now().isoformat(),
                            'arabic_text': arabic_text,
                            'english_text': english_text
                        }
                        self.transcripts.append(transcript_entry)
                    
                except sr.UnknownValueError:
                    # No speech detected in this chunk
                    pass
                except sr.RequestError as e:
                    print(f"\nError with speech recognition service: {e}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"\nError processing audio: {e}")
    
    def run(self):
        """Main run loop with threading for simultaneous capture and processing"""
        self.running = True
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        while True:
            # Start audio capture thread
            capture_thread = threading.Thread(target=self.capture_audio)
            capture_thread.start()
            
            # Start audio processing thread
            process_thread = threading.Thread(target=self.process_audio)
            process_thread.start()
            
            try:
                # Keep main thread alive and check for device change requests
                while self.running:
                    if self.device_change_requested:
                        print("\n\nStopping current session for device change...")
                        self.running = False
                        break
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n\nStopping transcription...")
                self.running = False
            
            # Wait for threads to finish
            capture_thread.join(timeout=2)
            process_thread.join(timeout=5)
            
            # Handle device change request
            if self.device_change_requested:
                self.device_change_requested = False
                if self.change_device_interactive():
                    # Restart with new device
                    self.running = True
                    print("\n" + "=" * 50)
                    print("RESUMING TRANSCRIPTION WITH NEW DEVICE")
                    print("=" * 50)
                    continue
                else:
                    # User cancelled, ask if they want to continue with current device
                    choice = input("\nContinue with current device? (y/n): ").strip().lower()
                    if choice == 'y':
                        self.running = True
                        continue
                    else:
                        break
            else:
                # Normal exit
                break
        
        # Save transcript before stopping
        self.save_transcript()
        print("Transcription stopped.")
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for device selection"""
        def on_device_change():
            self.device_change_requested = True
            print("\n🔄 Device change requested. Press Ctrl+C to stop current session and change device.")
        
        # Register Ctrl+D for device change
        keyboard.add_hotkey('ctrl+d', on_device_change)
        print("\n⌨️  Keyboard shortcuts:")
        print("   Ctrl+D: Change audio device")
        print("   Ctrl+C: Stop transcription")
    
    def change_device_interactive(self):
        """Interactive device change during runtime"""
        print("\n" + "=" * 50)
        print("CHANGE AUDIO DEVICE")
        print("=" * 50)
        
        new_device = select_audio_device()
        if new_device:
            self.selected_device = new_device
            save_device_config(new_device.name)
            print(f"\n✅ Device changed to: {new_device.name}")
            return True
        else:
            print("\n❌ Device change cancelled.")
            return False
    
    def save_transcript(self):
        """Save all transcripts to a text file"""
        if not self.transcripts:
            print("No transcripts to save.")
            return
        
        try:
            # Create transcripts directory if it doesn't exist
            transcript_dir = "transcripts"
            if not os.path.exists(transcript_dir):
                os.makedirs(transcript_dir)
            
            # Generate filename with timestamp
            timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"transcript_{timestamp}.txt"
            filepath = os.path.join(transcript_dir, filename)
            
            # Save to text file
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write session header
                f.write("=" * 60 + "\n")
                f.write("ARABIC AUDIO TRANSCRIPTION SESSION\n")
                f.write("=" * 60 + "\n")
                f.write(f"Session Start: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Session End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Audio Device: {self.selected_device.name if self.selected_device else 'Unknown'}\n")
                f.write(f"Total Entries: {len(self.transcripts)}\n")
                f.write("=" * 60 + "\n\n")
                
                # Write each transcript entry
                for i, entry in enumerate(self.transcripts, 1):
                    entry_time = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
                    f.write(f"[{i:03d}] {entry_time}\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"🎤 Arabic:  {entry['arabic_text']}\n")
                    f.write(f"🔤 English: {entry['english_text']}\n")
                    f.write("\n")
            
            print(f"\n📄 Transcript saved to: {filepath}")
            print(f"   Total entries: {len(self.transcripts)}")
            
        except Exception as e:
            print(f"\n❌ Error saving transcript: {e}")

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'soundcard': 'soundcard',
        'numpy': 'numpy',
        'speech_recognition': 'SpeechRecognition',
        'transformers': 'transformers',
        'torch': 'torch',  # Required by transformers
        'keyboard': 'keyboard'  # For keyboard shortcuts
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("Missing required packages. Please install them using:")
        print(f"pip install {' '.join(missing)}")
        print("\nFor transformers to work properly, you might also need:")
        print("pip install sentencepiece protobuf")
        return False
    return True

def select_audio_device(show_saved_device=True):
    """Interactive device selector"""
    print("\n" + "=" * 50)
    print("AUDIO DEVICE SELECTION")
    print("=" * 50)
    
    # Check for saved device
    saved_device_name = load_device_config() if show_saved_device else None
    saved_device = None
    if saved_device_name:
        saved_device = find_device_by_name(saved_device_name)
        if saved_device:
            print(f"\n💾 Saved Default Device: {saved_device.name}")
            print("   Press ENTER to use saved device, or select a different one below.")
        else:
            print(f"\n⚠️  Saved device '{saved_device_name}' not found. Please select a new device.")
    
    # Get all available microphones including loopback devices
    all_devices = sc.all_microphones(include_loopback=True)
    
    if not all_devices:
        print("No audio devices found!")
        return None
    
    # Separate devices by type
    loopback_devices = []
    microphone_devices = []
    
    for device in all_devices:
        if device.isloopback:
            loopback_devices.append(device)
        else:
            microphone_devices.append(device)
    
    # Display devices
    print("\n📢 DESKTOP AUDIO (Loopback) Devices:")
    print("-" * 40)
    if loopback_devices:
        for i, device in enumerate(loopback_devices):
            print(f"  {i + 1}. {device.name}")
    else:
        print("  No loopback devices found")
    
    print("\n🎤 MICROPHONE Devices:")
    print("-" * 40)
    if microphone_devices:
        for i, device in enumerate(microphone_devices):
            idx = len(loopback_devices) + i + 1
            print(f"  {idx}. {device.name}")
    else:
        print("  No microphone devices found")
    
    # Get default devices for reference
    print("\n💡 Default Devices:")
    print("-" * 40)
    try:
        default_speaker = sc.default_speaker()
        if default_speaker:
            print(f"  Default Speaker: {default_speaker.name}")
    except:
        pass
    
    try:
        default_mic = sc.default_microphone()
        if default_mic:
            print(f"  Default Microphone: {default_mic.name}")
    except:
        pass
    
    # Let user select
    print("\n" + "=" * 50)
    print("Select an audio device:")
    if saved_device:
        print("  • Press ENTER to use saved default device")
    print("  • For desktop audio (YouTube, music, etc.), choose a loopback device")
    print("  • For microphone input, choose a microphone device")
    print("  • Enter 0 to try auto-detect desktop audio")
    print("  • Enter Q to quit")
    print("=" * 50)
    
    while True:
        try:
            prompt = "\nEnter device number (1-{})" + (" or ENTER for default" if saved_device else "") + ": "
            choice = input(prompt.format(len(all_devices))).strip()
            
            if choice.upper() == 'Q':
                return None
            
            # Handle ENTER for saved device
            if choice == "" and saved_device:
                print(f"\nUsing saved device: {saved_device.name}")
                return saved_device
            
            choice_num = int(choice)
            
            if choice_num == 0:
                # Auto-detect desktop audio
                print("\nAuto-detecting desktop audio device...")
                if loopback_devices:
                    selected = loopback_devices[0]
                    print(f"Selected: {selected.name}")
                    return selected
                else:
                    print("No loopback devices found. Please select a microphone instead.")
                    continue
            
            if 1 <= choice_num <= len(all_devices):
                # Map choice to device
                if choice_num <= len(loopback_devices):
                    selected = loopback_devices[choice_num - 1]
                else:
                    mic_idx = choice_num - len(loopback_devices) - 1
                    selected = microphone_devices[mic_idx]
                
                device_type = "Desktop Audio (Loopback)" if selected.isloopback else "Microphone"
                print(f"\nSelected: {selected.name} [{device_type}]")
                
                if not selected.isloopback:
                    print("⚠️  Note: Microphone selected - this will capture from your mic, not desktop audio")
                
                confirm = input("Confirm selection? (y/n): ").strip().lower()
                if confirm == 'y':
                    # Save the selected device as default
                    save_device_config(selected.name)
                    return selected
                else:
                    print("Selection cancelled. Please choose again.")
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(all_devices)}")
                
        except ValueError:
            print("Invalid input. Please enter a number or 'Q' to quit.")
        except Exception as e:
            print(f"Error: {e}")
            return None

def main():
    """Main entry point"""
    print("=" * 50)
    print("Arabic Desktop Audio Transcriber & Translator")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Parse command line arguments for quick options
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("\nUsage: python arabic_transcriber.py [options]")
            print("\nOptions:")
            print("  --help          Show this help message")
            print("\nWithout options, the program will start with interactive device selection")
            sys.exit(0)
    
    try:
        # Check for saved device first
        saved_device_name = load_device_config()
        selected_device = None
        
        if saved_device_name:
            saved_device = find_device_by_name(saved_device_name)
            if saved_device:
                print(f"\n💾 Found saved default device: {saved_device.name}")
                use_saved = input("Use saved device? (Y/n): ").strip().lower()
                if use_saved != 'n':
                    selected_device = saved_device
                    print(f"✅ Using saved device: {selected_device.name}")
        
        # If no saved device or user chose not to use it, show device selector
        if selected_device is None:
            selected_device = select_audio_device()
            
            if selected_device is None:
                print("\nNo device selected. Exiting...")
                sys.exit(0)
        
        # Create and run transcriber with selected device
        print("\n" + "=" * 50)
        print("Starting Transcription")
        print("=" * 50)
        
        transcriber = ArabicAudioTranscriber(selected_device=selected_device)
        transcriber.run()
        
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()