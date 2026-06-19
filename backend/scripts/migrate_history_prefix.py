"""
ChromaDB history_db_ 문서에 [사료명] prefix 추가 마이그레이션

사용법 (백엔드 컨테이너 내부에서 실행):
    docker exec -it history_backend python /app/scripts/migrate_history_prefix.py

또는 호스트에서 CHROMA_HOST 환경변수로 ChromaDB 주소 오버라이드:
    CHROMA_HOST=localhost CHROMA_PORT=8001 python scripts/migrate_history_prefix.py
"""

import os
import sys
import re

# 컨테이너 안에서 실행할 경우 /app이 패키지 루트
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_HOST = os.environ.get("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
EMBED_MODEL  = os.environ.get("EMBED_MODEL", "paraphrase-multilingual-mpnet-base-v2")
BATCH_SIZE   = 200


def main():
    print(f"ChromaDB 연결: {CHROMA_HOST}:{CHROMA_PORT}")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    col    = client.get_or_create_collection(
        name="korean_history",
        metadata={"hnsw:space": "cosine"},
    )
    total = col.count()
    print(f"전체 문서 수: {total}")

    print(f"임베딩 모델 로드: {EMBED_MODEL}")
    embedder = SentenceTransformer(EMBED_MODEL)

    # 1. 전체 ID 수집
    all_ids: list[str] = col.get(include=[])["ids"]
    target_ids = [i for i in all_ids if i.startswith("history_db_")]
    print(f"history_db_ 대상 문서: {len(target_ids)}건")

    updated = 0
    skipped = 0

    # 2. 배치 처리
    for start in range(0, len(target_ids), BATCH_SIZE):
        batch_ids = target_ids[start : start + BATCH_SIZE]
        result    = col.get(ids=batch_ids, include=["documents", "metadatas"])

        new_ids, new_docs, new_embeddings, new_metas = [], [], [], []

        for doc_id, text, meta in zip(
            result["ids"], result["documents"], result["metadatas"]
        ):
            source = meta.get("source", "")

            # 이미 prefix 붙어있으면 건너뜀
            expected_prefix = f"[{source}]"
            if text.startswith(expected_prefix):
                skipped += 1
                continue

            # 기존 text가 다른 [xxx] 로 시작하는지 확인 (이중 방지)
            if re.match(r"^\[.+?\] ", text):
                skipped += 1
                continue

            new_text = f"{expected_prefix} {text}"

            embed_text = f"{source}: {new_text}" if source else new_text
            new_ids.append(doc_id)
            new_docs.append(new_text)
            new_embeddings.append(embedder.encode(embed_text, normalize_embeddings=True).tolist())
            new_metas.append(meta)

        if new_ids:
            col.upsert(
                ids=new_ids,
                embeddings=new_embeddings,
                documents=new_docs,
                metadatas=new_metas,
            )
            updated += len(new_ids)

        done = min(start + BATCH_SIZE, len(target_ids))
        print(f"  진행: {done}/{len(target_ids)} (갱신 {updated}, 스킵 {skipped})")

    print(f"\n완료 — 갱신: {updated}건, 스킵(이미 prefix 있음): {skipped}건")


if __name__ == "__main__":
    main()
