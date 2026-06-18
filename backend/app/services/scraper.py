import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

_SEOUL_ARCHIVE_BASE = "https://museum.seoul.go.kr"
_HISTORY_DB_BASE = "https://db.history.go.kr"

# 근현대 사진 컬렉션 카테고리 (서울역사아카이브 근현대서울사진)
SEOUL_PHOTO_CATEGORIES = [
    "CTGRY793", "CTGRY794", "CTGRY796", "CTGRY797", "CTGRY798",
    "CTGRY799", "CTGRY800", "CTGRY801", "CTGRY803", "CTGRY804",
    "CTGRY805", "CTGRY807", "CTGRY808", "CTGRY809", "CTGRY810",
    "CTGRY811", "CTGRY812", "CTGRY813", "CTGRY814", "CTGRY816",
    "CTGRY818", "CTGRY819", "CTGRY820", "CTGRY821", "CTGRY823",
    "CTGRY824",
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


async def scrape_seoul_history_photos(keyword: str, limit: int = 12) -> list[dict]:
    """
    서울역사아카이브 NR_search.do 검색으로 근현대 사진 수집
    - 키워드로 검색, ND_thumbnail.tmb 이미지 URL 추출
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0)"}
    photos = []

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(
                f"{_SEOUL_ARCHIVE_BASE}/archive/search/NR_search.do",
                params={"query": keyword, "type": "D"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for img in soup.find_all("img", src=lambda s: s and "ND_thumbnail.tmb" in s):
                src = img.get("src", "")
                alt = img.get("alt", "")

                # fileId 추출: fileSn=300&fileId=H-TRNS-XXXXX-XXX
                file_id_match = re.search(r"fileId=([^&]+)", src)
                if not file_id_match:
                    continue
                file_id = file_id_match.group(1)

                # 제목·연도·내용 파싱 (부모 컨테이너 텍스트)
                container = img
                for _ in range(6):
                    container = container.parent
                    if not container:
                        break
                    text = container.get_text(separator=" ", strip=True)
                    if len(text) > 30:
                        break

                title = alt or file_id
                year = ""
                content = ""
                if container:
                    ct = container.get_text(separator=" ", strip=True)
                    m_title = re.search(r"제\s*목\s*[:：]\s*([^\s시기아카]+)", ct)
                    m_year = re.search(r"시\s*기\s*[:：]\s*(\d{4})", ct)
                    m_content = re.search(r"내\s*용\s*[:：]\s*(.{10,80})", ct)
                    if m_title:
                        title = m_title.group(1).strip()
                    if m_year:
                        year = m_year.group(1)
                    if m_content:
                        content = m_content.group(1).strip()

                thumbnail = f"/api/img/seoul?f={file_id}"
                original = f"/api/img/seoul?f={file_id}&sn=1000"
                archive_url = f"{_SEOUL_ARCHIVE_BASE}/archive/archiveNew/NR_archiveView.do?fileId={file_id}"

                photos.append({
                    "id": f"seoul_archive_{file_id}",
                    "title": title,
                    "year": year,
                    "thumbnail": thumbnail,
                    "original": original,
                    "source": "서울역사아카이브",
                    "license": "서울특별시",
                    "url": archive_url,
                    "description": content,
                })

                if len(photos) >= limit:
                    break

        except Exception as e:
            print(f"서울역사아카이브 사진 검색 실패: {e}")

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
    body_div = cont_view.find("div", id="cont_view")
    if not body_div:
        return None
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

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for year in years:
            if len(documents) >= max_docs:
                break

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
                continue

            print(f"  {year}년: {len(doc_links)}개 문서 발견")

            # 각 문서 크롤링
            for doc_url, level_id in doc_links:
                if len(documents) >= max_docs:
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

        # 2단계: 볼륨별 leaf 문서 탐색 → 본문 수집
        for num in top_nums:
            if max_docs > 0 and len(documents) >= max_docs:
                break

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

        # 2단계: 호수별 기사 목록 → 본문 수집
        for issue_id in issue_ids:
            if len(documents) >= max_docs:
                break

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
                if len(documents) >= max_docs:
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

    print(f"✅ {magazine_name} 수집 완료: {len(documents)}개 기사")
    return documents
