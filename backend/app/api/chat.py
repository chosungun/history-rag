import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag import rag_chat
from app.services.public_api import fetch_gongu_photos, fetch_wikimedia_photos

router = APIRouter()


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    top_k: int = 5


@router.post("")
async def chat(req: ChatRequest):
    if not req.messages:
        return {"answer": "질문을 입력해주세요.", "sources": [], "photos": []}

    user_msg = req.messages[-1].content.strip()
    if not user_msg:
        return {"answer": "질문을 입력해주세요.", "sources": [], "photos": []}

    # 히스토리: 마지막 user 메시지 제외, role+content만 전달
    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    # RAG 답변 + 사진 검색 병렬 실행
    rag_task = rag_chat(user_msg, history, req.top_k)
    photo_task = _fetch_photos(user_msg)

    result, photos = await asyncio.gather(rag_task, photo_task, return_exceptions=False)
    result["photos"] = photos
    return result


async def _fetch_photos(query: str) -> list[dict]:
    """공유마당 + Wikimedia Commons 병렬 검색, 최대 20장"""
    try:
        gongu_task = fetch_gongu_photos(query, page=1, per_page=12)
        wiki_task = fetch_wikimedia_photos(query, limit=12)

        gongu_data, wiki_photos = await asyncio.gather(
            gongu_task, wiki_task, return_exceptions=True
        )

        photos: list[dict] = []

        # 공유마당 파싱
        if not isinstance(gongu_data, Exception):
            items = (
                gongu_data.get("response", {})
                .get("body", {})
                .get("items", {})
                .get("item", [])
            )
            if isinstance(items, dict):
                items = [items]
            for item in items:
                thumb = item.get("thumbnailFileUrl", "")
                if not thumb:
                    continue
                photos.append({
                    "id": f"gongu_{item.get('wrtSn', '')}",
                    "title": item.get("wrtNm", ""),
                    "year": item.get("registDt", "")[:4] if item.get("registDt") else "",
                    "thumbnail": thumb,
                    "original": item.get("originalFileUrl", "") or thumb,
                    "source": "공유마당",
                    "license": item.get("ccLsNm", "CC BY"),
                    "url": f"https://gongu.copyright.or.kr/gongu/wrt/wrt/view.do?wrtSn={item.get('wrtSn', '')}",
                })

        # Wikimedia 파싱
        if not isinstance(wiki_photos, Exception) and isinstance(wiki_photos, list):
            photos.extend(wiki_photos)

        return photos[:20]

    except Exception:
        return []
