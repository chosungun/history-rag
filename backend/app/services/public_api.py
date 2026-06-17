import httpx
from app.core.config import settings

HISTORY_DB_BASE = "https://api.db.history.go.kr/v1"
INDEPENDENCE_BASE = "https://search.i815.or.kr/openapi"


async def fetch_history_db(keyword: str, page: int = 1, per_page: int = 10) -> dict:
    """국사편찬위원회 한국사DB 검색 API"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{HISTORY_DB_BASE}/search",
            params={
                "keyword": keyword,
                "page": page,
                "per_page": per_page,
                "apiKey": settings.public_data_api_key,
            }
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_independence_records(keyword: str, page: int = 1) -> dict:
    """독립기념관 독립운동 정보시스템 API
    공공데이터포털: https://www.data.go.kr 에서 '독립기념관' 검색 후 API 신청
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{INDEPENDENCE_BASE}/search",
            params={
                "serviceKey": settings.independence_api_key,
                "searchWord": keyword,
                "pageNo": page,
                "numOfRows": 10,
                "resultType": "json",
            }
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_gongu_photos(keyword: str, page: int = 1) -> dict:
    """공유마당(저작권위원회) 이미지 API - 1920년대 조선 사진 무료
    https://gongu.copyright.or.kr/gongu/openapi/openapi.do
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://gongu.copyright.or.kr/gongu/openapi/openapi.do",
            params={
                "serviceKey": settings.public_data_api_key,
                "searchWrd": keyword,
                "pageNo": page,
                "numOfRows": 12,
                "resultType": "json",
                "cateCode": "010",  # 사진
            }
        )
        resp.raise_for_status()
        return resp.json()
