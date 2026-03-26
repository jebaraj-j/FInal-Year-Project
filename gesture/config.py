"""
Configuration module for gesture recognition system.
Defines settings, color palette, and finger definitions.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Config:
    """Main configuration class for the gesture recognition system."""
    camera_width: int = 1280
    camera_height: int = 720
    target_fps: int = 30
    max_hands: int = 2
    model_complexity: int = 1
    min_detection_conf: float = 0.35
    min_tracking_conf: float = 0.35
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
    mild_pinch_max: float = 0.060   # Small gap → single click mode
    tight_pinch_max: float = 0.035  # Very small gap → double click mode
    
    # Repeat rates
    single_repeat_sec: float = 1.0
    double_repeat_sec: float = 2.0
    
    # Relative movement
    sensitivity: float = 4.5
    deadzone: float = 0.003
    
    # Left-hand pinch detection for Alt+Tab
    left_pinch_threshold: float = 0.05
    tab_repeat_sec: float = 0.6
    
    # Scroll gesture detection
    scroll_deadzone: float = 0.05
    scroll_sensitivity: float = 1.0


# Global configuration instance
CFG = Config()


class Palette:
    """Color palette for visualization."""
    LINE_OPEN = (0, 255, 0)      # Green - open
    LINE_MILD = (0, 165, 255)    # Orange - mild pinch (single click)
    LINE_TIGHT = (0, 0, 255)     # Red - tight pinch (double click)
    CURSOR_POINTER = (0, 255, 255)  # Yellow ring


FINGER_DEFS: Dict[str, Dict[str, int]] = {
    "Thumb": {"tip": 4, "pip": 3, "mcp": 2},
    "Index": {"tip": 8, "pip": 6, "mcp": 5},
    "Middle": {"tip": 12, "pip": 10, "mcp": 9},
    "Ring": {"tip": 16, "pip": 14, "mcp": 13},
    "Pinky": {"tip": 20, "pip": 18, "mcp": 17},
}

BONE_GROUPS: Dict[str, List[int]] = {
    "thumb": [0, 1, 2, 3, 4],
    "index": [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring": [13, 14, 15, 16],
    "pinky": [17, 18, 19, 20],
    "palm": [0, 5, 9, 13, 17, 0],
}

BONE_COLOURS: Dict[str, Tuple[int, int, int]] = {
    "thumb": (255, 200, 60),
    "index": (60, 220, 255),
    "middle": (180, 255, 60),
    "ring": (255, 80, 200),
    "pinky": (255, 160, 40),
    "palm": (200, 200, 200),
}
