"""
STT 처리 상태 확인 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server"))

from sqlmodel import Session, select
from core.db import engine
from core.models import Course, Video, CourseStatus
from ai.config import AISettings
from ai.services.vectorstore import get_chroma_client, get_collection

def check_course_status(course_id: str = None):
    """강의 처리 상태 확인"""
    print("=" * 60)
    print("STT 처리 상태 확인")
    print("=" * 60)
    
    with Session(engine) as session:
        if course_id:
            # 특정 강의 확인
            course = session.get(Course, course_id)
            if not course:
                print(f"\n❌ 강의 '{course_id}'를 찾을 수 없습니다.")
                return
            
            print(f"\n📚 강의: {course.id}")
            print(f"   강사: {course.instructor_id}")
            print(f"   상태: {course.status}")
            print(f"   생성일: {course.created_at}")
            print(f"   수정일: {course.updated_at}")
            
            # Video 레코드 확인
            videos = session.exec(
                select(Video).where(Video.course_id == course_id)
            ).all()
            
            print(f"\n📹 비디오 파일: {len(videos)}개")
            for vid in videos:
                print(f"   - {vid.filename}")
                print(f"     저장 경로: {vid.storage_path}")
                print(f"     생성일: {vid.created_at}")
            
            # 벡터 DB 확인 (선택적)
            try:
                settings = AISettings()
                client = get_chroma_client(settings)
                collection = get_collection(client, settings)
                
                # course_id로 필터링하여 문서 수 확인
                results = collection.get(
                    where={"course_id": course_id},
                    limit=1
                )
                doc_count = len(results.get("ids", [])) if results.get("ids") else 0
                print(f"\n🔍 벡터 DB 문서 수: {doc_count}개")
                
                if doc_count > 0:
                    print("   ✅ STT 처리가 완료되어 벡터 DB에 저장되었습니다!")
                else:
                    print("   ⚠️  벡터 DB에 문서가 없습니다. STT 처리가 완료되지 않았을 수 있습니다.")
            except Exception as e:
                print(f"\n⚠️  벡터 DB 확인 중 오류 (무시 가능): {type(e).__name__}")
                if course.status == CourseStatus.completed:
                    print("   ✅ 강의 상태가 'completed'이므로 STT 처리가 완료된 것으로 보입니다.")
            
        else:
            # 모든 강의 확인
            courses = session.exec(select(Course)).all()
            print(f"\n📚 전체 강의 수: {len(courses)}개\n")
            
            for course in courses:
                status_icon = "✅" if course.status == CourseStatus.completed else "⏳" if course.status == CourseStatus.processing else "❌"
                print(f"{status_icon} {course.id} (상태: {course.status.value}, 강사: {course.instructor_id})")
            
            if courses:
                print(f"\n💡 특정 강의를 확인하려면: python check_stt_status.py <course_id>")

if __name__ == "__main__":
    course_id = sys.argv[1] if len(sys.argv) > 1 else None
    check_course_status(course_id)

