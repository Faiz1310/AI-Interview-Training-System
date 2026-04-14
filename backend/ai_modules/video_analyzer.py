"""
Video behavioral analysis module.
Processes facial landmark data from MediaPipe FaceMesh (sent from frontend).
Extracts: eye contact ratio, head stability, blink rate, facial stress indicators.
These features contribute ONLY to confidence estimation.
"""
import logging
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Landmark indices for key facial features (MediaPipe FaceMesh 468 points)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
LEFT_IRIS_CENTER = 468  # MediaPipe iris landmark
RIGHT_IRIS_CENTER = 473
NOSE_TIP = 1
LEFT_EAR = 234
RIGHT_EAR = 454
FOREHEAD = 10
CHIN = 152

# Blink detection: eye aspect ratio threshold
EAR_BLINK_THRESHOLD = 0.22


def _eye_aspect_ratio(landmarks: List[Dict], indices: List[int]) -> float:
    """Compute Eye Aspect Ratio (EAR) for blink detection."""
    try:
        p = [landmarks[i] for i in indices]
        vertical_1 = math.sqrt((p[1]["x"] - p[5]["x"]) ** 2 + (p[1]["y"] - p[5]["y"]) ** 2)
        vertical_2 = math.sqrt((p[2]["x"] - p[4]["x"]) ** 2 + (p[2]["y"] - p[4]["y"]) ** 2)
        horizontal = math.sqrt((p[0]["x"] - p[3]["x"]) ** 2 + (p[0]["y"] - p[3]["y"]) ** 2)
        if horizontal == 0:
            return 0.0
        return (vertical_1 + vertical_2) / (2.0 * horizontal)
    except (IndexError, KeyError):
        return 0.3  # neutral fallback


def compute_eye_contact(landmarks: List[Dict]) -> float:
    """
    Estimate eye contact ratio (0-1) based on iris position relative to eye bounds.
    Higher = looking more toward the camera.
    """
    try:
        if len(landmarks) < 474:
            # No iris landmarks, estimate from eye openness
            left_ear = _eye_aspect_ratio(landmarks, LEFT_EYE_INDICES)
            right_ear = _eye_aspect_ratio(landmarks, RIGHT_EYE_INDICES)
            avg_ear = (left_ear + right_ear) / 2.0
            return min(1.0, max(0.0, avg_ear / 0.35))

        nose = landmarks[NOSE_TIP]
        left_iris = landmarks[LEFT_IRIS_CENTER]
        right_iris = landmarks[RIGHT_IRIS_CENTER]

        # Compute gaze deviation from center
        left_eye_center_x = sum(landmarks[i]["x"] for i in LEFT_EYE_INDICES) / len(LEFT_EYE_INDICES)
        right_eye_center_x = sum(landmarks[i]["x"] for i in RIGHT_EYE_INDICES) / len(RIGHT_EYE_INDICES)

        left_deviation = abs(left_iris["x"] - left_eye_center_x)
        right_deviation = abs(right_iris["x"] - right_eye_center_x)
        avg_deviation = (left_deviation + right_deviation) / 2.0

        # Lower deviation = more centered gaze = better eye contact
        score = max(0.0, 1.0 - avg_deviation * 15.0)
        return min(1.0, score)

    except (IndexError, KeyError) as e:
        logger.debug(f"[VideoAnalyzer] Eye contact estimation failed: {e}")
        return 0.5


def compute_head_stability(landmarks_history: List[List[Dict]], max_frames: int = 10) -> float:
    """
    Compute head stability (0-1) by measuring nose tip movement over recent frames.
    1.0 = perfectly still, 0.0 = very shaky.
    """
    try:
        frames = landmarks_history[-max_frames:]
        if len(frames) < 2:
            return 0.7  # not enough data

        nose_positions = []
        for lm in frames:
            if len(lm) > NOSE_TIP:
                nose_positions.append((lm[NOSE_TIP]["x"], lm[NOSE_TIP]["y"]))

        if len(nose_positions) < 2:
            return 0.7

        total_movement = 0.0
        for i in range(1, len(nose_positions)):
            dx = nose_positions[i][0] - nose_positions[i - 1][0]
            dy = nose_positions[i][1] - nose_positions[i - 1][1]
            total_movement += math.sqrt(dx * dx + dy * dy)

        avg_movement = total_movement / (len(nose_positions) - 1)

        # Normalize: 0 movement = 1.0 score, 0.05+ movement = 0.0
        stability = max(0.0, 1.0 - avg_movement * 20.0)
        return min(1.0, stability)

    except Exception as e:
        logger.debug(f"[VideoAnalyzer] Head stability failed: {e}")
        return 0.5


def detect_blink(landmarks: List[Dict]) -> bool:
    """Detect if eyes are closed (blink) using Eye Aspect Ratio."""
    left_ear = _eye_aspect_ratio(landmarks, LEFT_EYE_INDICES)
    right_ear = _eye_aspect_ratio(landmarks, RIGHT_EYE_INDICES)
    avg_ear = (left_ear + right_ear) / 2.0
    return avg_ear < EAR_BLINK_THRESHOLD


def compute_facial_stress(landmarks: List[Dict]) -> float:
    """
    Estimate facial stress (0-1) from facial landmark analysis.
    Considers: brow tension, mouth compression, face asymmetry.
    """
    try:
        # Brow tension: distance between inner eyebrow points
        left_brow_inner = landmarks[107] if len(landmarks) > 107 else None
        right_brow_inner = landmarks[336] if len(landmarks) > 336 else None

        stress = 0.0

        if left_brow_inner and right_brow_inner:
            brow_dist = math.sqrt(
                (left_brow_inner["x"] - right_brow_inner["x"]) ** 2
                + (left_brow_inner["y"] - right_brow_inner["y"]) ** 2
            )
            # Closer brows = more tension
            if brow_dist < 0.08:
                stress += 0.3

        # Mouth compression
        upper_lip = landmarks[13] if len(landmarks) > 13 else None
        lower_lip = landmarks[14] if len(landmarks) > 14 else None
        if upper_lip and lower_lip:
            lip_dist = abs(upper_lip["y"] - lower_lip["y"])
            if lip_dist < 0.015:
                stress += 0.3

        # Face asymmetry
        if len(landmarks) > max(LEFT_EAR, RIGHT_EAR):
            left = landmarks[LEFT_EAR]
            right = landmarks[RIGHT_EAR]
            nose = landmarks[NOSE_TIP]
            left_dist = abs(nose["x"] - left["x"])
            right_dist = abs(nose["x"] - right["x"])
            asymmetry = abs(left_dist - right_dist) / max(left_dist, right_dist, 0.001)
            stress += min(0.4, asymmetry)

        return min(1.0, max(0.0, stress))

    except (IndexError, KeyError) as e:
        logger.debug(f"[VideoAnalyzer] Stress estimation failed: {e}")
        return 0.3


def analyze_frame(
    landmarks: List[Dict],
    landmarks_history: Optional[List[List[Dict]]] = None,
) -> Dict:
    """
    Analyze a single frame of facial landmarks.

    Args:
        landmarks: List of {x, y, z} dicts from MediaPipe FaceMesh (468+ points)
        landmarks_history: Previous frames for stability computation

    Returns:
        Dict with eye_contact, head_stability, is_blink, facial_stress
    """
    eye_contact = compute_eye_contact(landmarks)
    head_stability = compute_head_stability(landmarks_history or [landmarks])
    is_blink = detect_blink(landmarks)
    facial_stress = compute_facial_stress(landmarks)

    return {
        "eye_contact": round(eye_contact, 3),
        "head_stability": round(head_stability, 3),
        "is_blink": is_blink,
        "facial_stress": round(facial_stress, 3),
    }
