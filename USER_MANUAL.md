# 🖐️ Gesture & Voice Control System - User Manual

Welcome to your advanced, process-level mode switching control system. This manual explains how to use both **Gesture Mode** and **Voice Mode** effectively.

---

## 🚀 Getting Started

To launch the system, open a terminal in the project root and run:
```powershell
python system_launcher.py
```
By default, the system starts in **Gesture Mode**.

---

## 🔄 Mode Switching (The Bridge)

The system is designed to run only one mode at a time to save resources and prevent conflicts.

### **Gesture Mode ➔ Voice Mode**
*   **Gesture**: Left hand, **Thumb + Index + Middle** fingers extended (Ring + Pinky closed).
*   **Action**: Hold this gesture for **1.5 seconds**.
*   **Feedback**: A yellow progress bar will fill at the top of the camera window.

### **Voice Mode ➔ Gesture Mode**
*   **Command**: Say "Switch to gesture" or "Switch gesture".
*   **Action**: The voice assistant will close, and the camera window will reactivate automatically.

---

## 🖱️ Gesture Mode Reference (Right Hand)

Control your cursor, clicks, and scrolling with your primary hand.

| Action | Gesture |
| :--- | :--- |
| **Move Cursor** | ONLY Index finger extended. |
| **Single Click** | Mild pinch (Thumb + Index). |
| **Double Click** | Quick tight pinch (Thumb + Index) and release (<0.3s). |
| **Drag & Drop** | Hold tight pinch (Thumb + Index) for >0.35s to grab. Release to drop. |
| **Right Click** | Pinch Thumb + Middle finger. |
| **Scroll Mode** | Extend Index + Middle fingers together. Move hand up/down. |

---

## 🪟 Gesture Mode Reference (Left Hand)

Manage your windows and tasks with your left hand.

| Action | Gesture |
| :--- | :--- |
| **Minimize Window** | Closed fist. |
| **Maximize Window** | Open palm. |
| **Task Switching** | Pinch Thumb + Index (Alt+Tab). Hold to cycle, release to select. |
| **Mode Switch** | Thumb + Index + Middle extended (Hold 1.5s). |

---

## 🎙️ Voice Mode Reference

Once in voice mode, say a wake word (e.g., "Hey Assistant") followed by a command.

### **Common Commands**
*   **Brightness**: "Increase brightness", "Set brightness to 50%", "Maximum brightness".
*   **Volume**: "Volume up", "Mute sound", "Set volume to 80%".
*   **Applications**: "Open Chrome", "Launch VS Code", "Open Notepad".
*   **System**: "Lock computer", "Put system to sleep", "Shutdown pc".
*   **Help**: Say "Help" or "Show commands" to see the full list in the terminal.

---

## ⌨️ Keyboard Shortcuts (Camera Window)
*   **H**: Toggle on-screen Help Overlay.
*   **S**: Take a screenshot of the current view.
*   **Q**: Quit the entire system.
