# G-Vox User Manual

## Starting the App

```powershell
python main.py
```
or double-click `run.bat`

The app opens in **Gesture Mode** automatically.

---

## Modes Overview

| Mode | How to activate |
|------|----------------|
| Gesture Mode | Default on startup, or say `"gesture mode"` / `"switch to gesture"` |
| Voice Mode | Left hand gesture (thumb + index + middle, hold 1.5s), or click **VOICE CONTROL** button |
| Stop | Click **Stop** button |

---

## Gesture Mode

### Right Hand — Cursor & Click

| Gesture | Action |
|---------|--------|
| Index finger only | Move cursor |
| Mild thumb + index pinch | Single click |
| Tight thumb + index pinch (quick release) | Double click |
| Tight thumb + index pinch (hold) | Drag & drop |
| Ring + pinky extended, index + middle folded (hold 0.7s) | Right click |
| Index + middle extended | Scroll |

### Left Hand — Window & System

| Gesture | Action |
|---------|--------|
| Thumb + index pinch, middle/ring/pinky extended (hold 1s) | Alt+Tab task switch |
| Pinky only (hold 1s) | Copy (Ctrl+C) |
| Ring + pinky (hold 1s) | Paste (Ctrl+V) |
| Thumb only (hold 1s) | Minimize window |
| Open palm — all fingers (hold 1s) | Maximize window |
| Thumb + index + middle extended, ring + pinky closed (hold 1.5s) | **Switch to Voice Mode** |
| Both fists — left + right (hold 3s) | Exit G-Vox |

---

## Voice Mode

### Wake Words

Say one of these to activate Nora:

```
"Hey Nora"
"OK Nora"
"Hi Nora"
"Hello Nora"
"Nora On"
```

After the wake word, the Recognition Status panel shows **"Listening..."** with an animated wave. Say your command immediately — no need to repeat the wake word for each command.

### Stop Listening

Say any of these to put Nora back to sleep (wake word required again):

```
"Stop Nora"
"Nora Stop"
"Stop Listening"
```

The UI resets to **"Waiting for wake word..."**

### Switch Back to Gesture Mode

```
"Switch to Gesture"
"Switch Gesture"
"Switch Mode"
"Gesture Mode"
"Gesture Control"
"Go to Gesture"
```

---

## Voice Commands Reference

> **Note:** Single-word commands are only accepted for the specific words listed below. All other commands require at least 2 words to avoid accidental triggers.

### Window Control

| Say | Action |
|-----|--------|
| `"minimize"` / `"minimize window"` | Minimize active window |
| `"maximize"` / `"maximize window"` / `"maximize screen"` | Maximize active window |
| `"close window"` / `"exit window"` | Close active window (Alt+F4) |
| `"screenshot"` | Take screenshot |
| `"scroll up"` / `"scroll down"` | Scroll page |
| `"zoom in"` / `"zoom out"` | Zoom |
| `"go back"` | Navigate back |
| `"copy"` / `"paste"` | Clipboard |
| `"next page"` / `"previous page"` | Page navigation |
| `"next image"` / `"previous image"` | Image navigation |

### Volume

| Say | Action |
|-----|--------|
| `"volume up"` / `"louder"` | Increase volume by 10% |
| `"volume down"` / `"quieter"` | Decrease volume by 10% |
| `"volume high"` | Set volume to 100% |
| `"volume low"` / `"mute"` | Set volume to 0% |
| `"set volume fifty"` | Set volume to exact % (say number as word) |

### Brightness

| Say | Action |
|-----|--------|
| `"brightness up"` / `"brighter"` | Increase brightness by 10% |
| `"brightness down"` / `"dimmer"` / `"dim"` | Decrease brightness by 10% |
| `"brightness high"` | Set brightness to 100% |
| `"brightness low"` | Set brightness to 0% |
| `"set brightness seventy"` | Set brightness to exact % |

### Applications

| Say | Action |
|-----|--------|
| `"open chrome"` / `"launch chrome"` / `"open browser"` | Open Chrome |
| `"close chrome"` | Close Chrome |
| `"open notepad"` / `"start notepad"` | Open Notepad |
| `"close notepad"` | Close Notepad |
| `"open settings"` / `"open system settings"` | Open Windows Settings |
| `"close settings"` | Close Settings |
| `"open explorer"` / `"open file explorer"` / `"open files"` | Open File Explorer |
| `"close file explorer"` | Close File Explorer |

### Folders

| Say | Action |
|-----|--------|
| `"open desktop"` / `"go to desktop"` | Open Desktop folder |
| `"open downloads"` / `"go to downloads"` | Open Downloads folder |
| `"open documents"` / `"go to documents"` | Open Documents folder |
| `"open pictures"` / `"go to pictures"` | Open Pictures folder |
| `"open videos"` / `"go to videos"` | Open Videos folder |
| `"open music"` / `"go to music"` | Open Music folder |
| `"open ProjectFiles"` | Opens a subfolder named "ProjectFiles" from Desktop/Downloads/Documents |

> **Dynamic folders:** When File Explorer is open, say `"open <folder name>"` to navigate to any subfolder found inside Desktop, Downloads, or Documents.

### System Commands

System commands require voice confirmation — a dialog appears and Nora speaks the confirmation prompt.

| Say | Action |
|-----|--------|
| `"shutdown"` / `"shut down"` / `"power off"` | Shutdown PC |
| `"restart"` / `"reboot"` | Restart PC |
| `"sleep"` / `"sleep mode"` / `"hibernate"` | Sleep PC |
| `"lock"` / `"lock screen"` | Lock screen |

**Confirmation flow:**
1. Say `"shutdown"` → dialog appears + Nora says *"Say Yes to confirm shutdown, or No to cancel"*
2. Say `"yes"` or click **Yes** → executes
3. Say `"no"` or click **No** → cancelled, dialog closes

### Help

| Say | Action |
|-----|--------|
| `"open help"` / `"show help"` | Open User Guide dialog |
| `"user guide"` / `"open user guide"` | Open User Guide dialog |
| `"show commands"` / `"voice commands"` | Open User Guide dialog |

### Exit App

| Say | Action |
|-----|--------|
| `"exit gvox"` / `"exit g vox"` | Exit G-Vox (with confirmation) |

---

## Recognition Status Panel

The right-side **Recognition Status** panel changes based on the active mode:

**Gesture Mode:**
- Shows detected gesture name, subtitle, and confidence %
- Hold progress bar for timed gestures

**Voice Mode:**
- Animated wave bars — flat when idle, animated when listening
- Status label:
  - `"Waiting for wake word..."` — idle, say a wake word
  - `"🎙 Listening..."` — wake word detected, say a command
  - `"⚡ Processing command..."` — command heard, executing
- Last heard text shown below the wave

---

## Commands Log Panel

All activity is logged with timestamps in the **Commands Log** panel (bottom-right):

| Log entry | Meaning |
|-----------|---------|
| `Voice Mode started - say a wake word to begin.` | Voice mode just activated |
| `Wake word detected - listening for command...` | Nora heard the wake word |
| `VOICE HEARD: open chrome` | What Nora understood |
| `VOICE OK: app_launcher.open_chrome` | Command executed successfully |
| `VOICE: Say Yes to confirm shutdown...` | Confirmation requested |
| `Nora stopped. Say a wake word to start again.` | Stop word was spoken |

Click **Clear** to clear the log.

---

## Camera Panel (Voice Mode)

When Voice Mode is active, the camera feed stops and the panel displays:

- **Idle:** Wake word instructions
- **After wake word:** `"🎙 WAKE WORD DETECTED — Listening for your command..."`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Nora not responding | Check microphone is not muted; say wake word clearly |
| Wrong command executed | Speak clearly with 2+ words; avoid background noise |
| "Listening timed out" | No longer happens — Nora stays active until you say `"Stop Nora"` |
| Shutdown dialog not closing | Say `"no"` clearly or click the **No** button |
| Switch to gesture not working | Say `"switch mode"` or `"gesture mode"` — both work |
| Camera not showing in voice mode | Expected — camera is off in voice mode to save resources |
| Volume/brightness changing unexpectedly | Only `"volume up"` / `"volume down"` trigger relative changes; avoid saying just `"up"` or `"down"` |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `voice_assistant/config/voice_settings.json` | Wake words, audio settings, thresholds |
| `voice_assistant/config/commands.json` | All voice command patterns |
| `voice_assistant/config/apps.json` | Application and folder paths |
| `gesture/config.py` | Camera resolution, sensitivity, pinch thresholds |

### Changing Wake Words
Edit `voice_settings.json`:
```json
"wake_words": ["hey nora", "ok nora", "hi nora", "hello nora", "nora on"]
```

### Adding a Custom App
Edit `apps.json`:
```json
"vscode": "C:\\Users\\<username>\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"
```
Then add patterns to `commands.json` under `app_launcher.actions`.

---

## Keyboard Shortcuts (Gesture Mode Camera Window)

| Key | Action |
|-----|--------|
| `H` | Toggle help overlay |
| `S` | Take screenshot |
| `Q` | Quit |
