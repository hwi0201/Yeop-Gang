from pathlib import Path
from typing import Any, Dict, List
import tempfile
import os

from ai.config import AISettings


def _openai_client(settings: AISettings):
    from openai import OpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key)


def _split_audio_file(
    audio_path: Path, max_size_mb: float = 20.0, temp_dir: Path | None = None
) -> List[Path]:
    """
    Split audio file into chunks that are under max_size_mb.
    
    Returns list of chunk file paths.
    Uses pydub which requires ffmpeg.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        raise ImportError(
            "pydub is required for audio splitting. Install with: pip install pydub"
            " Also install ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
        )
    
    if temp_dir is None:
        temp_dir = Path(tempfile.mkdtemp())
    else:
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Load audio file
    audio = AudioSegment.from_file(str(audio_path))
    duration_ms = len(audio)
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    
    # Estimate duration per chunk (conservative estimate: 20MB per 10 minutes)
    # Use a safer ratio: assume 20MB = ~10 minutes of audio
    estimated_ms_per_mb = (10 * 60 * 1000) / 20  # 10 minutes in ms / 20MB
    chunk_duration_ms = int(max_size_mb * estimated_ms_per_mb * 0.9)  # 90% to be safe
    
    chunks: List[Path] = []
    chunk_index = 0
    start_ms = 0
    
    while start_ms < duration_ms:
        end_ms = min(start_ms + chunk_duration_ms, duration_ms)
        chunk_audio = audio[start_ms:end_ms]
        
        # Export chunk
        chunk_path = temp_dir / f"chunk_{chunk_index:03d}.mp3"
        chunk_audio.export(str(chunk_path), format="mp3")
        
        # Verify chunk size
        chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
        if chunk_size_mb > max_size_mb:
            # If chunk is still too large, reduce duration and retry
            print(f"Warning: Chunk {chunk_index} is {chunk_size_mb:.2f}MB, reducing duration...")
            chunk_duration_ms = int(chunk_duration_ms * 0.7)  # Reduce by 30%
            chunk_path.unlink()  # Delete oversized chunk
            continue
        
        chunks.append(chunk_path)
        chunk_index += 1
        start_ms = end_ms
        
        print(f"Created chunk {chunk_index}: {chunk_size_mb:.2f}MB ({start_ms/1000:.1f}s - {end_ms/1000:.1f}s)")
    
    return chunks


def _transcribe_single_file(file_path: Path, settings: AISettings) -> Dict[str, Any]:
    """Transcribe a single audio/video file (must be under 25MB)."""
    client = _openai_client(settings)
    
    # Read file into memory
    with file_path.open("rb") as f:
        file_content = f.read()
    
    # Create a file-like object from bytes
    import io
    file_obj = io.BytesIO(file_content)
    file_obj.name = file_path.name
    
    # Transcribe
    resp = client.audio.transcriptions.create(
        file=file_obj,
        model="whisper-1",
    )
    
    transcript_text = resp.text if hasattr(resp, "text") else str(resp)
    
    return {
        "text": transcript_text,
        "segments": [
            {
                "start": 0.0,
                "end": 0.0,
                "text": transcript_text,
            }
        ],
    }


def transcribe_video(video_path: str, settings: AISettings | None = None) -> Dict[str, Any]:
    """
    Transcribe a video/audio file using OpenAI Whisper.
    Automatically splits large files (>25MB) into chunks.

    Returns:
        {
            "text": str,
            "segments": List[{"start": float, "end": float, "text": str}]
        }

    Fallback: if API key가 없거나 에러 시 placeholder를 반환해 파이프라인이 계속 진행되도록 함.
    """
    settings = settings or AISettings()
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    try:
        # Check API key first
        if not settings.openai_api_key:
            print("ERROR: OPENAI_API_KEY is not set in settings")
            raise RuntimeError("OPENAI_API_KEY is not set")
        
        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f}MB")
        
        # If file is small enough, transcribe directly
        if file_size_mb <= 25:
            print("File is under 25MB, transcribing directly...")
            result = _transcribe_single_file(path, settings)
            print(f"STT success: transcribed text length: {len(result['text'])}")
            return result
        
        # File is too large, need to split
        print(f"File is {file_size_mb:.2f}MB, splitting into chunks...")
        temp_dir = Path(tempfile.mkdtemp(prefix="stt_chunks_"))
        
        try:
            chunks = _split_audio_file(path, max_size_mb=20.0, temp_dir=temp_dir)
            print(f"Split into {len(chunks)} chunks")
            
            # Transcribe each chunk
            all_texts: List[str] = []
            all_segments: List[Dict[str, Any]] = []
            time_offset = 0.0  # Track cumulative time offset
            
            for i, chunk_path in enumerate(chunks):
                print(f"Transcribing chunk {i+1}/{len(chunks)}...")
                chunk_result = _transcribe_single_file(chunk_path, settings)
                
                chunk_text = chunk_result["text"]
                all_texts.append(chunk_text)
                
                # Add segments with time offset
                for seg in chunk_result.get("segments", []):
                    if seg.get("text"):
                        all_segments.append({
                            "start": seg.get("start", 0.0) + time_offset,
                            "end": seg.get("end", 0.0) + time_offset,
                            "text": seg.get("text", ""),
                        })
                
                # Estimate time offset for next chunk (rough estimate: 1 char ≈ 0.05 seconds)
                # This is approximate; for accurate timing, we'd need actual audio duration
                estimated_duration = len(chunk_text) * 0.05
                time_offset += estimated_duration
            
            # Combine all texts
            combined_text = "\n\n".join(all_texts)
            
            print(f"STT success: transcribed {len(chunks)} chunks, total text length: {len(combined_text)}")
            return {
                "text": combined_text,
                "segments": all_segments if all_segments else [
                    {"start": 0.0, "end": 0.0, "text": combined_text}
                ],
            }
        finally:
            # Clean up temporary chunk files
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        
    except Exception as e:
        # Log the actual error for debugging
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"STT ERROR [{error_type}]: {error_msg}")
        # Fallback to placeholder transcript
        placeholder = (
            "Transcription placeholder. Whisper STT not available; "
            "please set OPENAI_API_KEY to enable real transcription."
        )
        return {"text": placeholder, "segments": []}
