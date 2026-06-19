import re
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag import rag_chat, ingest_documents, search_photos_chroma
from app.services.public_api import (
    fetch_gongu_photos, fetch_emuseum_photos,
    fetch_seoul_archive_photos, fetch_wikimedia_photos,
)

router = APIRouter()


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    top_k: int = 15
    include_photos: bool = True
    include_news: bool = True


@router.post("")
async def chat(req: ChatRequest):
    if not req.messages:
        return {"answer": "질문을 입력해주세요.", "sources": [], "photos": []}

    user_msg = req.messages[-1].content.strip()
    if not user_msg:
        return {"answer": "질문을 입력해주세요.", "sources": [], "photos": []}

    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    rag_task = rag_chat(user_msg, history, req.top_k, include_news=req.include_news)
    photo_task = _fetch_photos(user_msg) if req.include_photos else asyncio.sleep(0, result=[])

    result, photos = await asyncio.gather(rag_task, photo_task, return_exceptions=False)
    result["photos"] = photos if isinstance(photos, list) else []
    return result


def _parse_gongu(data) -> list[dict]:
    if isinstance(data, Exception) or not data:
        return []
    items = (
        data.get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )
    if isinstance(items, dict):
        items = [items]
    result = []
    for item in items:
        thumb = item.get("thumbnailFileUrl", "")
        if not thumb:
            continue
        result.append({
            "id": f"gongu_{item.get('wrtSn', '')}",
            "title": item.get("wrtNm", ""),
            "year": item.get("registDt", "")[:4] if item.get("registDt") else "",
            "thumbnail": thumb,
            "original": item.get("originalFileUrl", "") or thumb,
            "source": "공유마당",
            "license": item.get("ccLsNm", "CC BY"),
            "url": f"https://gongu.copyright.or.kr/gongu/wrt/wrt/view.do?wrtSn={item.get('wrtSn', '')}",
        })
    return result


def _fallback_query(query: str) -> str:
    """질문에서 연도·장소 추출해 폭넓은 검색어 생성"""
    year_match = re.search(r'(19[1-4]\d)', query)
    if year_match:
        decade = (int(year_match.group(1)) // 10) * 10
        for kw in ['경성', '서울', '평양', '개성', '인천', '부산', '전주', '대구']:
            if kw in query:
                return f"{kw} {decade}년대"
        return f"경성 {decade}년대"
    for kw in ['경성', '서울', '평양', '개성', '인천', '부산']:
        if kw in query:
            return f"{kw} 일제강점기"
    return "경성 일제강점기 1930년대"


async def _fetch_photos(query: str) -> list[dict]:
    """공유마당 + 서울아카이브(실시간+ChromaDB) + Wikimedia 병렬, 3장 미달 시 폴백"""
    try:
        gongu_data, emuseum_photos, seoul_photos, wiki_photos, chroma_photos = await asyncio.gather(
            fetch_gongu_photos(query, page=1, per_page=10),
            fetch_emuseum_photos(query, page=1, limit=4),
            fetch_seoul_archive_photos(query, limit=10),
            fetch_wikimedia_photos(query, limit=8),
            search_photos_chroma(query, top_k=8),
            return_exceptions=True,
        )

        photos: list[dict] = []
        seen: set[str] = set()

        def add(new_photos):
            for p in (new_photos or []):
                pid = p.get("id", "")
                if pid and pid not in seen and (p.get("thumbnail") or p.get("original")):
                    seen.add(pid)
                    photos.append(p)

        _seoul = seoul_photos if not isinstance(seoul_photos, Exception) else []
        _gongu = _parse_gongu(gongu_data)
        _wiki = wiki_photos if not isinstance(wiki_photos, Exception) else []
        _chroma = chroma_photos if not isinstance(chroma_photos, Exception) else []
        print(f"[photo] seoul={len(_seoul)} chroma={len(_chroma)} gongu={len(_gongu)} wiki={len(_wiki)}"
              + (f" seoul_err={seoul_photos}" if isinstance(seoul_photos, Exception) else "")
              + (f" chroma_err={chroma_photos}" if isinstance(chroma_photos, Exception) else ""))

        add(_seoul)
        add(_chroma)   # ChromaDB 유사도 검색 결과 (연대·카테고리 필터 적용)
        add(emuseum_photos if not isinstance(emuseum_photos, Exception) else [])
        add(_gongu)
        add(_wiki)

        # 서울아카이브 사진 설명 텍스트 → ChromaDB 자동 적재
        if not isinstance(seoul_photos, Exception):
            seoul_docs = [
                {
                    "id": f"seoul_desc_{p['id']}",
                    "text": p["description"],
                    "source": p["source"],
                    "year": p["year"],
                    "url": p["url"],
                    "image_url": p["thumbnail"],
                    "category": "서울역사아카이브",
                }
                for p in (seoul_photos or []) if p.get("description")
            ]
            if seoul_docs:
                await ingest_documents(seoul_docs)

        # 3장 미달 → 폴백 검색
        if len(photos) < 3:
            fallback = _fallback_query(query)
            fb_gongu, fb_seoul, fb_wiki = await asyncio.gather(
                fetch_gongu_photos(fallback, page=1, per_page=8),
                fetch_seoul_archive_photos(fallback, limit=6),
                fetch_wikimedia_photos(fallback, limit=8),
                return_exceptions=True,
            )
            _fb_seoul = fb_seoul if not isinstance(fb_seoul, Exception) else []
            _fb_gongu = _parse_gongu(fb_gongu)
            _fb_wiki = fb_wiki if not isinstance(fb_wiki, Exception) else []
            print(f"[photo fallback] seoul={len(_fb_seoul)} gongu={len(_fb_gongu)} wiki={len(_fb_wiki)}")
            add(_fb_seoul)
            add(_fb_gongu)
            add(_fb_wiki)

        return photos[:20]

    except Exception:
        return []
