from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import httpx

router = APIRouter()

_BASE = "https://museum.seoul.go.kr:8088/component/archv/data/ND_thumbnail.tmb"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}


@router.get("/seoul")
async def seoul_thumb(f: str, sn: int = 300):
    """서울역사아카이브 썸네일 프록시 (포트 8088 우회)"""
    if not f or "/" in f or ".." in f:
        raise HTTPException(400)
    url = f"{_BASE}?fileSn={sn}&fileId={f}" + ("&w=300&h=300" if sn == 300 else "")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=_HEADERS)
            r.raise_for_status()
        return Response(
            r.content,
            media_type=r.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code)
    except Exception:
        raise HTTPException(502)
