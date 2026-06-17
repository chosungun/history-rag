import anthropic
from app.core.chroma import get_collection, embed
from app.core.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """당신은 일제강점기(1910~1945) 한국 역사 소설 집필을 돕는 고증 전문가입니다.

답변 원칙:
1. 제공된 사료에 근거하여 답변하되, 사료가 부족하면 역사적으로 알려진 사실 기반으로 보완 (※ 일반 역사 지식 기반 표시)
2. 소설에 쓸 수 있는 감각적 묘사를 풍부하게 포함 — 시각·청각·후각·질감·계절감 등
3. 연도·장소·인물·건물·물건을 최대한 구체적으로 서술
4. 답변은 간결하되 생생하게 — 불필요한 반복 없이
5. 대화 맥락을 유지하며 이전 질문과 연결하여 답변
6. 사료 출처는 답변 마지막에 ▶ 출처: 형태로 간략 명시"""


async def rag_chat(query: str, history: list[dict], top_k: int = 5) -> dict:
    """채팅 형식 RAG 검색 + Claude 답변 (대화 히스토리 지원)"""
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

    # 2. 사료 컨텍스트 구성
    sources = []
    context = ""

    if docs:
        context_parts = []
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            source_name = meta.get("source", "출처미상")
            year = meta.get("year", "")
            context_parts.append(f"[사료 {i+1}] {source_name} ({year})\n{doc}")
            sources.append({
                "title": source_name,
                "year": year,
                "excerpt": doc[:150] + "..." if len(doc) > 150 else doc,
                "relevance": round(1 - dist, 3),
                "url": meta.get("url", ""),
            })
        context = "\n\n".join(context_parts)

    # 3. 메시지 구성 (히스토리 포함)
    messages = []
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # assistant 메시지에서 사진/출처 메타데이터는 제외, 텍스트만 전달
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    if context:
        user_content = f"[참고 사료]\n{context}\n\n[질문]\n{query}"
    else:
        user_content = f"[사료 없음 — 일반 역사 지식으로 답변]\n\n[질문]\n{query}"

    messages.append({"role": "user", "content": user_content})

    # 4. Claude 답변 생성
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    return {
        "answer": response.content[0].text,
        "sources": sources,
        "query": query,
    }


async def ingest_documents(documents: list[dict]) -> int:
    """문서를 ChromaDB에 임베딩하여 저장"""
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
