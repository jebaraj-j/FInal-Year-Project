"""
controller/voice_worker.py
===========================
QThread wrapper around the existing VoiceAssistant logic.
Adds a modular shortcut-command layer before forwarding to original voice_assistant/main.py.
Original voice_assistant/main.py is NOT modified.
"""

import os
import signal
import sys
import time
import json
from difflib import SequenceMatcher
from pathlib import Path
from threading import Lock

import pyautogui
from PyQt5.QtCore import QThread, pyqtSignal

# Prevent signal errors when running in Qt thread
_signal_module = __import__("signal")
_REAL_SIGNAL_FN = _signal_module.signal

# Offline Audio Response
from voice_assistant.speaker import SPEAKER

def _say(text: str):
    """Speak text using pyttsx3 in a background thread.
    Completely silent on any error - never crashes the app.
    """
    import threading
    def _run():
        try:
            import pyttsx3
            e = pyttsx3.init()
            e.setProperty("rate", 165)
            e.setProperty("volume", 0.9)
            e.say(str(text))
            e.runAndWait()
        except Exception:
            pass
        finally:
            try:
                e.stop()
            except Exception:
                pass
    try:
        threading.Thread(target=_run, daemon=True).start()
    except Exception:
        pass
from extensions.voice_shortcut_commands import check_and_execute as shortcut_check


ADDITIONAL_VOICE_PHRASES = [
    "screenshot",
    "take screenshot",
    "capture screenshot",
    "take a screenshot",
    "capture screen",
    "save screenshot",
    "open file",
    "close file",
    "close window",
    "exit window",
    "minimize window",
    "minimize",
    "maximize window",
    "maximize",
    "maximize screen",
    "minimize screen",
    "zoom in",
    "zoom out",
    "next image",
    "previous image",
    "scroll up",
    "scroll down",
    "next page",
    "previous page",
    "go back",
    "copy",
    "paste",
    "open notepad",
    "start notepad",
    "volume up",
    "volume down",
    "volume low",
    "volume high",
    "mute",
    "unmute",
    "louder",
    "quieter",
    "brightness up",
    "brightness down",
    "brightness low",
    "brightness high",
    "dim",
    "brighter",
    "dimmer",
    "shutdown",
    "restart",
    "sleep",
    "lock screen",
    "yes",
    "no",
    "confirm",
    "cancel",
    "switch to gesture",
    "switch gesture",
    "exit gvox",
    "exit g vox",
    "switch to gesture",
    "switch gesture",
    "switch mode",
    "gesture mode",
    "gesture control",
    "open help",
    "user guide",
    "open user guide",
    "show help",
    "show commands",
    "stop nora",
    "nora stop",
    "stop listening",
    "move up",
    "move down",
    "move left",
    "move right",
    "go up",
    "go down",
    "arrow up",
    "arrow down",
    "press enter",
    "press up",
    "press down",
    "up",
    "down",
    "left",
    "right",
    "enter",
    "back",
    "next",
    "previous",
]

STRICT_CONFIRM_YES = {"yes", "confirm"}
STRICT_CONFIRM_NO = {"no", "cancel"}
STRICT_SIMILARITY = 0.82
RECOGNITION_DELAY_SEC = 0.25


class VoiceWorker(QThread):
    """
    Runs VoiceAssistant in a background thread.
    Intercepts shortcut commands and mode switch before forwarding to original logic.
    """

    action_logged = pyqtSignal(str)
    switch_to_gesture = pyqtSignal()
    exit_requested = pyqtSignal()
    critical_confirmation_requested = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    wake_word_detected = pyqtSignal(str)
    voice_status_changed = pyqtSignal(str)   # idle | listening | active
    voice_heard = pyqtSignal(str)             # last heard text
    open_help_requested = pyqtSignal()
    nora_stopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._assistant = None
        self._pending_critical = None
        self._critical_lock = Lock()
        self._strict_phrases: list[str] = []
        self._value_prefixes: list[str] = []

    def stop(self):
        self._running = False
        if self._assistant:
            try:
                self._assistant.shutdown()
            except Exception:
                pass
        self.wait(3000)

    def set_critical_confirmation_result(self, approved: bool):
        with self._critical_lock:
            pending = self._pending_critical
            self._pending_critical = None

        if not pending:
            return

        if approved:
            self.action_logged.emit(f"VOICE: {pending['label']} confirmed via popup.")
            self._execute_critical_action(pending)
        else:
            self.action_logged.emit(f"VOICE: {pending['label']} cancelled via popup.")
            _say(f"Cancelled {pending['label']}")

    def _normalize(self, text: str) -> str:
        return " ".join((text or "").lower().strip().split())

    def _best_similarity(self, text: str, phrases: list[str]) -> tuple[str, float]:
        best_phrase = ""
        best_score = 0.0
        for phrase in phrases:
            score = SequenceMatcher(None, text, phrase).ratio()
            if score > best_score:
                best_score = score
                best_phrase = phrase
        return best_phrase, best_score

    def _strict_match(self, text: str, phrases: list[str]) -> str:
        if text in phrases:
            return text
        best_phrase, best_score = self._best_similarity(text, phrases)
        if best_score >= STRICT_SIMILARITY:
            return best_phrase
        return ""

    def _contains_phrase(self, text: str, phrase: str) -> bool:
        return f" {phrase} " in f" {text} "

    def _extract_best_phrase(self, text: str, phrases: list[str]) -> str:
        # Prefer longest phrase present as whole words inside recognized text.
        matches = [p for p in phrases if self._contains_phrase(text, p)]
        if not matches:
            return ""
        matches.sort(key=lambda x: len(x), reverse=True)
        return matches[0]

    def _strip_wake_words(self, text: str) -> str:
        wake_words = [self._normalize(w) for w in self._assistant.config.get("wake_words", [])]
        cleaned = f" {text} "
        for ww in wake_words:
            if ww:
                cleaned = cleaned.replace(f" {ww} ", " ")
        return self._normalize(cleaned)

    def _is_globally_allowed_command(self, text: str) -> bool:
        if not text:
            return False
        if text in self._strict_phrases:
            return True
        if self._extract_best_phrase(text, self._strict_phrases):
            return True
        _, score = self._best_similarity(text, self._strict_phrases)
        if score >= STRICT_SIMILARITY:
            return True
        return any(text.startswith(f"{p} ") for p in self._value_prefixes)

    def _request_critical_confirmation(self, label: str, execute_cb):
        with self._critical_lock:
            self._pending_critical = {"label": label, "exec": execute_cb}
        msg = f"Say Yes to confirm {label}, or No to cancel."
        self.action_logged.emit(f"VOICE: {msg}")
        _say(msg)
        # Show visual popup so user can also click Yes/No
        self.critical_confirmation_requested.emit(label)

    def _execute_critical_action(self, pending):
        try:
            pending["exec"]()
        except Exception as exc:
            self.action_logged.emit(f"VOICE: Critical action failed: {exc}")

    def _handle_pending_voice_confirmation(self, text: str) -> bool:
        with self._critical_lock:
            pending = self._pending_critical

        if not pending:
            return False

        label = pending["label"].lower()
        yes_phrases = set(STRICT_CONFIRM_YES)
        yes_phrases.add(f"{label} now")
        no_phrases = set(STRICT_CONFIRM_NO)

        if text in yes_phrases:
            with self._critical_lock:
                self._pending_critical = None
            self.action_logged.emit(f"VOICE: {pending['label']} confirmed by voice.")
            self._execute_critical_action(pending)
            return True

        if text in no_phrases:
            with self._critical_lock:
                self._pending_critical = None
            self.action_logged.emit(f"VOICE: {pending['label']} cancelled by voice.")
            _say(f"Cancelled {pending['label']}")
            return True

        self.action_logged.emit("VOICE: Awaiting explicit confirmation: say yes/confirm or no/cancel.")
        return True

    def _try_open_folder(self, folder_name: str) -> bool:
        """Open a folder by spoken name. Checks known folders then Desktop/Downloads subfolders."""
        import os, subprocess
        known = {
            "desktop":    os.path.expandvars("%USERPROFILE%\\Desktop"),
            "downloads":  os.path.expandvars("%USERPROFILE%\\Downloads"),
            "documents":  os.path.expandvars("%USERPROFILE%\\Documents"),
            "pictures":   os.path.expandvars("%USERPROFILE%\\Pictures"),
            "videos":     os.path.expandvars("%USERPROFILE%\\Videos"),
            "music":      os.path.expandvars("%USERPROFILE%\\Music"),
            "this pc":    "shell:MyComputerFolder",
            "my computer":"shell:MyComputerFolder",
        }
        # 1. Known folder
        target = known.get(folder_name.lower())
        if target:
            subprocess.Popen(["explorer.exe", target], shell=False)
            return True
        # 2. Subfolder inside Desktop / Downloads / Documents
        for base in ["Desktop", "Downloads", "Documents"]:
            path = os.path.expandvars(f"%USERPROFILE%\\{base}\\{folder_name}")
            if os.path.isdir(path):
                subprocess.Popen(["explorer.exe", path], shell=False)
                return True
        # 3. Absolute path spoken
        if os.path.isdir(folder_name):
            subprocess.Popen(["explorer.exe", folder_name], shell=False)
            return True
        return False

    def run(self):
        """Start the voice assistant in this thread."""
        self._running = True

        # Patch signal() to be a no-op so VoiceAssistant doesn't break in a Qt thread
        def _noop_signal(sig, handler):
            pass

        _signal_module.signal = _noop_signal

        try:
            # Add voice_assistant dir to path
            va_dir = Path(__file__).parent.parent / "voice_assistant"
            if str(va_dir) not in sys.path:
                sys.path.insert(0, str(va_dir))

            from voice_assistant.main import VoiceAssistant

            self._assistant = VoiceAssistant()
            # Ensure VOSK model path resolves correctly in UI mode.
            model_path = self._assistant.config.get("recognition", {}).get("model_path", "")
            if model_path and not Path(model_path).is_absolute():
                abs_model_path = (va_dir / model_path).resolve()
                self._assistant.config["recognition"]["model_path"] = str(abs_model_path)
                self._assistant.voice_listener.config["recognition"]["model_path"] = str(abs_model_path)

            # Raise confidence gates to reduce accidental triggers.
            self._assistant.command_confidence_threshold = max(self._assistant.command_confidence_threshold, 0.85)
            self._assistant.base_command_threshold = max(self._assistant.base_command_threshold, 0.85)
            self._assistant.app_command_threshold = max(self._assistant.app_command_threshold, 0.90)
            self._assistant.system_command_threshold = max(self._assistant.system_command_threshold, 0.90)

            # Slightly stronger silence/noise gate.
            self._assistant.voice_listener.audio_manager.silence_threshold = max(
                self._assistant.voice_listener.audio_manager.silence_threshold,
                420,
            )

            self.action_logged.emit("Voice Mode started - say a wake word.")

            # Build strict phrase bank from configured patterns.
            commands_cfg = self._assistant.commands_config
            strict_phrases = set(ADDITIONAL_VOICE_PHRASES)
            value_prefixes = set()
            for category_cfg in commands_cfg.values():
                for action_cfg in category_cfg.get("actions", {}).values():
                    for pattern in action_cfg.get("patterns", []):
                        p = self._normalize(pattern)
                        if "{value}" in p:
                            value_prefixes.add(self._normalize(p.replace("{value}", "")).strip())
                            continue
                        if p:
                            strict_phrases.add(p)
            self._strict_phrases = sorted(strict_phrases)
            self._value_prefixes = sorted(x for x in value_prefixes if x)

            # Patch execute_action methods to surface voice activity in UI log.
            for category, controller in self._assistant.controllers.items():
                if not hasattr(controller, "execute_action"):
                    continue
                original_exec = controller.execute_action

                def _make_exec_wrapper(cat, orig_fn):
                    def _wrapped(action, *args, **kwargs):
                        self.action_logged.emit(f"VOICE EXEC: {cat}.{action}")
                        ok = orig_fn(action, *args, **kwargs)
                        self.action_logged.emit(
                            f"VOICE {'OK' if ok else 'FAILED'}: {cat}.{action}"
                        )
                        return ok
                    return _wrapped

                controller.execute_action = _make_exec_wrapper(category, original_exec)

            # Extend grammar at runtime with additional shortcut phrases.
            def patched_get_grammar():
                merged = set()
                # Wake words: add full phrase AND each individual token
                for ww in self._assistant.config.get("wake_words", []):
                    p = self._normalize(ww)
                    if p:
                        merged.add(p)
                        for tok in p.split():
                            merged.add(tok)
                # Confirmation words
                merged.update(["yes", "no", "confirm", "cancel"])
                # Command patterns: add full phrase AND each individual token
                for category in self._assistant.commands_config.values():
                    actions = category.get("actions", {})
                    for action in actions.values():
                        for pattern in action.get("patterns", []):
                            p = self._normalize(str(pattern).replace("{value}", "").strip())
                            if p:
                                merged.add(p)
                                for tok in p.split():
                                    merged.add(tok)
                # Extension phrases and their tokens
                for phrase in ADDITIONAL_VOICE_PHRASES:
                    p = phrase.lower().strip()
                    if p:
                        merged.add(p)
                        for tok in p.split():
                            merged.add(tok)
                # Small number words for {value} commands
                for num in (
                    "zero one two three four five six seven eight nine ten "
                    "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
                    "thirty forty fifty sixty seventy eighty ninety hundred"
                ).split():
                    merged.add(num)
                # Allow unknown tokens so recognizer remains robust.
                merged.add("[unk]")
                return sorted(merged)

            self._assistant._get_compiled_grammar = patched_get_grammar

            # Patch _process_command to intercept additional shortcuts + switch signal
            original_process = self._assistant._process_command

            def patched_process(command_text: str):
                try:
                    _patched_process_inner(command_text)
                except Exception as _exc:
                    self.action_logged.emit(f"VOICE ERROR: {_exc}")

            def _patched_process_inner(command_text: str):
                time.sleep(RECOGNITION_DELAY_SEC)
                text = self._normalize(command_text)
                text = self._strip_wake_words(text)
                try:
                    text = self._assistant.voice_listener._clean_transcript(text)
                except Exception:
                    pass
                compact = text.replace(" ", "").replace("-", "")

                # Always show what was recognized in command log panel.
                if text:
                    self.action_logged.emit(f"VOICE HEARD: {text}")
                    self.voice_heard.emit(text)
                    self.voice_status_changed.emit("active")

                # Pending critical confirmation has highest priority.
                if self._handle_pending_voice_confirmation(text):
                    return

                # 0) Exit command -> confirmation required
                if compact in {"exitgvox", "quitgvox", "closegvox"}:
                    self._request_critical_confirmation("exit gvox", self.exit_requested.emit)
                    return

                # 1) Strict direct command matching (exact or >= 90% similar)
                strict_actions = {
                    "open notepad": lambda: self._assistant.controllers["app_launcher"].execute_action("open_notepad"),
                    "start notepad": lambda: self._assistant.controllers["app_launcher"].execute_action("open_notepad"),
                    "close window": lambda: pyautogui.hotkey("alt", "f4"),
                    "exit window": lambda: pyautogui.hotkey("alt", "f4"),
                    "minimize window": lambda: pyautogui.hotkey("win", "down"),
                    "minimize": lambda: pyautogui.hotkey("win", "down"),
                    "maximize window": lambda: pyautogui.hotkey("win", "up"),
                    "maximize": lambda: pyautogui.hotkey("win", "up"),
                    "volume up": lambda: self._assistant.controllers["volume"].execute_action("relative_increase", 0),
                    "louder": lambda: self._assistant.controllers["volume"].execute_action("relative_increase", 0),
                    "volume high": lambda: self._assistant.controllers["volume"].execute_action("absolute_increase", 0),
                    "volume down": lambda: self._assistant.controllers["volume"].execute_action("relative_decrease", 0),
                    "quieter": lambda: self._assistant.controllers["volume"].execute_action("relative_decrease", 0),
                    "volume low": lambda: self._assistant.controllers["volume"].execute_action("absolute_decrease", 0),
                    "mute": lambda: self._assistant.controllers["volume"].execute_action("absolute_decrease", 0),
                    "brightness up": lambda: self._assistant.controllers["brightness"].execute_action("relative_increase", 0),
                    "brighter": lambda: self._assistant.controllers["brightness"].execute_action("relative_increase", 0),
                    "brightness high": lambda: self._assistant.controllers["brightness"].execute_action("absolute_increase", 0),
                    "brightness down": lambda: self._assistant.controllers["brightness"].execute_action("relative_decrease", 0),
                    "dimmer": lambda: self._assistant.controllers["brightness"].execute_action("relative_decrease", 0),
                    "dim": lambda: self._assistant.controllers["brightness"].execute_action("relative_decrease", 0),
                    "brightness low": lambda: self._assistant.controllers["brightness"].execute_action("absolute_decrease", 0),
                }
                strict_phrases = list(strict_actions.keys())
                matched_phrase = self._strict_match(text, strict_phrases) or self._extract_best_phrase(text, strict_phrases)
                if matched_phrase:
                    strict_actions[matched_phrase]()
                    self.action_logged.emit(f"VOICE: {matched_phrase}")
                    return

                # 2) Critical system commands require explicit confirmation popup.
                critical_actions = {
                    "shutdown": lambda: self._assistant.controllers["system_control"].execute_action("shutdown", 0),
                    "restart": lambda: self._assistant.controllers["system_control"].execute_action("restart", 0),
                    "sleep": lambda: self._assistant.controllers["system_control"].execute_action("sleep", 0),
                    "lock screen": lambda: self._assistant.controllers["system_control"].execute_action("lock", 0),
                }
                critical_keys = list(critical_actions.keys())
                critical_phrase = self._strict_match(text, critical_keys) or self._extract_best_phrase(text, critical_keys)
                if critical_phrase:
                    self._request_critical_confirmation(critical_phrase, critical_actions[critical_phrase])
                    return

                # 3a) Dynamic folder open: "open <foldername>"
                if text.startswith("open ") and len(text.split()) >= 2:
                    folder_name = text[5:].strip()
                    if self._try_open_folder(folder_name):
                        self.action_logged.emit(f"VOICE: Opened folder '{folder_name}'")
                        return

                # 3) Additional shortcut command layer (exact only in extension module)
                handled, msg = shortcut_check(text)
                if handled:
                    self.action_logged.emit(f"VOICE: {msg}")
                    return

                # 4) Mode switch — checked BEFORE strict gates so it always works
                switch_phrases = {
                    "switch to gesture", "switch gesture", "switch mode",
                    "gesture mode", "go to gesture", "gesture control"
                }
                if text in switch_phrases or any(text.startswith(p) for p in switch_phrases):
                    self.action_logged.emit("VOICE: Switching to Gesture Mode...")
                    _say("Switching to Gesture Mode")
                    self.switch_to_gesture.emit()
                    return

                # 4b) Help / User Guide — checked BEFORE strict gates
                help_phrases = {
                    "open help", "user guide", "open user guide",
                    "show help", "open guide", "voice commands", "show commands"
                }
                if text in help_phrases or any(p in text for p in help_phrases):
                    self.action_logged.emit("VOICE: Opening User Guide...")
                    self.open_help_requested.emit()
                    return

                # Reset to listening after command processed
                self.voice_status_changed.emit("listening")
                self.voice_heard.emit("")

                # 5) Allow yes/no through when confirmation is pending
                with self._critical_lock:
                    has_pending = self._pending_critical is not None

                # 6) Global strict-gate for all remaining commands.
                if not self._is_globally_allowed_command(text):
                    self.action_logged.emit("VOICE: Rejected non-strict phrase.")
                    return

                # 7) Everything else -> original handler
                forwarded = self._extract_best_phrase(text, self._strict_phrases) or text
                original_process(forwarded)

            self._assistant._process_command = patched_process

            # Wire stop-word callback
            def _on_stop_word():
                self.action_logged.emit("VOICE: Nora stopped. Say a wake word to start again.")
                self.voice_status_changed.emit("idle")
                self.voice_heard.emit("")
                self.nora_stopped.emit()
            self._assistant.voice_listener.on_stop_word = _on_stop_word

            # Patch _enter_active_mode to log wake word detection in UI
            original_enter_active = self._assistant.voice_listener._enter_active_mode
            def patched_enter_active():
                original_enter_active()
                self.action_logged.emit("Wake word detected - listening for command...")
                self.wake_word_detected.emit("active")
                self.voice_status_changed.emit("listening")
            self._assistant.voice_listener._enter_active_mode = patched_enter_active

            # Start listening
            self._assistant.start()
            if not getattr(self._assistant, "is_running", False):
                msg = "Voice listener failed to start. Check microphone device and audio settings."
                self.error_occurred.emit(msg)
                self.action_logged.emit(f"Voice Error: {msg}")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.action_logged.emit(f"Voice Error: {e}")
        finally:
            _signal_module.signal = _REAL_SIGNAL_FN
            self._running = False
