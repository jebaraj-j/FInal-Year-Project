"""
Gesture worker thread.
Wraps the existing gesture module and adds app-level signals for UI/controller.
"""

import sys
import time
from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from PyQt5.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal
from PyQt5.QtGui import QImage

from extensions.left_hand_extensions import LeftHandExtensions

GESTURE_DIR = Path(__file__).parent.parent / "gesture"
if str(GESTURE_DIR) not in sys.path:
    sys.path.insert(0, str(GESTURE_DIR))

from vision_working import (  # noqa: E402
    CFG,
    FINGER_DEFS,
    ImageEnhancer,
    LandmarkSmoother,
    Palette,
    draw_finger_panel,
    draw_hud,
    draw_skeleton_and_line,
    is_finger_extended,
    open_camera,
)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01


class GestureWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    gesture_detected = pyqtSignal(str, str, int)
    hand_present = pyqtSignal(bool)
    fps_updated = pyqtSignal(float)
    action_logged = pyqtSignal(str)
    gesture_triggered = pyqtSignal(str, str)  # (label, icon)
    switch_to_voice = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._mutex = QMutex()

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(3000)

    def run(self):
        self._running = True
        cfg = CFG
        enhancer = ImageEnhancer(cfg)
        smoother = LandmarkSmoother(cfg.smoothing_alpha)
        lh_ext = LeftHandExtensions()
        cursor_sensitivity = cfg.sensitivity * 0.85  # slightly slower cursor movement

        cap, _ = open_camera(cfg)
        if cap is None:
            self.action_logged.emit("ERROR: No camera found.")
            return

        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=cfg.max_num_hands if hasattr(cfg, "max_num_hands") else cfg.max_hands,
            model_complexity=cfg.model_complexity,
            min_detection_confidence=cfg.min_detection_conf,
            min_tracking_confidence=cfg.min_tracking_conf,
        )

        frame_count = 0
        detected_count = 0
        start_time = time.time()
        det_history = deque(maxlen=cfg.history_size)

        # Right-hand state
        is_cursor_mode = False
        prev_index_norm = None
        pinch_state = "open"
        is_dragging = False
        right_click_active = False
        right_click_hold_start = None
        pinch_start_time = 0.0
        hard_pinch_active = False
        mild_pinch_start_time = 0.0
        mild_click_fired = False
        red_hold_confirmed = False
        red_doubleclick_fired = False
        red_last_index_norm = None
        drag_move_threshold = max(cfg.deadzone * 2.0, 0.01)
        scroll_mode = False
        base_scroll_y = 0.0
        last_scroll_time = 0.0

        # Left-hand state
        task_switch_active = False
        last_tab_time = 0.0
        left_tab_hold_start = None

        # Mode switch / exit gesture timers
        startup_time = time.time()
        switch_gesture_start_time = None
        exit_hold_start = None
        exit_hold_announced = False

        last_hand_state = None
        self.action_logged.emit("Gesture Mode started. Camera active.")

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            frame_count += 1

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            enhancing = float(gray.mean()) < 100
            enhanced = enhancer.process(frame)
            rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)
            hand_detected = bool(results.multi_hand_landmarks)
            display = frame.copy()

            if hand_detected and results.multi_handedness:
                scores = [h.classification[0].score for h in results.multi_handedness]
                if sum(scores) / len(scores) < 0.6:
                    hand_detected = False

            det_history.append(1 if hand_detected else 0)
            if hand_detected != last_hand_state:
                self.hand_present.emit(hand_detected)
                last_hand_state = hand_detected

            current_gesture = "No hand detected"
            current_subtitle = ""
            current_confidence = 0
            cursor_hand = False
            current_pinch_state = "open"
            line_color = Palette.LINE_OPEN
            found_right = False
            found_left = False
            right_fist = False
            left_fist = False

            if hand_detected:
                detected_count += 1
                current_confidence = int(
                    sum(h.classification[0].score for h in results.multi_handedness)
                    / len(results.multi_handedness)
                    * 100
                )
                h_px, w_px = display.shape[:2]

                for idx in range(len(results.multi_hand_landmarks)):
                    hand_lms = results.multi_hand_landmarks[idx]
                    label = results.multi_handedness[idx].classification[0].label
                    pts = smoother.smooth(idx, hand_lms.landmark)
                    wrist = (int(pts[0][0] * w_px), int(pts[0][1] * h_px))

                    if cfg.show_finger_info:
                        draw_finger_panel(display, pts, label, wrist)

                    states = {n: is_finger_extended(pts, n, label) for n in FINGER_DEFS}
                    # Fist detection for exit:
                    # keep it robust by requiring the four long fingers closed.
                    # Thumb angle can vary when users close their palm.
                    is_fist_shape = (
                        not states["Index"]
                        and not states["Middle"]
                        and not states["Ring"]
                        and not states["Pinky"]
                    )

                    if label == "Right":
                        found_right = True
                        right_fist = is_fist_shape

                        # Right click mapping:
                        # Right ring+pinky extended, index/middle closed (thumb ignored).
                        is_rc_shape = (
                            states["Ring"]
                            and states["Pinky"]
                            and not states["Index"]
                            and not states["Middle"]
                        )

                        if is_rc_shape:
                            now_rc = time.time()
                            if right_click_hold_start is None:
                                right_click_hold_start = now_rc
                            hold_sec = now_rc - right_click_hold_start

                            if hold_sec >= 0.7 and not right_click_active:
                                pyautogui.rightClick()
                                self.action_logged.emit("RIGHT CLICK")
                                self.gesture_triggered.emit("Right Click", "🖱️")
                                right_click_active = True

                            if not right_click_active:
                                current_gesture = "Right Click Hold"
                                current_subtitle = f"Ring+Pinky hold {hold_sec:.1f}/0.7s"
                            else:
                                current_gesture = "Right Click"
                                current_subtitle = "Confirmed"

                        else:
                            right_click_active = False
                            right_click_hold_start = None

                        is_scroll = False
                        if not is_rc_shape:
                            ix_ext = pts[6][1] - pts[8][1]
                            mx_ext = pts[10][1] - pts[12][1]
                            is_scroll = (
                                states["Index"]
                                and states["Middle"]
                                and not states["Ring"]
                                and not states["Pinky"]
                                and ix_ext > 0.04
                                and mx_ext > 0.04
                            )

                        if is_scroll:
                            if not scroll_mode:
                                scroll_mode = True
                                base_scroll_y = pts[8][1]
                                last_scroll_time = time.time()
                                self.action_logged.emit("SCROLL MODE activated")

                            dy = pts[8][1] - base_scroll_y
                            now_s = time.time()
                            if now_s - last_scroll_time >= cfg.scroll_repeat_sec:
                                if abs(dy) > cfg.scroll_deadzone:
                                    amt = int(-dy * cfg.scroll_sensitivity * 500)
                                    if amt:
                                        pyautogui.scroll(amt)
                                        self.action_logged.emit("SCROLL " + ("UP" if amt > 0 else "DOWN"))
                                    last_scroll_time = now_s

                            cursor_hand = False
                            current_gesture = "Scroll Mode"
                            current_subtitle = "Index + Middle extended"

                        elif (
                            states["Index"]
                            and not states["Middle"]
                            and not states["Ring"]
                            and not states["Pinky"]
                            and not is_rc_shape
                        ):
                            cursor_hand = True
                            scroll_mode = False
                            base_scroll_y = 0.0

                            ta = np.array(pts[4][:2])
                            ia = np.array(pts[8][:2])
                            dist = np.linalg.norm(ta - ia)

                            if dist <= cfg.tight_pinch_max:
                                current_pinch_state = "tight"
                                line_color = Palette.LINE_TIGHT
                            elif dist <= cfg.mild_pinch_max:
                                current_pinch_state = "mild"
                                line_color = Palette.LINE_MILD
                            else:
                                current_pinch_state = "open"
                                line_color = Palette.LINE_OPEN

                            now = time.time()
                            if current_pinch_state == "mild":
                                if pinch_state != "mild":
                                    mild_pinch_start_time = now
                                    mild_click_fired = False
                                hold_t = now - mild_pinch_start_time
                                if hold_t >= 0.25 and not mild_click_fired:
                                    pyautogui.click()
                                    self.action_logged.emit("SINGLE CLICK")
                                    mild_click_fired = True
                                    current_gesture = "Single Click"
                                    current_subtitle = "Orange hold confirmed"
                                else:
                                    current_gesture = "Single Click Hold"
                                    current_subtitle = f"Orange hold {hold_t:.1f}/0.25s"
                                hard_pinch_active = False
                                red_hold_confirmed = False
                                red_doubleclick_fired = False
                                red_last_index_norm = None

                            elif current_pinch_state == "tight":
                                if pinch_state != "tight":
                                    pinch_start_time = now
                                    hard_pinch_active = True
                                    red_hold_confirmed = False
                                    red_doubleclick_fired = False
                                    red_last_index_norm = np.array(pts[8][:2])
                                hold_t = now - pinch_start_time

                                if hold_t >= 1.0 and not red_doubleclick_fired:
                                    pyautogui.doubleClick()
                                    self.action_logged.emit("DOUBLE CLICK")
                                    red_doubleclick_fired = True
                                    red_hold_confirmed = True
                                    current_gesture = "Double Click"
                                    current_subtitle = "Red hold confirmed (1.0s)"
                                elif not red_hold_confirmed:
                                    current_gesture = "Tight Pinch Hold"
                                    current_subtitle = f"Red hold {hold_t:.1f}/1.0s"
                                else:
                                    current_gesture = "Drag Ready"
                                    current_subtitle = "Move while holding to drag"

                                current_index_norm = np.array(pts[8][:2])
                                if red_hold_confirmed and not is_dragging and red_last_index_norm is not None:
                                    move_vec = current_index_norm - red_last_index_norm
                                    if np.linalg.norm(move_vec) > drag_move_threshold:
                                        is_dragging = True
                                        pyautogui.mouseDown()
                                        self.action_logged.emit("DRAG START")
                                        current_gesture = "Drag"
                                        current_subtitle = "Red hold + movement"
                                red_last_index_norm = current_index_norm
                                mild_click_fired = False

                            elif current_pinch_state == "open" and hard_pinch_active:
                                if is_dragging:
                                    pyautogui.mouseUp()
                                    self.action_logged.emit("DRAG END")
                                    current_gesture = "Drag Released"
                                is_dragging = False
                                hard_pinch_active = False
                                red_hold_confirmed = False
                                red_doubleclick_fired = False
                                red_last_index_norm = None
                                mild_click_fired = False

                            index_norm = np.array(pts[8][:2])
                            if prev_index_norm is not None and (is_dragging or current_pinch_state == "open"):
                                dx = index_norm[0] - prev_index_norm[0]
                                dy = index_norm[1] - prev_index_norm[1]
                                if np.linalg.norm([dx, dy]) > cfg.deadzone:
                                    pyautogui.moveRel(
                                        int(dx * cursor_sensitivity * w_px),
                                        int(dy * cursor_sensitivity * h_px),
                                    )
                            prev_index_norm = index_norm.copy()
                            if current_gesture == "No hand detected":
                                current_gesture = "Cursor Mode"
                                current_subtitle = "Index finger extended"

                        else:
                            cursor_hand = False
                            scroll_mode = False
                            base_scroll_y = 0.0

                    elif label == "Left":
                        found_left = True
                        left_fist = is_fist_shape

                        thumb_l = np.array(pts[4][:2])
                        index_l = np.array(pts[8][:2])
                        is_left_pinch = np.linalg.norm(thumb_l - index_l) <= cfg.left_pinch_threshold

                        # Mode switch using left hand:
                        # thumb + index + middle extended, ring + pinky closed.
                        is_left_mode_switch = (
                            states["Thumb"]
                            and states["Index"]
                            and states["Middle"]
                            and not states["Ring"]
                            and not states["Pinky"]
                        )
                        if is_left_mode_switch and time.time() - startup_time > 2.0:
                            now_sw = time.time()
                            if switch_gesture_start_time is None:
                                switch_gesture_start_time = now_sw
                            hold_sw = now_sw - switch_gesture_start_time

                            if hold_sw >= 1.5:
                                if is_dragging:
                                    pyautogui.mouseUp()
                                if task_switch_active:
                                    pyautogui.keyUp("alt")
                                self.action_logged.emit("Switching to Voice Mode...")
                                self.switch_to_voice.emit()
                                break

                            current_gesture = "Switch Mode Hold"
                            current_subtitle = f"Thumb+Index+Middle {hold_sw:.1f}/1.5s"
                            prog = min(1.0, hold_sw / 1.5)
                            cv2.rectangle(display, (10, 10), (int(10 + prog * 220), 30), (0, 255, 255), -1)
                            cv2.putText(
                                display,
                                "SWITCH TO VOICE (1.5s HOLD)",
                                (10, 52),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 255),
                                2,
                            )
                        else:
                            switch_gesture_start_time = None

                        ext = lh_ext.process(states, is_left_pinch)

                        extension_blocks_tab = (
                            ext["gesture"].startswith("Copy")
                            or ext["gesture"].startswith("Paste")
                            or ext["gesture"].startswith("Minimize")
                            or ext["gesture"].startswith("Maximize")
                        )

                        now_l = time.time()
                        is_tab_switch = (
                            is_left_pinch
                            and states["Middle"]
                            and states["Ring"]
                            and states["Pinky"]
                            and not extension_blocks_tab
                        )
                        if is_tab_switch:
                            if left_tab_hold_start is None:
                                left_tab_hold_start = now_l
                            hold_sec = now_l - left_tab_hold_start

                            if hold_sec >= 1.0:
                                if not task_switch_active:
                                    pyautogui.keyDown("alt")
                                    pyautogui.press("tab")
                                    task_switch_active = True
                                    last_tab_time = now_l
                                    self.action_logged.emit("TASK SWITCH START")
                                elif now_l - last_tab_time >= cfg.tab_repeat_sec:
                                    pyautogui.press("tab")
                                    last_tab_time = now_l
                                current_gesture = "Task Switch"
                                current_subtitle = "Left pinch hold confirmed - Alt+Tab"
                            else:
                                current_gesture = "Task Switch Hold"
                                current_subtitle = f"Hold {hold_sec:.1f}/1.0s"
                        else:
                            left_tab_hold_start = None
                            if task_switch_active:
                                pyautogui.keyUp("alt")
                                task_switch_active = False
                                self.action_logged.emit("TASK SWITCH END")

                        if ext["action"]:
                            self.action_logged.emit(ext["action"].upper())
                            # Keep popup notifications off for minimize/maximize.
                            if ext["action"] not in ("minimize", "maximize"):
                                action_map = {
                                    "copy": ("Copied", "📋"),
                                    "paste": ("Pasted", "📥"),
                                }
                                label_icon = action_map.get(ext["action"], (ext["action"], "✅"))
                                self.gesture_triggered.emit(*label_icon)

                        if ext["gesture"]:
                            current_gesture = ext["gesture"]
                            current_subtitle = ext["subtitle"]

                    draw_skeleton_and_line(
                        display,
                        pts,
                        label,
                        glow=cfg.skeleton_glow,
                        dense=cfg.dense_points_per_bone,
                        line_color=line_color,
                    )

                pinch_state = current_pinch_state

                # Exit gesture: both palms closed (fists) hold 3s.
                if (
                    found_left
                    and found_right
                    and left_fist
                    and right_fist
                    and switch_gesture_start_time is None
                    and not task_switch_active
                ):
                    now_exit = time.time()
                    if exit_hold_start is None:
                        exit_hold_start = now_exit
                        exit_hold_announced = False
                        self.action_logged.emit("Exit gesture detected - hold 3.0s...")

                    hold_exit = now_exit - exit_hold_start
                    current_gesture = "Exit Hold"
                    current_subtitle = f"Both fists hold {hold_exit:.1f}/3.0s"
                    prog = min(1.0, hold_exit / 3.0)
                    cv2.rectangle(display, (10, 68), (int(10 + prog * 220), 88), (0, 70, 255), -1)
                    cv2.putText(
                        display,
                        "EXITING G-VOX...",
                        (10, 112),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 70, 255),
                        2,
                    )

                    if hold_exit >= 3.0 and not exit_hold_announced:
                        exit_hold_announced = True
                        self.action_logged.emit("Exit gesture confirmed.")
                        self.gesture_triggered.emit("Exit G-Vox", "⛔")
                        self.exit_requested.emit()
                        break
                else:
                    exit_hold_start = None
                    exit_hold_announced = False

            else:
                for i in range(cfg.max_hands):
                    smoother.reset(i)
                lh_ext.reset_all()
                prev_index_norm = None
                scroll_mode = False
                base_scroll_y = 0.0
                switch_gesture_start_time = None
                exit_hold_start = None
                exit_hold_announced = False

                if is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False
                right_click_active = False
                right_click_hold_start = None
                hard_pinch_active = False
                pinch_start_time = 0.0
                mild_pinch_start_time = 0.0
                mild_click_fired = False
                red_hold_confirmed = False
                red_doubleclick_fired = False
                red_last_index_norm = None

                if task_switch_active:
                    pyautogui.keyUp("alt")
                    task_switch_active = False
                left_tab_hold_start = None

                current_gesture = "No hand detected"
                current_subtitle = "Show hand in camera"

            if not found_left and task_switch_active:
                pyautogui.keyUp("alt")
                task_switch_active = False
            if not found_left:
                left_tab_hold_start = None
                switch_gesture_start_time = None
            if not found_right:
                if is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False
                scroll_mode = False
                right_click_hold_start = None
                hard_pinch_active = False
                pinch_start_time = 0.0
                mild_pinch_start_time = 0.0
                mild_click_fired = False
                red_hold_confirmed = False
                red_doubleclick_fired = False
                red_last_index_norm = None
            if not (found_left and found_right):
                exit_hold_start = None
                exit_hold_announced = False

            if cursor_hand and not is_cursor_mode:
                is_cursor_mode = True
                prev_index_norm = None
            elif not cursor_hand and is_cursor_mode:
                is_cursor_mode = False
                prev_index_norm = None

            fps_cur = frame_count / (time.time() - start_time + 1e-6)
            det_rate = sum(det_history) / len(det_history) * 100 if det_history else 0
            draw_hud(
                display,
                fps_cur,
                det_rate,
                frame_count,
                detected_count,
                hand_detected,
                enhancing,
                is_cursor_mode,
                pinch_state,
                "none",
                task_switch_active,
            )

            rgb_out = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            hi, wi, ch = rgb_out.shape
            q_img = QImage(rgb_out.data, wi, hi, ch * wi, QImage.Format_RGB888)
            self.frame_ready.emit(q_img.copy())
            self.gesture_detected.emit(current_gesture, current_subtitle, current_confidence)
            self.fps_updated.emit(fps_cur)

        if is_dragging:
            pyautogui.mouseUp()
        if task_switch_active:
            pyautogui.keyUp("alt")
        cap.release()
        hands.close()
        self.action_logged.emit("Gesture Mode stopped.")
