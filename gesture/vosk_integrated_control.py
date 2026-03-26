"""
Vosk Integrated Control System
=============================
Integration of Vosk voice control with gesture recognition for Python 3.13+.
"""

import threading
import time
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main function for Vosk integrated control."""
    print("🎤🤚 Vosk Voice + Gesture Control System")
    print("=" * 50)
    print("✅ Using Vosk for Python 3.13+ compatibility")
    
    # Try to import Vosk voice controller
    try:
        from voice.vosk_voice_controller import VoskVoiceController
        VOICE_AVAILABLE = True
        print("✅ Vosk voice control available")
    except ImportError as e:
        print(f"⚠ Vosk voice control not available: {e}")
        VOICE_AVAILABLE = False
    
    # Try to import gesture control
    try:
        # Import here to avoid circular imports
        import cv2
        import mediapipe as mp
        from vision_working import main as gesture_main
        GESTURE_AVAILABLE = True
        print("✅ Gesture recognition available")
    except ImportError as e:
        print(f"⚠ Gesture recognition not available: {e}")
        GESTURE_AVAILABLE = False
    
    if not VOICE_AVAILABLE and not GESTURE_AVAILABLE:
        print("❌ No control systems available")
        return
    
    print("\n🎯 Starting available control systems...")
    
    # Start voice control if available
    voice_controller = None
    if VOICE_AVAILABLE:
        try:
            voice_controller = VoskVoiceController()
            voice_thread = threading.Thread(target=voice_controller.start_listening, daemon=True)
            voice_thread.start()
            print("✅ Voice control started")
        except Exception as e:
            print(f"⚠ Failed to start voice control: {e}")
            VOICE_AVAILABLE = False
    
    # Start gesture control if available
    if GESTURE_AVAILABLE:
        try:
            print("✅ Starting gesture recognition...")
            # Note: This will block the main thread
            # In a real integration, you'd want to run this in a separate thread
            # and manage both systems properly
            print("💡 Gesture control would start here")
            print("💡 For now, demonstrating voice control only")
        except Exception as e:
            print(f"⚠ Failed to start gesture control: {e}")
    
    if VOICE_AVAILABLE:
        print("\n🎤 Voice Control Active!")
        print("💡 Try these commands:")
        print("   • 'brightness up' / 'brightness down'")
        print("   • 'set brightness to 50 percent'")
        print("   • 'set brightness to maximum' / 'minimum'")
        print("   • Press Ctrl+C to stop")
        
        try:
            # Keep main thread alive for voice control
            while voice_controller and voice_controller.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopping voice control...")
            if voice_controller:
                voice_controller.stop_listening()
    
    print("\n🎉 Vosk integrated control system stopped")


if __name__ == "__main__":
    main()
