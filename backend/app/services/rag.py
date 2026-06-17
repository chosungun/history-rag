import anthropic
from app.core.chroma import get_collection, embed
from app.core.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """당신은 일제강점기(1910~1945) 한국 근현대사 전문 고증 AI입니다.
역사 소설 작가의 고증 질문에 답변합니다.

규칙:
1. 반드시 제공된 사료(context)에 근거하여 답변하세요.
2. 사료에 없는 내용은 "사료에서 확인되지 않습니다"라고 명시하세요.
3. 연도, 인물, 장소는 최대한 구체적으로 답변하세요.
4. 소설 집필에 활용할 수 있도록 생생한 묘사 힌트도 함께 제공하세요.
5. 출처(사료명)를 항상 명시하세요."""


async def rag_search(query: str, top_k: int = 5) -> dict:
    """벡터 검색 + Claude RAG 답변"""
    collection = get_collection()

    # 1. 벡터 검색
    query_embedding = embed([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return {
            "answer": "관련 사료를 찾지 못했습니다. 데이터 수집(ingest)을 먼저 실행해주세요.",
            "sources": [],
            "photos": []
        }

    # 2. 컨텍스트 구성
    context_parts = []
    sources = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        source_name = meta.get("source", "출처미상")
        year = meta.get("year", "")
        context_parts.append(f"[사료 {i+1}] ({source_name}, {year})\n{doc}")
        sources.append({
            "title": source_name,
            "year": year,
            "excerpt": doc[:150] + "..." if len(doc) > 150 else doc,
            "relevance": round(1 - dist, 3),
            "url": meta.get("url", ""),
            "image_url": meta.get("image_url", ""),
        })

    context = "\n\n".join(context_parts)

    # 3. Claude 답변 생성
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"다음 사료들을 참고하여 질문에 답변해주세요.\n\n=== 사료 ===\n{context}\n\n=== 질문 ===\n{query}"
            }
        ]
    )

    return {
        "answer": message.content[0].text,
        "sources": sources,
        "query": query
    }


async def ingest_documents(documents: list[dict]) -> int:
    """문서를 ChromaDB에 임베딩하여 저장
    documents: [{"id": str, "text": str, "source": str, "year": str, "url": str, "image_url": str}]
    """
    collection = get_collection()

    texts = [d["text"] for d in documents]
    embeddings = embed(texts)

    collection.upsert(
        ids=[d["id"] for d in documents],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{
            "source": d.get("source", ""),
            "year": d.get("year", ""),
            "url": d.get("url", ""),
            "image_url": d.get("image_url", ""),
            "category": d.get("category", ""),
        } for d in documents]
    )
    return len(documents)
