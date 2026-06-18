import httpx
import re
from app.core.config import settings
from app.services.scraper import scrape_seoul_history_photos


async def fetch_gongu_photos(keyword: str, page: int = 1, per_page: int = 12) -> dict:
    """공유마당(저작권위원회) 이미지 API"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://gongu.copyright.or.kr/gongu/openapi/openapi.do",
            params={
                "serviceKey": settings.gongu_api_key,
                "searchWrd": keyword,
                "pageNo": page,
                "numOfRows": per_page,
                "resultType": "json",
                "cateCode": "010",  # 사진
            }
        )
        resp.raise_for_status()
        return resp.json()


# 한국어 장소/키워드 → Wikimedia Commons 검색어 매핑
_PLACE_MAP = {
    '조선호텔': 'Chosun Hotel Seoul',
    '경성': 'Keijo Korea',
    '명동': 'Honmachi Keijo Korea',
    '혼마치': 'Honmachi Korea',
    '종로': 'Jongno Korea colonial',
    '남대문': 'Namdaemun Gate Seoul',
    '동대문': 'Dongdaemun Gate Seoul',
    '덕수궁': 'Deoksugung Palace Korea',
    '경복궁': 'Gyeongbokgung Palace Korea',
    '조선총독부': 'Government General Korea building',
    '한강': 'Han River Korea colonial',
    '북촌': 'Bukchon Korea',
    '인천': 'Incheon Korea colonial',
    '부산': 'Busan Korea colonial',
    '평양': 'Pyongyang Korea colonial',
    '개성': 'Kaesong Korea colonial',
    '기생': 'Gisaeng Korea',
    '독립문': 'Independence Gate Korea',
}


def _build_wikimedia_query(query: str) -> str:
    year_match = re.search(r'(\d{4})', query)
    decade = f"{year_match.group(1)[:3]}0s" if year_match else ''
    for korean, english in _PLACE_MAP.items():
        if korean in query:
            return f"{english} {decade}".strip()
    return f"Korea Japanese colonial {decade}".strip() if decade else "Korea Japanese colonial 1920s"


async def fetch_wikimedia_photos(query: str, limit: int = 12) -> list[dict]:
    """Wikimedia Commons — 한국 근현대사 사진 (API 키 불필요)"""
    search_query = _build_wikimedia_query(query)

    headers = {"User-Agent": "history-rag/1.0 (korean-history-research-tool)"}
    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
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


async def fetch_emuseum_photos(keyword: str, page: int = 1, limit: int = 10) -> list[dict]:
    """e-뮤지엄(국립중앙박물관) 소장품 검색 API 연동 뼈대"""
    # 실제 발급받은 e-뮤지엄 API 엔드포인트로 변경 필요
    api_url = "https://api.data.go.kr/openapi/tn_pubr_public_museum_artcl_api"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                api_url,
                params={
                    "serviceKey": settings.public_data_api_key,
                    "pageNo": page,
                    "numOfRows": limit,
                    "type": "json",
                    "artclNm": keyword
                }
            )
            resp.raise_for_status()
            # TODO: 실제 API 응답 구조에 맞게 사진 리스트 파싱 및 정규화
            return []
        except Exception as e:
            print(f"e-뮤지엄 사진 수집 실패: {e}")
            return []


async def fetch_seoul_archive_photos(keyword: str, limit: int = 12) -> list[dict]:
    """서울역사아카이브 근현대서울사진 키워드 검색"""
    return await scrape_seoul_history_photos(keyword, limit=limit)


async def fetch_heritage_data(keyword: str) -> list[dict]:
    """국가유산청(구 문화재청) 근대 문화유산 정보 검색 연동 뼈대"""
    # 실제 국가유산청 API 엔드포인트로 변경 (예: SearchKindOpenapiList.do)
    api_url = "https://www.cha.go.kr/cha/SearchKindOpenapiList.do"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # XML 응답인 경우 xmltodict 라이브러리로 파싱 필요
            resp = await client.get(
                api_url,
                params={
                    "ccbaMnm1": keyword,
                    # 시대 코드(일제강점기 등) 필터 추가 가능
                }
            )
            resp.raise_for_status()
            # TODO: 텍스트 및 사료 메타데이터 추출 (id, text, source, year 등)
            return []
        except Exception as e:
            print(f"국가유산청 데이터 수집 실패: {e}")
            return []
