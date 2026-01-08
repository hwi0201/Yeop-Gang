from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile
import os
import json
import shutil

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


def _transcribe_with_google(file_path: Path, settings: AISettings) -> Dict[str, Any]:
    """
    Google Cloud Speech-to-Text API를 사용하여 오디오/비디오 파일을 전사합니다.
    YouTube와 유사한 높은 품질의 음성 인식을 제공합니다.
    """
    try:
        from google.cloud import speech
        from google.oauth2 import service_account
        import io
        
        print(f"🎤 Using Google Cloud Speech-to-Text (YouTube-quality) for: {file_path.name}")
        print(f"📦 File size: {file_path.stat().st_size / (1024 * 1024):.2f}MB")
        
        # Google 인증 설정
        credentials = None
        if settings.google_credentials_path:
            # 서비스 계정 키 파일 사용
            credentials_path = Path(settings.google_credentials_path)
            if credentials_path.exists():
                credentials = service_account.Credentials.from_service_account_file(
                    str(credentials_path),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                print(f"✅ Using service account credentials: {credentials_path}")
            else:
                print(f"⚠️ Credentials file not found: {credentials_path}")
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            # 환경 변수에서 자동으로 로드
            print("✅ Using GOOGLE_APPLICATION_CREDENTIALS environment variable")
        
        # Speech client 생성
        if credentials:
            client = speech.SpeechClient(credentials=credentials)
        else:
            client = speech.SpeechClient()
        
        # 오디오 파일 읽기
        with io.open(file_path, "rb") as audio_file:
            content = audio_file.read()
        
        # 오디오 설정 (한국어)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # 자동 감지
            sample_rate_hertz=16000,  # 일반적인 샘플 레이트
            language_code="ko-KR",  # 한국어
            enable_automatic_punctuation=True,  # 자동 구두점
            enable_word_time_offsets=True,  # 단어별 타임스탬프
            model="latest_long",  # 긴 오디오에 최적화된 모델
        )
        
        # 오디오 파일이 크면 (10MB 이상) long-running recognition 사용
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 10:
            print("📤 Using long-running recognition for large file...")
            audio = speech.RecognitionAudio(content=content)
            operation = client.long_running_recognize(config=config, audio=audio)
            print("⏳ Waiting for operation to complete (this may take a while)...")
            response = operation.result(timeout=600)  # 최대 10분 대기
        else:
            print("⏳ Transcribing audio file...")
            audio = speech.RecognitionAudio(content=content)
            response = client.recognize(config=config, audio=audio)
        
        # 결과 파싱
        transcript_text = ""
        segments = []
        
        for result in response.results:
            alternative = result.alternatives[0]
            transcript_text += alternative.transcript + " "
            
            # 단어별 타임스탬프가 있으면 세그먼트 생성
            if alternative.words:
                segment_start = alternative.words[0].start_time.total_seconds() if alternative.words[0].start_time else 0.0
                segment_end = alternative.words[-1].end_time.total_seconds() if alternative.words[-1].end_time else 0.0
                segments.append({
                    "start": segment_start,
                    "end": segment_end,
                    "text": alternative.transcript,
                })
        
        transcript_text = transcript_text.strip()
        
        # 세그먼트가 없으면 전체 텍스트를 하나의 세그먼트로
        if not segments:
            segments = [{
                "start": 0.0,
                "end": 0.0,
                "text": transcript_text,
            }]
        
        print(f"✅ Google STT complete: {len(transcript_text)} characters, {len(segments)} segments")
        
        return {
            "text": transcript_text,
            "segments": segments,
        }
        
    except ImportError:
        error_msg = (
            "google-cloud-speech 패키지가 설치되지 않았습니다. "
            "다음 명령어로 설치하세요: pip install google-cloud-speech"
        )
        print(f"❌ {error_msg}")
        raise ImportError(error_msg)
    except Exception as e:
        import traceback
        print(f"❌ Error in _transcribe_with_google: {type(e).__name__}: {str(e)}")
        print(f"📋 Traceback:")
        print(traceback.format_exc())
        raise


def _transcribe_with_openai_api(file_path: Path, settings: AISettings) -> Dict[str, Any]:
    """
    OpenAI Whisper API를 사용하여 오디오/비디오 파일을 전사합니다.
    유료 API이지만 안정적이고 빠른 전사 서비스를 제공합니다.
    """
    try:
        client = _openai_client(settings)
        
        print(f"🎤 Using OpenAI Whisper API for: {file_path.name}")
        print(f"📦 File size: {file_path.stat().st_size / (1024 * 1024):.2f}MB")
        
        # 파일 열기
        with open(file_path, "rb") as audio_file:
            print("⏳ Transcribing with OpenAI Whisper API (this may take a while for large files)...")
            
            # OpenAI Whisper API 호출
            # response_format="verbose_json"을 사용하면 타임스탬프 정보도 포함됨
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko",  # 한국어 지정
                response_format="verbose_json",  # 타임스탬프 포함된 JSON 형식
            )
        
        # 결과 파싱
        # verbose_json 형식은 dict 또는 객체를 반환할 수 있음
        # OpenAI Python SDK는 보통 객체를 반환하지만, JSON 파싱 시 dict일 수도 있음
        if isinstance(transcript, dict):
            transcript_text = transcript.get("text", "")
            raw_segments = transcript.get("segments", [])
        else:
            # 객체인 경우 속성으로 접근
            transcript_text = getattr(transcript, "text", "") if hasattr(transcript, "text") else ""
            raw_segments = getattr(transcript, "segments", []) if hasattr(transcript, "segments") else []
        
        segments = []
        
        # segments 배열 처리
        if raw_segments:
            for seg in raw_segments:
                # dict 또는 객체 모두 처리
                if isinstance(seg, dict):
                    start = seg.get("start", 0.0)
                    end = seg.get("end", 0.0)
                    text = seg.get("text", "")
                else:
                    # 객체인 경우
                    start = getattr(seg, "start", 0.0) if hasattr(seg, "start") else 0.0
                    end = getattr(seg, "end", 0.0) if hasattr(seg, "end") else 0.0
                    text = getattr(seg, "text", "") if hasattr(seg, "text") else ""
                
                # 타입 변환 및 검증
                try:
                    start = float(start) if start is not None else 0.0
                    end = float(end) if end is not None else 0.0
                except (ValueError, TypeError):
                    start = 0.0
                    end = 0.0
                
                segments.append({
                    "start": start,
                    "end": end,
                    "text": str(text) if text else "",
                })
        
        # 세그먼트가 없으면 전체 텍스트를 하나의 세그먼트로
        if not segments:
            segments = [{
                "start": 0.0,
                "end": 0.0,
                "text": transcript_text if transcript_text else "",
            }]
        
        # 세그먼트 정보 정리 (사람이 읽기 쉬운 형식 포함)
        def format_time(seconds: float) -> str:
            """초를 분:초 형식으로 변환"""
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        
        formatted_segments = []
        for seg in segments:
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            formatted_segments.append({
                "start": start,
                "end": end,
                "start_formatted": format_time(start),  # 사람이 읽기 쉬운 형식 (예: "5:30")
                "end_formatted": format_time(end),      # 사람이 읽기 쉬운 형식 (예: "5:45")
                "text": seg.get("text", ""),
            })
        
        print(f"✅ OpenAI Whisper API transcription complete: {len(transcript_text)} characters, {len(formatted_segments)} segments")
        
        # fallback segment에도 형식 추가
        if not formatted_segments:
            formatted_segments = [{
                "start": 0.0,
                "end": 0.0,
                "start_formatted": "0:00",
                "end_formatted": "0:00",
                "text": transcript_text,
            }]
        
        return {
            "text": transcript_text,
            "segments": formatted_segments,
        }
    except ImportError:
        error_msg = (
            "openai 패키지가 설치되지 않았습니다. "
            "다음 명령어로 설치하세요: pip install openai"
        )
        print(f"❌ {error_msg}")
        raise ImportError(error_msg)
    except Exception as e:
        import traceback
        print(f"❌ Error in _transcribe_with_openai_api: {type(e).__name__}: {str(e)}")
        print(f"📋 Traceback:")
        print(traceback.format_exc())
        raise


def load_transcript_from_file(transcript_path: str) -> Optional[Dict[str, Any]]:
    """
    저장된 transcript JSON 파일을 로드합니다.
    
    Args:
        transcript_path: transcript JSON 파일 경로
        
    Returns:
        transcript 데이터 또는 None (파일이 없거나 오류 시)
    """
    try:
        path = Path(transcript_path)
        if not path.exists():
            return None
        
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 필수 필드 확인
        if "text" in data and data["text"]:
            print(f"✅ Loaded transcript from file: {transcript_path}")
            return {
                "text": data.get("text", ""),
                "segments": data.get("segments", []),
            }
        return None
    except Exception as e:
        print(f"⚠️ Failed to load transcript file {transcript_path}: {e}")
        return None


def transcribe_video(
    video_path: str, 
    settings: AISettings | None = None,
    transcript_path: Optional[str] = None,
    force_retranscribe: bool = False,
    instructor_id: Optional[str] = None,
    course_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribe a video/audio file using OpenAI Whisper.
    Automatically splits large files (>25MB) into chunks.
    
    만약 transcript_path가 제공되고 파일이 존재하면, STT를 건너뛰고 파일에서 로드합니다.

    Args:
        video_path: 비디오/오디오 파일 경로
        settings: AI 설정
        transcript_path: 저장된 transcript 파일 경로 (선택적)
        force_retranscribe: True면 파일이 있어도 강제로 재전사
        instructor_id: 강사 ID (대체 경로 찾기용, 선택적)
        course_id: 강의 ID (대체 경로 찾기용, 선택적)

    Returns:
        {
            "text": str,
            "segments": List[{"start": float, "end": float, "text": str}]
        }

    Fallback: if API key가 없거나 에러 시 placeholder를 반환해 파이프라인이 계속 진행되도록 함.
    """
    settings = settings or AISettings()
    path = Path(video_path)
    
    # 경로 정규화 및 확인
    if not path.is_absolute():
        # 상대 경로인 경우 절대 경로로 변환 시도
        path = path.resolve()
    
    print(f"📁 Checking file: {path}")
    print(f"📁 File exists: {path.exists()}")
    print(f"📁 Absolute path: {path.absolute()}")
    
    # 파일이 없으면 대체 경로 시도
    if not path.exists():
        if instructor_id and course_id:
            try:
                from core.config import AppSettings
                app_settings = AppSettings()
                potential_path = app_settings.uploads_dir / instructor_id / course_id / path.name
                if potential_path.exists():
                    path = potential_path.resolve()
                    print(f"📁 Found file at alternative path: {path}")
                else:
                    error_msg = f"Video not found: {video_path} (resolved: {path}, also tried: {potential_path})"
                    print(f"❌ {error_msg}")
                    raise FileNotFoundError(error_msg)
            except Exception as e:
                error_msg = f"Video not found: {video_path} (resolved: {path}), error checking alternative: {e}"
                print(f"❌ {error_msg}")
                raise FileNotFoundError(error_msg)
        else:
            error_msg = f"Video not found: {video_path} (resolved: {path})"
            print(f"❌ {error_msg}")
            raise FileNotFoundError(error_msg)

    # 저장된 transcript 파일이 있으면 먼저 확인
    if transcript_path and not force_retranscribe:
        loaded = load_transcript_from_file(transcript_path)
        if loaded:
            print(f"✅ Using existing transcript file (skipping STT): {transcript_path}")
            return loaded
        else:
            print(f"⚠️ Transcript file not found or invalid, proceeding with STT: {transcript_path}")

    try:
        # 오디오 파일이면 그대로 사용, 비디오 파일(MP4 등)만 MP3로 변환
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        
        file_ext = path.suffix.lower()
        audio_path = path
        
        # 오디오 파일이면 변환 없이 바로 사용
        if file_ext in audio_extensions:
            print(f"🎵 Audio file detected ({file_ext}), using directly (no conversion needed)")
        elif file_ext in video_extensions:
            print(f"🎬 Video file detected ({file_ext}), converting to MP3...")
            
            # ffmpeg 경로 확인
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                possible_paths = [
                    r"C:\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                ]
                for p in possible_paths:
                    if Path(p).exists():
                        ffmpeg_path = p
                        break
            
            if not ffmpeg_path:
                raise RuntimeError("ffmpeg not found. Please install ffmpeg to convert video files.")
            
            # 임시 MP3 파일 생성
            temp_dir = Path(tempfile.gettempdir())
            audio_path = temp_dir / f"{path.stem}_converted.mp3"
            
            print(f"🔄 Converting {path.name} to MP3...")
            from subprocess import run
            cmd = [
                ffmpeg_path,
                "-i", str(path),
                "-vn",  # 비디오 스트림 제거
                "-acodec", "libmp3lame",  # MP3 코덱
                "-ar", "16000",  # 샘플 레이트 16kHz (Whisper 권장)
                "-ac", "1",  # 모노
                "-b:a", "128k",  # 비트레이트
                "-y",  # 덮어쓰기
                str(audio_path)
            ]
            
            env = os.environ.copy()
            if ffmpeg_path:
                ffmpeg_dir = str(Path(ffmpeg_path).parent)
                env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
            
            try:
                run(cmd, check=True, capture_output=True, env=env)
                print(f"✅ Converted to MP3: {audio_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to convert video to MP3: {e}")
        elif file_ext not in audio_extensions:
            print(f"⚠️ Unknown file format ({file_ext}), attempting direct processing...")
        
        # OpenAI Whisper API 사용 (유료 API)
        print("✅ Using OpenAI Whisper API")
        
        # Check file size
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        print(f"📁 Audio file size: {file_size_mb:.2f}MB")
        
        # OpenAI Whisper API는 25MB 제한이 있으므로 큰 파일은 분할 필요
        if file_size_mb > 25:
            print(f"⚠️ File size ({file_size_mb:.2f}MB) exceeds 25MB limit. Splitting into chunks...")
            chunks = _split_audio_file(audio_path, max_size_mb=20.0)
            
            all_text = ""
            all_segments = []
            offset = 0.0  # 시간 오프셋
            
            def format_time(seconds: float) -> str:
                """초를 분:초 형식으로 변환"""
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}:{secs:02d}"
            
            for i, chunk_path in enumerate(chunks):
                print(f"📤 Transcribing chunk {i+1}/{len(chunks)}...")
                try:
                    chunk_result = _transcribe_with_openai_api(chunk_path, settings)
                    
                    # 세그먼트 시간 오프셋 적용
                    for seg in chunk_result.get("segments", []):
                        seg["start"] = float(seg.get("start", 0.0)) + offset
                        seg["end"] = float(seg.get("end", 0.0)) + offset
                        # 시간 포맷 재계산
                        seg["start_formatted"] = format_time(seg["start"])
                        seg["end_formatted"] = format_time(seg["end"])
                    
                    all_text += chunk_result.get("text", "") + " "
                    all_segments.extend(chunk_result.get("segments", []))
                    
                    # 다음 청크의 오프셋 계산 (마지막 세그먼트의 끝 시간)
                    if chunk_result.get("segments"):
                        offset = float(chunk_result["segments"][-1].get("end", 0.0))
                except Exception as e:
                    print(f"⚠️ Error transcribing chunk {i+1}: {e}")
                    import traceback
                    print(traceback.format_exc())
                    # 청크 실패해도 계속 진행
                    continue
                finally:
                    # 임시 청크 파일 삭제
                    try:
                        if chunk_path.exists():
                            chunk_path.unlink()
                    except Exception:
                        pass
            
            result = {
                "text": all_text.strip(),
                "segments": all_segments,
            }
        else:
            # 25MB 이하면 직접 전사
            print("🎤 Transcribing with OpenAI Whisper API...")
            result = _transcribe_with_openai_api(audio_path, settings)
        
        print(f"✅ STT success: transcribed text length: {len(result['text'])}")
        
        # 임시 변환 파일 삭제
        if file_ext in video_extensions and audio_path.exists() and audio_path != path:
            try:
                audio_path.unlink()
                print(f"🗑️ Cleaned up temporary MP3 file")
            except Exception:
                pass
        
        return result
        
    except ImportError as e:
        # openai 패키지가 없는 경우
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"❌ STT ERROR [{error_type}]: {error_msg}")
        print("💡 Please install openai: pip install openai")
        print("💡 Also make sure OPENAI_API_KEY is set in your environment")
        # 에러 발생 - 저장하지 않음
        raise
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"❌ STT ERROR [{error_type}]: {error_msg}")
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        
        print(f"⚠️ OpenAI Whisper API STT failed. Possible causes:")
        print(f"   - openai package not installed: pip install openai")
        print(f"   - OPENAI_API_KEY not set or invalid")
        print(f"   - File format not supported")
        print(f"   - File size exceeds 25MB (will be split automatically)")
        print(f"   - API rate limit or quota exceeded")
        
        # 에러 발생 - 저장하지 않음
        raise
