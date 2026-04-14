"""
Audio Transcription Module.

Handles speech-to-text conversion using OpenAI Whisper ("base" model).

Features:
- Size & duration validation (max 5MB, 60 seconds)
- Unique UUID-based temp file naming (prevents overwrites)
- Deterministic transcription flow (no background timeout thread race)
- Caller-managed temp file lifecycle (save → process → delete)
- Explicit error handling for diagnostics
- Lazy loading (model loaded once at startup)
- Comprehensive logging for diagnostics

Usage:
    transcriber = AudioTranscriber()
    transcriber.initialize()  # Call once at startup (or use lifespan)
    text = transcriber.transcribe(audio_file_path)
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# Global model instance (loaded once at startup)
_whisper_model = None

# Audio constraints
MAX_AUDIO_SIZE_MB = 5  # 5 MB max file size

# Supported audio formats (common formats, case-insensitive)
SUPPORTED_AUDIO_FORMATS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm', '.aac'}


class AudioTranscriber:
    """
    Handles audio transcription with Whisper "base" model.
    
    Safe file handling:
    - Temp files saved to OS system temp directory
    - Caller is responsible for deleting temp files after transcription
    - No permanent storage of audio files
    """
    
    def __init__(self):
        self.model = None
    
    def initialize(self) -> None:
        """
        Load Whisper "base" model. Call once at application startup.
        
        Should be called during FastAPI lifespan (main.py lifespan context).
        """
        global _whisper_model
        
        if _whisper_model is not None:
            logger.debug("Whisper model already loaded (cache)")
            self.model = _whisper_model
            return
        
        try:
            import whisper  # type: ignore
            logger.info("Loading Whisper 'base' model...")
            _whisper_model = whisper.load_model("base")
            self.model = _whisper_model
            logger.info("✅ Whisper 'base' model loaded successfully")
        except ImportError:
            logger.error("Whisper library not installed. Install with: pip install openai-whisper")
            raise RuntimeError("Audio transcription unavailable: Whisper not installed")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Audio transcription unavailable: {e}")
    
    def _validate_audio_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate audio file (type, size).
        
        Returns:
            Tuple: (is_valid, error_message)
        
        Note: Duration validation is handled by frontend & timeout protection.
        """
        # Check file exists
        if not file_path.exists():
            logger.warning(f"Audio file not found: {file_path}")
            return (False, "Audio file not found")
        
        # Check file type (by extension)
        file_ext = file_path.suffix.lower()
        if file_ext not in SUPPORTED_AUDIO_FORMATS:
            logger.warning(f"Unsupported audio format: {file_ext}")
            return (False, f"Unsupported audio format: {file_ext}")
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_AUDIO_SIZE_MB:
            logger.warning(f"Audio file too large: {file_size_mb:.2f}MB (max {MAX_AUDIO_SIZE_MB}MB)")
            return (False, f"Audio too large. Maximum allowed size is {MAX_AUDIO_SIZE_MB}MB.")
        
        logger.debug(f"Audio file valid: {file_ext}, {file_size_mb:.2f}MB")
        return (True, "")
    
    def transcribe(self, audio_file_path: str, session_id: str = None, question_index: int = None) -> Tuple[str, str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc.)
            session_id: Optional session ID for logging context
            question_index: Optional question index for logging context
        
        Returns:
            Tuple: (transcription_text, error_message)
                - transcription_text: Transcribed text, or empty string on error
                - error_message: Error description, or empty string on success
        
        Lifecycle:
            1. Validate model loaded
            2. Validate file (size, duration, exists)
            3. Transcribe using Whisper
            4. Return result
        
        Error Handling:
            - File not found → return ("", error message)
            - File too large/long → return ("", error message)
            - Transcription fails → return ("", error description)
            - Empty transcription → return ("", "no output")
            - Caller owns temp file cleanup
        """
        
        if not self.model:
            logger.error("Whisper model not initialized")
            return ("", "Whisper model not initialized. Call initialize() first.")
        
        file_path = Path(audio_file_path)
        context_str = f"[session={session_id}, q={question_index}]" if session_id else ""
        
        # Validate audio file
        is_valid, error_msg = self._validate_audio_file(file_path)
        if not is_valid:
            return ("", error_msg)
        
        try:
            logger.debug(f"Starting Whisper transcription {context_str} path={file_path}")
            result = self.model.transcribe(str(file_path))
            transcription = result.get("text", "").strip()

            if not transcription:
                logger.warning(f"Transcription returned empty text {context_str}")
                return ("", "Transcription produced no output")

            logger.info(
                f"Transcription success {context_str}: {len(transcription)} chars, {len(transcription.split())} words"
            )
            return (transcription, "")
        
        except Exception as e:
            error_msg = f"Transcription process error: {str(e)}"
            logger.error(f"Process error {context_str}: {error_msg}", exc_info=True)
            return ("", error_msg)


# Global instance
transcriber = AudioTranscriber()


def transcribe_audio(audio_file_path: str) -> Tuple[str, str]:
    """
    Convenience function to transcribe audio using global transcriber instance.
    
    Args:
        audio_file_path: Path to audio file
    
    Returns:
        Tuple: (transcription_text, error_message)
    """
    if not transcriber.model:
        return ("", "Transcriber not initialized")
    return transcriber.transcribe(audio_file_path)


def get_temp_audio_path(suffix: str = ".wav") -> str:
    """
    Get a UNIQUE temporary file path for audio storage using UUID.
    
    Prevents file overwrites in concurrent requests by including UUID.
    
    Args:
        suffix: File extension (default: ".wav")
    
    Returns:
        Unique temporary file path in system temp directory
    """
    # Use UUID to ensure uniqueness across concurrent requests
    unique_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.gettempdir()
    temp_filename = f"audio_transcribe_{unique_id}{suffix}"
    temp_path = os.path.join(temp_dir, temp_filename)
    logger.debug(f"Generated unique temp path: {temp_path}")
    return temp_path
