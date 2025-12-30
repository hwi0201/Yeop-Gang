from pathlib import Path


def transcribe_video(video_path: str) -> str:
    """
    Placeholder for Whisper-based transcription.

    Replace with actual Whisper / OpenAI API integration.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # TODO: Integrate OpenAI Whisper or hosted STT service.
    return "Transcription placeholder. Implement Whisper STT here."

