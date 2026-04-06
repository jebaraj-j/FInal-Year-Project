
# vision.py
import cv2
import mediapipe as mp
import numpy as np
import time
import sys
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple, Optional
import pyautogui
import threading
import queue
import json
import os


pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01  # Small pause for smooth actions

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
@dataclass
class Config:
    camera_width: int = 1280
    camera_height: int = 720
    target_fps: int = 30
    max_hands: int = 2
    model_complexity: int = 1
    # Detection: Confidence thresholds (increased for better accuracy)
    min_detection_conf: float = 0.7  
    min_tracking_conf: float = 0.7   
    clahe_clip_limit: float = 3.0
    clahe_grid_size: tuple = (8, 8)
    denoise_h: int = 7
    denoise_template: int = 7
    denoise_search: int = 21
    gamma_correction: float = 1.4
    smoothing_alpha: float = 0.6
    history_size: int = 60
    skeleton_glow: bool = True
    dense_points_per_bone: int = 6
    show_finger_info: bool = True
    
    # Pinch thresholds (tune if needed)
    mild_pinch_max: float = 0.060   # Small gap → single click mode (higher = easier to enter)
    tight_pinch_max: float = 0.035  # Very small gap → double click mode
    
    # Repeat rates
    single_repeat_sec: float = 1.0
    double_repeat_sec: float = 2.0
    
    # Relative movement
    sensitivity: float = 3  #
    deadzone: float = 0.003
    
    # Left-hand pinch detection for Alt+Tab
    left_pinch_threshold: float = 0.05
    tab_repeat_sec: float = 0.6
    
    # Scroll gesture parameters
    scroll_sensitivity: float = 3.0  # Increased from 1.0
    scroll_deadzone: float = 0.02   # Reduced from 0.05 for more responsiveness
    scroll_repeat_sec: float = 0.1
    
    # Drag & Drop and Right-Click parameters
    right_click_threshold: float = 0.25  # Further increased distance threshold for right-click
    drag_hold_threshold: float = 0.8     # Seconds to distinguish drag from click (old)
    
    # New pinch timing parameters
    double_click_threshold: float = 0.25  # Quick release for double click
    drag_threshold: float = 0.35          # Sustained hold for drag

CFG = Config()

# ─────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────
class Palette:
    LINE_OPEN   = (0, 255, 0)    # Green - open
    LINE_MILD   = (0, 165, 255)  # Orange - mild pinch (single click)
    LINE_TIGHT  = (0, 0, 255)    # Red - tight pinch (double click)
    CURSOR_POINTER = (0, 255, 255)  # Yellow ring

# ─────────────────────────────────────────────
# LANDMARK SMOOTHER / IMAGE ENHANCER / FINGER ANALYSIS (unchanged)
# ─────────────────────────────────────────────
class LandmarkSmoother:
    def __init__(self, alpha: float = 0.6):
        self.alpha = alpha
        self._prev = {}

    def smooth(self, hand_id: int, landmarks) -> List[Tuple[float, float, float]]:
        pts = [(lm.x, lm.y, lm.z) for lm in landmarks]
        if hand_id not in self._prev:
            self._prev[hand_id] = pts
            return pts
        prev = self._prev[hand_id]
        smoothed = [
            (self.alpha * c[0] + (1 - self.alpha) * p[0],
             self.alpha * c[1] + (1 - self.alpha) * p[1],
             self.alpha * c[2] + (1 - self.alpha) * p[2])
            for c, p in zip(pts, prev)
        ]
        self._prev[hand_id] = smoothed
        return smoothed

    def reset(self, hand_id: int):
        self._prev.pop(hand_id, None)

class ImageEnhancer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.clahe = cv2.createCLAHE(clipLimit=cfg.clahe_clip_limit, tileGridSize=cfg.clahe_grid_size)
        self._gamma_lut = np.array([((i / 255.0) ** (1.0 / cfg.gamma_correction)) * 255 
                                    for i in range(256)]).astype("uint8")

    def process(self, bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        mean_lum = float(gray.mean())
        if mean_lum >= 100:
            return bgr
        enhanced = cv2.LUT(bgr, self._gamma_lut)
        lab = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        l, a, b = cv2.split(lab)
        l_eq = self.clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l_eq, a, b]), cv2.COLOR_LAB2BGR)
        if mean_lum < 50:
            enhanced = cv2.bilateralFilter(enhanced, self.cfg.denoise_h,
                                           self.cfg.denoise_template, self.cfg.denoise_search)
        return enhanced

FINGER_DEFS = {
    "Thumb":  {"tip":4, "pip":3, "mcp":2},
    "Index":  {"tip":8, "pip":6, "mcp":5},
    "Middle": {"tip":12,"pip":10,"mcp":9},
    "Ring":   {"tip":16,"pip":14,"mcp":13},
    "Pinky":  {"tip":20,"pip":18,"mcp":17},
}

def is_finger_extended(pts: List[Tuple[float,float,float]], name: str, hand_label: str) -> bool:
    d = FINGER_DEFS[name]
    tip, pip, mcp = pts[d["tip"]], pts[d["pip"]], pts[d["mcp"]]
    
    if name == "Thumb":
        # Distance-based extension check for Thumb
        # Tip-to-MCP should be longer than Pip-to-MCP
        tip_mcp_dist = np.linalg.norm(np.array(tip) - np.array(mcp))
        pip_mcp_dist = np.linalg.norm(np.array(pip) - np.array(mcp))
        return tip_mcp_dist > pip_mcp_dist
        
    # Standard extension detection: Tip is above Pip
    extension_threshold = 0.02
    extended = (tip[1] < pip[1] - extension_threshold)
    return extended

# ─────────────────────────────────────────────
# SKELETON + PINCH LINE
# ─────────────────────────────────────────────
BONE_GROUPS = {
    "thumb":  [0,1,2,3,4],
    "index":  [5,6,7,8],
    "middle": [9,10,11,12],
    "ring":   [13,14,15,16],
    "pinky":  [17,18,19,20],
    "palm":   [0,5,9,13,17,0],
}
BONE_COLOURS = {
    "thumb":  (255, 200, 60),
    "index":  (60, 220, 255),
    "middle": (180, 255, 60),
    "ring":   (255, 80, 200),
    "pinky":  (255, 160, 40),
    "palm":   (200, 200, 200),
}

def _to_px(pt, w, h): return (int(pt[0] * w), int(pt[1] * h))

def draw_skeleton_and_line(frame: np.ndarray, pts: List[Tuple[float,float,float]], hand_label: str,
                           glow: bool = True, dense: int = 6, line_color: Tuple[int,int,int] = (0,255,0)):
    h, w = frame.shape[:2]
    
    # Skeleton
    for group, indices in BONE_GROUPS.items():
        colour = BONE_COLOURS[group]
        coords = [_to_px(pts[i], w, h) for i in indices]
        for a, b in zip(coords, coords[1:]):
            if glow:
                cv2.line(frame, a, b, colour, 8, cv2.LINE_AA)
                cv2.line(frame, a, b, (255,255,255), 3, cv2.LINE_AA)
            else:
                cv2.line(frame, a, b, colour, 3, cv2.LINE_AA)

    # Joints
    for i, pt in enumerate(pts):
        px = _to_px(pt, w, h)
        is_tip = i in (4,8,12,16,20)
        r_outer = 8 if is_tip else 6
        cv2.circle(frame, px, r_outer + 4, BONE_COLOURS.get(next((g for g, ids in BONE_GROUPS.items() if i in ids), "palm"), (200,200,200)), -1)
        cv2.circle(frame, px, r_outer, (220,220,220), -1)
        cv2.circle(frame, px, 4 if is_tip else 3, (255,255,255), -1)

    # Always draw thumb-index line in cursor mode
    thumb_px = _to_px(pts[4], w, h)
    index_px = _to_px(pts[8], w, h)
    cv2.line(frame, thumb_px, index_px, line_color, 4, cv2.LINE_AA)
    cv2.circle(frame, thumb_px, 12, line_color, 3)
    cv2.circle(frame, index_px, 12, line_color, 3)

    # Cursor pointer
    cv2.circle(frame, index_px, 20, Palette.CURSOR_POINTER, 3, cv2.LINE_AA)
    cv2.circle(frame, index_px, 10, (255, 255, 0), -1)

# ─────────────────────────────────────────────
# FINGER PANEL / HUD (minor updates)
# ─────────────────────────────────────────────
def draw_finger_panel(frame, pts, label, wrist_px):
    names = list(FINGER_DEFS.keys())
    states = {n: is_finger_extended(pts, n, label) for n in names}
    wx, wy = wrist_px
    ox, oy = wx + 30, wy - 140
    overlay = frame.copy()
    cv2.rectangle(overlay, (ox-10, oy-10), (ox+140, oy+130), (10,10,18), -1)
    frame[:] = cv2.addWeighted(overlay, 0.65, frame, 0.35, 0)
    col = (30, 180, 255) if label == "Right" else (255, 120, 30)
    cv2.putText(frame, label.upper(), (ox, oy+20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
    for i, name in enumerate(names):
        up = states[name]
        icon = "▲" if up else "▼"
        fg = (0,255,120) if up else (0,80,255)
        y = oy + 45 + i*22
        cv2.putText(frame, f"{icon} {name[:3]}", (ox, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, fg, 1)

def draw_hud(frame, fps, det_rate, frame_count, detected_count, hand_detected, enhancing, is_cursor_mode, pinch_mode, left_hand_state, task_switch_active):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    extra = 1 if is_cursor_mode else 0
    if pinch_mode != "open": extra += 1
    if left_hand_state != "none": extra += 1
    if task_switch_active: extra += 1
    cv2.rectangle(overlay, (0,0), (360,140 + extra*25), (10,10,18), -1)
    frame[:] = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    col = (0,255,120) if hand_detected else (0,80,255)
    cv2.putText(frame, "HAND DETECTED" if hand_detected else "NO HAND", (12, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
    cv2.putText(frame, f"FPS: {int(fps)}   Frames: {frame_count}", (12, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
    cv2.putText(frame, f"Detected: {detected_count} ({det_rate:.1f}%)", (12, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
    
    y = 115
    if enhancing:
        cv2.putText(frame, "LOW-LIGHT ACTIVE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,220,255), 1)
        y += 25
    if is_cursor_mode:
        cv2.putText(frame, "CURSOR MODE (RELATIVE)", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
        y += 25
    if pinch_mode == "mild":
        cv2.putText(frame, "MILD PINCH → SINGLE CLICK (REPEAT 1s)", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,165,255), 1)
    elif pinch_mode == "tight":
        cv2.putText(frame, "TIGHT PINCH → DOUBLE CLICK (REPEAT 2s)", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
    
    if left_hand_state == "fist":
        cv2.putText(frame, "LEFT HAND: MINIMIZE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,100,100), 1)
    elif left_hand_state == "open":
        cv2.putText(frame, "LEFT HAND: MAXIMIZE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100,255,100), 1)

    if task_switch_active:
        cv2.putText(frame, "LEFT HAND: TASK SWITCH", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,150,255), 1)

    cv2.putText(frame, "Q=quit  S=screenshot", (w-220, h-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,180,180), 1)

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def open_camera(cfg):
    """
    Open a camera reliably on Windows.
    Tries DirectShow first (more stable for many webcams), then fallback backends.
    Validates by reading at least one frame before accepting a device.
    """
    backends = [
        ("DSHOW", cv2.CAP_DSHOW),
        ("ANY", None),
        ("MSMF", cv2.CAP_MSMF),
    ]
    for backend_name, backend_flag in backends:
        for i in range(4):
            try:
                cap = cv2.VideoCapture(i, backend_flag) if backend_flag is not None else cv2.VideoCapture(i)
            except Exception:
                cap = None
            if cap is None or not cap.isOpened():
                continue

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera_height)
            cap.set(cv2.CAP_PROP_FPS, cfg.target_fps)

            # Warm up and verify we can actually read frames.
            ok = False
            for _ in range(8):
                ret, _ = cap.read()
                if ret:
                    ok = True
                    break
                time.sleep(0.03)

            if ok:
                print(
                    f"Camera {i} opened at {cfg.camera_width}x{cfg.camera_height} "
                    f"(backend={backend_name})"
                )
                return cap, i

            cap.release()
    return None, -1

def draw_help_overlay(img: np.ndarray):
    """Draw a semi-transparent help overlay on the image."""
    h, w = img.shape[:2]
    # Semi-transparent background
    overlay = img.copy()
    cv2.rectangle(overlay, (50, 50), (w - 50, h - 50), (0, 0, 0), -1)
    alpha = 0.75
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    
    # Text headers
    cv2.putText(img, "=== GESTURE CONTROL HELP (Press 'H' to close) ===", (70, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    y = 130
    lines = [
        "RIGHT HAND (Cursor & Clicks):",
        "  - Move: Index finger extended only",
        "  - Click: Mild pinch Thumb + Index (Green Line)",
        "  - Double Click: Quick tight pinch (<0.3s)",
        "  - Drag: Hold tight pinch (>0.35s)",
        "  - Right Click: Pinch Thumb + Middle",
        "  - Scroll: Index + Middle extended. Move hand UP/DOWN",
        "",
        "LEFT HAND (System Control):",
        "  - Copy (Ctrl+C): Pinky extended only (hold 1s)",
        "  - Paste (Ctrl+V): Ring + Pinky extended (hold 1s)",
        "  - Minimize (Win+Down): Thumb only (hold 1s)",
        "  - Maximize (Win+Up): Open Palm (hold 1s)",
        "  - Task Switch (Alt+Tab): Thumb+Index pinch + others up (hold 1s)",
        "",
        "MODE SWITCHING (TO VOICE):",
        "  - Thumb + Index + Middle Extended (Left Hand)",
        "  - Hold for 1.5 seconds. Watch the yellow progress bar.",
        "",
        "CONTROLS: Q = Quit, S = Screenshot, H = Toggle Help"
    ]
    
    for line in lines:
        color = (255, 255, 255) if not line.isupper() else (0, 255, 255)
        scale = 0.55 if not line.isupper() else 0.6
        cv2.putText(img, line, (70, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1 if not line.isupper() else 2)
        y += 30

def main():
    print("Starting Easy Hand Cursor Control (Hold Pinch for Repeated Clicks)...")
    
    start_up_time = time.time()
    switch_gesture_start_time = None
    
    cfg = CFG
    enhancer = ImageEnhancer(cfg)
    smoother = LandmarkSmoother(cfg.smoothing_alpha)
    cap, _ = open_camera(cfg)
    if cap is None:
        print("No camera found.")
        return

    hands = mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=cfg.max_hands,
        model_complexity=cfg.model_complexity,
        min_detection_confidence=cfg.min_detection_conf,
        min_tracking_confidence=cfg.min_tracking_conf
    )

    frame_count = detected_count = 0
    start_time = time.time()
    det_history = deque(maxlen=cfg.history_size)

    is_cursor_mode = False
    prev_index_norm: Optional[np.ndarray] = None
    pinch_state = "open"  # open, mild, tight
    last_single_time = 0.0
    last_double_time = 0.0
    
    # Left-hand gesture state tracking
    left_hand_state = "none"  # "none", "fist", "open"

    # Task switching state variables
    task_switch_active = False
    last_tab_time = 0.0
    tab_hold_start = 0.0

    # Scroll mode state variables
    scroll_mode = False
    scroll_was_active = False
    base_scroll_y = 0.0  # Reference position when scroll gesture starts
    last_scroll_time = 0.0
    
    # Drag & Drop and Right-Click state variables (redesigned)
    is_dragging = False
    right_click_active = False
    right_click_hold_start = 0.0
    pinch_start_time = 0.0      # When hard pinch begins
    hard_pinch_active = False   # Track hard pinch state
    show_help = False           # Help overlay toggle

    # Left-hand hold-to-confirm timers (1.0s)
    left_hold_start = {
        "copy": 0.0,
        "paste": 0.0,
        "minimize": 0.0,
        "maximize": 0.0,
    }
    left_hold_fired = {
        "copy": False,
        "paste": False,
        "minimize": False,
        "maximize": False,
    }

    print("\n=== EASY CONTROL GUIDE ===")
    print("  * Right hand, ONLY index extended -> Cursor mode")
    print("  * Move index finger -> Smooth cursor")
    print("* Line always shown between thumb & index")
    print("  - Green: Open (move freely)")
    print("  - Orange: Mild pinch -> Single click")
    print("  - Red: Tight pinch -> Double click (quick) OR Drag (hold 0.35s+)")
    print("* Right hand, index + middle extended -> Scroll mode")
    print("  - Move fingers up/down -> Scroll up/down")
    print("* Right hand, thumb + middle pinch -> Right click")
    print("* Right hand, thumb + index hard pinch hold -> Drag & drop")
    print("* Left hand gestures (1.0s hold confirm):")
    print("  - Copy: Pinky extended only -> Ctrl+C")
    print("  - Paste: Ring + Pinky extended -> Ctrl+V")
    print("  - Minimize: Thumb extended only -> Win+Down")
    print("  - Maximize: Open palm -> Win+Up")
    print("  - Task Switch: Thumb-Index pinch + Middle/Ring/Pinky extended -> Alt+Tab")
    print("Q = quit    S = screenshot\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        frame_count += 1

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_lum = float(gray.mean())
        enhancing = mean_lum < 100

        enhanced = enhancer.process(frame)
        rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb)
        hand_detected = bool(results.multi_hand_landmarks)

        display = frame.copy()
        
        
        # Additional validation: check hand confidence scores
        if hand_detected and results.multi_handedness:
            hand_confidences = [hand.classification[0].score for hand in results.multi_handedness]
            avg_confidence = sum(hand_confidences) / len(hand_confidences)
            # Only consider hands detected if average confidence is high enough
            if avg_confidence < 0.6:
                hand_detected = False
                print(f"Low confidence hand detection: {avg_confidence:.3f} - ignoring")
        
        det_history.append(1 if hand_detected else 0)

        cursor_hand = False
        current_pinch_state = "open"
        line_color = Palette.LINE_OPEN
        seen_left_hand = False

        if hand_detected:
            # --- HIGH PRIORITY MODE SWITCH CHECK ---
            found_switch_gesture = False
            for idx in range(len(results.multi_hand_landmarks)):
                h_lms = results.multi_hand_landmarks[idx]
                h_label = results.multi_handedness[idx].classification[0].label
                
                if h_label == "Left":
                    s_pts = smoother.smooth(idx, h_lms.landmark)
                    # Specific Gesture: Thumb, Index, Middle Extended; Ring, Pinky Closed
                    thumb_e = is_finger_extended(s_pts, "Thumb", h_label)
                    index_e = is_finger_extended(s_pts, "Index", h_label)
                    middle_e = is_finger_extended(s_pts, "Middle", h_label)
                    ring_e = is_finger_extended(s_pts, "Ring", h_label)
                    pinky_e = is_finger_extended(s_pts, "Pinky", h_label)
                    
                    if thumb_e and index_e and middle_e and not ring_e and not pinky_e:
                        found_switch_gesture = True
                        break
                    
                    # Debug print to help user get the gesture right
                    if (index_e or middle_e) and time.time() % 0.5 < 0.03:
                        print(f"SWITCH CHECK (L-Hand): Thumb={thumb_e}, Index={index_e}, Middle={middle_e}, Ring={ring_e}, Pinky={pinky_e}")
            
            if found_switch_gesture:
                if time.time() - start_up_time > 2.0: # Startup cooldown
                    if switch_gesture_start_time is None:
                        switch_gesture_start_time = time.time()
                    elif time.time() - switch_gesture_start_time > 1.5:
                        print("[SYSTEM_SIGNAL]:SWITCH_TO_VOICE", flush=True)
                        # Cleanup any stuck states before exiting
                        if is_dragging: pyautogui.mouseUp()
                        if task_switch_active: pyautogui.keyUp("alt")
                        sys.exit(0)
            else:
                switch_gesture_start_time = None
            # ---------------------------------------

            detected_count += 1
            h, w = display.shape[:2]
            for idx in range(len(results.multi_hand_landmarks)):
                hand_lms = results.multi_hand_landmarks[idx]
                label = results.multi_handedness[idx].classification[0].label
                pts = smoother.smooth(idx, hand_lms.landmark)

                wrist_px = _to_px(pts[0], w, h)
                if cfg.show_finger_info:
                    draw_finger_panel(display, pts, label, wrist_px)

                if label == "Right":
                    states = {n: is_finger_extended(pts, n, label) for n in FINGER_DEFS}
                    
                    # Check for right-click gesture (thumb + middle pinch hold 0.7s)
                    thumb_tip = np.array(pts[4][:2])      # Thumb tip (landmark 4)
                    middle_tip = np.array(pts[12][:2])    # Middle finger tip (landmark 12)
                    right_click_dist = np.linalg.norm(thumb_tip - middle_tip)

                    # Strict posture: index, ring, and pinky must be extended.
                    is_right_click_shape = (
                        right_click_dist < 0.08
                        and states["Index"]
                        and states["Ring"]
                        and states["Pinky"]
                    )

                    if is_right_click_shape:
                        if right_click_hold_start == 0.0:
                            right_click_hold_start = time.time()
                        hold_t = time.time() - right_click_hold_start
                        if hold_t >= 0.7 and not right_click_active:
                            pyautogui.rightClick()
                            print(f"RIGHT CLICK CONFIRMED (hold {hold_t:.2f}s)")
                            right_click_active = True
                    else:
                        right_click_active = False
                        right_click_hold_start = 0.0
                    
                    # Check for scroll gesture (index + middle extended)
                    is_scroll_gesture = False
                    if not is_right_click_shape:  
                        index_extension = pts[6][1] - pts[8][1]
                        middle_extension = pts[10][1] - pts[12][1]
                        min_extension = 0.04
                        
                        is_scroll_gesture = (
                            states["Index"] and states["Middle"] and 
                            not states["Ring"] and not states["Pinky"] and
                            index_extension > min_extension and 
                            middle_extension > min_extension
                        )
                    
                    if is_scroll_gesture:
                        if not scroll_mode:
                            scroll_mode = True
                            base_scroll_y = pts[8][1]  
                            last_scroll_time = time.time()
                            print(">>> SCROLL MODE ACTIVATED (Reference set) <<<")
                        
                        current_index_y = pts[8][1]  
                        dy = current_index_y - base_scroll_y
                        
                        current_time = time.time()
                        if current_time - last_scroll_time >= cfg.scroll_repeat_sec:
                            if abs(dy) > cfg.scroll_deadzone:
                                scroll_amount = int(-dy * cfg.scroll_sensitivity * 500)
                                if scroll_amount != 0:
                                    pyautogui.scroll(scroll_amount)
                                    dir_str = "UP" if scroll_amount > 0 else "DOWN"
                                    print(f"SCROLL {dir_str} ({abs(scroll_amount)})")
                                last_scroll_time = current_time
                        cursor_hand = False
                        
                    elif states["Index"] and not states["Middle"] and not any(states[n] for n in ["Ring", "Pinky"]):
                        cursor_hand = True
                        scroll_mode = False
                        base_scroll_y = 0.0

                        thumb_tip = np.array(pts[4][:2])
                        index_tip = np.array(pts[8][:2])
                        dist = np.linalg.norm(thumb_tip - index_tip)

                        if dist <= cfg.tight_pinch_max:
                            current_pinch_state = "tight"
                            line_color = Palette.LINE_TIGHT
                        elif dist <= cfg.mild_pinch_max:
                            current_pinch_state = "mild"
                            line_color = Palette.LINE_MILD
                        else:
                            current_pinch_state = "open"
                            line_color = Palette.LINE_OPEN

                        current_time = time.time()

                        if current_pinch_state == "mild":
                            if pinch_state != "mild":
                                pyautogui.click()
                                print("SINGLE CLICK (mild pinch)")
                                last_single_time = current_time

                        elif current_pinch_state == "tight":
                            if pinch_state != "tight":
                                pinch_start_time = current_time
                                hard_pinch_active = True
                                print("HARD PINCH START - timing for action determination")
                            
                            if hard_pinch_active and not is_dragging and current_time - pinch_start_time >= cfg.drag_threshold:
                                is_dragging = True
                                pyautogui.mouseDown()
                                print("DRAG START (hard pinch held for drag threshold)")

                        elif current_pinch_state == "open":
                            if hard_pinch_active:
                                pinch_duration = current_time - pinch_start_time
                                if not is_dragging and pinch_duration < cfg.double_click_threshold:
                                    pyautogui.doubleClick()
                                    print(f"DOUBLE CLICK (hard pinch released in {pinch_duration:.2f}s)")
                                elif is_dragging:
                                    pyautogui.mouseUp()
                                    print(f"DRAG END (pinch released after {pinch_duration:.2f}s)")
                                is_dragging = False
                                hard_pinch_active = False

                        index_norm = np.array(pts[8][:2])
                        if prev_index_norm is not None:
                            if is_dragging or current_pinch_state == "open":
                                dx = index_norm[0] - prev_index_norm[0]
                                dy = index_norm[1] - prev_index_norm[1]
                                movement = np.linalg.norm([dx, dy])
                                if movement > cfg.deadzone:
                                    move_x = int(dx * cfg.sensitivity * w)
                                    move_y = int(dy * cfg.sensitivity * h)
                                    pyautogui.moveRel(move_x, move_y)
                                    if is_dragging:
                                        print(f"DRAG MOVE: ({move_x}, {move_y})")
                        prev_index_norm = index_norm.copy()
                    else:
                        cursor_hand = False
                        scroll_mode = False
                        base_scroll_y = 0.0

                elif label == "Left":
                    seen_left_hand = True
                    states = {n: is_finger_extended(pts, n, label) for n in FINGER_DEFS}
                    thumb_tip = np.array(pts[4][:2])
                    index_tip = np.array(pts[8][:2])
                    pinch_dist = np.linalg.norm(thumb_tip - index_tip)
                    is_left_pinch = pinch_dist <= cfg.left_pinch_threshold
                    current_time = time.time()

                    thumb_e = states["Thumb"]
                    index_e = states["Index"]
                    middle_e = states["Middle"]
                    ring_e = states["Ring"]
                    pinky_e = states["Pinky"]

                    # New left-hand gesture mapping requested by user.
                    # Priority rule: pinky-based gestures must win before pinch-based tab switch.
                    # This avoids false tab triggers when thumb/index are close during copy/paste.
                    is_copy = pinky_e and (not ring_e) and (not middle_e)
                    is_paste = pinky_e and ring_e and (not middle_e)
                    is_minimize = thumb_e and (not index_e) and (not middle_e) and (not ring_e) and (not pinky_e)
                    is_maximize = thumb_e and index_e and middle_e and ring_e and pinky_e
                    # Tab switch: thumb-index pinch + other fingers extended.
                    is_tab_switch = (not is_copy) and (not is_paste) and is_left_pinch and middle_e and ring_e and pinky_e

                    active_left = "none"
                    if is_copy:
                        active_left = "copy"
                    elif is_paste:
                        active_left = "paste"
                    elif is_minimize:
                        active_left = "minimize"
                    elif is_maximize:
                        active_left = "maximize"
                    elif is_tab_switch:
                        active_left = "tab"

                    # Reset non-active hold timers
                    for g in ("copy", "paste", "minimize", "maximize"):
                        if active_left != g:
                            left_hold_start[g] = 0.0
                            left_hold_fired[g] = False

                    # Handle copy/paste/minimize/maximize with 1s hold confirm
                    if active_left in left_hold_start:
                        if left_hold_start[active_left] == 0.0:
                            left_hold_start[active_left] = current_time
                        hold_t = current_time - left_hold_start[active_left]

                        if hold_t >= 1.0 and not left_hold_fired[active_left]:
                            if active_left == "copy":
                                pyautogui.hotkey("ctrl", "c")
                                print("LEFT HAND: COPY (hold 1.0s)")
                            elif active_left == "paste":
                                pyautogui.hotkey("ctrl", "v")
                                print("LEFT HAND: PASTE (hold 1.0s)")
                            elif active_left == "minimize":
                                # Press twice so minimize works even from maximized windows.
                                pyautogui.hotkey("win", "down")
                                time.sleep(0.05)
                                pyautogui.hotkey("win", "down")
                                print("LEFT HAND: MINIMIZE WINDOW (hold 1.0s)")
                            elif active_left == "maximize":
                                pyautogui.hotkey("win", "up")
                                print("LEFT HAND: MAXIMIZE WINDOW (hold 1.0s)")
                            left_hold_fired[active_left] = True

                        left_hand_state = active_left
                    else:
                        left_hand_state = "none"

                    # Tab switching with 1s hold confirm
                    if active_left == "tab":
                        if tab_hold_start == 0.0:
                            tab_hold_start = current_time
                        tab_hold_t = current_time - tab_hold_start

                        if tab_hold_t >= 1.0:
                            if not task_switch_active:
                                pyautogui.keyDown("alt")
                                pyautogui.press("tab")
                                task_switch_active = True
                                last_tab_time = current_time
                                print("LEFT HAND: TASK SWITCH START (hold 1.0s)")
                            elif current_time - last_tab_time >= cfg.tab_repeat_sec:
                                pyautogui.press("tab")
                                last_tab_time = current_time
                                print("LEFT HAND: TASK SWITCH CYCLE")
                        else:
                            print(f"LEFT HAND: TASK SWITCH HOLD {tab_hold_t:.1f}/1.0s", end="\r")
                    else:
                        tab_hold_start = 0.0
                        if task_switch_active:
                            pyautogui.keyUp("alt")
                            task_switch_active = False
                            print("LEFT HAND: TASK SWITCH END")

                # Draw skeleton + pinch line
                draw_skeleton_and_line(display, pts, label, glow=cfg.skeleton_glow,
                                       dense=cfg.dense_points_per_bone, line_color=line_color)

            # If no left hand is visible in this frame, clear left-hand hold state.
            if not seen_left_hand:
                left_hand_state = "none"
                tab_hold_start = 0.0
                for g in ("copy", "paste", "minimize", "maximize"):
                    left_hold_start[g] = 0.0
                    left_hold_fired[g] = False
                if task_switch_active:
                    pyautogui.keyUp("alt")
                    task_switch_active = False

        else:
            for i in range(cfg.max_hands):
                smoother.reset(i)
            prev_index_norm = None
            # Reset left hand state when no hands detected
            left_hand_state = "none"
            # Reset scroll mode when no hands detected
            scroll_mode = False
            scroll_was_active = False
            base_scroll_y = 0.0  # Reset scroll reference
            # Reset drag & right-click states when no hands detected
            if is_dragging:
                pyautogui.mouseUp()
                print("DRAG FORCE END (no hands)")
            is_dragging = False
            right_click_active = False
            right_click_hold_start = 0.0
            pinch_start_time = 0.0
            hard_pinch_active = False
            tab_hold_start = 0.0
            for g in ("copy", "paste", "minimize", "maximize"):
                left_hold_start[g] = 0.0
                left_hold_fired[g] = False
            # Safety: Release Alt key if task switch was active
            if task_switch_active:
                pyautogui.keyUp("alt")
                task_switch_active = False
                print("LEFT HAND: TASK SWITCH FORCE END (no hands)")

        # Mode enter/exit
        if cursor_hand and not is_cursor_mode:
            print(">>> CURSOR MODE ACTIVATED <<<")
            is_cursor_mode = True
            prev_index_norm = None
        elif not cursor_hand and is_cursor_mode:
            print("<<< CURSOR MODE DEACTIVATED <<<")
            is_cursor_mode = False
            prev_index_norm = None
            
        # Scroll mode enter/exit
        if scroll_mode and not scroll_was_active:
            print(">>> SCROLL MODE ACTIVATED <<<")
            scroll_was_active = True
        elif not scroll_mode and scroll_was_active:
            print("<<< SCROLL MODE DEACTIVATED <<<")
            scroll_was_active = False

        pinch_state = current_pinch_state

        # HUD
        fps_current = frame_count / (time.time() - start_time + 1e-6)
        det_rate = sum(det_history) / len(det_history) * 100 if det_history else 0
        draw_hud(display, fps_current, det_rate, frame_count, detected_count,
                 hand_detected, enhancing, is_cursor_mode, current_pinch_state, left_hand_state, task_switch_active)

        if switch_gesture_start_time:
            progress = min(1.0, (time.time() - switch_gesture_start_time) / 1.5)
            cv2.rectangle(display, (10, 10), (int(10 + progress * 200), 30), (0, 255, 255), -1)
            cv2.putText(display, "SWITCHING TO VOICE...", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if show_help:
            draw_help_overlay(display)

        cv2.imshow("Easy Hand Cursor - Hold Pinch for Clicks", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('h'):
            show_help = not show_help
            print(f"Help overlay {'ENABLED' if show_help else 'DISABLED'}")
        if key == ord('s'):
            fname = f"hand_{time.strftime('%Y%m%d_%H%M%S')}.png"
            cv2.imwrite(fname, display)
            print(f"Screenshot saved: {fname}")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()

if __name__ == "__main__":
    main()
