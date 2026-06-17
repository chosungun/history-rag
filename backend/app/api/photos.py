from fastapi import APIRouter, Query
from app.services.public_api import fetch_gongu_photos

router = APIRouter()

@router.get("")
async def get_photos(
    keyword: str = Query(..., description="검색어 (예: 경성, 조선풍속)"),
    page: int = Query(1, ge=1)
):
    """공유마당 저작권 무료 사진 검색"""
    try:
        data = await fetch_gongu_photos(keyword, page)
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        photos = [
            {
                "id": item.get("wrtSn", ""),
                "title": item.get("wrtNm", ""),
                "year": item.get("registDt", "")[:4] if item.get("registDt") else "",
                "thumbnail": item.get("thumbnailFileUrl", ""),
                "original": item.get("originalFileUrl", ""),
                "source": "공유마당(한국저작권위원회)",
                "license": item.get("ccLsNm", "CC BY"),
                "url": f"https://gongu.copyright.or.kr/gongu/wrt/wrt/view.do?wrtSn={item.get('wrtSn', '')}",
            }
            for item in items
        ]
        return {"photos": photos, "total": len(photos), "keyword": keyword}
    except Exception as e:
        return {"photos": [], "total": 0, "error": str(e)}
