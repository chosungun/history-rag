import httpx
import re
from app.core.config import settings


async def fetch_gongu_photos(keyword: str, page: int = 1, per_page: int = 12) -> dict:
    """공유마당(저작권위원회) 이미지 API"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://gongu.copyright.or.kr/gongu/openapi/openapi.do",
            params={
                "serviceKey": settings.public_data_api_key,
                "searchWrd": keyword,
                "pageNo": page,
                "numOfRows": per_page,
                "resultType": "json",
                "cateCode": "010",  # 사진
            }
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_wikimedia_photos(query: str, limit: int = 12) -> list[dict]:
    """Wikimedia Commons — 한국 근현대사 사진 (API 키 불필요)
    generator=search로 파일 검색과 imageinfo를 한 번의 요청으로 처리
    """
    # 한국어 검색어 + 조선 필터로 관련도 높임
    search_query = query
    # 연도 추출해서 검색어 보강
    year_match = re.search(r'(\d{4})', query)
    if year_match:
        year = year_match.group(1)
        search_query = f"{query} {year}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": search_query,
                "gsrnamespace": "6",  # File 네임스페이스
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url|thumburl|extmetadata",
                "iiurlwidth": 400,
                "format": "json",
                "origin": "*",
            }
        )
        resp.raise_for_status()
        data = resp.json()

    photos = []
    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if int(page_id) < 0:  # missing pages
            continue
        infos = page.get("imageinfo", [])
        if not infos:
            continue
        info = infos[0]
        thumb = info.get("thumburl", "")
        original = info.get("url", "")
        if not thumb and not original:
            continue

        # 설명/날짜 메타데이터 추출
        meta = info.get("extmetadata", {})
        date_str = meta.get("DateTimeOriginal", {}).get("value", "") or meta.get("DateTime", {}).get("value", "")
        year = date_str[:4] if date_str and date_str[:4].isdigit() else ""
        title = page.get("title", "").replace("File:", "")

        photos.append({
            "id": f"wiki_{page_id}",
            "title": title,
            "year": year,
            "thumbnail": thumb or original,
            "original": original,
            "source": "Wikimedia Commons",
            "license": meta.get("LicenseShortName", {}).get("value", "CC"),
            "url": f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
        })

    return photos


async def fetch_korean_wikipedia(keyword: str, limit: int = 5) -> list[dict]:
    """한국어 위키백과 — 역사 기사 텍스트 수집 (API 키 불필요)"""
    async with httpx.AsyncClient(timeout=15) as client:
        # 1. 검색
        search_resp = await client.get(
            "https://ko.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": keyword,
                "srlimit": limit,
                "format": "json",
                "origin": "*",
            }
        )
        search_data = search_resp.json()
        pages = search_data.get("query", {}).get("search", [])
        if not pages:
            return []

        # 2. 본문 추출
        page_ids = "|".join(str(p["pageid"]) for p in pages)
        content_resp = await client.get(
            "https://ko.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "pageids": page_ids,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsectionformat": "plain",
                "format": "json",
                "origin": "*",
            }
        )
        content_data = content_resp.json()

    results = []
    for page_id, page in content_data.get("query", {}).get("pages", {}).items():
        extract = page.get("extract", "").strip()
        if not extract or len(extract) < 100:
            continue
        results.append({
            "id": f"wiki_{page_id}",
            "text": extract[:3000],
            "source": "한국어 위키백과",
            "year": "",
            "url": f"https://ko.wikipedia.org/?curid={page_id}",
            "image_url": "",
            "category": "백과사전",
        })

    return results
