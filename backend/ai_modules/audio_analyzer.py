"""
Audio behavioral analysis using librosa.
Extracts: speech rate, pause duration, pitch variation, energy variation.
These features contribute to confidence estimation.
"""
import io
import logging
import numpy as np
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


def analyze_audio_features(audio_bytes: bytes, sample_rate: int = 22050) -> Dict:
    """
    Analyze audio features from audio bytes.

    Args:
        audio_bytes: Raw audio data (assumes WAV format)
        sample_rate: Target sample rate for analysis

    Returns:
        Dict with speech_rate, pause_duration, pitch_variation, energy_variation
    """
    try:
        import librosa
        import soundfile as sf

        # Load audio from bytes
        audio, sr = sf.read(io.BytesIO(audio_bytes))

        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # Resample if needed
        if sr != sample_rate:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=sample_rate)
            sr = sample_rate

        # Analyze features
        speech_rate = _calculate_speech_rate(audio, sr)
        pause_duration = _calculate_pause_duration(audio, sr)
        pitch_variation = _calculate_pitch_variation(audio, sr)
        energy_variation = _calculate_energy_variation(audio, sr)

        return {
            "speech_rate": round(speech_rate, 2),
            "pause_duration": round(pause_duration, 2),
            "pitch_variation": round(pitch_variation, 2),
            "energy_variation": round(energy_variation, 2),
        }

    except Exception as e:
        logger.error(f"[AudioAnalyzer] Failed to analyze audio: {e}")
        return {
            "speech_rate": 0.0,
            "pause_duration": 0.0,
            "pitch_variation": 0.0,
            "energy_variation": 0.0,
            "error": str(e),
        }


def _calculate_speech_rate(audio: np.ndarray, sr: int) -> float:
    """Calculate speech rate (words per minute estimate)."""
    try:
        import librosa

        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        estimated_syllables = len(onsets)
        duration_minutes = len(audio) / sr / 60.0

        if duration_minutes <= 0:
            return 0.0

        estimated_words = estimated_syllables / 1.5
        wpm = estimated_words / duration_minutes

        if wpm < 80:
            return max(0.0, wpm / 80.0 * 0.5)
        elif wpm > 200:
            return max(0.0, 1.0 - (wpm - 200) / 100.0 * 0.5)
        else:
            return 0.7 + 0.3 * (1.0 - abs(wpm - 135) / 65)

    except Exception as e:
        logger.warning(f"[AudioAnalyzer] Speech rate calculation failed: {e}")
        return 0.5


def _calculate_pause_duration(audio: np.ndarray, sr: int) -> float:
    """Calculate average pause duration."""
    try:
        import librosa

        frame_length = int(sr * 0.025)
        hop_length = int(sr * 0.010)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        silence_threshold = np.max(rms) * 0.05 if np.max(rms) > 0 else 0.01
        silent_frames = rms < silence_threshold

        pauses = []
        current_pause = 0

        for is_silent in silent_frames:
            if is_silent:
                current_pause += 1
            else:
                if current_pause > 0:
                    pauses.append(current_pause)
                current_pause = 0

        if not pauses:
            return 1.0

        avg_pause_frames = np.mean(pauses)
        avg_pause_seconds = (avg_pause_frames * hop_length) / sr

        if avg_pause_seconds < 0.3:
            return 1.0
        elif avg_pause_seconds > 2.0:
            return 0.0
        else:
            return 1.0 - (avg_pause_seconds - 0.3) / 1.7

    except Exception as e:
        logger.warning(f"[AudioAnalyzer] Pause duration calculation failed: {e}")
        return 0.5


def _calculate_pitch_variation(audio: np.ndarray, sr: int) -> float:
    """Calculate pitch variation (intonation)."""
    try:
        import librosa

        pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
        pitch_values = []

        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)

        if len(pitch_values) < 2:
            return 0.5

        pitch_mean = np.mean(pitch_values)
        pitch_std = np.std(pitch_values)

        if pitch_mean == 0:
            return 0.5

        cv = pitch_std / pitch_mean

        if cv < 0.05:
            return cv / 0.05 * 0.5
        elif cv > 0.5:
            return max(0.0, 1.0 - (cv - 0.5) / 0.5 * 0.5)
        else:
            return 0.5 + 0.5 * (1.0 - abs(cv - 0.2) / 0.3)

    except Exception as e:
        logger.warning(f"[AudioAnalyzer] Pitch variation calculation failed: {e}")
        return 0.5


def _calculate_energy_variation(audio: np.ndarray, sr: int) -> float:
    """Calculate energy/volume variation."""
    try:
        import librosa

        frame_length = int(sr * 0.025)
        hop_length = int(sr * 0.010)
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        if len(rms) < 2 or np.mean(rms) == 0:
            return 0.5

        energy_mean = np.mean(rms)
        energy_std = np.std(rms)
        cv = energy_std / energy_mean

        if cv < 0.1:
            return cv / 0.1 * 0.5
        elif cv > 1.0:
            return max(0.0, 1.0 - (cv - 1.0) / 1.0 * 0.5)
        else:
            return 0.5 + 0.5 * (1.0 - abs(cv - 0.35) / 0.35)

    except Exception as e:
        logger.warning(f"[AudioAnalyzer] Energy variation calculation failed: {e}")
        return 0.5


def compute_audio_confidence(audio_features: Dict) -> float:
    """Compute confidence score (0-100) from audio features."""
    speech_rate = audio_features.get("speech_rate", 0.5)
    pause_duration = audio_features.get("pause_duration", 0.5)
    pitch_variation = audio_features.get("pitch_variation", 0.5)
    energy_variation = audio_features.get("energy_variation", 0.5)

    score = (
        0.30 * speech_rate +
        0.30 * pause_duration +
        0.25 * pitch_variation +
        0.15 * energy_variation
    ) * 100.0

    return round(max(0.0, min(100.0, score)), 2)


def analyze_text_hesitation(text: str) -> Dict:
    """Analyze text for hesitation indicators."""
    import re

    hesitation_patterns = [
        r"\b(uh+|um+|er+|ah+|oh+)\b",
        r"\b(like)\b.*\b(like)\b",
        r"\b(you know)\b.*\b(you know)\b",
        r"\b(sort of|kind of)\b",
        r"\b(i mean)\b",
        r"\.{3,}",
        r"\b(etc|whatever|stuff like that)\b",
    ]

    text_lower = text.lower()
    hesitation_count = 0

    for pattern in hesitation_patterns:
        matches = re.findall(pattern, text_lower)
        hesitation_count += len(matches)

    words = len(text.split())
    if words == 0:
        return {"hesitation_score": 1.0, "hesitation_count": 0}

    hesitation_ratio = hesitation_count / words
    hesitation_score = max(0.0, 1.0 - hesitation_ratio * 5)

    return {
        "hesitation_score": round(hesitation_score, 2),
        "hesitation_count": hesitation_count,
    }
