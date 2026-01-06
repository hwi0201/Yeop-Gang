"""
ChromaDB 데이터 확인 스크립트
특정 course_id의 저장된 문서를 확인

사용법:
  cd server
  python check_chromadb.py
"""
from ai.config import AISettings
from ai.services.vectorstore import get_chroma_client, get_collection

settings = AISettings()
client = get_chroma_client(settings)
collection = get_collection(client, settings)

# 모든 데이터 조회 (디버깅용)
all_data = collection.get()
print(f"총 문서 수: {len(all_data.get('ids', []))}")

# course_id별로 그룹화
course_docs = {}
for i, doc_id in enumerate(all_data.get('ids', [])):
    metadata = all_data.get('metadatas', [{}])[i] if all_data.get('metadatas') else {}
    course_id = metadata.get('course_id', 'unknown')
    if course_id not in course_docs:
        course_docs[course_id] = []
    
    doc_text = all_data.get('documents', [''])[i] if all_data.get('documents') else ''
    course_docs[course_id].append({
        'id': doc_id,
        'metadata': metadata,
        'text_preview': doc_text[:200] if doc_text else '',
    })

print("\n" + "="*70)
print("=== course_id별 문서 목록 ===")
print("="*70 + "\n")

for course_id, docs in sorted(course_docs.items()):
    print(f"📚 course_id: {course_id}")
    print(f"   문서 수: {len(docs)}")
    
    # 페르소나 문서 찾기
    persona_docs = [d for d in docs if d['metadata'].get('type') == 'persona']
    if persona_docs:
        print(f"\n   🎭 페르소나 문서 발견 ({len(persona_docs)}개):")
        for doc in persona_docs:
            # 전체 텍스트 가져오기
            doc_idx = all_data.get('ids', []).index(doc['id']) if doc['id'] in all_data.get('ids', []) else -1
            if doc_idx >= 0:
                full_text = all_data.get('documents', [''])[doc_idx] if all_data.get('documents') else doc['text_preview']
            else:
                full_text = doc['text_preview']
            
            print(f"       문서 ID: {doc['id']}")
            print(f"       페르소나 프롬프트:")
            # 너무 길면 일부만 표시
            if len(full_text) > 800:
                lines = full_text.split('\n')[:10]
                print(f"       {chr(10).join('       ' + line for line in lines)}")
                print(f"       ... (총 {len(full_text)}자, 일부만 표시)")
            else:
                for line in full_text.split('\n'):
                    print(f"       {line}")
            print()
    
    print()
    displayed = 0
    for idx, doc in enumerate(docs):
        if doc['metadata'].get('type') == 'persona':
            continue
        if displayed >= 3:  # 페르소나 제외하고 3개만 표시
            break
        print(f"   [{displayed+1}] 문서 ID: {doc['id']}")
        print(f"       텍스트 미리보기: {doc['text_preview']}...")
        print(f"       메타데이터: {doc['metadata']}")
        print()
        displayed += 1
    
    non_persona_count = len([d for d in docs if d['metadata'].get('type') != 'persona'])
    if non_persona_count > 3:
        print(f"   ... 외 {non_persona_count-3}개 더")
    
    print("-"*70)
    print()
