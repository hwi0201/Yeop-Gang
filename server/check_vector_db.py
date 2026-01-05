"""벡터 DB 확인 스크립트"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server"))

from ai.config import AISettings
from ai.services.vectorstore import get_chroma_client, get_collection

def check_vector_db(course_id: str = "0"):
    settings = AISettings()
    client = get_chroma_client(settings)
    collection = get_collection(client, settings)
    
    print(f"벡터 DB 확인 (course_id: {course_id})")
    print("=" * 60)
    
    try:
        # course_id로 필터링하여 모든 문서 가져오기
        results = collection.get(
            where={"course_id": course_id},
            limit=100
        )
        
        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        
        print(f"\n문서 수: {len(ids)}개")
        
        if len(ids) == 0:
            print("\n❌ 벡터 DB에 문서가 없습니다!")
            print("STT 처리가 완료되지 않았거나 데이터 저장에 문제가 있을 수 있습니다.")
        else:
            print("\n✅ 벡터 DB에 문서가 저장되어 있습니다.")
            print(f"\n처음 5개 문서 미리보기:")
            for i in range(min(5, len(documents))):
                doc = documents[i]
                meta = metadatas[i] if i < len(metadatas) else {}
                print(f"\n[{i+1}] {meta.get('source', 'unknown')}")
                print(f"    타입: {meta.get('type', 'text')}")
                print(f"    텍스트: {doc[:100]}...")
        
        # 페르소나 프롬프트 확인
        persona_results = collection.get(
            where={"course_id": course_id, "type": "persona"},
            limit=1
        )
        persona_ids = persona_results.get("ids", [])
        if persona_ids:
            print("\n✅ 페르소나 프롬프트가 저장되어 있습니다.")
        else:
            print("\n⚠️  페르소나 프롬프트가 없습니다.")
            
    except Exception as e:
        print(f"\n❌ 오류: {e}")

if __name__ == "__main__":
    course_id = sys.argv[1] if len(sys.argv) > 1 else "0"
    check_vector_db(course_id)

