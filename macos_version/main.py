#!/usr/bin/env python3
"""
Arabic Desktop Audio Transcriber and Translator
Captures desktop audio, transcribes Arabic speech, and translates to English
"""

import warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", message=r"`return_token_timestamps` is deprecated.*", category=FutureWarning)
import sys
import json
from datetime import datetime
import os
import atexit
import keyboard
import configparser
import platform
import signal
import socket
import torch
import pyaudio
import numpy as np
import speech_recognition as sr
from transformers import pipeline
import threading
import queue
import time

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
    """Find audio device by name using PyAudio"""
    try:
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['name'] == device_name and device_info['maxInputChannels'] > 0:
                device_info['index'] = i  # Add index for PyAudio
                p.terminate()
                return device_info
        p.terminate()
    except Exception as e:
        print(f"Error finding device: {e}")
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

        self.asr_backend = os.environ.get("ASR_BACKEND", "google").strip().lower()
        self.asr_fallback = os.environ.get("ASR_FALLBACK", "whisper").strip().lower()
        if self.asr_fallback in ("", "none", "null", "0"):
            self.asr_fallback = None
        self.offline_only = os.environ.get("OFFLINE_ONLY", "0").strip() == "1"

        self.torch_device = 0 if torch.cuda.is_available() else -1
        self.torch_dtype = torch.float16 if self.torch_device == 0 else None
        if self.torch_device == 0:
            print("✅ GPU detected (CUDA). Using GPU acceleration.")
        else:
            print("⚠️ CUDA not available. Using CPU.")
        
        # PyAudio setup
        self.pyaudio_instance = pyaudio.PyAudio()
        self.stream = None
        
        # Initialize speech recognizer (Google web API)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.speech_api_timeout_s = 12
        socket.setdefaulttimeout(self.speech_api_timeout_s)

        # Initialize offline ASR (Whisper via transformers)
        self.asr = None
        needs_whisper = self.asr_backend == "whisper" or self.asr_fallback == "whisper"
        if needs_whisper:
            whisper_model = os.environ.get("WHISPER_MODEL", "openai/whisper-small").strip()
            print("Loading offline ASR model (Whisper)...")
            if self.offline_only:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            try:
                asr_kwargs = {
                    "model": whisper_model,
                    "device": self.torch_device,
                }
                if self.torch_dtype is not None:
                    asr_kwargs["torch_dtype"] = self.torch_dtype
                try:
                    self.asr = pipeline("automatic-speech-recognition", **asr_kwargs)
                except TypeError:
                    asr_kwargs.pop("torch_dtype", None)
                    self.asr = pipeline("automatic-speech-recognition", **asr_kwargs)
                try:
                    self.asr.feature_extractor.return_attention_mask = True
                except Exception:
                    pass
                print("✅ Offline ASR ready.")
            except Exception as e:
                print(f"❌ Failed to initialize offline ASR: {e}")
                if self.offline_only:
                    print("💡 Offline-only is enabled. Set OFFLINE_ONLY=0 once to allow the model to download, then rerun.")
                else:
                    print("💡 Offline ASR unavailable. Set ASR_FALLBACK=none to silence fallback attempts.")
                self.asr = None
                if self.asr_backend == "whisper":
                    print("💡 Falling back to Google speech recognition for now (set ASR_BACKEND=google to force).")
                    self.asr_backend = "google"
                if self.asr_fallback == "whisper":
                    self.asr_fallback = None
        
        # Initialize translation pipeline (Helsinki-NLP)
        print("Loading translation model (this may take a moment on first run)...")
        self.translator = pipeline(
            "translation", 
            model="Helsinki-NLP/opus-mt-ar-en",
            device=self.torch_device
        )
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for speech recognition
        self.chunk_duration = 3  # Process audio in 3-second chunks
        
        # Threading components
        self.audio_queue = queue.Queue()
        self.running = False
        
        print("Initialization complete!\n")

    def recognize_arabic(self, audio):
        result_queue = queue.Queue(maxsize=1)

        def do_recognize():
            try:
                text = self.recognizer.recognize_google(
                    audio,
                    language="ar-AR",
                    show_all=False,
                )
                result_queue.put(("ok", text))
            except Exception as e:
                result_queue.put(("err", e))

        t = threading.Thread(target=do_recognize, daemon=True)
        t.start()
        try:
            status, payload = result_queue.get(timeout=self.speech_api_timeout_s + 1)
        except queue.Empty:
            raise TimeoutError(f"Speech recognition timed out after ~{self.speech_api_timeout_s}s")

        if status == "ok":
            return payload
        raise payload

    def recognize_arabic_google_cloud(self, audio):
        credentials_json = os.environ.get("GOOGLE_CLOUD_CREDENTIALS_JSON", "").strip()
        if not credentials_json:
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            if creds_path:
                with open(creds_path, "r", encoding="utf-8") as f:
                    credentials_json = f.read()
        if not credentials_json:
            raise RuntimeError(
                "Google Cloud credentials not set. Set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON path "
                "or set GOOGLE_CLOUD_CREDENTIALS_JSON to the JSON contents."
            )

        result_queue = queue.Queue(maxsize=1)

        def do_recognize():
            try:
                text = self.recognizer.recognize_google_cloud(
                    audio,
                    credentials_json=credentials_json,
                    language="ar-AR",
                    show_all=False,
                )
                result_queue.put(("ok", text))
            except Exception as e:
                result_queue.put(("err", e))

        t = threading.Thread(target=do_recognize, daemon=True)
        t.start()
        try:
            status, payload = result_queue.get(timeout=self.speech_api_timeout_s + 1)
        except queue.Empty:
            raise TimeoutError(f"Speech recognition timed out after ~{self.speech_api_timeout_s}s")

        if status == "ok":
            return payload
        raise payload

    def recognize_arabic_offline(self, audio_array):
        if not self.asr:
            raise RuntimeError("Offline ASR is not initialized")
        result = self.asr(
            {"array": audio_array.astype(np.float32), "sampling_rate": self.sample_rate},
            generate_kwargs={"task": "transcribe", "language": "ar"},
            return_timestamps=False,
        )
        text = (result or {}).get("text", "")
        return text.strip()
    
    def capture_audio(self):
        """Capture audio from the selected device using PyAudio"""
        try:
            if not self.selected_device:
                print("❌ No audio device selected")
                return
                
            print(f"🎤 Starting audio capture from: {self.selected_device['name']}")
            
            # Calculate chunk size
            chunk_size = int(self.sample_rate * self.chunk_duration)
            
            # Open PyAudio stream
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.selected_device['index'],
                frames_per_buffer=chunk_size
            )
            
            while self.running:
                try:
                    # Read audio data
                    audio_data = self.stream.read(chunk_size, exception_on_overflow=False)
                    
                    # Convert to numpy array
                    audio_array = np.frombuffer(audio_data, dtype=np.float32)
                    
                    if len(audio_array) > 0:
                        # Add to queue for processing
                        self.audio_queue.put(audio_array)
                    
                    # Check if device change was requested
                    if self.device_change_requested:
                        print("🔄 Device change requested, stopping current capture...")
                        break
                        
                except Exception as e:
                    print(f"⚠️ Audio capture error: {e}")
                    # Try to continue with a short delay
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            print(f"❌ Failed to start audio capture: {e}")
            print("💡 Try the following solutions:")
            print("   1. Check audio device permissions")
            print("   2. Restart the application")
            print("   3. Check if the selected device is available")
            
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            print("🛑 Audio capture stopped")
    
    def process_audio(self):
        """Process audio chunks from queue: transcribe and translate"""
        while self.running or not self.audio_queue.empty():
            try:
                # Get audio chunk from queue (timeout prevents hanging)
                audio_data = self.audio_queue.get(timeout=1)
                
                try:
                    # Transcribe Arabic audio
                    print("Listening...", end="\r")
                    audio_data_int16 = (audio_data * 32767).astype(np.int16)
                    audio = sr.AudioData(
                        audio_data_int16.tobytes(),
                        self.sample_rate,
                        2,
                    )
                    primary_backend = self.asr_backend
                    if primary_backend == "google_web":
                        primary_backend = "google"

                    if primary_backend == "whisper":
                        arabic_text = self.recognize_arabic_offline(audio_data)
                    elif primary_backend == "google":
                        arabic_text = self.recognize_arabic(audio)
                    elif primary_backend == "google_cloud":
                        arabic_text = self.recognize_arabic_google_cloud(audio)
                    else:
                        raise RuntimeError(f"Unknown ASR_BACKEND: {self.asr_backend}")
                    
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
                except TimeoutError as e:
                    print(f"\nError with speech recognition service: {e}")
                except Exception as e:
                    if self.asr_backend == "whisper":
                        hint = ""
                        if self.offline_only:
                            hint = " (set OFFLINE_ONLY=0 to allow first-time model download)"
                        print(f"\nOffline ASR error: {e}{hint}")
                    else:
                        if self.asr_fallback == "whisper" and self.asr:
                            try:
                                arabic_text = self.recognize_arabic_offline(audio_data)
                            except Exception as fallback_error:
                                print(f"\nError with speech recognition service: {e}")
                                print(f"\nOffline ASR error: {fallback_error}")
                                arabic_text = ""
                        else:
                            print(f"\nError with speech recognition service: {e}")
                            arabic_text = ""
                        if arabic_text:
                            print(f"\n🎤 Arabic: {arabic_text}")
                            translation = self.translator(
                                arabic_text,
                                max_length=512,
                                truncation=True
                            )
                            english_text = translation[0]['translation_text']
                            print(f"🔤 English: {english_text}")
                            print("-" * 50)
                            transcript_entry = {
                                'timestamp': datetime.now().isoformat(),
                                'arabic_text': arabic_text,
                                'english_text': english_text
                            }
                            self.transcripts.append(transcript_entry)
                        continue
                
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
        
        # Clean up resources
        self.cleanup()
        print("Transcription stopped.")
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        print("\n🧹 Cleaning up resources...")
        
        # Stop and close PyAudio stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # Terminate PyAudio instance
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        # Clear the audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        print("✅ Cleanup completed")
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for device selection"""
        def on_device_change():
            self.device_change_requested = True
            if platform.system() == "Darwin":  # macOS
                print("\n🔄 Device change requested. Press Cmd+C to stop current session and change device.")
            else:
                print("\n🔄 Device change requested. Press Ctrl+C to stop current session and change device.")
        
        try:
            # Register platform-specific hotkey for device change
            if platform.system() == "Darwin":  # macOS
                # Use 'command' instead of 'cmd' for macOS
                keyboard.add_hotkey('command+d', on_device_change)
                print("\n⌨️  Keyboard shortcuts:")
                print("   Cmd+D: Change audio device")
                print("   Cmd+C: Stop transcription")
            else:
                keyboard.add_hotkey('ctrl+d', on_device_change)
                print("\n⌨️  Keyboard shortcuts:")
                print("   Ctrl+D: Change audio device")
                print("   Ctrl+C: Stop transcription")
        except Exception as e:
            if platform.system() == "Darwin":
                print("\n⚠️  Keyboard shortcuts unavailable (permissions required)")
                print("   To enable: System Preferences > Security & Privacy > Privacy > Accessibility")
                print("   Enable access for Terminal (or your Python IDE)")
                print("\n⌨️  Alternative controls:")
                print("   Cmd+C: Stop transcription (then restart to change device)")
            else:
                print(f"\n⚠️  Keyboard shortcuts unavailable: {e}")
                print("\n⌨️  Alternative controls:")
                print("   Ctrl+C: Stop transcription (then restart to change device)")
    
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



def check_macos_permissions():
    """Check and guide user through macOS permissions setup"""
    if platform.system() != "Darwin":
        return True
    
    print("\n🍎 macOS Permissions Check")
    print("-" * 30)
    
    # Test microphone access using PyAudio
    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        p.terminate()
        print("✅ Audio system access: OK")
    except Exception as e:
        print("❌ Audio system access: DENIED")
        print("\n🔧 To fix audio access:")
        print("   1. Open System Preferences > Security & Privacy > Privacy")
        print("   2. Click 'Microphone' in the left sidebar")
        print("   3. Enable access for Terminal (or your Python IDE)")
        print("   4. Restart this application")
        return False
    
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'pyaudio': 'PyAudio',
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
    """Interactive device selector using PyAudio"""
    print("\n" + "=" * 50)
    print("AUDIO DEVICE SELECTION")
    print("=" * 50)
    
    # Check for saved device
    saved_device_name = load_device_config() if show_saved_device else None
    saved_device = None
    if saved_device_name:
        saved_device = find_device_by_name(saved_device_name)
        if saved_device:
            print(f"\n💾 Saved Default Device: {saved_device['name']}")
            print("   Press ENTER to use saved device, or select a different one below.")
        else:
            print(f"\n⚠️  Saved device '{saved_device_name}' not found. Please select a new device.")
    
    # Get all available audio devices using PyAudio
    try:
        p = pyaudio.PyAudio()
        all_devices = []
        
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # Only input devices
                device_info['index'] = i
                all_devices.append(device_info)
        
        p.terminate()
        
    except Exception as e:
        print(f"\n❌ Error accessing audio devices: {e}")
        return None
    
    if not all_devices:
        print("No audio devices found!")
        return None
    
    # Display devices
    print("\n🎤 Available Audio Input Devices:")
    print("-" * 40)
    for i, device in enumerate(all_devices):
        print(f"  {i + 1}. {device['name']}")
    
    # Let user select
    print("\n" + "=" * 50)
    print("Select an audio device:")
    if saved_device:
        print("  • Press ENTER to use saved default device")
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
                print(f"\nUsing saved device: {saved_device['name']}")
                return saved_device
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(all_devices):
                selected = all_devices[choice_num - 1]
                
                print(f"\nSelected: {selected['name']}")
                
                confirm = input("Confirm selection? (y/n): ").strip().lower()
                if confirm == 'y':
                    # Save the selected device as default
                    save_device_config(selected['name'])
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

def timeout_handler(signum, frame):
    print("\n⏰ Operation timed out - Core Audio may be unresponsive")
    print("🔧 Try restarting your Mac or running: sudo killall coreaudiod")
    sys.exit(1)

def main():
    """Main entry point"""
    print("=" * 50)
    print("Arabic Desktop Audio Transcriber & Translator")
    print("=" * 50)
    
    # Set timeout for macOS Core Audio issues
    if platform.system() == "Darwin":
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
    
    try:
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        # Check macOS permissions if on macOS
        if not check_macos_permissions():
            print("\n❌ Required permissions not granted. Please fix the permissions and try again.")
            sys.exit(1)
        
        # Parse command line arguments for quick options
        if len(sys.argv) > 1:
            if sys.argv[1] == "--help":
                print("\nUsage: python arabic_transcriber.py [options]")
                print("\nOptions:")
                print("  --help          Show this help message")
                print("\nWithout options, the program will start with interactive device selection")
                sys.exit(0)
        
        # Check for saved device first
        saved_device_name = load_device_config()
        selected_device = None
        
        if saved_device_name:
            saved_device = find_device_by_name(saved_device_name)
            if saved_device:
                print(f"\n💾 Found saved default device: {saved_device['name']}")
                use_saved = input("Use saved device? (Y/n): ").strip().lower()
                if use_saved != 'n':
                    selected_device = saved_device
                    print(f"✅ Using saved device: {selected_device['name']}")
        
        # If no saved device or user chose not to use it, show device selector
        if selected_device is None:
            selected_device = select_audio_device()
            
            if selected_device is None:
                print("\nNo device selected. Exiting...")
                sys.exit(0)
        
        # Cancel timeout once device selection is complete
        if platform.system() == "Darwin":
            signal.alarm(0)
        
        # Create and run transcriber with selected device
        print("\n" + "=" * 50)
        print("Starting Transcription")
        print("=" * 50)
        
        transcriber = ArabicAudioTranscriber(selected_device=selected_device)
        transcriber.run()
        
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        if platform.system() == "Darwin":
            signal.alarm(0)
        print(f"\nFatal error: {e}")
        if "coreaudio" in str(e).lower():
            print("🔧 This appears to be a Core Audio issue. Try restarting your Mac.")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
