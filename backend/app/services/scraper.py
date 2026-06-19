import re
import asyncio
import json
import os
import hashlib
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

CHECKPOINT_DIR = "/data/checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


def _save_checkpoint(name: str, data: dict):
    with open(f"{CHECKPOINT_DIR}/{name}.json", "w") as f:
        json.dump(data, f)


def _load_checkpoint(name: str) -> dict | None:
    path = f"{CHECKPOINT_DIR}/{name}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _clear_checkpoint(name: str):
    path = f"{CHECKPOINT_DIR}/{name}.json"
    if os.path.exists(path):
        os.remove(path)

_SEOUL_ARCHIVE_BASE = "https://museum.seoul.go.kr"
_HISTORY_DB_BASE = "https://db.history.go.kr"

# 근현대 사진 컬렉션 카테고리 (서울역사아카이브 근현대서울사진)
SEOUL_PHOTO_CATEGORIES = [
    # 건설개발
    "CTGRY807",  # 도시경관 (경성거리, 본정통, 혼마치, 종로, 황금정)
    "CTGRY808",  # 관공서 (조선총독부, 경성부청, 우편국, 서대문형무소)
    "CTGRY809",  # 광화문통
    "CTGRY810",  # 근대공원 (파고다공원, 남산공원, 장충단, 효창원)
    "CTGRY811",  # 대한제국기 건축물 (덕수궁, 독립문, 환구단)
    "CTGRY812",  # 서울전경
    "CTGRY813",  # 전통건축 (경복궁, 창덕궁, 창경궁)
    "CTGRY814",  # 한양도성 (남대문, 동대문, 흥인지문)
    # 보건의료
    "CTGRY816",  # 병원/의료 (세브란스, 총독부의원)
    # 사회생활
    "CTGRY817",  # 사회생활 (상위 카테고리 — 104건)
    "CTGRY818",  # 종교신앙 (무당, 장승, 성황당)
    "CTGRY819",  # 인물도감 (양반, 조선풍속, 기생)
    "CTGRY820",  # 조선신궁
    "CTGRY821",  # 조선의 신사 (경성신사, 명동성당, 박문사)
    # 교육
    "CTGRY823",  # 교육시설 (경성제대, 이화학당, 서당)
    "CTGRY824",  # 학교생활
    # 문화예술
    "CTGRY825",  # 문화예술 (상위 카테고리 — 136건)
    "CTGRY826",  # 기생 (검무, 승무, 기생학교)
    "CTGRY827",  # 동식물원 (창경원)
    "CTGRY828",  # 박물관 (총독부박물관, 이왕가박물관)
    "CTGRY829",  # 박람회 (조선물산공진회, 조선박람회)
    # 산업경제
    "CTGRY793",  # 조선시찰단 (경복궁, 경성 풍경)
    "CTGRY794",  # 황실 (고종, 순종, 영친왕)
    "CTGRY796",  # 은사수산장
    "CTGRY797",  # 장인 (갓, 도자기, 수공업)
    "CTGRY798",  # 상업 (미츠코시, 시장, 오복점)
    "CTGRY799",  # 금융 (조선은행, 동양척식)
    "CTGRY800",  # 기업/공장
    "CTGRY801",  # 농림업
    # 교통
    "CTGRY803",  # 가마/인력거
    "CTGRY804",  # 전차/자동차
    "CTGRY805",  # 철도 (경성역, 기차, 한강철교)
    # 여가/관광/체육
    "CTGRY830",  # 여가/관광/체육 (상위 카테고리 — 73건)
    "CTGRY831",  # 경성유람버스
    "CTGRY832",  # 극장
    "CTGRY833",  # 요릿집 (명월관, 식도원)
    "CTGRY834",  # 호텔·여관 (조선호텔)
    "CTGRY835",  # 여가 (한강, 벚꽃, 아리랑)
    "CTGRY836",  # 체육 (경성운동장)
]

# 한국근현대사료DB 수집 대상 아이템 ID
HISTORY_DB_ITEMS = {
    # 민족운동·사회운동
    "had":  ("국내 항일운동 자료",         "/modern/level.do"),
    "haf":  ("국외 항일운동 자료",         "/modern/level.do"),
    "ij":   ("대한민국임시정부자료집",      "/modern/level.do"),
    "pro":  ("소요사건 도장관 보고철",     "/modern/level.do"),
    "jssy": ("조선소요사건관계서류",        "/modern/level.do"),
    "kd":   ("한국독립운동사자료",          "/modern/level.do"),
    "hdsr": ("한민족독립운동사",            "/modern/level.do"),
    "hd":   ("한민족독립운동사자료집",      "/modern/level.do"),
    # 관보
    "gbdh": ("조선·대한제국 관보",         "/modern/level.do"),
    "gbtg": ("통감부 공보",                "/modern/level.do"),
    "gb":   ("조선총독부 관보",            "/modern/gb/level.do"),
    # 신문
    "npgr": ("공립신보",                   "/modern/level.do"),
    "npda": ("동아일보",                   "/modern/level.do"),
    "npbs": ("부산일보",                   "/modern/level.do"),
    "npsd": ("시대일보",                   "/modern/level.do"),
    "npsh": ("신한민보",                   "/modern/level.do"),
    "npjs": ("조선시보",                   "/modern/level.do"),
    "npjj": ("조선중앙일보",               "/modern/level.do"),
    "npja": ("중앙일보",                   "/modern/level.do"),
    "npjo": ("중외일보",                   "/modern/level.do"),
    "npsc": ("신문스크랩자료",             "/modern/level.do"),
    # 편년자료·문서
    "jh":   ("주한일본공사관기록·통감부문서", "/modern/level.do"),
    "ju":   ("중추원조사자료",             "/modern/level.do"),
    "su":   ("일제침략하한국36년사",        "/modern/level.do"),
    # 목록·총서
    "smla": ("근대한일외교자료",            "/modern/level.do"),
    "wj":   ("일본군 위안부·전쟁범죄 자료집", "/modern/level.do"),
    "gsdc": ("경성지방법원 기록 해제",     "/modern/level.do"),
    "smlb": ("일제시기 희귀자료",          "/modern/level.do"),
    "mh":   ("한국근대사기초자료집",        "/modern/level.do"),
    "hk":   ("한국근대사자료집성",          "/modern/level.do"),
    # 근대 전환기
    "mk":   ("각사등록 근대편",            "/modern/level.do"),
    "gj":   ("고종시대사",                 "/modern/level.do"),
    "sk":   ("사료 고종시대사",            "/modern/level.do"),
    "prd":  ("동학농민혁명자료총서",        "/modern/level.do"),
    "pry":  ("동학농민혁명사일지",          "/modern/level.do"),
    "prc":  ("동학농민혁명연표",           "/modern/level.do"),
    "prw":  ("동학농민혁명증언록",          "/modern/level.do"),
    "ykc":  ("유길준 자료 DB",             "/modern/level.do"),
}

# 근현대잡지자료 — levelId : 잡지명
MAGAZINE_ITEMS = {
    "ma_013": "개벽",
    "ma_015": "별건곤",
    "ma_016": "삼천리",
    "ma_102": "신여성",
    "ma_109": "소년",
    "ma_126": "어린이",
    "ma_014": "동광",
    "ma_091": "학지광",
    "ma_069": "사상운동",
    "ma_074": "시사평론",
    "ma_001": "대한자강회월보",
    "ma_004": "서북학회월보",
    "ma_066": "동명",
}


# 키워드 → 서울역사아카이브 카테고리 매핑
_SEOUL_CATEGORY_MAP = {
    # ── 도시/거리 풍경 (CTGRY807)
    '경성거리': 'CTGRY807', '본정': 'CTGRY807', '혼마치': 'CTGRY807',
    '황금정': 'CTGRY807', '명동거리': 'CTGRY807', '남대문통': 'CTGRY807',
    '종로거리': 'CTGRY807', '광화문거리': 'CTGRY807', '야경': 'CTGRY807',
    '경성시가': 'CTGRY807', '용산신시가': 'CTGRY807',
    # ── 관공서 (CTGRY808)
    '조선총독부': 'CTGRY808', '총독부': 'CTGRY808', '경성부청': 'CTGRY808',
    '우편국': 'CTGRY808', '서대문형무소': 'CTGRY808', '경기도청': 'CTGRY808',
    '통감부': 'CTGRY808', '고등법원': 'CTGRY808', '경성일보': 'CTGRY808',
    '총독관저': 'CTGRY808', '경성우편국': 'CTGRY808',
    # ── 광화문 (CTGRY809)
    '광화문': 'CTGRY809',
    # ── 공원 (CTGRY810)
    '파고다공원': 'CTGRY810', '탑골공원': 'CTGRY810', '남산공원': 'CTGRY810',
    '장충단': 'CTGRY810', '효창원': 'CTGRY810', '왜성대공원': 'CTGRY810',
    '사직단': 'CTGRY810', '남산벚꽃': 'CTGRY810',
    # ── 대한제국 건축물 (CTGRY811)
    '덕수궁': 'CTGRY811', '독립문': 'CTGRY811', '환구단': 'CTGRY811',
    '원구단': 'CTGRY811', '황궁우': 'CTGRY811', '석조전': 'CTGRY811',
    '러시아공사관': 'CTGRY811', '칭경기념비': 'CTGRY811',
    # ── 서울전경 (CTGRY812)
    '경성전경': 'CTGRY812', '서울전경': 'CTGRY812', '남산전경': 'CTGRY812',
    '항공사진': 'CTGRY812',
    # ── 전통건축/궁궐 (CTGRY813)
    '경복궁': 'CTGRY813', '창덕궁': 'CTGRY813', '창경궁': 'CTGRY813',
    '경회루': 'CTGRY813', '근정전': 'CTGRY813', '인정전': 'CTGRY813',
    '비원': 'CTGRY813', '창경원': 'CTGRY813', '향원정': 'CTGRY813',
    '경운궁': 'CTGRY813',
    # ── 성문/성곽 (CTGRY814)
    '남대문': 'CTGRY814', '숭례문': 'CTGRY814', '동대문': 'CTGRY814',
    '흥인지문': 'CTGRY814', '서대문': 'CTGRY814', '한양도성': 'CTGRY814',
    '성곽': 'CTGRY814', '창의문': 'CTGRY814', '광희문': 'CTGRY814',
    # ── 병원/의료 (CTGRY816)
    '병원': 'CTGRY816', '세브란스': 'CTGRY816', '총독부의원': 'CTGRY816',
    '의원': 'CTGRY816', '의료': 'CTGRY816', '대한의원': 'CTGRY816',
    # ── 종교/무속 (CTGRY818)
    '무당': 'CTGRY818', '장승': 'CTGRY818', '성황당': 'CTGRY818',
    '무속': 'CTGRY818', '샤머니즘': 'CTGRY818', '산신제': 'CTGRY818',
    # ── 인물/복식 (CTGRY819)
    '양반': 'CTGRY819', '조선인물': 'CTGRY819', '복식': 'CTGRY819',
    '한복': 'CTGRY819', '조선풍속': 'CTGRY819', '상류층': 'CTGRY819',
    # ── 조선신궁 (CTGRY820)
    '조선신궁': 'CTGRY820', '신궁': 'CTGRY820',
    # ── 신사/종교시설 (CTGRY821)
    '경성신사': 'CTGRY821', '명동성당': 'CTGRY821', '박문사': 'CTGRY821',
    '신사': 'CTGRY821', '교회': 'CTGRY821', '성당': 'CTGRY821',
    # ── 학교/교육시설 (CTGRY823)
    '경성제국대학': 'CTGRY823', '이화학당': 'CTGRY823', '서당': 'CTGRY823',
    '학교': 'CTGRY823', '보통학교': 'CTGRY823', '고등보통학교': 'CTGRY823',
    '성균관': 'CTGRY823', '경학원': 'CTGRY823',
    # ── 학교생활 (CTGRY824)
    '수업': 'CTGRY824', '운동회': 'CTGRY824', '학교생활': 'CTGRY824',
    # ── 기생/공연 (CTGRY826)
    '기생': 'CTGRY826', '검무': 'CTGRY826', '승무': 'CTGRY826',
    '기생학교': 'CTGRY826', '관기': 'CTGRY826', '가야금': 'CTGRY826',
    '무용': 'CTGRY826', '기녀': 'CTGRY826',
    # ── 창경원/동식물원 (CTGRY827)
    '동물원': 'CTGRY827', '식물원': 'CTGRY827', '창경원동물': 'CTGRY827',
    # ── 박물관 (CTGRY828)
    '박물관': 'CTGRY828', '총독부박물관': 'CTGRY828', '이왕가박물관': 'CTGRY828',
    # ── 박람회 (CTGRY829)
    '박람회': 'CTGRY829', '공진회': 'CTGRY829', '조선박람회': 'CTGRY829',
    '물산공진회': 'CTGRY829',
    # ── 황실 (CTGRY794)
    '고종': 'CTGRY794', '순종': 'CTGRY794', '영친왕': 'CTGRY794',
    '황실': 'CTGRY794', '황제': 'CTGRY794', '대한제국황실': 'CTGRY794',
    # ── 장인/수공업 (CTGRY797)
    '장인': 'CTGRY797', '도자기': 'CTGRY797', '갓제조': 'CTGRY797',
    '수공업': 'CTGRY797', '빨래방망이': 'CTGRY797',
    # ── 상업/시장/백화점 (CTGRY798)
    '시장': 'CTGRY798', '백화점': 'CTGRY798', '미츠코시': 'CTGRY798',
    '상점': 'CTGRY798', '오복점': 'CTGRY798', '장날': 'CTGRY798',
    '행상': 'CTGRY798', '장수': 'CTGRY798', '화신백화점': 'CTGRY798',
    '종로상가': 'CTGRY798', '조지야': 'CTGRY798', '히노데': 'CTGRY798',
    # ── 금융/경제 (CTGRY799)
    '조선은행': 'CTGRY799', '은행': 'CTGRY799', '동양척식': 'CTGRY799',
    '경성상업회의소': 'CTGRY799',
    # ── 공장/기업 (CTGRY800)
    '공장': 'CTGRY800', '방적': 'CTGRY800', '종연방적': 'CTGRY800',
    # ── 농림업 (CTGRY801)
    '농촌': 'CTGRY801', '농업': 'CTGRY801', '산림': 'CTGRY801',
    # ── 가마/인력거 (CTGRY803)
    '가마': 'CTGRY803', '인력거': 'CTGRY803', '조랑말': 'CTGRY803',
    # ── 전차/자동차 (CTGRY804)
    '전차': 'CTGRY804', '자동차': 'CTGRY804',
    # ── 철도/기차 (CTGRY805)
    '기차': 'CTGRY805', '철도': 'CTGRY805', '경성역': 'CTGRY805',
    '용산역': 'CTGRY805', '한강철교': 'CTGRY805', '열차': 'CTGRY805',
    '남대문역': 'CTGRY805',
    # ── 경성유람버스 (CTGRY831)
    '유람버스': 'CTGRY831', '버스': 'CTGRY831',
    # ── 극장 (CTGRY832)
    '극장': 'CTGRY832', '영화관': 'CTGRY832', '공회당': 'CTGRY832',
    '연극': 'CTGRY832', '활동사진': 'CTGRY832',
    # ── 요릿집/음식점 (CTGRY833)
    '명월관': 'CTGRY833', '식도원': 'CTGRY833', '요릿집': 'CTGRY833',
    '음식점': 'CTGRY833', '카페': 'CTGRY833', '요리점': 'CTGRY833',
    # ── 호텔/여관 (CTGRY834)
    '조선호텔': 'CTGRY834', '호텔': 'CTGRY834', '여관': 'CTGRY834',
    '손탁호텔': 'CTGRY834',
    # ── 여가/관광 (CTGRY835)
    '한강': 'CTGRY835', '낚시': 'CTGRY835', '벚꽃': 'CTGRY835',
    '아리랑': 'CTGRY835', '놀이': 'CTGRY835',
    # ── 체육 (CTGRY836)
    '운동장': 'CTGRY836', '야구': 'CTGRY836', '체육': 'CTGRY836',
    '경성운동장': 'CTGRY836',
}

_SEOUL_DEFAULT_CATEGORY = 'CTGRY807'  # 기본값: 도시경관 (범용적)

_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        from app.core.config import settings
        _anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


async def _enrich_photo_text(title: str, period: str, place: str, content: str) -> str:
    """Claude Haiku로 사진 메타데이터를 검색 키워드로 보강. 실패 시 기본 조합 반환."""
    parts = [p for p in [title, period, place, content] if p]
    fallback = " | ".join(parts)
    if not parts:
        return ""

    meta = "\n".join(
        f"{k}: {v}" for k, v in [
            ("명칭", title), ("시기", period), ("장소", place), ("내용", content)
        ] if v
    )
    try:
        client = _get_anthropic_client()
        resp = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": (
                "서울역사아카이브 사진 메타데이터에서 검색 키워드를 보강해줘. "
                "건물명·장소·연도·건축양식·용도·시대 맥락을 쉼표로 나열. "
                "60단어 이내, 한국어만, 키워드만 출력.\n\n" + meta
            )}],
        )
        enriched = resp.content[0].text.strip()
        return f"{title}, {enriched}" if title and title not in enriched else enriched
    except Exception as e:
        print(f"Claude 텍스트 보강 실패 ({title}): {e}")
        return fallback


def get_category_for_keyword(query: str) -> str:
    """질문에서 가장 관련있는 카테고리 ID 반환"""
    for keyword, ctgry_id in _SEOUL_CATEGORY_MAP.items():
        if keyword in query:
            return ctgry_id
    return _SEOUL_DEFAULT_CATEGORY


def _parse_seoul_archive_detail_html(
    soup: BeautifulSoup, file_id: str, detail_url: str
) -> dict | None:
    """BeautifulSoup 객체에서 서울역사아카이브 상세 정보 추출"""
    tbl = soup.select_one("div.view_table_info table")
    if not tbl:
        return None

    meta: dict[str, str] = {}
    for row in tbl.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if th and td:
            key = th.get_text(strip=True)
            val = td.get_text(" ", strip=True)
            if key:
                meta[key] = val

    title = meta.get("명칭", file_id)
    period = meta.get("시기", "")
    place = meta.get("장소", "")
    source = meta.get("자료출처", "서울역사아카이브")
    content = meta.get("내용", "")
    archive_no = meta.get("아카이브 번호", file_id)
    artifact_no = meta.get("유물번호", "")

    year = ""
    m = re.search(r"(1[89]\d{2}|20[012]\d)", period)
    if m:
        year = m.group(1)

    # 원본 이미지: ARCHIVE_DATA 경로 우선, 없으면 ND_originFile
    original_url = ""
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "ARCHIVE_DATA" in src:
            original_url = src
            break
    if not original_url:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "ND_originFile" in src:
                original_url = src
                break

    parts = [p for p in [title, period, place, content] if p]
    text = " | ".join(parts)

    return {
        "file_id": file_id,
        "title": title,
        "year": year,
        "period": period,
        "place": place,
        "content": content,
        "archive_no": archive_no,
        "artifact_no": artifact_no,
        "original_url": original_url,
        "thumbnail": f"/api/img/seoul?f={file_id}",
        "description": content,
        "source": source,
        "text": text,
        "meta": meta,
        "url": detail_url,
    }


def _seoul_detail_url(ctgry_id: str, file_id: str) -> str:
    return (
        f"{_SEOUL_ARCHIVE_BASE}/archive/archiveNew/NR_archiveView.do"
        f"?ctgryId={ctgry_id}&subCtgryId=&upperNodeId={ctgry_id}"
        f"&type=D&fileSn=300&fileId={file_id}"
    )


async def scrape_seoul_archive_detail(file_id: str, ctgry_id: str) -> dict | None:
    """서울역사아카이브 상세 페이지에서 고화질 원본 이미지 + 메타데이터 추출"""
    url = _seoul_detail_url(ctgry_id, file_id)
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            result = _parse_seoul_archive_detail_html(soup, file_id, url)
            if result is None:
                print(f"서울역사아카이브 상세 파싱 실패 ({file_id}): view_table_info 없음")
            return result
        except Exception as e:
            print(f"서울역사아카이브 상세 수집 실패 ({file_id}): {e}")
            return None


async def scrape_seoul_history_photos(keyword: str, limit: int = 12) -> list[dict]:
    """서울역사아카이브 키워드 → 카테고리 매핑 후 사진 + 상세 수집"""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HistoryResearchBot/1.0)"}

    ctgry_id = _SEOUL_DEFAULT_CATEGORY
    matched_kw = ""
    for kw, cid in _SEOUL_CATEGORY_MAP.items():
        if kw in keyword:
            ctgry_id = cid
            matched_kw = kw
            break

    # searchVal: 매핑된 키워드 사용 (전체 질문 대신), 없으면 빈 문자열로 카테고리 전체 탐색
    search_val = matched_kw if matched_kw else keyword

    # 1단계: 목록에서 file_id 수집
    file_ids = []
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        try:
            for page in range(1, 3):
                resp = await client.post(
                    "https://museum.seoul.go.kr/archive/archiveNew/NR_archiveList.do",
                    data={
                        "currentPage": str(page),
                        "type": "D",
                        "ctgryId": ctgry_id,
                        "subCtgryId": "",
                        "upperNodeId": ctgry_id,
                        "searchVal": search_val,
                        "sortOrder": "",
                    },
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                imgs = soup.find_all("img", src=lambda s: s and "ND_thumbnail.tmb" in s)
                if not imgs:
                    break

                for img in imgs:
                    m = re.search(r"fileId=([^&]+)", img.get("src", ""))
                    if m:
                        file_ids.append(m.group(1))
                    if len(file_ids) >= limit:
                        break

                if len(file_ids) >= limit:
                    break

                await asyncio.sleep(0.3)

        except Exception as e:
            print(f"서울역사아카이브 목록 수집 실패: {e}")

    # 2단계: 각 상세 페이지에서 텍스트·메타데이터 수집
    photos = []
    for file_id in file_ids[:limit]:
        detail = await scrape_seoul_archive_detail(file_id, ctgry_id)
        if detail:
            photos.append({
                "id": f"seoul_archive_{file_id}",
                "title": detail["title"],
                "year": detail["year"],
                "period": detail["period"],
                "place": detail["place"],
                "archive_no": detail["archive_no"],
                "artifact_no": detail["artifact_no"],
                "thumbnail": detail["thumbnail"],
                "original": detail["original_url"] or detail["thumbnail"],
                "source": detail["source"],
                "license": "공공누리 제1유형",
                "url": detail["url"],
                "description": detail["content"],
            })
        await asyncio.sleep(0.3)

    return photos


async def crawl_seoul_archive_photos(on_progress=None, enrich: bool = False) -> list[dict]:
    """서울역사아카이브 근현대서울사진 전체 카테고리 크롤링 → ChromaDB 문서로 변환
    enrich=True 시 Claude Haiku로 text 키워드 보강 (수집 속도 느려짐)
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    documents = []
    seen_ids: set[str] = set()

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for ctgry_id in SEOUL_PHOTO_CATEGORIES:
            page = 1
            while True:
                try:
                    resp = await client.post(
                        f"{_SEOUL_ARCHIVE_BASE}/archive/archiveNew/NR_archiveList.do",
                        data={
                            "currentPage": str(page),
                            "type": "D",
                            "ctgryId": ctgry_id,
                            "subCtgryId": "",
                            "upperNodeId": ctgry_id,
                            "searchVal": "",
                            "sortOrder": "",
                        },
                    )
                    soup = BeautifulSoup(resp.text, "html.parser")
                    imgs = [img for img in soup.find_all("img", src=lambda s: s and "ND_thumbnail.tmb" in s)]
                    if not imgs:
                        break  # 더 이상 페이지 없음

                    for img in imgs:
                        src = img.get("src", "")
                        alt = img.get("alt", "").strip()
                        file_id_match = re.search(r"fileId=([^&]+)", src)
                        if not file_id_match:
                            continue
                        file_id = file_id_match.group(1)
                        if file_id in seen_ids:
                            continue
                        seen_ids.add(file_id)

                        detail_url = _seoul_detail_url(ctgry_id, file_id)
                        try:
                            detail_resp = await client.get(detail_url)
                            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                            detail = _parse_seoul_archive_detail_html(detail_soup, file_id, detail_url)
                        except Exception as de:
                            print(f"서울역사아카이브 상세 수집 실패 ({file_id}): {de}")
                            detail = None

                        if detail:
                            if enrich:
                                text = await _enrich_photo_text(
                                    detail["title"], detail["period"],
                                    detail["place"], detail["content"],
                                )
                            else:
                                text = detail["text"]
                            documents.append({
                                "id": f"seoul_archive_{file_id}",
                                "title": detail["title"],
                                "text": text,
                                "source": "서울역사아카이브 근현대서울사진",
                                "year": detail["year"],
                                "url": detail_url,
                                "image_url": detail["original_url"] or f"/api/img/seoul?f={file_id}",
                                "category": "근현대서울사진",
                            })
                        else:
                            title = alt or file_id
                            documents.append({
                                "id": f"seoul_archive_{file_id}",
                                "title": title,
                                "text": title,
                                "source": "서울역사아카이브 근현대서울사진",
                                "year": "",
                                "url": detail_url,
                                "image_url": f"/api/img/seoul?f={file_id}",
                                "category": "근현대서울사진",
                            })

                        if on_progress:
                            on_progress(len(documents))
                        await asyncio.sleep(0.3)

                    page += 1
                    await asyncio.sleep(0.4)
                except Exception as e:
                    print(f"서울역사아카이브 수집 실패 ({ctgry_id} p{page}): {e}")
                    break

            await asyncio.sleep(0.3)

    print(f"✅ 서울역사아카이브 수집 완료: {len(documents)}개 사진")
    return documents


async def scrape_seoul_archive_listing(ctgry_id: str, page: int = 1, limit: int = 20) -> list[dict]:
    """
    서울역사아카이브 특정 컬렉션(ctgryId) 목록 페이지에서 사진 수집
    - 페이지네이션 지원
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    photos = []

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.post(
                f"{_SEOUL_ARCHIVE_BASE}/archive/archiveNew/NR_archiveList.do",
                data={
                    "currentPage": str(page),
                    "type": "D",
                    "ctgryId": ctgry_id,
                    "subCtgryId": "",
                    "upperNodeId": ctgry_id,
                    "searchVal": "",
                    "sortOrder": "",
                },
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            file_ids = []
            for img in soup.find_all("img", src=lambda s: s and "ND_thumbnail.tmb" in s):
                src = img.get("src", "")
                file_id_match = re.search(r"fileId=([^&]+)", src)
                if file_id_match:
                    file_ids.append((file_id_match.group(1), img.get("alt", "")))
                if len(file_ids) >= limit:
                    break

            for file_id, alt in file_ids:
                detail_url = _seoul_detail_url(ctgry_id, file_id)
                try:
                    detail_resp = await client.get(detail_url)
                    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                    detail = _parse_seoul_archive_detail_html(detail_soup, file_id, detail_url)
                except Exception as de:
                    print(f"서울역사아카이브 상세 수집 실패 ({file_id}): {de}")
                    detail = None

                if detail:
                    photos.append({
                        "id": f"seoul_archive_{file_id}",
                        "title": detail["title"],
                        "year": detail["year"],
                        "period": detail["period"],
                        "place": detail["place"],
                        "archive_no": detail["archive_no"],
                        "artifact_no": detail["artifact_no"],
                        "thumbnail": detail["thumbnail"],
                        "original": detail["original_url"] or f"/api/img/seoul?f={file_id}",
                        "source": detail["source"],
                        "license": "서울특별시",
                        "url": detail_url,
                        "description": detail["content"],
                    })
                else:
                    photos.append({
                        "id": f"seoul_archive_{file_id}",
                        "title": alt or file_id,
                        "year": "",
                        "period": "",
                        "place": "",
                        "archive_no": file_id,
                        "artifact_no": "",
                        "thumbnail": f"/api/img/seoul?f={file_id}",
                        "original": f"/api/img/seoul?f={file_id}",
                        "source": "서울역사아카이브",
                        "license": "서울특별시",
                        "url": detail_url,
                        "description": alt,
                    })

                await asyncio.sleep(0.3)

        except Exception as e:
            print(f"서울역사아카이브 목록 수집 실패 ({ctgry_id}): {e}")

    return photos


def _extract_doc_content(soup: BeautifulSoup, url: str, item_id: str, level_id: str) -> dict | None:
    """한국근현대사료DB 문서 페이지에서 메타데이터·본문 추출"""
    cont_view = soup.find("div", class_="cont_view")
    if not cont_view:
        return None

    # 메타데이터 파싱
    meta = {}
    for item in cont_view.find_all("div", class_="item"):
        tit_el = item.find("div", class_="tit")
        cont_el = item.find("div", class_="cont")
        if tit_el and cont_el:
            key = tit_el.get_text(strip=True)
            val = re.sub(r"\s+", " ", cont_el.get_text(strip=True))
            meta[key] = val

    # 본문 텍스트 (일본어 원문)
    # id="cont_view" 중첩 구조 대응 — 가장 안쪽 div 사용
    body_divs = cont_view.find_all("div", id="cont_view")
    body_div = body_divs[-1] if body_divs else None
    if not body_div:
        # 본문 없는 경우 — 제목 자체가 사료 내용인 문서 (jh, smla 등)
        title_text = meta.get("기사제목", meta.get("문서제목", ""))
        if not title_text or len(title_text) < 5:
            return None
        body_text = title_text
    else:
        for tag in body_div(["script", "style"]):
            tag.extract()
        body_text = re.sub(r"\s+", " ", body_div.get_text(separator=" ", strip=True)).strip()

    if len(body_text) < 10:
        return None

    # 날짜·연도 파싱
    date_str = meta.get("발행일", meta.get("작성일", ""))
    year_match = re.search(r"(\d{4})년", date_str)
    year = year_match.group(1) if year_match else ""

    # 기사제목
    title = meta.get("기사제목", meta.get("문서제목", soup.title.string.strip() if soup.title else "제목 없음"))

    source_name = {
        "gb": "조선총독부 관보",
        "had": "국내 항일운동 자료(경성지방법원)",
        "haf": "국외 항일운동 자료(일본 외무성)",
        "pro": "소요사건 도장관 보고",
        "jssy": "조선소요사건 관계서류",
        "kd": "고등경찰 관계 연표",
    }.get(item_id) or HISTORY_DB_ITEMS.get(item_id, (item_id,))[0]

    return {
        "id": f"history_db_{level_id}",
        "title": title,
        "text": f"[{source_name}] {body_text}"[:4000],
        "source": source_name,
        "year": year,
        "url": url,
        "image_url": "",
        "category": "일본어원문사료",
        "meta": meta,
    }


async def crawl_history_db_by_year(
    item_id: str = "gb",
    years: list[int] | None = None,
    max_docs: int = 200,
    on_progress=None,
) -> list[dict]:
    """
    한국근현대사료DB 연도별 문서 크롤링
    - item_id: 'gb'(관보), 'had'(항일운동국내), 'haf'(항일운동국외) 등
    - years: 수집할 연도 목록 (기본: 1910~1945)
    - max_docs: 최대 수집 문서 수
    """
    if years is None:
        years = list(range(1910, 1946))

    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    documents = []

    level_base = f"/modern/{item_id}/level.do" if item_id in ("gb",) else "/modern/level.do"

    ckpt_name = f"year_{item_id}"
    ckpt = _load_checkpoint(ckpt_name)
    done_years = set(ckpt["done_years"]) if ckpt else set()
    print(f"  체크포인트: {len(done_years)}/{len(years)} 연도 이미 완료")

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for year in years:
            if max_docs > 0 and len(documents) >= max_docs:
                break

            if str(year) in done_years:
                continue

            # 연도별 목록 페이지
            list_url = f"{_HISTORY_DB_BASE}{level_base}?itemId={item_id}&levelId={item_id}_{year}"
            try:
                resp = await client.get(list_url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as e:
                print(f"목록 페이지 실패 ({year}): {e}")
                continue

            # levelId 링크 수집
            doc_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "levelId=" in href and f"{item_id}_{year}_" in href:
                    full_url = urljoin(_HISTORY_DB_BASE, href)
                    level_id_match = re.search(r"levelId=([^&]+)", href)
                    if level_id_match:
                        doc_links.append((full_url, level_id_match.group(1)))

            if not doc_links:
                done_years.add(str(year))
                _save_checkpoint(ckpt_name, {"done_years": list(done_years), "count": len(documents)})
                continue

            print(f"  {year}년: {len(doc_links)}개 문서 발견")

            # 각 문서 크롤링
            for doc_url, level_id in doc_links:
                if max_docs > 0 and len(documents) >= max_docs:
                    break
                try:
                    doc_resp = await client.get(doc_url)
                    if doc_resp.status_code != 200:
                        continue
                    doc_soup = BeautifulSoup(doc_resp.text, "html.parser")
                    doc = _extract_doc_content(doc_soup, doc_url, item_id, level_id)
                    if doc:
                        documents.append(doc)
                        if on_progress:
                            on_progress(len(documents))
                    await asyncio.sleep(0.4)
                except Exception as e:
                    print(f"    문서 크롤링 실패 ({level_id}): {e}")
                    await asyncio.sleep(1.0)

            done_years.add(str(year))
            _save_checkpoint(ckpt_name, {"done_years": list(done_years), "count": len(documents)})

    _clear_checkpoint(ckpt_name)
    print(f"✅ 한국근현대사료DB 수집 완료: {len(documents)}개 문서")
    return documents


async def _get_leaf_ids(client: httpx.AsyncClient, parent_id: str, level: int, max_depth: int = 7) -> list[str]:
    """AJAX로 하위 leaf 문서 ID 재귀 수집"""
    if level > max_depth:
        return [parent_id]
    try:
        resp = await client.get(
            f"{_HISTORY_DB_BASE}/modern/getChildItemLevelListAjax.do",
            params={"parentId": parent_id, "level": str(level), "sideNavYn": "true"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        children = [d for d in soup.find_all("div", attrs={"data-id": True})
                    if d["data-id"].startswith(parent_id + "_")]
        if not children:
            return [parent_id]
        leaves = []
        for ch in children:
            child_id = ch["data-id"]
            if ch.get("data-leaf") == "1":
                leaves.append(child_id)
            else:
                sub = await _get_leaf_ids(client, child_id, level + 1, max_depth)
                leaves.extend(sub)
        return leaves
    except Exception:
        return [parent_id]


async def crawl_sequential(
    item_id: str,
    max_docs: int = 0,
    on_progress=None,
) -> list[dict]:
    """
    순번형 ID 구조 사료 크롤링 (had, haf, ju, prd 등)
    - 최상위 페이지에서 moveDetailList 패턴으로 볼륨 ID 수집
    - 각 볼륨에서 AJAX로 leaf 문서까지 재귀 탐색
    - max_docs=0 이면 무제한
    """
    item_label = HISTORY_DB_ITEMS.get(item_id, (item_id,))[0]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    documents = []

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        # 1단계: 최상위 볼륨 ID 수집
        try:
            top_resp = await client.get(f"{_HISTORY_DB_BASE}/modern/level.do?itemId={item_id}")
            top_resp.raise_for_status()
        except Exception as e:
            print(f"⚠️  {item_label} 최상위 페이지 실패: {e}")
            return []

        top_nums = re.findall(rf"moveDetailList\('{item_id}_(\d+)'\)", top_resp.text)
        if not top_nums:
            print(f"⚠️  {item_label}: 최상위 항목 없음")
            return []

        print(f"  {item_label}: {len(top_nums)}개 볼륨 발견")

        # 체크포인트 로드
        ckpt_name = f"sequential_{item_id}"
        ckpt = _load_checkpoint(ckpt_name)
        done_nums = set(ckpt["done_nums"]) if ckpt else set()
        print(f"  체크포인트: {len(done_nums)}/{len(top_nums)} 볼륨 이미 완료")

        # 2단계: 볼륨별 leaf 문서 탐색 → 본문 수집
        for num in top_nums:
            if max_docs > 0 and len(documents) >= max_docs:
                break

            if num in done_nums:
                continue

            parent_id = f"{item_id}_{num}"
            try:
                leaf_ids = await _get_leaf_ids(client, parent_id, level=2)
            except Exception as e:
                print(f"  leaf 탐색 실패 ({parent_id}): {e}")
                continue

            for leaf_id in leaf_ids:
                if max_docs > 0 and len(documents) >= max_docs:
                    break
                doc_url = f"{_HISTORY_DB_BASE}/modern/level.do?levelId={leaf_id}"
                try:
                    doc_resp = await client.get(doc_url)
                    if doc_resp.status_code != 200:
                        continue
                    doc_soup = BeautifulSoup(doc_resp.text, "html.parser")
                    doc = _extract_doc_content(doc_soup, doc_url, item_id, leaf_id)
                    if doc:
                        documents.append(doc)
                        if on_progress:
                            on_progress(len(documents))
                    await asyncio.sleep(0.4)
                except Exception as e:
                    print(f"    문서 수집 실패 ({leaf_id}): {e}")
                    await asyncio.sleep(1.0)

            done_nums.add(num)
            _save_checkpoint(ckpt_name, {"done_nums": list(done_nums), "count": len(documents)})

    _clear_checkpoint(ckpt_name)
    print(f"✅ {item_label} 수집 완료: {len(documents)}개 문서")
    return documents


def _extract_magazine_article(soup: BeautifulSoup, url: str, level_id: str, magazine_name: str) -> dict | None:
    """근현대잡지 기사 페이지에서 본문·메타데이터 추출"""
    # 본문
    body_div = soup.find("div", id="cont_view")
    if not body_div:
        return None
    for tag in body_div(["script", "style"]):
        tag.extract()
    body_text = re.sub(r"\s+", " ", body_div.get_text(separator=" ", strip=True)).strip()
    if len(body_text) < 20:
        return None

    # 메타데이터
    meta = {}
    for item in soup.find_all("div", class_="item"):
        tit_el = item.find("div", class_="tit")
        cont_el = item.find("div", class_="cont")
        if tit_el and cont_el:
            meta[tit_el.get_text(strip=True)] = re.sub(r"\s+", " ", cont_el.get_text(strip=True))

    date_str = meta.get("발행일", "")
    year_match = re.search(r"(\d{4})년", date_str)
    year = year_match.group(1) if year_match else ""
    title = meta.get("기사제목", soup.title.string.strip() if soup.title else "제목 없음")

    return {
        "id": f"magazine_{level_id}",
        "title": title,
        "text": body_text[:4000],
        "source": magazine_name,
        "year": year,
        "url": url,
        "image_url": "",
        "category": "근현대잡지",
        "meta": meta,
    }


async def crawl_magazine(
    mag_level_id: str = "ma_013",
    max_docs: int = 100,
    year_filter: list[str] | None = None,
    on_progress=None,
) -> list[dict]:
    """
    근현대잡지자료 크롤링
    - mag_level_id: MAGAZINE_ITEMS 키 (예: 'ma_013' = 개벽)
    - year_filter: ['1920', '1921', ...] — None이면 전체 수집
    - max_docs: 최대 기사 수
    """
    magazine_name = MAGAZINE_ITEMS.get(mag_level_id, mag_level_id)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    documents = []

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        # 1단계: 호수 목록 수집
        list_url = f"{_HISTORY_DB_BASE}/modern/level.do?itemId=ma&levelId={mag_level_id}&types=R"
        try:
            resp = await client.get(list_url)
            resp.raise_for_status()
        except Exception as e:
            print(f"잡지 목록 수집 실패 ({mag_level_id}): {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        issue_ids = []
        for div in soup.find_all("div", attrs={"data-id": True}):
            did = div["data-id"]
            if did.startswith(mag_level_id + "_") and did.count("_") == 2:
                # 연도 필터
                if year_filter:
                    date_div = div.find("div", class_="date")
                    if date_div:
                        year_in_date = re.search(r"(\d{4})년", date_div.get_text())
                        if year_in_date and year_in_date.group(1) not in year_filter:
                            continue
                issue_ids.append(did)

        print(f"  {magazine_name}: {len(issue_ids)}호 발견")

        # 체크포인트 로드
        ckpt_name = f"magazine_{mag_level_id}"
        ckpt = _load_checkpoint(ckpt_name)
        done_issues = set(ckpt["done_issues"]) if ckpt else set()
        print(f"  체크포인트: {len(done_issues)}/{len(issue_ids)}호 이미 완료")

        # 2단계: 호수별 기사 목록 → 본문 수집
        for issue_id in issue_ids:
            if max_docs > 0 and len(documents) >= max_docs:
                break

            if issue_id in done_issues:
                continue

            try:
                ajax_resp = await client.get(
                    f"{_HISTORY_DB_BASE}/modern/getChildItemLevelListAjax.do",
                    params={"parentId": issue_id, "level": "3", "sideNavYn": "true"},
                )
                ajax_resp.raise_for_status()
                ajax_soup = BeautifulSoup(ajax_resp.text, "html.parser")
                article_divs = ajax_soup.find_all("div", attrs={"data-id": True})
                article_ids = [d["data-id"] for d in article_divs if d["data-id"].startswith(issue_id + "_")]
            except Exception as e:
                print(f"  기사 목록 실패 ({issue_id}): {e}")
                continue

            for article_id in article_ids:
                if max_docs > 0 and len(documents) >= max_docs:
                    break
                article_url = f"{_HISTORY_DB_BASE}/modern/level.do?levelId={article_id}"
                try:
                    art_resp = await client.get(article_url)
                    if art_resp.status_code != 200:
                        continue
                    art_soup = BeautifulSoup(art_resp.text, "html.parser")
                    doc = _extract_magazine_article(art_soup, article_url, article_id, magazine_name)
                    if doc:
                        documents.append(doc)
                        if on_progress:
                            on_progress(len(documents))
                    await asyncio.sleep(0.4)
                except Exception as e:
                    print(f"    기사 수집 실패 ({article_id}): {e}")
                    await asyncio.sleep(1.0)

            done_issues.add(issue_id)
            _save_checkpoint(ckpt_name, {"done_issues": list(done_issues), "count": len(documents)})

    _clear_checkpoint(ckpt_name)
    print(f"✅ {magazine_name} 수집 완료: {len(documents)}개 기사")
    return documents


# ── 국립중앙도서관 신문 아카이브 ────────────────────────────────────────

_NL_SEARCH_URL = "https://www.nl.go.kr/NL/search/openApi/search.do"
_NL_NEWSPAPER_DETAIL = "https://www.nl.go.kr/newspaper/detail.do"


_NL_BASE = "https://www.nl.go.kr"


def _xml_text(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _nl_parse_item(item) -> dict:
    """국중도 API XML <item> 요소 → 공통 필드 딕셔너리"""
    title      = _xml_text(item, "title_info")
    control_no = _xml_text(item, "control_no")
    date_str   = _xml_text(item, "pub_year_info")
    publisher  = _xml_text(item, "pub_info")
    link_str   = _xml_text(item, "detail_link")

    year_m = re.search(r"(\d{4})", date_str)
    year = year_m.group(1) if year_m else ""

    # URL 조합: 상대경로면 앞에 도메인 붙이기
    if link_str:
        url = link_str if link_str.startswith("http") else f"{_NL_BASE}{link_str}"
    elif control_no:
        url = f"{_NL_NEWSPAPER_DETAIL}?id={control_no}"
    else:
        url = _NL_SEARCH_URL

    # 중복 제거 키
    if link_str:
        doc_key = re.sub(r"[^A-Za-z0-9_-]", "_", link_str)[-60:]
    elif control_no:
        doc_key = control_no
    else:
        doc_key = hashlib.md5(f"{title}{date_str}".encode()).hexdigest()[:12]

    text_parts = [p for p in [publisher, f"({date_str})" if date_str else "", title] if p]

    return {
        "title": title,
        "control_no": control_no,
        "date_str": date_str,
        "publisher": publisher,
        "year": year,
        "url": url,
        "doc_key": doc_key,
        "text": " ".join(text_parts),
    }


async def crawl_nl_newspaper(
    keyword: str,
    max_docs: int = 200,
    on_progress=None,
) -> list[dict]:
    """
    국립중앙도서관 open API → 신문(연속간행물) 카테고리 키워드 검색 후 메타데이터 수집
    - text 필드: "{신문명} ({발행일}) - {제목}"  ← RAG 검색용 요약
    - 원문 링크: https://www.nl.go.kr/newspaper/detail.do?id={controlNo}
    """
    from app.core.config import settings

    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    documents = []
    page = 1
    page_size = 100
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        while True:
            if max_docs > 0 and len(documents) >= max_docs:
                break

            params = {
                "key": settings.nl_api_key,
                "kwd": keyword,
                "pageNum": str(page),
                "pageSize": str(page_size),
                "category": "신문",          # 연속간행물 중 신문만
                "srchTarget": "all",
                "sort": "date",
            }

            try:
                resp = await client.get(_NL_SEARCH_URL, params=params)
                resp.raise_for_status()
            except Exception as e:
                print(f"국중도 API 요청 실패 (p{page}): {e}")
                break

            # XML 파싱
            try:
                root = ET.fromstring(resp.content)
            except ET.ParseError as e:
                print(f"국중도 XML 파싱 실패 (p{page}): {e}")
                break

            items = root.findall(".//item")
            if not items:
                break

            for item in items:
                if max_docs > 0 and len(documents) >= max_docs:
                    break

                p = _nl_parse_item(item)
                if not p["title"] or p["doc_key"] in seen:
                    continue
                seen.add(p["doc_key"])

                documents.append({
                    "id": f"nl_newspaper_{p['doc_key']}",
                    "title": p["title"],
                    "text": p["text"],
                    "source": p["publisher"] or "국립중앙도서관 신문",
                    "year": p["year"],
                    "url": p["url"],
                    "image_url": "",
                    "category": "신문",
                    "meta": {
                        "publisher": p["publisher"],
                        "date": p["date_str"],
                        "controlNo": p["control_no"],
                    },
                })

                if on_progress:
                    on_progress(len(documents))

            # 페이지네이션 종료 판단
            total_el = root.find(".//totalCount")
            total = int(total_el.text or "0") if total_el is not None else 0
            if total and page * page_size >= total:
                break
            if len(items) < page_size:
                break

            page += 1
            await asyncio.sleep(0.5)

    print(f"✅ 국중도 신문 수집 완료 [{keyword}]: {len(documents)}건")
    return documents


# 근현대 주요 신문 목록 (일괄 수집 대상)
NL_NEWSPAPER_TITLES = [
    # 개화기·대한제국
    "한성순보", "한성주보", "독립신문", "황성신문",
    "대한매일신보", "제국신문", "만세보", "대한민보",
    "국민신보", "한성신보",
    # 일제강점기 국내
    "매일신보", "경성일보", "동아일보", "조선일보",
    "시대일보", "중외일보", "조선중앙일보", "조선시보",
    "부산일보",
    # 재미 교포 신문
    "공립신보", "신한민보",
    # 해방 이후
    "서울신문", "경향신문", "자유신문", "민족일보",
]


async def crawl_nl_newspaper_bulk(
    max_docs: int = 0,
    on_progress=None,
) -> list[dict]:
    """
    국립중앙도서관 신문 아카이브 전체 일괄 수집
    - NL_NEWSPAPER_TITLES 신문별 순회 + 페이지네이션
    - checkpoint: nl_newspaper_bulk.json → {"done_papers": [...], "count": N}
    - max_docs=0 이면 무제한
    """
    from app.core.config import settings

    ckpt_name = "nl_newspaper_bulk"
    ckpt = _load_checkpoint(ckpt_name)
    done_papers: list[str] = ckpt.get("done_papers", []) if ckpt else []
    total_count: int = ckpt.get("count", 0) if ckpt else 0
    done_set = set(done_papers)

    print(f"  체크포인트: {len(done_set)}/{len(NL_NEWSPAPER_TITLES)} 신문 이미 완료, 누계 {total_count}건")

    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    documents = []
    seen: set[str] = set()
    page_size = 100

    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        for paper in NL_NEWSPAPER_TITLES:
            if max_docs > 0 and (total_count + len(documents)) >= max_docs:
                break
            if paper in done_set:
                continue

            page = 1
            paper_docs = 0
            print(f"  [{paper}] 수집 시작")

            while True:
                if max_docs > 0 and (total_count + len(documents)) >= max_docs:
                    break

                params = {
                    "key": settings.nl_api_key,
                    "kwd": paper,
                    "pageNum": str(page),
                    "pageSize": str(page_size),
                    "category": "신문",
                    "srchTarget": "title",
                    "sort": "date",
                }

                try:
                    resp = await client.get(_NL_SEARCH_URL, params=params)
                    resp.raise_for_status()
                except Exception as e:
                    print(f"    {paper} p{page} 요청 실패: {e}")
                    break

                try:
                    root = ET.fromstring(resp.content)
                except ET.ParseError as e:
                    print(f"    {paper} p{page} XML 파싱 실패: {e}")
                    break

                items = root.findall(".//item")
                if not items:
                    break

                for item in items:
                    p = _nl_parse_item(item)
                    if not p["title"] or p["doc_key"] in seen:
                        continue
                    seen.add(p["doc_key"])

                    documents.append({
                        "id": f"nl_newspaper_{p['doc_key']}",
                        "title": p["title"],
                        "text": p["text"],
                        "source": p["publisher"] or paper,
                        "year": p["year"],
                        "url": p["url"],
                        "image_url": "",
                        "category": "신문",
                        "meta": {
                            "publisher": p["publisher"] or paper,
                            "date": p["date_str"],
                            "controlNo": p["control_no"],
                        },
                    })
                    paper_docs += 1

                    if on_progress:
                        on_progress(total_count + len(documents))

                # 페이지네이션 종료
                total_el = root.find(".//totalCount")
                total_api = int(total_el.text or "0") if total_el is not None else 0
                if total_api and page * page_size >= total_api:
                    break
                if len(items) < page_size:
                    break

                page += 1
                await asyncio.sleep(0.4)

            # 해당 신문 완료 → 체크포인트 저장
            done_papers.append(paper)
            done_set.add(paper)
            _save_checkpoint(ckpt_name, {
                "done_papers": done_papers,
                "count": total_count + len(documents),
            })
            print(f"  [{paper}] 완료: {paper_docs}건")
            await asyncio.sleep(0.5)

    _clear_checkpoint(ckpt_name)
    print(f"✅ 국중도 신문 일괄 수집 완료: {len(documents)}건")
    return documents
