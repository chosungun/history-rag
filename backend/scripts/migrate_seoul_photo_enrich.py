"""
ChromaDB에 저장된 서울역사아카이브 사진(seoul_archive_*) 텍스트를
Claude Haiku로 검색 키워드 보강 후 re-upsert

사용법 (백엔드 컨테이너 내부):
    docker exec -it history_backend python /app/scripts/migrate_seoul_photo_enrich.py

환경변수:
    CHROMA_HOST      (기본: chromadb)
    CHROMA_PORT      (기본: 8000)
    ANTHROPIC_API_KEY
    EMBED_MODEL      (기본: paraphrase-multilingual-mpnet-base-v2)
    MAX_CONCURRENT   Claude 동시 호출 수 (기본: 5)
    BATCH_SIZE       upsert 배치 크기 (기본: 50)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chromadb
from anthropic import AsyncAnthropic
from sentence_transformers import SentenceTransformer

CHROMA_HOST    = os.environ.get("CHROMA_HOST", "chromadb")
CHROMA_PORT    = int(os.environ.get("CHROMA_PORT", "8000"))
API_KEY        = os.environ.get("ANTHROPIC_API_KEY", "")
EMBED_MODEL    = os.environ.get("EMBED_MODEL", "paraphrase-multilingual-mpnet-base-v2")
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "5"))
BATCH_SIZE     = int(os.environ.get("BATCH_SIZE", "50"))


async def _enrich(client: AsyncAnthropic, text: str, sem: asyncio.Semaphore) -> str:
    """기존 text를 Claude Haiku로 검색 키워드로 보강. 실패 시 원본 반환."""
    async with sem:
        try:
            resp = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=100,
                messages=[{"role": "user", "content": (
                    "서울역사아카이브 사진 설명을 보고 검색 키워드를 보강해줘. "
                    "건물명·장소·연도·건축양식·용도·시대 맥락을 쉼표로 나열. "
                    "60단어 이내, 한국어만, 키워드만 출력.\n\n" + text
                )}],
            )
            enriched = resp.content[0].text.strip()
            # 원본 첫 토큰(명칭)은 유지
            orig_title = text.split("|")[0].strip() if "|" in text else text.split(",")[0].strip()
            return f"{orig_title}, {enriched}" if orig_title and orig_title not in enriched else enriched
        except Exception as e:
            print(f"  보강 실패: {e}")
            return text


async def main():
    if not API_KEY:
        print("ANTHROPIC_API_KEY 환경변수가 필요합니다.")
        sys.exit(1)

    print(f"ChromaDB 연결: {CHROMA_HOST}:{CHROMA_PORT}")
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    col = chroma.get_or_create_collection(
        "korean_history", metadata={"hnsw:space": "cosine"}
    )
    print(f"전체 문서 수: {col.count()}")

    print(f"임베딩 모델 로드: {EMBED_MODEL}")
    embedder = SentenceTransformer(EMBED_MODEL)

    client = AsyncAnthropic(api_key=API_KEY)
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    # 대상 ID 수집
    all_ids: list[str] = col.get(include=[])["ids"]
    target_ids = [i for i in all_ids if i.startswith("seoul_archive_")]
    print(f"서울아카이브 대상: {len(target_ids)}건  (배치={BATCH_SIZE}, 동시={MAX_CONCURRENT})")

    if not target_ids:
        print("대상 문서 없음 — 종료")
        return

    updated = 0

    for start in range(0, len(target_ids), BATCH_SIZE):
        batch_ids = target_ids[start : start + BATCH_SIZE]
        result = col.get(ids=batch_ids, include=["documents", "metadatas"])

        # Claude 병렬 보강
        tasks = [_enrich(client, doc, sem) for doc in result["documents"]]
        enriched_texts: list[str] = await asyncio.gather(*tasks)

        # re-embed + upsert
        new_ids, new_docs, new_embs, new_metas = [], [], [], []
        for doc_id, enriched, meta in zip(result["ids"], enriched_texts, result["metadatas"]):
            source = meta.get("source", "")
            embed_text = f"{source}: {enriched}" if source else enriched
            new_ids.append(doc_id)
            new_docs.append(enriched)
            new_embs.append(
                embedder.encode(embed_text, normalize_embeddings=True).tolist()
            )
            new_metas.append(meta)

        col.upsert(
            ids=new_ids,
            embeddings=new_embs,
            documents=new_docs,
            metadatas=new_metas,
        )
        updated += len(new_ids)

        done = min(start + BATCH_SIZE, len(target_ids))
        print(f"  {done}/{len(target_ids)} 완료 (누계 {updated}건 갱신)")

    print(f"\n완료 — {updated}건 텍스트 보강됨")


if __name__ == "__main__":
    asyncio.run(main())
