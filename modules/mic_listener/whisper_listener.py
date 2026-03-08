"""
whisper_listener.py — Speech-to-text layer for mic_listener.

Uses OpenAI Whisper (local, free, no API key) to transcribe the most recent
audio recording made by the Audio MCP Server.

The Audio MCP Server saves recordings to Windows %TEMP% as .wav files.
After recording, call get_spoken_context() to transcribe and return the text
ready for injection into the § heartbeat prompt as spoken_context.

Model sizes:
  base   — ~140MB, fast, good for clean speech (default)
  small  — ~460MB, better with background noise
  medium — ~1.5GB, high accuracy, slower

First call to get_model() downloads the model if not cached (~140MB for base).
Subsequent calls are instant — model stays in memory as a singleton.
"""

import os
import glob
import tempfile
import logging

logger = logging.getLogger(__name__)

_model = None


def get_model(size: str = "base"):
    """Load Whisper model once and cache it in memory."""
    global _model
    if _model is None:
        logger.info(f"whisper_listener: loading Whisper '{size}' model (first run may download ~140MB)...")
        import whisper
        _model = whisper.load_model(size)
        logger.info("whisper_listener: model loaded.")
    return _model


def find_latest_recording() -> str | None:
    """Find the most recently modified .wav file in the system temp directory."""
    temp_dir = tempfile.gettempdir()
    wav_files = glob.glob(os.path.join(temp_dir, "*.wav"))
    if not wav_files:
        logger.warning("whisper_listener: no .wav files found in temp dir.")
        return None
    latest = max(wav_files, key=os.path.getmtime)
    logger.info(f"whisper_listener: found recording at {latest}")
    return latest


def transcribe_latest(model_size: str = "base") -> str | None:
    """Transcribe the most recent Audio MCP recording. Returns text or None."""
    path = find_latest_recording()
    if not path:
        return None
    try:
        import whisper
        model = get_model(model_size)
        result = model.transcribe(path)
        text = result["text"].strip()
        logger.info(f"whisper_listener: transcribed: {text[:80]}...")
        return text
    except Exception as e:
        logger.error(f"whisper_listener: transcription failed: {e}")
        return None


def get_spoken_context(model_size: str = "base") -> str | None:
    """
    Main entry point for heartbeat integration.
    Returns a formatted string ready for injection into the § prompt, or None.

    Usage in heartbeat.py:
        from modules.mic_listener.whisper_listener import get_spoken_context
        spoken = get_spoken_context()
        if spoken:
            prompt += f"\\n{spoken}"
    """
    text = transcribe_latest(model_size)
    if text:
        return f"[spoken] {text}"
    return None
