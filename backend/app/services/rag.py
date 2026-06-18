import re
import anthropic
from app.core.chroma import get_collection, embed
from app.core.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """당신은 일제강점기(1910~1945) 한국 근현대사 고증 전문가입니다. 역사 소설 집필을 위한 자료를 제공합니다.

답변 원칙:
1. 제공된 사료에 근거하여 답변한다. 사료가 부족하면 역사적으로 알려진 사실로 보완하되, ~~이처럼 보완된 내용~~ 형식으로 표시한다.
2. 묘사는 포함하되 과장하지 않는다. 사실에서 추론 가능한 범위만 서술한다.
3. 연도·수치·명칭·구조 등 구체적 정보를 우선한다.
4. 형용사·부사를 최소화하고, 사실 나열 위주로 서술한다.
5. 이전 대화 맥락을 유지한다.
6. 출처는 답변 마지막에 ▶ 출처: 형태로 명시한다.
7. 사진·이미지에 대해 절대 언급하지 않는다. "사진을 제공할 수 없다", "이미지를 드릴 수 없다" 같은 말을 하면 안 된다. 사진은 별도 시스템이 처리하므로 텍스트 답변에서 사진 관련 내용은 완전히 무시한다.
8. 한자(漢字)를 절대 사용하지 않는다. 고유명사·직책·지명 등 모든 표현은 한글로만 쓴다. 일본어 원문 인용 시 한자가 포함된 원문은 그대로 인용하되, 한국어 해설은 반드시 한글로만 작성한다.
9. 특정 장소·건물의 위치를 설명하는 질문에는 답변 본문 맨 끝에 반드시 [COORD:위도,경도] 형식으로 좌표를 추가한다. 위치 질문이 아니면 절대 추가하지 않는다. 경성 주요 좌표 참고: 광화문 37.5759/126.9769, 종로 37.5735/126.9788, 명동 37.5636/126.9826, 남산 37.5512/126.9882, 경성역(서울역) 37.5548/126.9707, 동대문 37.5711/127.0098, 서대문 37.5720/126.9596, 인사동 37.5742/126.9850.

일본어 원문 사료 인용 방식:
- 출처가 '조선총독부 관보', '국내 항일운동 자료', '국외 항일운동 자료' 등 일본어 원문 사료일 경우, 반드시 아래 형식으로 인용한다.

  원문(일본어): 「...원문 발췌...」
  이를 풀면: ...한국어 해설...
  이러한 기록이 있으니, ...역사적 맥락과 소설 활용 방향...

- 원문은 사료에서 가장 핵심이 되는 1~2문장만 발췌한다.
- 한국어 해설은 원문의 뜻을 자연스러운 현대 한국어로 풀어 쓴다.
- 이후 그 기록이 함의하는 역사적 사실과 소설에서 활용할 수 있는 구체적 맥락을 이어 서술한다."""


def _extract_keywords(query: str) -> str:
    """Claude Haiku로 ChromaDB 검색용 핵심 키워드 추출. 실패 시 원본 쿼리 반환."""
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=30,
            system=(
                "사용자 질문에서 역사 자료 검색에 최적화된 핵심 한국어 명사 키워드만 추출하라. "
                "2~4개 단어, 공백으로 구분. "
                "예: '1922년 조선호텔 외관은?' → '조선호텔'. "
                "예: '의열단이 경성에서 활동한 방식은?' → '의열단 경성'. "
                "오직 키워드만 출력하고 다른 설명 없이."
            ),
            messages=[{"role": "user", "content": query}],
        )
        keywords = resp.content[0].text.strip()
        return keywords if keywords else query
    except Exception:
        return query


async def rag_chat(query: str, history: list[dict], top_k: int = 5, include_news: bool = True) -> dict:
    """채팅 형식 RAG 검색 + Claude 답변 (대화 히스토리 지원)"""
    collection = get_collection()

    # 1. 벡터 검색 (컬렉션이 비어있으면 스킵)
    docs, metas, distances = [], [], []
    sources_news: list[dict] = []

    if collection.count() > 0:
        # 1-0. 검색 키워드 추출 (ChromaDB 검색 최적화)
        search_query = _extract_keywords(query)
        query_embedding = embed([search_query])[0]

        # 1-a. 전체 카테고리 일반 검색
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        # 1-b. 신문 전용 검색 (k=3, category 필터)
        if include_news:
            try:
                _news_count = len(collection.get(
                    where={"category": {"$eq": "신문"}}, limit=1, include=[]
                )["ids"])
                if _news_count == 0:
                    raise ValueError("신문 문서 없음")
                news_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3,
                    where={"category": {"$eq": "신문"}},
                    include=["documents", "metadatas", "distances"]
                )
                for doc, meta, dist in zip(
                    news_results["documents"][0],
                    news_results["metadatas"][0],
                    news_results["distances"][0],
                ):
                    sources_news.append({
                        "title": meta.get("source", "신문"),
                        "year": meta.get("year", ""),
                        "excerpt": doc[:200] + "..." if len(doc) > 200 else doc,
                        "relevance": round(1 - dist, 3),
                        "url": meta.get("url", ""),
                        "image_url": "",
                        "category": "신문",
                    })
            except Exception:
                pass

    # 2. 사료 컨텍스트 구성
    sources = []
    context = ""
    seen_urls: set[str] = set()

    if docs:
        context_parts = []
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            source_name = meta.get("source", "출처미상")
            year = meta.get("year", "")
            url = meta.get("url", "")
            context_parts.append(f"[사료 {i+1}] {source_name} ({year})\n{doc}")
            sources.append({
                "title": source_name,
                "year": year,
                "excerpt": doc[:150] + "..." if len(doc) > 150 else doc,
                "relevance": round(1 - dist, 3),
                "url": url,
                "image_url": meta.get("image_url", ""),
                "category": meta.get("category", ""),
            })
            if url:
                seen_urls.add(url)

        # 신문 전용 결과 중 일반 검색에 없는 것만 컨텍스트에 추가
        for ns in sources_news:
            if ns["url"] not in seen_urls:
                context_parts.append(f"[신문] {ns['title']} ({ns['year']})\n{ns['excerpt']}")
                seen_urls.add(ns["url"])

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
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    answer = response.content[0].text
    truncated = response.stop_reason == "max_tokens"
    if truncated:
        answer += "\n\n※ (응답이 너무 길어 일부 잘렸습니다.)"

    # 좌표 태그 추출 후 답변에서 제거
    coords = None
    coord_match = re.search(r'\[COORD:([\d.]+),([\d.]+)\]', answer)
    if coord_match:
        coords = {"lat": float(coord_match.group(1)), "lng": float(coord_match.group(2))}
        answer = answer[:coord_match.start()].rstrip()

    return {
        "answer": answer,
        "sources": sources,
        "sources_news": sources_news,
        "query": query,
        "truncated": truncated,
        "coords": coords,
    }


async def ingest_documents(documents: list[dict]) -> int:
    """문서를 ChromaDB에 임베딩하여 저장"""
    collection = get_collection()

    embed_texts = [
        f"{d['source']}: {d['text']}" if d.get("source") else d["text"]
        for d in documents
    ]
    store_texts = [d["text"] for d in documents]
    embeddings = embed(embed_texts)

    collection.upsert(
        ids=[d["id"] for d in documents],
        embeddings=embeddings,
        documents=store_texts,
        metadatas=[{
            "source": d.get("source", ""),
            "year": d.get("year", ""),
            "url": d.get("url", ""),
            "image_url": d.get("image_url", ""),
            "category": d.get("category", ""),
        } for d in documents]
    )
    return len(documents)
