import re
import asyncio
import httpx
from bs4 import BeautifulSoup

# ── 소설 ──────────────────────────────────────────────────────────────
NOVELS = [
    ("이광수", "무정", "https://ko.wikisource.org/wiki/%EB%AC%B4%EC%A0%95", "1917"),
    ("현진건", "운수 좋은 날", "https://ko.wikisource.org/wiki/%EC%9A%B4%EC%88%98_%EC%A2%8B%EC%9D%80_%EB%82%A0", "1924"),
    ("현진건", "빈처", "https://ko.wikisource.org/wiki/%EB%B9%88%EC%B2%98", "1921"),
    ("현진건", "술 권하는 사회", "https://ko.wikisource.org/wiki/%EC%88%A0_%EA%B6%8C%ED%95%98%EB%8A%94_%EC%82%AC%ED%9A%8C", "1921"),
    ("현진건", "고향", "https://ko.wikisource.org/wiki/%EA%B3%A0%ED%96%A5_(%ED%98%84%EC%A7%84%EA%B1%B4)", "1926"),
    ("현진건", "B사감과 러브레터", "https://ko.wikisource.org/wiki/B%EC%82%AC%EA%B0%90%EA%B3%BC_%EB%9F%AC%EB%B8%8C%EB%A0%88%ED%84%B0", "1925"),
    ("염상섭", "만세전", "https://ko.wikisource.org/wiki/%EB%A7%8C%EC%84%B8%EC%A0%84", "1922"),
    ("염상섭", "표본실의 청개구리", "https://ko.wikisource.org/wiki/%ED%91%9C%EB%B3%B8%EC%8B%A4%EC%9D%98_%EC%B2%AD%EA%B0%9C%EA%B5%AC%EB%A6%AC", "1921"),
    ("김동인", "감자", "https://ko.wikisource.org/wiki/%EA%B0%90%EC%9E%90_(%EA%B9%80%EB%8F%99%EC%9D%B8)", "1925"),
    ("김동인", "배따라기", "https://ko.wikisource.org/wiki/%EB%B0%B0%EB%94%B0%EB%9D%BC%EA%B8%B0", "1921"),
    ("김동인", "약한 자의 슬픔", "https://ko.wikisource.org/wiki/%EC%95%BD%ED%95%9C_%EC%9E%90%EC%9D%98_%EC%8A%AC%ED%94%94", "1919"),
    ("박태원", "소설가 구보씨의 일일", "https://ko.wikisource.org/wiki/%EC%86%8C%EC%84%A4%EA%B0%80_%EA%B5%AC%EB%B3%B4%EC%94%A8%EC%9D%98_%EC%9D%BC%EC%9D%BC", "1934"),
    ("박태원", "천변풍경", "https://ko.wikisource.org/wiki/%EC%B2%9C%EB%B3%80%ED%92%8D%EA%B2%BD", "1936"),
    ("이상", "날개", "https://ko.wikisource.org/wiki/%EB%82%A0%EA%B0%9C", "1936"),
    ("이상", "봉별기", "https://ko.wikisource.org/wiki/%EB%B4%89%EB%B3%84%EA%B8%B0", "1936"),
    ("이상", "지주회시", "https://ko.wikisource.org/wiki/%EC%A7%80%EC%A3%BC%ED%9A%8C%EC%8B%9C", "1936"),
    ("이상", "동해", "https://ko.wikisource.org/wiki/%EB%8F%99%ED%95%B4", "1937"),
    ("채만식", "태평천하", "https://ko.wikisource.org/wiki/%ED%83%9C%ED%8F%89%EC%B2%9C%ED%95%98", "1938"),
    ("채만식", "레디메이드 인생", "https://ko.wikisource.org/wiki/%EB%A0%88%EB%94%94%EB%A9%94%EC%9D%B4%EB%93%9C_%EC%9D%B8%EC%83%9D", "1934"),
    ("채만식", "치숙", "https://ko.wikisource.org/wiki/%EC%B9%98%EC%88%99", "1938"),
    ("채만식", "논 이야기", "https://ko.wikisource.org/wiki/%EB%85%BC_%EC%9D%B4%EC%95%BC%EA%B8%B0", "1946"),
    ("강경애", "인간문제", "https://ko.wikisource.org/wiki/%EC%9D%B8%EA%B0%84%EB%AC%B8%EC%A0%9C", "1934"),
    ("강경애", "지하촌", "https://ko.wikisource.org/wiki/%EC%A7%80%ED%95%98%EC%B4%8C", "1936"),
    ("나도향", "물레방아", "https://ko.wikisource.org/wiki/%EB%AC%BC%EB%A0%88%EB%B0%A9%EC%95%84", "1925"),
    ("나도향", "벙어리 삼룡이", "https://ko.wikisource.org/wiki/%EB%B2%99%EC%96%B4%EB%A6%AC_%EC%82%BC%EB%A3%A1%EC%9D%B4", "1925"),
    ("최서해", "탈출기", "https://ko.wikisource.org/wiki/%ED%83%88%EC%B6%9C%EA%B8%B0", "1925"),
    ("최서해", "홍염", "https://ko.wikisource.org/wiki/%ED%99%8D%EC%97%BC_(%EC%B5%9C%EC%84%9C%ED%95%B4)", "1927"),
    ("전영택", "화수분", "https://ko.wikisource.org/wiki/%ED%99%94%EC%88%98%EB%B6%84", "1925"),
    ("이효석", "메밀꽃 필 무렵", "https://ko.wikisource.org/wiki/%EB%A9%94%EB%B0%80%EA%BD%83_%ED%95%84_%EB%AC%B4%EB%A0%B5", "1936"),
    ("이효석", "돈", "https://ko.wikisource.org/wiki/%EB%8F%88_(%EC%9D%B4%ED%9A%A8%EC%84%9D)", "1933"),
    ("김유정", "동백꽃", "https://ko.wikisource.org/wiki/%EB%8F%99%EB%B0%B1%EA%BD%83", "1936"),
    ("김유정", "봄봄", "https://ko.wikisource.org/wiki/%EB%B4%84%EB%B4%84", "1935"),
    ("김유정", "금 따는 콩밭", "https://ko.wikisource.org/wiki/%EA%B8%88_%EB%94%B0%EB%8A%94_%EC%BD%A9%EB%B0%AD", "1935"),
    ("심훈", "상록수", "https://ko.wikisource.org/wiki/%EC%83%81%EB%A1%9D%EC%88%98_(%EC%86%8C%EC%84%A4)", "1935"),
]

# ── 시 ────────────────────────────────────────────────────────────────
POEMS = [
    ("김소월", "진달래꽃", "https://ko.wikisource.org/wiki/%EC%A7%84%EB%8B%AC%EB%9E%98%EA%BD%83_(%EC%8B%9C)", "1922"),
    ("김소월", "산유화", "https://ko.wikisource.org/wiki/%EC%82%B0%EC%9C%A0%ED%99%94", "1925"),
    ("김소월", "초혼", "https://ko.wikisource.org/wiki/%EC%B4%88%ED%98%BC_(%EA%B9%80%EC%86%8C%EC%9B%94)", "1925"),
    ("김소월", "엄마야 누나야", "https://ko.wikisource.org/wiki/%EC%97%84%EB%A7%88%EC%95%BC_%EB%88%84%EB%82%98%EC%95%BC", "1922"),
    ("김소월", "먼 후일", "https://ko.wikisource.org/wiki/%EB%A8%BC_%ED%9B%84%EC%9D%BC", "1922"),
    ("한용운", "님의 침묵", "https://ko.wikisource.org/wiki/%EB%8B%98%EC%9D%98_%EC%B9%A8%EB%AC%B5/%EB%8B%98%EC%9D%98_%EC%B9%A8%EB%AC%B5", "1926"),
    ("한용운", "알 수 없어요", "https://ko.wikisource.org/wiki/%EB%8B%98%EC%9D%98_%EC%B9%A8%EB%AC%B5/%EC%95%8C_%EC%88%98_%EC%97%86%EC%96%B4%EC%9A%94", "1926"),
    ("한용운", "나룻배와 행인", "https://ko.wikisource.org/wiki/%EB%8B%98%EC%9D%98_%EC%B9%A8%EB%AC%B5/%EB%82%98%EB%A3%BB%EB%B0%B0%EC%99%80_%ED%96%89%EC%9D%B8", "1926"),
    ("이상화", "빼앗긴 들에도 봄은 오는가", "https://ko.wikisource.org/wiki/%EB%B9%BC%EC%95%97%EA%B8%B4_%EB%93%A4%EC%97%90%EB%8F%84_%EB%B4%84%EC%9D%80_%EC%98%A4%EB%8A%94%EA%B0%80", "1926"),
    ("이상화", "나의 침실로", "https://ko.wikisource.org/wiki/%EB%82%98%EC%9D%98_%EC%B9%A8%EC%8B%A4%EB%A1%9C", "1923"),
    ("심훈", "그날이 오면", "https://ko.wikisource.org/wiki/%EA%B7%B8%EB%82%A0%EC%9D%B4_%EC%98%A4%EB%A9%B4", "1930"),
    ("이육사", "광야", "https://ko.wikisource.org/wiki/%EA%B4%91%EC%95%BC_(%EC%9D%B4%EC%9C%A1%EC%82%AC)", "1945"),
    ("이육사", "절정", "https://ko.wikisource.org/wiki/%EC%A0%88%EC%A0%95", "1940"),
    ("이육사", "청포도", "https://ko.wikisource.org/wiki/%EC%B2%AD%ED%8F%AC%EB%8F%84", "1939"),
    ("이육사", "교목", "https://ko.wikisource.org/wiki/%EA%B5%90%EB%AA%A9_(%EC%9D%B4%EC%9C%A1%EC%82%AC)", "1940"),
    ("이육사", "황혼", "https://ko.wikisource.org/wiki/%ED%99%A9%ED%98%BC_(%EC%9D%B4%EC%9C%A1%EC%82%AC)", "1938"),
    ("윤동주", "서시", "https://ko.wikisource.org/wiki/%ED%95%98%EB%8A%98%EA%B3%BC_%EB%B0%94%EB%9E%8C%EA%B3%BC_%EB%B3%84%EA%B3%BC_%EC%8B%9C/%EC%84%9C%EC%8B%9C", "1941"),
    ("윤동주", "자화상", "https://ko.wikisource.org/wiki/%ED%95%98%EB%8A%98%EA%B3%BC_%EB%B0%94%EB%9E%8C%EA%B3%BC_%EB%B3%84%EA%B3%BC_%EC%8B%9C/%EC%9E%90%ED%99%94%EC%83%81", "1939"),
    ("윤동주", "별 헤는 밤", "https://ko.wikisource.org/wiki/%ED%95%98%EB%8A%98%EA%B3%BC_%EB%B0%94%EB%9E%8C%EA%B3%BC_%EB%B3%84%EA%B3%BC_%EC%8B%9C/%EB%B3%84_%ED%97%A4%EB%8A%94_%EB%B0%A4", "1941"),
    ("윤동주", "참회록", "https://ko.wikisource.org/wiki/%ED%95%98%EB%8A%98%EA%B3%BC_%EB%B0%94%EB%9E%8C%EA%B3%BC_%EB%B3%84%EA%B3%BC_%EC%8B%9C/%EC%B0%B8%ED%9A%8C%EB%A1%9D", "1942"),
    ("윤동주", "쉽게 씌어진 시", "https://ko.wikisource.org/wiki/%ED%95%98%EB%8A%98%EA%B3%BC_%EB%B0%94%EB%9E%8C%EA%B3%BC_%EB%B3%84%EA%B3%BC_%EC%8B%9C/%EC%89%BD%EA%B2%8C_%EC%94%B4_%EC%96%B4%EC%A7%84_%EC%8B%9C", "1942"),
    ("윤동주", "병원", "https://ko.wikisource.org/wiki/%ED%95%98%EB%8A%98%EA%B3%BC_%EB%B0%94%EB%9E%8C%EA%B3%BC_%EB%B3%84%EA%B3%BC_%EC%8B%9C/%EB%B3%91%EC%9B%90", "1940"),
    ("정지용", "향수", "https://ko.wikisource.org/wiki/%ED%96%A5%EC%88%98_(%EC%A0%95%EC%A7%80%EC%9A%A9)", "1927"),
    ("정지용", "유리창", "https://ko.wikisource.org/wiki/%EC%9C%A0%EB%A6%AC%EC%B0%BD_1", "1930"),
    ("정지용", "불사조", "https://ko.wikisource.org/wiki/%EB%B6%88%EC%82%AC%EC%A1%B0_(%EC%A0%95%EC%A7%80%EC%9A%A9)", "1931"),
    ("이용악", "전라도 가시내", "https://ko.wikisource.org/wiki/%EC%A0%84%EB%9D%BC%EB%8F%84_%EA%B0%80%EC%8B%9C%EB%82%B4", "1938"),
    ("이용악", "오랑캐꽃", "https://ko.wikisource.org/wiki/%EC%98%A4%EB%9E%91%EC%BA%90%EA%BD%83", "1938"),
    ("이용악", "낡은 집", "https://ko.wikisource.org/wiki/%EB%82%A1%EC%9D%80_%EC%A7%91_(%EC%9D%B4%EC%9A%A9%EC%95%85)", "1938"),
    ("유치환", "깃발", "https://ko.wikisource.org/wiki/%EA%B9%83%EB%B0%9C_(%EC%9C%A0%EC%B9%98%ED%99%98)", "1936"),
    ("유치환", "생명의 서", "https://ko.wikisource.org/wiki/%EC%83%9D%EB%AA%85%EC%9D%98_%EC%84%9C", "1947"),
    ("조지훈", "승무", "https://ko.wikisource.org/wiki/%EC%8A%B9%EB%AC%B4_(%EC%A1%B0%EC%A7%80%ED%9B%88)", "1939"),
    ("조지훈", "고풍의상", "https://ko.wikisource.org/wiki/%EA%B3%A0%ED%92%8D%EC%9D%98%EC%83%81", "1939"),
    ("장만영", "달·포도·잎사귀", "https://ko.wikisource.org/wiki/%EB%8B%AC%C2%B7%ED%8F%AC%EB%8F%84%C2%B7%EC%9E%8E%EC%82%AC%EA%B7%80", "1938"),
    ("신석정", "그 먼 나라를 알으십니까", "https://ko.wikisource.org/wiki/%EA%B7%B8_%EB%A8%BC_%EB%82%98%EB%9D%BC%EB%A5%BC_%EC%95%8C%EC%9C%BC%EC%8B%AD%EB%8B%88%EA%B9%8C", "1933"),
    ("이장희", "봄은 고양이로다", "https://ko.wikisource.org/wiki/%EB%B4%84%EC%9D%80_%EA%B3%A0%EC%96%91%EC%9D%B4%EB%A1%9C%EB%8B%A4", "1924"),
    ("이상", "오감도", "https://ko.wikisource.org/wiki/%EC%98%A4%EA%B0%90%EB%8F%84", "1934"),
    ("이상", "가외가전", "https://ko.wikisource.org/wiki/%EA%B0%80%EC%99%B8%EA%B0%80%EC%A0%84", "1936"),
    ("이상", "거울", "https://ko.wikisource.org/wiki/%EA%B1%B0%EC%9A%B8", "1933"),
    ("이상", "이런 시", "https://ko.wikisource.org/wiki/%EC%9D%B4%EB%9F%B0_%EC%8B%9C", "1933"),
]

LITERATURE_LIST = NOVELS + POEMS

_POEM_SET = {(a, t) for a, t, _, _ in POEMS}


async def crawl_wikisource_work(
    author: str,
    title: str,
    url: str,
    year: str,
    on_progress=None,
) -> list[dict]:
    """위키문헌 단일 작품 크롤링 → 문단 단위로 분할"""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; history-rag/1.0; korean-history-research)"}
    documents = []

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            content_div = (
                soup.find("div", class_="mw-parser-output")
                or soup.find("div", id="mw-content-text")
            )
            if not content_div:
                print(f"  본문 없음: {title}")
                return []

            for tag in content_div.find_all(
                ["table", "div", "span"],
                class_=re.compile(r"(noprint|navigation|toc|mw-editsection|sister-project)")
            ):
                tag.decompose()
            for tag in content_div.find_all("sup"):
                tag.decompose()

            paragraphs = []
            for p in content_div.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 20:
                    paragraphs.append(text)

            if not paragraphs:
                full_text = content_div.get_text(separator="\n", strip=True)
                full_text = re.sub(r"\n{3,}", "\n\n", full_text)
                paragraphs = [c.strip() for c in full_text.split("\n\n") if len(c.strip()) > 20]

            is_poem = (author, title) in _POEM_SET
            chunk_size = 999 if is_poem else 4

            for i in range(0, len(paragraphs), chunk_size):
                chunk = "\n\n".join(paragraphs[i:i + chunk_size])
                if len(chunk) < 20:
                    continue
                genre = "시" if is_poem else "소설"
                doc_id = f"wikisrc_{author}_{title}_{i}".replace(" ", "_")
                documents.append({
                    "id": doc_id,
                    "text": f"[{author} 〈{title}〉 ({year})]\n\n{chunk}",
                    "source": f"위키문헌 — {author} 〈{title}〉",
                    "year": year,
                    "url": url,
                    "image_url": "",
                    "category": f"근대문학_{genre}",
                })
                if on_progress:
                    on_progress(len(documents))

            print(f"  ✅ {author} 〈{title}〉 — {len(documents)}개 청크")

        except Exception as e:
            print(f"  ❌ {author} 〈{title}〉 실패: {e}")

    return documents


async def crawl_all_literature(
    on_progress=None,
    max_works: int = 0,
) -> list[dict]:
    """전체 문학 작품 크롤링"""
    all_documents = []
    works = LITERATURE_LIST[:max_works] if max_works > 0 else LITERATURE_LIST

    print(f"📚 위키문헌 문학 크롤링 시작 — {len(works)}개 작품")
    print(f"   소설 {len(NOVELS)}편 + 시 {len(POEMS)}편")

    for author, title, url, year in works:
        print(f"  수집 중: {author} 〈{title}〉")
        docs = await crawl_wikisource_work(author, title, url, year, on_progress)
        all_documents.extend(docs)
        await asyncio.sleep(1.0)

    print(f"\n✅ 문학 크롤링 완료 — 총 {len(all_documents)}개 청크")
    return all_documents
