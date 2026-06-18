import re
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag import rag_chat
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


@router.post("")
async def chat(req: ChatRequest):
    if not req.messages:
        return {"answer": "질문을 입력해주세요.", "sources": [], "photos": []}

    user_msg = req.messages[-1].content.strip()
    if not user_msg:
        return {"answer": "질문을 입력해주세요.", "sources": [], "photos": []}

    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    rag_task = rag_chat(user_msg, history, req.top_k)
    photo_task = _fetch_photos(user_msg)

    result, photos = await asyncio.gather(rag_task, photo_task, return_exceptions=False)
    result["photos"] = photos
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
    """공유마당 + 서울아카이브 + Wikimedia 병렬, 3장 미달 시 폴백"""
    try:
        gongu_data, emuseum_photos, seoul_photos, wiki_photos = await asyncio.gather(
            fetch_gongu_photos(query, page=1, per_page=10),
            fetch_emuseum_photos(query, page=1, limit=4),
            fetch_seoul_archive_photos(query, limit=10),
            fetch_wikimedia_photos(query, limit=8),
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

        add(seoul_photos if not isinstance(seoul_photos, Exception) else [])
        add(emuseum_photos if not isinstance(emuseum_photos, Exception) else [])
        add(_parse_gongu(gongu_data))
        add(wiki_photos if not isinstance(wiki_photos, Exception) else [])

        # 3장 미달 → 폴백 검색
        if len(photos) < 3:
            fallback = _fallback_query(query)
            fb_gongu, fb_seoul, fb_wiki = await asyncio.gather(
                fetch_gongu_photos(fallback, page=1, per_page=8),
                fetch_seoul_archive_photos(fallback, limit=6),
                fetch_wikimedia_photos(fallback, limit=8),
                return_exceptions=True,
            )
            add(fb_seoul if not isinstance(fb_seoul, Exception) else [])
            add(_parse_gongu(fb_gongu))
            add(fb_wiki if not isinstance(fb_wiki, Exception) else [])

        return photos[:20]

    except Exception:
        return []
