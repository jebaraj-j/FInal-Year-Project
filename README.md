# 🖐️ Gesture & Voice Control System

An advanced computer control system that combines hand gesture recognition and voice commands for hands-free interaction with your Windows PC.

## 📋 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)

## ✨ Features

### 🖐️ Gesture Control
- **Real-time hand tracking** using MediaPipe
- **Cursor control** with smooth movement
- **Click actions**: Single click, double click, right-click, drag & drop
- **Scrolling** with natural hand gestures
- **Window management**: Minimize, maximize, task switching
- **Visual feedback** with color-coded gesture indicators

### 🎙️ Voice Control
- **Offline speech recognition** using VOSK
- **Wake word detection** for hands-free activation
- **Brightness control** with precise percentage adjustments
- **Volume control** with mute functionality
- **Application launching** with configurable paths
- **System operations**: Shutdown, restart, sleep, lock

### 🔄 Mode Switching
- **Seamless switching** between gesture and voice modes
- **Gesture-to-voice**: Left hand gesture (1.5 second hold)
- **Voice-to-gesture**: Voice command "Switch to gesture"
- **Resource optimization** by running only one mode at a time

## 🏗️ System Architecture

### Overall Architecture Flow
```
┌─────────────────────────────────────────────────────────────┐
│                    System Launcher                           │
│                 (system_launcher.py)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐        ┌────────▼────────┐
│  Gesture Mode   │        │   Voice Mode    │
│ (vision_working.py) │    │   (main.py)     │
└───────┬────────┘        └────────┬────────┘
        │                           │
┌───────▼────────┐        ┌────────▼────────┐
│  MediaPipe      │        │   VOSK          │
│  Hand Tracking  │        │   Speech Recog  │
└────────────────┘        └────────────────┘
```

### Mode Switching Diagram
```
┌─────────────────┐    Gesture Signal    ┌─────────────────┐
│   Gesture Mode  │ ───────────────────► │   Voice Mode    │
│                 │                      │                 │
│ • Hand Tracking │                      │ • Wake Word     │
│ • Cursor Ctrl   │                      │ • Voice Cmds    │
│ • Window Mgmt   │                      │ • System Ctrl   │
└─────────────────┘ ◄───────────────────-┘─────────────────┘
      Voice Signal      "Switch to gesture"
```

### Gesture Recognition Pipeline
```
Camera Input → Image Enhancement → MediaPipe Processing → Gesture Detection
     │                │                      │                    │
  Webcam         CLAHE +              Hand Landmark        Gesture
  (1280x720)     Denoising             Extraction          Classification
     │                │                      │                    │
     └────────────────┴──────────────────────┴────────────────┘
                                   │
                                   ▼
                           Action Execution
                    (Cursor Movement, Clicks, etc.)
```

### Voice Processing Pipeline
```
Microphone → Audio Stream → Wake Word Detection → Command Recognition → Action Execution
    │              │              │                    │                    │
 Audio Device   PyAudio       VOSK Model           Intent Engine        Controllers
 (16kHz, 1ch)   Management   (Offline)            Pattern Match       (Brightness,
    │              │              │                    │                    │  Volume, etc.)
    └──────────────┴──────────────┴────────────────────┴────────────────┘
```

## 📦 Requirements

### Hardware
- **Windows PC** (Windows 10/11 recommended)
- **Webcam** for gesture recognition
- **Microphone** for voice commands

### Software Dependencies
```bash
# Install all dependencies from the unified requirements.txt
pip install -r requirements.txt
```

The main `requirements.txt` includes all necessary packages for both gesture and voice control:

**Core Dependencies:**
- `mediapipe>=0.10.0` - Hand tracking and gesture recognition
- `opencv-python>=4.8.0` - Computer vision and image processing
- `numpy>=1.24.0` - Numerical computations
- `pyautogui>=0.9.54` - Mouse and keyboard automation

**Speech Recognition:**
- `vosk>=0.3.45` - Offline speech recognition engine
- `PyAudio>=0.2.11` - Audio stream management
- `SpeechRecognition>=3.10.0` - Speech recognition utilities

**System Control:**
- `screen-brightness-control>=0.4.0` - Display brightness management
- `pycaw>=2023.9.3` - Windows audio control
- `comtypes>=1.2.0` - COM interface for Windows

**Text Processing:**
- `fuzzywuzzy>=0.18.0` - String matching for voice commands
- `python-Levenshtein>=0.12.2` - Text similarity calculations

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd projectnew
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download VOSK Model (Voice Recognition)
```bash
# Create models directory in voice_assistant
mkdir voice_assistant/models

# Download English model (≈50MB)
# Visit: https://alphacephei.com/vosk/models
# Download and extract to: voice_assistant/models/vosk-model-small-en-us-0.15
```

**Note:** The project now uses a unified `requirements.txt` file in the root directory. The duplicate `voice_assistant/requirements.txt` has been removed to avoid confusion.

## 🎯 Quick Start

### Launch the System
```bash
python main.py
```

The system starts in the redesigned desktop UI and enters **Gesture Mode** automatically.

For legacy headless switching flow (no PyQt UI), you can still run:
```bash
python system_launcher.py
```

### Basic Usage
1. **Gesture Mode**: Use hand gestures to control cursor and windows
2. **Switch to Voice**: Hold left hand thumb+index+middle fingers for 1.5 seconds
3. **Voice Commands**: Say wake word ("Hey Assistant") followed by command
4. **Switch Back**: Say "Switch to gesture"

## 📖 Usage Guide

### 🖐️ Gesture Mode

#### Right Hand Controls
| Action | Gesture | Visual Indicator |
|--------|---------|------------------|
| **Move Cursor** | Only index finger extended | Green line between thumb-index |
| **Single Click** | Mild pinch (thumb + index) | Orange line between thumb-index |
| **Double Click** | Tight pinch (thumb + index) | Red line between thumb-index |
| **Right Click** | Pinch thumb + middle finger | Yellow indicator |
| **Drag & Drop** | Hold tight pinch for >0.35s | Red line sustained |
| **Scroll** | Index + middle fingers extended | Blue scroll indicator |

#### Left Hand Controls
| Action | Gesture | Visual Indicator |
|--------|---------|------------------|
| **Task Switch** | Pinch thumb + index (Alt+Tab) | Purple indicator |
| **Minimize Window** | Closed fist | Gray indicator |
| **Maximize Window** | Open palm | Cyan indicator |
| **Switch to Voice** | Thumb + index + middle extended (1.5s) | Yellow progress bar |

#### Hand Gesture Diagrams
```
RIGHT HAND GESTURES:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   CURSOR MOVE   │  │   SINGLE CLICK  │  │   DOUBLE CLICK  │
│                 │  │                 │  │                 │
│      ☝         │  │      🤏        │  │      👌         │
│   Index Only    │  │   Mild Pinch    │  │  Tight Pinch    │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   RIGHT CLICK   │  │   DRAG & DROP   │  │     SCROLL      │
│                 │  │                 │  │                 │
│      🤌         │  │      👌        │  │      ✌️         │
│ Thumb+Middle    │  │  Hold Tight     │  │ Index+Middle    │
└─────────────────┘  └─────────────────┘  └─────────────────┘

LEFT HAND GESTURES:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   TASK SWITCH   │  │  MINIMIZE WIN   │  │  MAXIMIZE WIN   │
│                 │  │                 │  │                 │
│      🤏         │  │      ✊        │  │      ✋         │
│ Thumb+Index     │  │   Closed Fist   │  │   Open Palm     │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐
│ SWITCH TO VOICE │
│                 │
│      🤟         │
│ Thumb+Index+Mid │
│   (1.5s hold)   │
└─────────────────┘
```

#### Keyboard Shortcuts (Camera Window)
- **H**: Toggle help overlay
- **S**: Take screenshot
- **Q**: Quit system

### 🎙️ Voice Mode

#### Wake Words
- "Hey Assistant"
- "OK Assistant" 
- "Hello System"

#### Voice Command Flow
```
┌─────────────────┐    Wake Word     ┌─────────────────┐    Command     ┌─────────────────┐
│   Idle State    │ ───────────────► │  Active Listen   │ ─────────────► │  Action Exec    │
│                 │                  │                  │               │                 │
│ • Listening     │                  │ • Processing     │               │ • Brightness    │
│ • Low CPU       │                  │ • Recognizing    │               │ • Volume        │
│ • Waiting       │                  │ • Intent Match   │               │ • Apps          │
└─────────────────┘ ◄────────────────┘─────────────────┘ ◄───────────┘─────────────────┘
      Timeout           Command Complete      Action Complete
```

#### Voice Command Categories
```
┌─────────────────────────────────────────────────────────────────┐
│                    VOICE COMMANDS                                │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│  BRIGHTNESS     │     VOLUME      │    APPS         │  SYSTEM   │
├─────────────────┼─────────────────┼─────────────────┼───────────┤
│ • Brightness up │ • Volume up     │ • Open Chrome   │ • Shutdown │
│ • Brightness    │ • Volume down   │ • Open VS Code  │ • Restart │
│   down          │ • Set volume 50 │ • Open Notepad  │ • Sleep   │
│ • Max bright    │ • Mute          │ • Open Settings │ • Lock    │
│ • Min bright    │ • Unmute        │ • Open Explorer │           │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
```

## ⚙️ Configuration

### Gesture Settings
Edit `gesture/config.py`:
```python
@dataclass
class Config:
    # Camera settings
    camera_width: int = 1280
    camera_height: int = 720
    target_fps: int = 30
    
    # Sensitivity
    sensitivity: float = 4.5
    deadzone: float = 0.003
    
    # Pinch thresholds
    mild_pinch_max: float = 0.060   # Single click
    tight_pinch_max: float = 0.035  # Double click
```

### Voice Settings
Edit `voice_assistant/config/voice_settings.json`:
```json
{
  "wake_words": ["hey assistant", "ok assistant"],
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "format": "int16"
  }
}
```

### Application Paths
Edit `voice_assistant/config/apps.json`:
```json
{
  "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "vscode": "C:\\Users\\{username}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"
}
```

## 🔧 Troubleshooting

### Common Issues

#### Camera Not Working
- Check webcam connection and drivers
- Ensure no other app is using the camera
- Try different camera indices in config

#### Voice Recognition Not Responding
- Verify microphone is working and not muted
- Check VOSK model is correctly downloaded
- Ensure wake word is clearly spoken

#### Gesture Detection Inaccurate
- Ensure good lighting conditions
- Adjust camera position for better hand visibility
- Fine-tune sensitivity parameters in config

#### PyAutoGUI Fail-safe
- The system disables PyAutoGUI fail-safe for smooth control
- Move mouse to corner of screen to emergency stop
- Use Ctrl+C in terminal to quit system

### Performance Tips
- Use good lighting for gesture recognition
- Speak clearly and at moderate pace for voice commands
- Close unnecessary background applications
- Adjust camera resolution if performance is slow

## 📁 Project Structure

```
projectnew/
├── system_launcher.py          # Main system orchestrator
├── requirements.txt            # Python dependencies
├── USER_MANUAL.md             # Detailed user manual
├── README.md                  # This file
├── gesture/                   # Gesture recognition module
│   ├── vision_working.py      # Core vision system (749 lines)
│   ├── config.py             # Configuration settings
│   ├── utils.py              # Utility functions
│   ├── gestures/             # Gesture-specific modules
│   │   ├── cursor_gesture.py     # Cursor control (106 lines)
│   │   ├── scroll_gesture.py     # Scroll detection (61 lines)
│   │   ├── task_switch_gesture.py # Task switching
│   │   └── window_control_gesture.py # Window control
│   └── gestures.txt          # Quick reference
└── voice_assistant/          # Voice control module
    ├── main.py               # Voice assistant main (420 lines)
    ├── speech/               # Speech processing
    │   ├── voice_listener.py      # Voice recognition (317 lines)
    │   ├── wake_word_detector.py  # Wake word detection
    │   └── audio_stream_manager.py # Audio management
    ├── config/               # Configuration files
    │   ├── commands.json          # Command patterns
    │   ├── voice_settings.json   # Audio settings
    │   └── apps.json             # Application paths
    ├── brightness_control/  # Brightness management
    │   ├── brightness_controller.py # Control logic
    │   └── brightness_intent_engine.py # Intent processing
    ├── volume_control/      # Volume management
    │   ├── volume_controller.py # Control logic
    │   └── volume_intent_engine.py # Intent processing
    ├── app_control/         # Application launching
    │   ├── app_launcher.py # Control logic
    │   └── app_intent_engine.py # Intent processing
    ├── system_control/      # System operations
    │   ├── system_controller.py # Control logic
    │   └── system_intent_engine.py # Intent processing
    └── commands.txt         # Command reference
```

### Component Interaction Diagram
```
┌─────────────────────────────────────────────────────────────────────┐
│                        SYSTEM LAUNCHER                             │
│                  (Process Orchestration)                           │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐        ┌────────▼────────┐
│  GESTURE MODULE │        │ VOICE ASSISTANT │
│                 │        │                 │
│ ┌─────────────┐ │        │ ┌─────────────┐ │
│ │Vision System│ │        │ │Speech Engine│ │
│ │- MediaPipe  │ │        │ │- VOSK       │ │
│ │- OpenCV     │ │        │ │- PyAudio    │ │
│ │- PyAutoGUI  │ │        │ └─────────────┘ │
│ └─────────────┘ │        │ ┌─────────────┐ │
│ ┌─────────────┐ │        │ │Controllers  │ │
│ │Gesture Mods │ │        │ │- Brightness │ │
│ │- Cursor     │ │        │ │- Volume     │ │
│ │- Scroll     │ │        │ │- Apps       │ │
│ │- Window     │ │        │ │- System     │ │
│ │- Task Switch│ │        │ └─────────────┘ │
│ └─────────────┘ │        └────────────────┘
└─────────────────┘
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **MediaPipe** for hand tracking technology
- **VOSK** for offline speech recognition
- **OpenCV** for computer vision
- **PyAutoGUI** for automation capabilities

## 📞 Support

For issues, questions, or feature requests:
- Check the troubleshooting section
- Review the user manual (`USER_MANUAL.md`)
- Create an issue in the repository

---

**Enjoy hands-free computer control! 🚀**
