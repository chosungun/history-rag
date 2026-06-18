import re
import asyncio
import httpx
from xml.etree import ElementTree as ET

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag import rag_chat
from app.core.config import settings

router = APIRouter()

_NL_SEARCH_URL = "https://www.nl.go.kr/NL/search/openApi/search.do"
_NL_BASE = "https://www.nl.go.kr"


def _xt(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


async def _fetch_nl_live(query: str, k: int = 5) -> list[dict]:
    """국립중앙도서관 search.do 실시간 신문 검색"""
    if not settings.nl_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                _NL_SEARCH_URL,
                params={
                    "key": settings.nl_api_key,
                    "kwd": query,
                    "pageNum": "1",
                    "pageSize": str(k),
                    "category": "신문",
                    "srchTarget": "all",
                    "sort": "date",
                },
                headers={"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"},
            )
            resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"NL 실시간 신문 검색 실패: {e}")
        return []

    results = []
    for item in root.findall(".//item"):
        title     = _xt(item, "title_info")
        if not title:
            continue
        date_str  = _xt(item, "pub_year_info")
        publisher = _xt(item, "pub_info")
        link_str  = _xt(item, "detail_link")

        year_m = re.search(r"(\d{4})", date_str)
        year = year_m.group(1) if year_m else ""

        if link_str:
            url = link_str if link_str.startswith("http") else f"{_NL_BASE}{link_str}"
        else:
            url = ""

        parts = [p for p in [publisher, f"({date_str})" if date_str else ""] if p]
        excerpt = " ".join(parts) + f" — {title}" if parts else title

        results.append({
            "title": publisher or title,   # 신문명을 타이틀로
            "year": year,
            "excerpt": excerpt,
            "relevance": 1.0,
            "url": url,
            "image_url": "",
            "category": "신문",
        })
        if len(results) >= k:
            break

    return results


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("")
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력하세요.")

    rag_task = rag_chat(req.query, [], req.top_k)
    nl_task  = _fetch_nl_live(req.query, k=5)

    result, nl_news = await asyncio.gather(rag_task, nl_task)

    # ChromaDB 신문 결과 + NL 실시간 결과 병합 (URL 중복 제거)
    existing_urls = {s["url"] for s in result.get("sources_news", []) if s.get("url")}
    for item in nl_news:
        if not item["url"] or item["url"] not in existing_urls:
            result["sources_news"].append(item)
            if item["url"]:
                existing_urls.add(item["url"])

    return result


@router.get("/ping")
async def ping():
    return {"ok": True}
