"""
Utility module for gesture recognition system.
Includes landmark smoothing, image enhancement, and drawing functions.
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from config import Config, Palette, FINGER_DEFS, BONE_GROUPS, BONE_COLOURS


class LandmarkSmoother:
    """Smooths hand landmarks using exponential moving average."""
    
    def __init__(self, alpha: float = 0.6):
        self.alpha = alpha
        self._prev: Dict[int, List[Tuple[float, float, float]]] = {}

    def smooth(self, hand_id: int, landmarks) -> List[Tuple[float, float, float]]:
        """Smooth landmarks for a given hand."""
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
        """Reset smoothing state for a hand."""
        self._prev.pop(hand_id, None)


class ImageEnhancer:
    """Enhances image quality in low-light conditions."""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.clahe = cv2.createCLAHE(
            clipLimit=cfg.clahe_clip_limit,
            tileGridSize=cfg.clahe_grid_size
        )
        self._gamma_lut = np.array([
            ((i / 255.0) ** (1.0 / cfg.gamma_correction)) * 255
            for i in range(256)
        ]).astype("uint8")

    def process(self, bgr: np.ndarray) -> np.ndarray:
        """Enhance image for better hand detection in low light."""
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
            enhanced = cv2.bilateralFilter(
                enhanced, self.cfg.denoise_h,
                self.cfg.denoise_template, self.cfg.denoise_search
            )
        return enhanced


def is_finger_extended(pts: List[Tuple[float, float, float]], 
                       name: str, hand_label: str) -> bool:
    """Check if a finger is extended based on landmark positions."""
    d = FINGER_DEFS[name]
    tip, pip, mcp = pts[d["tip"]], pts[d["pip"]], pts[d["mcp"]]
    
    if name == "Thumb":
        return tip[0] > pip[0] if hand_label == "Right" else tip[0] < pip[0]
    return tip[1] < pip[1] and pip[1] < mcp[1]


def _to_px(pt: Tuple[float, float, float], w: int, h: int) -> Tuple[int, int]:
    """Convert normalized coordinates to pixel coordinates."""
    return (int(pt[0] * w), int(pt[1] * h))


def draw_skeleton_and_line(
    frame: np.ndarray,
    pts: List[Tuple[float, float, float]],
    hand_label: str,
    glow: bool = True,
    dense: int = 6,
    line_color: Tuple[int, int, int] = (0, 255, 0)
):
    """Draw hand skeleton and thumb-index pinch line."""
    h, w = frame.shape[:2]
    
    # Draw skeleton bones
    for group, indices in BONE_GROUPS.items():
        colour = BONE_COLOURS[group]
        coords = [_to_px(pts[i], w, h) for i in indices]
        for a, b in zip(coords, coords[1:]):
            if glow:
                cv2.line(frame, a, b, colour, 8, cv2.LINE_AA)
                cv2.line(frame, a, b, (255, 255, 255), 3, cv2.LINE_AA)
            else:
                cv2.line(frame, a, b, colour, 3, cv2.LINE_AA)

    # Draw joints
    for i, pt in enumerate(pts):
        px = _to_px(pt, w, h)
        is_tip = i in (4, 8, 12, 16, 20)
        r_outer = 8 if is_tip else 6
        group_colour = BONE_COLOURS.get(
            next((g for g, ids in BONE_GROUPS.items() if i in ids), "palm"),
            (200, 200, 200)
        )
        cv2.circle(frame, px, r_outer + 4, group_colour, -1)
        cv2.circle(frame, px, r_outer, (220, 220, 220), -1)
        cv2.circle(frame, px, 4 if is_tip else 3, (255, 255, 255), -1)

    # Draw thumb-index line
    thumb_px = _to_px(pts[4], w, h)
    index_px = _to_px(pts[8], w, h)
    cv2.line(frame, thumb_px, index_px, line_color, 4, cv2.LINE_AA)
    cv2.circle(frame, thumb_px, 12, line_color, 3)
    cv2.circle(frame, index_px, 12, line_color, 3)

    # Draw cursor pointer
    cv2.circle(frame, index_px, 20, Palette.CURSOR_POINTER, 3, cv2.LINE_AA)
    cv2.circle(frame, index_px, 10, (255, 255, 0), -1)


def draw_hud(
    frame: np.ndarray,
    fps: float,
    det_rate: float,
    frame_count: int,
    detected_count: int,
    hand_detected: bool,
    enhancing: bool,
    is_cursor_mode: bool,
    pinch_mode: str,
    left_hand_state: str,
    task_switch_active: bool
):
    """Draw heads-up display with status information."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    
    # Calculate HUD height
    extra = 1 if is_cursor_mode else 0
    if pinch_mode != "open":
        extra += 1
    if left_hand_state != "none":
        extra += 1
    if task_switch_active:
        extra += 1
    
    cv2.rectangle(overlay, (0, 0), (360, 140 + extra * 25), (10, 10, 18), -1)
    frame[:] = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    # Hand detection status
    col = (0, 255, 120) if hand_detected else (0, 80, 255)
    status_text = "HAND DETECTED" if hand_detected else "NO HAND"
    cv2.putText(frame, status_text, (12, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
    
    # FPS and frame count
    fps_text = f"FPS: {int(fps)}   Frames: {frame_count}"
    cv2.putText(frame, fps_text, (12, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Detection rate
    det_text = f"Detected: {detected_count} ({det_rate:.1f}%)"
    cv2.putText(frame, det_text, (12, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    y = 115
    if enhancing:
        cv2.putText(frame, "LOW-LIGHT ACTIVE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
        y += 25
    
    if is_cursor_mode:
        cv2.putText(frame, "CURSOR MODE (RELATIVE)", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        y += 25
    
    if pinch_mode == "mild":
        text = "MILD PINCH → SINGLE CLICK (REPEAT 1s)"
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    elif pinch_mode == "tight":
        text = "TIGHT PINCH → DOUBLE CLICK (REPEAT 2s)"
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    if left_hand_state == "fist":
        cv2.putText(frame, "LEFT HAND: MINIMIZE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 1)

    if task_switch_active:
        cv2.putText(frame, "LEFT HAND: TASK SWITCH", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 150, 255), 1)

    # Footer
    cv2.putText(frame, "Q=quit  S=screenshot", (w - 220, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)


def open_camera(cfg: Config):
    """Open camera and set resolution."""
    for i in range(4):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera_height)
            cap.set(cv2.CAP_PROP_FPS, cfg.target_fps)
            print(f"Camera {i} opened at {cfg.camera_width}x{cfg.camera_height}")
            return cap, i
    return None, -1
