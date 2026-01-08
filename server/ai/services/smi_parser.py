"""
SMI (SAMI) 자막 파일 파싱
- SMI 파일을 읽어서 transcript JSON 형식으로 변환
- STT를 건너뛰고 자막 파일을 직접 사용
"""
import re
from pathlib import Path
from typing import Dict
import json


def parse_smi_file(smi_path: Path) -> Dict:
    """
    SMI 파일을 파싱하여 transcript JSON 형식으로 변환
    
    Args:
        smi_path: SMI 파일 경로
        
    Returns:
        {
            "text": "전체 텍스트",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "start_formatted": "0:00",
                    "end_formatted": "0:05",
                    "text": "자막 텍스트"
                },
                ...
            ]
        }
    """
    if not smi_path.exists():
        raise FileNotFoundError(f"SMI file not found: {smi_path}")
    
    # SMI 파일 읽기 (여러 인코딩 시도)
    encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16']
    content = None
    
    for encoding in encodings:
        try:
            with open(smi_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✅ SMI file read with encoding: {encoding}")
            break
        except (UnicodeDecodeError, Exception):
            continue
    
    if content is None:
        raise ValueError(f"Failed to read SMI file with any encoding: {smi_path}")
    
    # SYNC 태그 파싱
    # <SYNC Start=1000><P Class=KRCC>자막 텍스트</P>
    sync_pattern = re.compile(
        r'<SYNC\s+Start=(\d+)>\s*<P[^>]*>(.*?)</P>',
        re.IGNORECASE | re.DOTALL
    )
    
    matches = sync_pattern.findall(content)
    
    if not matches:
        # 대체 패턴 시도 (닫는 태그가 없는 경우)
        sync_pattern = re.compile(
            r'<SYNC\s+Start=(\d+)>\s*<P[^>]*>(.*?)(?=<SYNC|$)',
            re.IGNORECASE | re.DOTALL
        )
        matches = sync_pattern.findall(content)
    
    if not matches:
        raise ValueError(f"No SYNC tags found in SMI file: {smi_path}")
    
    print(f"📝 Found {len(matches)} SYNC tags in SMI file")
    
    segments = []
    full_text_parts = []
    
    for i, (start_ms, text) in enumerate(matches):
        # 시작 시간 (밀리초 → 초)
        start_time = int(start_ms) / 1000.0
        
        # 종료 시간 (다음 자막의 시작 시간, 마지막이면 +5초)
        if i + 1 < len(matches):
            end_time = int(matches[i + 1][0]) / 1000.0
        else:
            end_time = start_time + 5.0
        
        # HTML 태그 제거 및 텍스트 정리
        clean_text = _clean_smi_text(text)
        
        if not clean_text or clean_text.strip() in ['&nbsp;', '']:
            continue
        
        # 시간 포맷팅
        start_minutes = int(start_time // 60)
        start_seconds = int(start_time % 60)
        end_minutes = int(end_time // 60)
        end_seconds = int(end_time % 60)
        
        segment = {
            "start": start_time,
            "end": end_time,
            "start_formatted": f"{start_minutes}:{start_seconds:02d}",
            "end_formatted": f"{end_minutes}:{end_seconds:02d}",
            "text": clean_text,
        }
        
        segments.append(segment)
        full_text_parts.append(clean_text)
    
    # 전체 텍스트
    full_text = " ".join(full_text_parts)
    
    print(f"✅ SMI parsed: {len(segments)} segments, {len(full_text)} chars")
    
    result = {
        "text": full_text,
        "segments": segments,
    }
    
    return result


def _clean_smi_text(text: str) -> str:
    """
    SMI 텍스트에서 HTML 태그 제거 및 정리
    """
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML 엔티티 변환
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # 여러 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def save_transcript_json(transcript_data: Dict, output_path: Path) -> None:
    """
    Transcript 데이터를 JSON 파일로 저장
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Transcript JSON saved: {output_path}")
