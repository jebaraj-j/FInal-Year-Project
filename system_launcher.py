import subprocess
import time
import sys
import os
import signal
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.absolute()
GESTURE_SCRIPT = PROJECT_ROOT / "gesture" / "vision_working.py"
VOICE_SCRIPT = PROJECT_ROOT / "voice_assistant" / "main.py"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

class SystemController:
    def __init__(self):
        self.mode = "gesture"
        self.gesture_process = None
        self.voice_process = None
        self.last_switch_time = 0
        self.cooldown = 2.0  # 2 second cooldown
        # Prefer project-local virtual environment interpreter when available.
        self.python_exec = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    def stop_all(self):
        """Safely terminate any running processes."""
        for p in [self.gesture_process, self.voice_process]:
            if p and p.poll() is None:
                print(f"Terminating process: {p.pid}")
                # Use platform-specific termination to be gentle
                if sys.platform == "win32":
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    p.terminate()
                
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                    
        self.gesture_process = None
        self.voice_process = None

    def start_gesture_mode(self):
        print("\n🚀 STARTING GESTURE MODE...")
        self.stop_all()
        # Create-Process for Window console events support
        # Set environment for UTF-8 support
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        self.gesture_process = subprocess.Popen(
            [self.python_exec, str(GESTURE_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            encoding='utf-8',
            env=env
        )
        self.mode = "gesture"
        self.last_switch_time = time.time()

    def start_voice_mode(self):
        print("\n🎙️ STARTING VOICE MODE...")
        self.stop_all()
        
        # Note: we change CWD for voice assistant as it expects it
        # Set environment for UTF-8 support
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        self.voice_process = subprocess.Popen(
            [self.python_exec, str(VOICE_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(PROJECT_ROOT / "voice_assistant"),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            encoding='utf-8',
            env=env
        )
        self.mode = "voice"
        self.last_switch_time = time.time()

    def run(self):
        """Main orchestrator loop."""
        self.start_gesture_mode()
        
        try:
            while True:
                active_process = self.gesture_process if self.mode == "gesture" else self.voice_process
                
                # Always attempt to read available output
                if active_process:
                    line = active_process.stdout.readline()
                    if line:
                        print(f"[{self.mode.upper()}] {line.strip()}")
                        
                        # Monitor for signals
                        if "[SYSTEM_SIGNAL]:SWITCH_TO_VOICE" in line:
                            if time.time() - self.last_switch_time > self.cooldown:
                                self.start_voice_mode()
                                continue # Skip the poll check for the old process
                            else:
                                print("Switch blocked by cooldown...")
                                
                        elif "[SYSTEM_SIGNAL]:SWITCH_TO_GESTURE" in line:
                            if time.time() - self.last_switch_time > self.cooldown:
                                self.start_gesture_mode()
                                continue # Skip the poll check for the old process
                            else:
                                print("Switch blocked by cooldown...")
                                
                # After checking for signals in output, see if the process actually died
                if active_process and active_process.poll() is not None:
                    # Final check: is the mode still what it was? (Did a signal just change it?)
                    if (self.mode == "gesture" and active_process == self.gesture_process) or \
                       (self.mode == "voice" and active_process == self.voice_process):
                        print(f"Warning: {self.mode} process exited with code {active_process.returncode}")
                        time.sleep(1)
                        # Restart current mode
                        if self.mode == "gesture": self.start_gesture_mode()
                        else: self.start_voice_mode()
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nStopping system controller...")
        finally:
            self.stop_all()

if __name__ == "__main__":
    controller = SystemController()
    controller.run()
