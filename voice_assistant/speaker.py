"""
voice_assistant/speaker.py
===========================
Offline TTS using pyttsx3 (no internet required).
Male-preferred voice, runs in a background thread to avoid UI blocking.
"""

import threading
import queue

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False


class _Speaker:
    """Thread-safe offline TTS speaker."""

    def __init__(self):
        self._q      = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        if not _TTS_AVAILABLE:
            return
        try:
            engine = pyttsx3.init()
            # Prefer a male voice; gracefully fall back to default if unavailable.
            voices = engine.getProperty("voices")
            selected_voice_id = None
            for v in voices:
                name = v.name.lower()
                if any(k in name for k in ("david", "mark", "male", "guy", "james", "richard", "george")):
                    selected_voice_id = v.id
                    break
            if selected_voice_id:
                engine.setProperty("voice", selected_voice_id)
            engine.setProperty("rate", 170)
            engine.setProperty("volume", 0.9)

            while True:
                text = self._q.get()
                if text is None:
                    break
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    pass
        except Exception:
            pass

    def say(self, text: str):
        """Queue a phrase to be spoken offline."""
        if _TTS_AVAILABLE:
            # Clear backlog if too many queued
            while self._q.qsize() > 2:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
            self._q.put(str(text))

    def stop(self):
        self._q.put(None)


# Global singleton
SPEAKER = _Speaker()
