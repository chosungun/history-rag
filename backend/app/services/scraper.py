import re
import asyncio
import json
import os
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
    "CTGRY818",  # 종교신앙 (무당, 장승, 성황당)
    "CTGRY819",  # 인물도감 (양반, 조선풍속, 기생)
    "CTGRY820",  # 조선신궁
    "CTGRY821",  # 조선의 신사 (경성신사, 명동성당, 박문사)
    # 교육
    "CTGRY823",  # 교육시설 (경성제대, 이화학당, 서당)
    "CTGRY824",  # 학교생활
    # 문화예술
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


def get_category_for_keyword(query: str) -> str:
    """질문에서 가장 관련있는 카테고리 ID 반환"""
    for keyword, ctgry_id in _SEOUL_CATEGORY_MAP.items():
        if keyword in query:
            return ctgry_id
    return _SEOUL_DEFAULT_CATEGORY


async def scrape_seoul_archive_detail(file_id: str, ctgry_id: str) -> dict | None:
    """서울역사아카이브 상세 페이지에서 고화질 사진 + 설명 텍스트 추출"""
    url = f"https://museum.seoul.go.kr/archive/archiveNew/NR_archiveView.do?ctgryId={ctgry_id}&fileId={file_id}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HistoryResearchBot/1.0)"}

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 메타데이터 파싱
            meta = {}
            for row in soup.select("table tr, dl dt, dl dd, div.info_list li"):
                text = row.get_text(separator="|", strip=True)
                parts = text.split("|")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val:
                        meta[key] = val

            # 설명 텍스트
            desc = ""
            for key in ["내용", "설명", "description"]:
                if key in meta:
                    desc = meta[key]
                    break
            if not desc:
                desc_el = soup.select_one("div.cont_view p, div.view_cont p, td.cont")
                if desc_el:
                    desc = desc_el.get_text(strip=True)

            # 연도 추출
            year = ""
            for key in ["시기", "제작연도", "연도", "date"]:
                if key in meta:
                    m = re.search(r"(\d{4})", meta[key])
                    if m:
                        year = m.group(1)
                    break

            title_el = soup.select_one("h2, h3, div.view_title, strong.tit")
            title = title_el.get_text(strip=True) if title_el else file_id

            return {
                "file_id": file_id,
                "title": title,
                "year": year,
                "original": f"/api/img/seoul?f={file_id}&sn=1000",
                "thumbnail": f"/api/img/seoul?f={file_id}",
                "description": desc,
                "source": meta.get("자료출처", "서울역사아카이브"),
                "meta": meta,
                "url": url,
            }
        except Exception as e:
            print(f"서울역사아카이브 상세 수집 실패 ({file_id}): {e}")
            return None


async def scrape_seoul_history_photos(keyword: str, limit: int = 12) -> list[dict]:
    """서울역사아카이브 키워드 → 카테고리 매핑 후 사진 + 상세 수집"""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HistoryResearchBot/1.0)"}

    ctgry_id = _SEOUL_DEFAULT_CATEGORY
    for kw, cid in _SEOUL_CATEGORY_MAP.items():
        if kw in keyword:
            ctgry_id = cid
            break

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
                        "searchVal": keyword,
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
                "thumbnail": detail["thumbnail"],
                "original": detail["original"],
                "source": detail["source"],
                "license": "공공누리 제1유형",
                "url": detail["url"],
                "description": detail["description"],
            })
        await asyncio.sleep(0.3)

    return photos


async def crawl_seoul_archive_photos(on_progress=None) -> list[dict]:
    """서울역사아카이브 근현대서울사진 26개 카테고리 전체 크롤링 → ChromaDB 문서로 변환"""
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

                        # 연도 추출: 주변 텍스트에서 4자리 숫자
                        year = ""
                        container = img
                        for _ in range(6):
                            container = container.parent
                            if not container:
                                break
                            txt = container.get_text(separator=" ", strip=True)
                            if len(txt) > 10:
                                m = re.search(r"(1[89]\d{2}|20[01]\d)", txt)
                                if m:
                                    year = m.group(1)
                                break

                        thumbnail = f"/api/img/seoul?f={file_id}"
                        archive_url = f"{_SEOUL_ARCHIVE_BASE}/archive/archiveNew/NR_archiveView.do?ctgryId={ctgry_id}&fileId={file_id}"
                        title = alt or file_id
                        text = f"{title}" + (f" ({year}년)" if year else "")

                        documents.append({
                            "id": f"seoul_archive_{file_id}",
                            "text": text,
                            "source": "서울역사아카이브 근현대서울사진",
                            "year": year,
                            "url": archive_url,
                            "image_url": thumbnail,
                            "category": "근현대서울사진",
                        })
                        if on_progress:
                            on_progress(len(documents))

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

            for img in soup.find_all("img", src=lambda s: s and "ND_thumbnail.tmb" in s):
                src = img.get("src", "")
                alt = img.get("alt", "")

                file_id_match = re.search(r"fileId=([^&]+)", src)
                if not file_id_match:
                    continue
                file_id = file_id_match.group(1)

                thumbnail = f"/api/img/seoul?f={file_id}"
                original = f"/api/img/seoul?f={file_id}&sn=1000"
                archive_url = f"{_SEOUL_ARCHIVE_BASE}/archive/archiveNew/NR_archiveView.do?ctgryId={ctgry_id}&fileId={file_id}"

                photos.append({
                    "id": f"seoul_archive_{file_id}",
                    "title": alt or file_id,
                    "year": "",
                    "thumbnail": thumbnail,
                    "original": original,
                    "source": "서울역사아카이브",
                    "license": "서울특별시",
                    "url": archive_url,
                    "description": alt,
                })

                if len(photos) >= limit:
                    break

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
    }.get(item_id, "한국근현대사료DB")

    return {
        "id": f"history_db_{level_id}",
        "title": title,
        "text": body_text[:4000],
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
