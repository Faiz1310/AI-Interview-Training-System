"""
Behavioral confidence from eye contact, head stability, blink rate, stress.
Updated to include audio features and full multimodal fusion.
"""
from typing import Optional, Dict

# Video weights
EYE_CONTACT_WEIGHT    = 0.40
HEAD_STABILITY_WEIGHT = 0.30
BLINK_WEIGHT          = 0.20
STRESS_WEIGHT         = 0.10

BLINK_NORMALIZE_DIVISOR      = 60.0   # blinks per minute
EYE_CONTACT_NUDGE_THRESHOLD  = 0.40
HEAD_STABILITY_NUDGE_THRESHOLD = 0.40
BLINK_SPIKE_THRESHOLD         = 30.0  # blinks/min

# Audio weights (for when audio is available)
AUDIO_SPEECH_RATE_WEIGHT     = 0.30
AUDIO_PAUSE_WEIGHT           = 0.30
AUDIO_PITCH_VAR_WEIGHT       = 0.25
AUDIO_ENERGY_VAR_WEIGHT      = 0.15

# Multimodal fusion weights
VIDEO_CONFIDENCE_WEIGHT      = 0.60
AUDIO_CONFIDENCE_WEIGHT      = 0.25
TEXT_HESITATION_WEIGHT       = 0.15


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def compute_behavioral_confidence(
    avg_eye_contact: float,
    avg_head_stability: float,
    avg_blink_rate: float,       # blinks per minute
    avg_facial_stress: float,
) -> float:
    """Compute behavioral confidence score (0-100) from video features."""
    normalized_blink = min(1.0, max(0.0, avg_blink_rate / BLINK_NORMALIZE_DIVISOR))
    score = (
        EYE_CONTACT_WEIGHT    * _clamp(avg_eye_contact, 0, 1)
        + HEAD_STABILITY_WEIGHT * _clamp(avg_head_stability, 0, 1)
        + BLINK_WEIGHT          * (1.0 - normalized_blink)
        + STRESS_WEIGHT         * (1.0 - _clamp(avg_facial_stress, 0, 1))
    ) * 100.0
    return round(_clamp(score, 0, 100), 2)


def compute_audio_confidence(
    speech_rate: float,
    pause_duration: float,
    pitch_variation: float,
    energy_variation: float,
) -> float:
    """Compute confidence score (0-100) from audio features."""
    score = (
        AUDIO_SPEECH_RATE_WEIGHT     * _clamp(speech_rate, 0, 1)
        + AUDIO_PAUSE_WEIGHT         * _clamp(pause_duration, 0, 1)
        + AUDIO_PITCH_VAR_WEIGHT     * _clamp(pitch_variation, 0, 1)
        + AUDIO_ENERGY_VAR_WEIGHT    * _clamp(energy_variation, 0, 1)
    ) * 100.0
    return round(_clamp(score, 0, 100), 2)


def compute_multimodal_confidence(
    video_confidence: float,
    audio_confidence: Optional[float] = None,
    text_hesitation_score: Optional[float] = None,
) -> float:
    """
    Fuse video, audio, and text cues into final confidence score.
    
    Weights:
    - Video (eye contact, head stability, etc.): 60%
    - Audio (speech rate, pauses, pitch, energy): 25%
    - Text hesitation: 15%
    """
    video_weight = VIDEO_CONFIDENCE_WEIGHT
    audio_weight = AUDIO_CONFIDENCE_WEIGHT if audio_confidence is not None else 0.0
    text_weight = TEXT_HESITATION_WEIGHT if text_hesitation_score is not None else 0.0
    
    # Normalize weights
    total_weight = video_weight + audio_weight + text_weight
    video_weight /= total_weight
    if audio_weight > 0:
        audio_weight /= total_weight
    if text_weight > 0:
        text_weight /= total_weight
    
    score = video_weight * _clamp(video_confidence, 0, 100)
    
    if audio_confidence is not None:
        score += audio_weight * _clamp(audio_confidence, 0, 100)
    
    if text_hesitation_score is not None:
        # Convert hesitation score to confidence (1 - hesitation = confidence)
        text_confidence = (1.0 - _clamp(text_hesitation_score, 0, 1)) * 100.0
        score += text_weight * text_confidence
    
    return round(_clamp(score, 0, 100), 2)


def get_nudge(
    avg_eye_contact: float,
    avg_head_stability: float,
    avg_blink_rate: float,
    window_seconds: float,
    audio_features: Optional[Dict] = None,
) -> Optional[str]:
    """Return real-time coaching nudge or None."""
    nudges = []
    
    # Video nudges
    if window_seconds >= 4 and avg_eye_contact < EYE_CONTACT_NUDGE_THRESHOLD:
        nudges.append("Maintain steady eye contact with the camera.")
    
    if avg_head_stability < HEAD_STABILITY_NUDGE_THRESHOLD:
        nudges.append("Try to keep your head still and steady.")
    
    if avg_blink_rate >= BLINK_SPIKE_THRESHOLD:
        nudges.append("Take a slow breath — you seem nervous.")
    
    # Audio nudges
    if audio_features:
        speech_rate = audio_features.get("speech_rate", 0.5)
        pause_duration = audio_features.get("pause_duration", 0.5)
        
        if speech_rate < 0.3:
            nudges.append("Try speaking a bit faster to sound more confident.")
        elif speech_rate > 0.9:
            nudges.append("Slow down a bit — take your time.")
        
        if pause_duration < 0.2:
            nudges.append("Add some pauses between key points.")
    
    # Return the most relevant nudge (first one) or None
    return nudges[0] if nudges else None


def get_supportive_feedback(
    confidence_score: float,
    stress_level: float,
) -> Optional[str]:
    """
    Provide supportive feedback when stress is detected.
    This is separate from nudges — it's encouragement, not correction.
    """
    if stress_level > 0.7 and confidence_score < 50:
        return "Take a moment and explain step by step. You've got this!"
    
    if stress_level > 0.6:
        return "You're doing well, continue calmly."
    
    if confidence_score < 40:
        return "Remember to breathe. Focus on one point at a time."
    
    return None
