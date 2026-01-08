"""
백엔드 A: 자동화 파이프라인 오케스트레이션
- STT → PDF 처리 → 페르소나 추출 → RAG 인제스트
- 순수 AI 처리 로직만 담당 (DB 작업 제외)
"""
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from ai.config import AISettings
from ai.pipelines.rag import RAGPipeline
from ai.services.stt import transcribe_video


def process_course_assets(
    *,
    course_id: str,
    instructor_id: str,
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
    smi_path: Optional[Path] = None,
    update_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    백엔드 A: 자동화 파이프라인 오케스트레이션
    
    Background pipeline: STT → PDF 처리 → 페르소나 추출 → RAG 인제스트
    
    이 함수는 순수 AI 처리 로직만 담당합니다.
    DB 작업(Course, Video 모델 생성 등)은 백엔드 B의 책임입니다.
    
    Args:
        course_id: 강의 ID
        instructor_id: 강사 ID
        video_path: 비디오/오디오 파일 경로 (선택적)
        audio_path: 오디오 파일 경로 (선택적)
        pdf_path: PDF 파일 경로 (선택적)
        smi_path: SMI 자막 파일 경로 (선택적, 제공 시 STT를 건너뜀)
        update_progress: 진행률 업데이트 콜백 함수 (progress: int, message: str) -> None
    
    Returns:
        {
            "status": "completed" | "error",
            "ingested_count": int,
            "error": str (optional)
        }
    """
    settings = AISettings()
    pipeline = RAGPipeline(settings)
    
    try:
        texts: List[str] = []
        ingested_count = 0

        # 1. Transcript 생성 (SMI 우선, 없으면 STT)
        # SMI가 있으면 STT를 건너뛰고 자막을 transcript로 사용
        transcript_text = ""
        segments: List[Dict[str, Any]] = []
        transcript_path = None

        # SMI 경로 정규화/대체 경로 탐색
        if smi_path:
            if not isinstance(smi_path, Path):
                smi_path = Path(smi_path)
            if not smi_path.is_absolute():
                smi_path = smi_path.resolve()
            print(f"[{course_id}] 📁 SMI path: {smi_path}")
            print(f"[{course_id}] 📁 SMI exists: {smi_path.exists()}")

            if not smi_path.exists():
                try:
                    from core.config import AppSettings
                    app_settings = AppSettings()
                    potential_path = app_settings.uploads_dir / instructor_id / course_id / smi_path.name
                    if potential_path.exists():
                        smi_path = potential_path.resolve()
                        print(f"[{course_id}] 📁 Found SMI at alternative path: {smi_path}")
                    else:
                        raise FileNotFoundError(f"SMI file not found: {smi_path} (also tried: {potential_path})")
                except Exception as e:
                    print(f"[{course_id}] ❌ Error finding SMI file: {e}")
                    raise

        # STT용 media_path 정규화 (SMI가 없을 때만 사용)
        media_path = audio_path or video_path
        
        # 경로를 절대 경로로 변환
        if media_path:
            if not isinstance(media_path, Path):
                media_path = Path(media_path)
            if not media_path.is_absolute():
                media_path = media_path.resolve()
            print(f"[{course_id}] 📁 Media path: {media_path}")
            print(f"[{course_id}] 📁 Media exists: {media_path.exists()}")
            
            # 파일이 없으면 대체 경로 시도
            if not media_path.exists():
                try:
                    from core.config import AppSettings
                    app_settings = AppSettings()
                    potential_path = app_settings.uploads_dir / instructor_id / course_id / media_path.name
                    if potential_path.exists():
                        media_path = potential_path.resolve()
                        print(f"[{course_id}] 📁 Found media at alternative path: {media_path}")
                    else:
                        print(f"[{course_id}] ❌ Media file not found: {media_path} (also tried: {potential_path})")
                        raise FileNotFoundError(f"Media file not found: {media_path}")
                except Exception as e:
                    print(f"[{course_id}] ❌ Error finding media file: {e}")
                    raise
        
        # SMI가 있으면 여기서 transcript 생성/저장
        if smi_path and smi_path.exists():
            try:
                from ai.services.smi_parser import parse_smi_file
                import json
                from core.config import AppSettings

                if update_progress:
                    update_progress(15, "SMI 자막 파일 파싱 중...")
                print(f"[{course_id}] 📝 SMI 자막 기반 transcript 생성 시작: {smi_path.name}")
                transcript_result = parse_smi_file(smi_path)
                transcript_text = transcript_result.get("text", "") or ""
                segments = transcript_result.get("segments", []) or []
                print(f"[{course_id}] ✅ SMI parsed - text length: {len(transcript_text)}, segments: {len(segments)}")
                
                if update_progress:
                    update_progress(30, "SMI 자막 파싱 완료, 세그먼트 임베딩 준비 중...")

                if not transcript_text.strip():
                    raise ValueError(f"[{course_id}] ❌ SMI 파싱 결과 텍스트가 비어있습니다.")

                app_settings = AppSettings()
                course_dir = app_settings.uploads_dir / instructor_id / course_id
                course_dir.mkdir(parents=True, exist_ok=True)

                transcript_filename = f"transcript_{smi_path.stem}.json"
                transcript_file_path = course_dir / transcript_filename

                transcript_data = {
                    "text": transcript_text,
                    "segments": segments,
                    "source_file": smi_path.name,
                    "course_id": course_id,
                    "instructor_id": instructor_id,
                }

                with transcript_file_path.open("w", encoding="utf-8") as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)

                if transcript_file_path.exists():
                    transcript_path = str(transcript_file_path)
                    print(f"[{course_id}] ✅ SMI transcript JSON saved: {transcript_path}")

                # persona 샘플 + 세그먼트 인제스트
                texts.append(transcript_text)
                print(f"[{course_id}] 📝 {len(segments)}개 자막 세그먼트 인제스트 시작...")
                total_segments = len(segments)
                for idx, seg in enumerate(segments):
                    seg_text = seg.get("text", "")
                    if not seg_text:
                        continue
                    seg_meta = {
                        "course_id": course_id,
                        "instructor_id": instructor_id,
                        "source": smi_path.name,
                        "start_time": seg.get("start"),
                        "end_time": seg.get("end"),
                        "segment_index": idx,
                        "start_formatted": seg.get("start_formatted"),
                        "end_formatted": seg.get("end_formatted"),
                        "type": "subtitle_segment",
                    }
                    result = pipeline.ingest_texts(
                        [seg_text],
                        course_id=course_id,
                        metadata=seg_meta,
                    )
                    ingested_count += result.get("ingested", 0)
                    
                    # 진행률 업데이트 (30% ~ 60%)
                    if update_progress and total_segments > 0:
                        embedding_progress = 30 + int((idx + 1) / total_segments * 30)
                        update_progress(embedding_progress, f"세그먼트 임베딩 중... ({idx + 1}/{total_segments})")
                print(f"[{course_id}] ✅ 자막 세그먼트 인제스트 완료")
                if update_progress:
                    update_progress(60, "세그먼트 임베딩 완료")
                    
            except Exception as e:
                error_msg = f"[{course_id}] ❌ SMI 처리 오류 ({smi_path.name if smi_path else 'unknown'}): {str(e)}"
                print(error_msg)
                # 오류가 발생해도 계속 진행
        # SMI가 없으면 기존 STT 처리
        elif media_path and media_path.exists():
            try:
                if update_progress:
                    update_progress(15, "파일 준비 중...")
                print(f"[{course_id}] 🎤 STT 처리 시작: {media_path.name}")

                # 첫 업로드이므로 무조건 STT 실행
                if update_progress:
                    update_progress(20, "음성 인식(STT) 시작...")
                print(f"[{course_id}] 🔄 Running STT (force_retranscribe=True)...")
                transcript_result = transcribe_video(
                    str(media_path),
                    settings=settings,
                    instructor_id=instructor_id,
                    course_id=course_id,
                    transcript_path=None,  # 기존 파일 무시
                    force_retranscribe=True  # 강제로 STT 실행
                )
                transcript_text = transcript_result.get("text", "")
                segments = transcript_result.get("segments", [])
                
                if update_progress:
                    update_progress(40, "음성 인식(STT) 완료, 세그먼트 임베딩 준비 중...")

                print(f"[{course_id}] 📝 STT result - text length: {len(transcript_text)}, segments: {len(segments)}")

                # STT placeholder 체크
                if "placeholder" in transcript_text.lower():
                    error_msg = f"[{course_id}] ❌ STT가 placeholder를 반환했습니다. 실제 전사가 실패했습니다."
                    print(error_msg)
                    raise ValueError(error_msg)

                if not transcript_text or not transcript_text.strip():
                    error_msg = f"[{course_id}] ❌ STT 결과가 비어있습니다."
                    print(error_msg)
                    raise ValueError(error_msg)

                print(f"[{course_id}] ✅ STT 성공! 전사된 텍스트 길이: {len(transcript_text)} 문자")

                # STT 결과를 파일로 저장
                if transcript_text:
                    try:
                        from core.config import AppSettings
                        import json

                        app_settings = AppSettings()
                        course_dir = app_settings.uploads_dir / instructor_id / course_id
                        course_dir.mkdir(parents=True, exist_ok=True)

                        # transcript 파일명: transcript_{원본파일명}.json
                        transcript_filename = f"transcript_{media_path.stem}.json"
                        transcript_file_path = course_dir / transcript_filename

                        # JSON 형식으로 저장 (전체 텍스트 + 세그먼트 정보)
                        transcript_data = {
                            "text": transcript_text,
                            "segments": segments,
                            "source_file": media_path.name,
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                        }

                        print(f"[{course_id}] Attempting to save transcript to: {transcript_file_path}")
                        print(f"[{course_id}] Transcript text length: {len(transcript_text)}")

                        with transcript_file_path.open("w", encoding="utf-8") as f:
                            json.dump(transcript_data, f, ensure_ascii=False, indent=2)

                        # 파일이 실제로 저장되었는지 확인
                        if transcript_file_path.exists():
                            file_size = transcript_file_path.stat().st_size
                            transcript_path = str(transcript_file_path)
                            print(f"[{course_id}] ✅ STT transcript JSON saved successfully: {transcript_path} (size: {file_size} bytes)")
                        else:
                            print(f"[{course_id}] ❌ Transcript file was not created: {transcript_file_path}")
                    except Exception as e:
                        import traceback
                        print(f"[{course_id}] ❌ Failed to save transcript file: {e}")
                        print(f"[{course_id}] Error details: {traceback.format_exc()}")
                        # 파일 저장 실패해도 계속 진행

                if transcript_text:
                    # 병합 텍스트 전체를 persona 생성용 샘플에 추가
                    texts.append(transcript_text)

                    # 세그먼트별 메타데이터 포함하여 RAG 인제스트
                    print(f"[{course_id}] 📝 {len(segments)}개 세그먼트 인제스트 시작...")
                    total_segments = len(segments)
                    for idx, seg in enumerate(segments):
                        seg_text = seg.get("text", "")
                        if not seg_text:
                            continue

                        seg_meta = {
                            "course_id": course_id,
                            "instructor_id": instructor_id,
                            "source": media_path.name,
                            "start_time": seg.get("start"),
                            "end_time": seg.get("end"),
                            "segment_index": idx,
                            "type": "video_segment" if video_path else "audio_segment",
                        }

                        result = pipeline.ingest_texts(
                            [seg_text],
                            course_id=course_id,
                            metadata=seg_meta,
                        )
                        ingested_count += result.get("ingested", 0)
                        
                        # 진행률 업데이트 (40% ~ 70%)
                        if update_progress and total_segments > 0:
                            embedding_progress = 40 + int((idx + 1) / total_segments * 30)
                            update_progress(embedding_progress, f"세그먼트 임베딩 중... ({idx + 1}/{total_segments})")

                    print(f"[{course_id}] ✅ 세그먼트 인제스트 완료")
                    if update_progress:
                        update_progress(70, "세그먼트 임베딩 완료")
                else:
                    print(f"[{course_id}] ⚠️ STT 결과 텍스트가 비어있습니다: {media_path.name}")

            except Exception as e:
                error_msg = f"[{course_id}] ❌ STT 처리 오류 ({media_path.name}): {str(e)}"
                print(error_msg)
                # 오류가 발생해도 계속 진행
        
        # 2. PDF 멀티모달 처리 (텍스트 + 이미지 설명)
        if pdf_path and pdf_path.exists():
            try:
                if update_progress:
                    update_progress(70, "PDF 처리 시작...")
                print(f"[{course_id}] 📄 PDF 멀티모달 처리 시작: {pdf_path.name}")
                # PDF 처리 모듈이 있으면 사용, 없으면 스킵
                try:
                    from ai.services.pdf import extract_pdf_content
                    pdf_result = extract_pdf_content(str(pdf_path), settings=settings, extract_images=True)
                    pdf_texts = pdf_result.get("texts", [])
                    pdf_metadata_list = pdf_result.get("metadata", [])
                    
                    if pdf_texts:
                        # PDF 텍스트를 persona 생성용 샘플에 추가
                        texts.extend(pdf_texts)
                        
                        # 페이지별로 개별 RAG 인제스트 (페이지 번호 등 메타데이터 포함)
                        print(f"[{course_id}] 🖼️ PDF {len(pdf_texts)}개 페이지 인제스트 시작...")
                        total_pages = len(pdf_texts)
                        for page_idx, (pdf_text, pdf_meta) in enumerate(zip(pdf_texts, pdf_metadata_list)):
                            page_meta = {
                                "course_id": course_id,
                                "instructor_id": instructor_id,
                                "source": pdf_path.name,
                                "page_number": pdf_meta.get("page_number"),
                                "type": "pdf_page",
                            }
                            
                            result = pipeline.ingest_texts(
                                [pdf_text],
                                course_id=course_id,
                                metadata=page_meta,
                            )
                            ingested_count += result.get("ingested", 0)
                            
                            # 진행률 업데이트 (70% ~ 75%)
                            if update_progress and total_pages > 0:
                                pdf_progress = 70 + int((page_idx + 1) / total_pages * 5)
                                update_progress(pdf_progress, f"PDF 페이지 처리 중... ({page_idx + 1}/{total_pages})")
                        
                        print(f"[{course_id}] ✅ PDF 페이지 인제스트 완료")
                    else:
                        print(f"[{course_id}] ⚠️ PDF에서 텍스트를 추출하지 못했습니다: {pdf_path.name}")
                except ImportError:
                    print(f"[{course_id}] ⚠️ PDF 처리 모듈이 없습니다. PDF 처리를 건너뜁니다.")
                    # PDF 처리 모듈이 없어도 계속 진행
                        
            except Exception as e:
                error_msg = f"[{course_id}] ❌ PDF 처리 오류 ({pdf_path.name}): {str(e)}"
                print(error_msg)
                # 오류가 발생해도 계속 진행
        
        # 3. 페르소나 추출 및 RAG 인제스트
        if texts:
            if update_progress:
                update_progress(75, "페르소나 추출 중...")
            print(f"[{course_id}] 🧑‍🏫 페르소나 추출 시작...")
            # 동적 페르소나 프롬프트 생성
            try:
                persona_prompt = pipeline.generate_persona_prompt(
                    course_id=course_id, sample_texts=texts
                )
                
                if update_progress:
                    update_progress(85, "페르소나 저장 중...")
                # 페르소나 프롬프트를 벡터 DB에 저장
                result = pipeline.ingest_texts(
                    [persona_prompt],
                    course_id=course_id,
                    metadata={
                        "course_id": course_id,
                        "instructor_id": instructor_id,
                        "type": "persona",
                    },
                )
                ingested_count += result.get("ingested", 0)
                print(f"[{course_id}] ✅ 페르소나 추출 및 저장 완료")
                if update_progress:
                    update_progress(95, "최종 처리 중...")
                
            except Exception as e:
                error_msg = f"[{course_id}] ❌ 페르소나 추출 오류: {str(e)}"
                print(error_msg)
                # 페르소나 추출 실패해도 계속 진행
        else:
            print(f"[{course_id}] ⚠️ 처리할 텍스트가 없습니다.")
        
        return {
            "status": "completed",
            "ingested_count": ingested_count,
            "transcript_path": transcript_path,  # STT 결과 파일 경로 (있는 경우)
        }
        
    except Exception as e:
        error_msg = f"[{course_id}] ❌ 파이프라인 오케스트레이션 오류: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "ingested_count": ingested_count if 'ingested_count' in locals() else 0,
            "error": error_msg,
        }
