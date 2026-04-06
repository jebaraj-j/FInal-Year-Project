# G-Vox User Manual

## Start
Run from project root:

```powershell
python main.py
```

or

```powershell
run.bat
```

System starts in Gesture Mode.

## Modes
- Gesture to Voice: left thumb + index + middle extended (ring/pinky closed), hold 1.5s.
- Voice to Gesture: say `switch to gesture` (or `switch gesture`, `switch mode`).

## Exit
- Gesture exit: close both left and right palms (both fists), hold 3s.
- Voice exit: say `exit gvox` (or `exit g vox`).
- Exit command closes G-Vox directly.

## Gesture Controls
### Right Hand
- Index only: move cursor
- Mild thumb-index pinch: single click
- Tight thumb-index quick release: double click
- Tight thumb-index hold: drag/drop
- Ring + pinky extended, index + middle folded (hold 0.7s): right click
- Index + middle extended: scroll

### Left Hand
- Thumb-index pinch + middle/ring/pinky extended (hold 1s): Alt+Tab task switch
- Pinky only (hold 1s): copy (Ctrl+C)
- Ring + pinky (hold 1s): paste (Ctrl+V)
- Thumb only (hold 1s): minimize window
- Open palm (all fingers, hold 1s): maximize window
- Thumb + index + middle extended (ring/pinky closed, hold 1.5s): switch to voice mode
- Both fists (left + right, hold 3s): exit G-Vox

## Voice Controls
Use wake word first:
- `hey nora`
- `ok nora`
- `hi nora`
- `hello nora`
- `nora on`

### Core
- `screenshot`
- `open file`, `close file`, `close`, `minimize`, `maximize`
- `zoom in`, `zoom out`
- `next image`, `previous image`
- `scroll up`, `scroll down`
- `next page`, `previous page`
- `up`, `down`, `left`, `right`, `next`, `previous`
- `open` / `enter` -> press Enter
- `go back` -> Alt+Left (fallback Backspace)
- `copy` -> Ctrl+C
- `paste` -> Ctrl+V

### Media
- `play`, `pause`, `play video`, `pause video`
- `next track`, `previous track`

### Applications
- Open/close Chrome
- Open/close Notepad
- Open/close Settings
- Open/close File Explorer

### System
- Shutdown, restart, sleep, lock
- Confirmation required by repeating the same command:
  - `shutdown` -> say `shutdown` again to confirm
  - `restart` -> say `restart` again to confirm
  - `sleep` -> say `sleep` again to confirm
  - `lock` -> say `lock` again to confirm

## UI Notes
- Right side panel:
  - Top: Recognition Status
  - Bottom: Commands Log
- Camera panel is expanded for larger live feed.
- Notifications appear in app and as system tray popups (bottom-right).

## Full Command Reference
- In app: click `Help`
- File: `voice_assistant/commands.txt`
