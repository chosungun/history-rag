from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.services.public_api import fetch_heritage_data
from app.services.scraper import crawl_history_db_by_year, crawl_magazine, crawl_sequential, crawl_seoul_archive_photos, MAGAZINE_ITEMS, HISTORY_DB_ITEMS
from app.services.rag import ingest_documents
import uuid
import time
from collections import OrderedDict

router = APIRouter()

# 작업 상태 저장소 (최근 20개)
_jobs: OrderedDict[str, dict] = OrderedDict()
_MAX_JOBS = 20


def _new_job(label: str, max_docs: int = 0) -> str:
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "id": job_id,
        "label": label,
        "status": "running",   # running | done | error
        "phase": "크롤링 중",
        "collected": 0,
        "max_docs": max_docs,
        "saved": 0,
        "started_at": time.time(),
        "finished_at": None,
        "error": None,
    }
    if len(_jobs) > _MAX_JOBS:
        _jobs.popitem(last=False)
    return job_id


def _finish_job(job_id: str, saved: int):
    if job_id in _jobs:
        j = _jobs[job_id]
        j["status"] = "done"
        j["phase"] = "완료"
        j["saved"] = saved
        j["finished_at"] = time.time()


def _fail_job(job_id: str, error: str):
    if job_id in _jobs:
        j = _jobs[job_id]
        j["status"] = "error"
        j["phase"] = "오류"
        j["error"] = error
        j["finished_at"] = time.time()


@router.get("/jobs")
async def list_jobs():
    """진행 중이거나 최근 완료된 수집 작업 목록"""
    return list(reversed(list(_jobs.values())))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in _jobs:
        return {"error": "not found"}
    return _jobs[job_id]


# ── 공개 API (국가유산청) ────────────────────────────────────────────

class IngestRequest(BaseModel):
    keyword: str


@router.post("/fetch")
async def ingest_from_api(req: IngestRequest, background_tasks: BackgroundTasks):
    job_id = _new_job(f"국가유산청: {req.keyword}")
    background_tasks.add_task(_do_ingest, req.keyword, job_id)
    return {"message": f"'{req.keyword}' 수집을 시작합니다.", "job_id": job_id}


async def _do_ingest(keyword: str, job_id: str):
    try:
        _jobs[job_id]["phase"] = "국가유산청 수집 중"
        items = await fetch_heritage_data(keyword)
        docs = []
        for item in items:
            item["id"] = f"heritage_{uuid.uuid4().hex[:8]}"
            docs.append(item)
        _jobs[job_id]["collected"] = len(docs)
        if docs:
            _jobs[job_id]["phase"] = "DB 저장 중"
            count = await ingest_documents(docs)
            _finish_job(job_id, count)
        else:
            _finish_job(job_id, 0)
    except Exception as e:
        _fail_job(job_id, str(e))


# ── 직접 JSON 업로드 ────────────────────────────────────────────────

@router.post("/manual")
async def ingest_manual(documents: list[dict]):
    count = await ingest_documents(documents)
    return {"ingested": count}


# ── 한국근현대사료DB ────────────────────────────────────────────────

class HistoryDbRequest(BaseModel):
    item_id: str = "gb"
    years: list[int] = list(range(1919, 1926))
    max_docs: int = 100


_HISTORY_LABELS = {
    "gb": "조선총독부 관보",
    "had": "국내 항일운동 자료",
    "haf": "국외 항일운동 자료",
    "pro": "소요사건 도장관 보고",
}


@router.post("/fetch-history-db")
async def ingest_history_db(req: HistoryDbRequest, background_tasks: BackgroundTasks):
    label = _HISTORY_LABELS.get(req.item_id, req.item_id)
    job_id = _new_job(f"{label} ({req.years[0]}~{req.years[-1]}년)", req.max_docs)
    background_tasks.add_task(_do_ingest_history_db, req.item_id, req.years, req.max_docs, job_id)
    return {"message": f"'{label}' 수집을 시작합니다. 최대 {req.max_docs}건.", "job_id": job_id}


async def _do_ingest_history_db(item_id: str, years: list[int], max_docs: int, job_id: str):
    def on_progress(n): _jobs[job_id]["collected"] = n
    try:
        _jobs[job_id]["phase"] = "크롤링 중"
        docs = await crawl_history_db_by_year(item_id=item_id, years=years, max_docs=max_docs, on_progress=on_progress)
        _jobs[job_id]["collected"] = len(docs)
        if docs:
            _jobs[job_id]["phase"] = "DB 저장 중"
            count = await ingest_documents(docs)
            _finish_job(job_id, count)
        else:
            _finish_job(job_id, 0)
    except Exception as e:
        _fail_job(job_id, str(e))


# ── 근현대잡지 ──────────────────────────────────────────────────────

class MagazineRequest(BaseModel):
    mag_level_id: str = "ma_013"
    year_filter: list[str] | None = None
    max_docs: int = 100


# ── Bulk 수집 소스 정의 (신문 제외) ─────────────────────────────────

# 잡지: 11종 전체 (crawl_magazine)
_BULK_MAGAZINES = [
    "ma_013", "ma_016", "ma_102", "ma_015", "ma_014",
    "ma_091", "ma_066", "ma_069", "ma_074", "ma_001", "ma_004",
    "ma_109", "ma_126",
]

# 연도 기반: 조선총독부 관보만 (crawl_history_db_by_year)
_BULK_YEAR_BASED = [("gb", list(range(1910, 1946)))]

# 순번형: (item_id, max_docs) — 0=무제한
# had(374볼륨)/haf(126)/ju(585볼륨)는 볼륨당 다수 문서 가능하여 cap 설정
_BULK_SEQUENTIAL: list[tuple[str, int]] = [
    # 민족운동·사회운동
    ("had",  1000), ("haf", 500), ("ij",   0), ("pro",  0),
    ("jssy",    0), ("kd",    0), ("hdsr", 0), ("hd",   0),
    # 편년자료·문서
    ("jh",      0), ("ju", 1500), ("su",   0),
    # 목록·총서
    ("smla",    0), ("wj",    0), ("gsdc", 0), ("smlb", 0), ("mh", 0), ("hk", 0),
    # 근대 전환기
    ("mk",      0), ("gj",    0), ("sk",   0),
    ("prd",     0), ("prc",   0), ("prw",  0), ("ykc",  0),
]


@router.post("/fetch-all")
async def ingest_all(background_tasks: BackgroundTasks):
    """신문 제외 전체 일괄 수집 (잡지 + 연도기반 + 순번형 + 서울아카이브, 순차 실행)"""
    job_ids = []

    for mag_id in _BULK_MAGAZINES:
        name = MAGAZINE_ITEMS.get(mag_id, mag_id)
        job_ids.append(_new_job(f"{name} (전체)", 0))

    for item_id, years in _BULK_YEAR_BASED:
        label = HISTORY_DB_ITEMS.get(item_id, (item_id,))[0]
        job_ids.append(_new_job(f"{label} ({years[0]}~{years[-1]})", 0))

    for item_id, max_docs in _BULK_SEQUENTIAL:
        label = HISTORY_DB_ITEMS.get(item_id, (item_id,))[0]
        cap_str = f" (최대 {max_docs}건)" if max_docs else " (전체)"
        job_ids.append(_new_job(f"{label}{cap_str}", max_docs))

    job_ids.append(_new_job("서울역사아카이브 근현대서울사진 (전체)", 0))

    background_tasks.add_task(_do_bulk_ingest, job_ids)
    total = len(_BULK_MAGAZINES) + len(_BULK_YEAR_BASED) + len(_BULK_SEQUENTIAL) + 1
    return {"message": f"총 {total}개 소스 일괄 수집을 시작합니다.", "job_ids": job_ids}


async def _do_bulk_ingest(job_ids: list[str]):
    idx = 0

    # 잡지
    for mag_id in _BULK_MAGAZINES:
        jid = job_ids[idx]; idx += 1
        def on_progress(n, j=jid): _jobs[j]["collected"] = n
        try:
            _jobs[jid]["phase"] = "크롤링 중"
            docs = await crawl_magazine(mag_level_id=mag_id, max_docs=0, on_progress=on_progress)
            _jobs[jid]["collected"] = len(docs)
            if docs:
                _jobs[jid]["phase"] = "DB 저장 중"
                _finish_job(jid, await ingest_documents(docs))
            else:
                _finish_job(jid, 0)
        except Exception as e:
            _fail_job(jid, str(e))

    # 연도 기반 (gb 등)
    for item_id, years in _BULK_YEAR_BASED:
        jid = job_ids[idx]; idx += 1
        def on_progress(n, j=jid): _jobs[j]["collected"] = n
        try:
            _jobs[jid]["phase"] = "크롤링 중"
            docs = await crawl_history_db_by_year(item_id=item_id, years=years, max_docs=0, on_progress=on_progress)
            _jobs[jid]["collected"] = len(docs)
            if docs:
                _jobs[jid]["phase"] = "DB 저장 중"
                _finish_job(jid, await ingest_documents(docs))
            else:
                _finish_job(jid, 0)
        except Exception as e:
            _fail_job(jid, str(e))

    # 순번형
    for item_id, max_docs in _BULK_SEQUENTIAL:
        jid = job_ids[idx]; idx += 1
        def on_progress(n, j=jid): _jobs[j]["collected"] = n
        try:
            _jobs[jid]["phase"] = "크롤링 중"
            docs = await crawl_sequential(item_id=item_id, max_docs=max_docs, on_progress=on_progress)
            _jobs[jid]["collected"] = len(docs)
            if docs:
                _jobs[jid]["phase"] = "DB 저장 중"
                _finish_job(jid, await ingest_documents(docs))
            else:
                _finish_job(jid, 0)
        except Exception as e:
            _fail_job(jid, str(e))

    # 서울역사아카이브 근현대서울사진
    jid = job_ids[idx]; idx += 1
    def on_progress(n, j=jid): _jobs[j]["collected"] = n
    try:
        _jobs[jid]["phase"] = "크롤링 중"
        docs = await crawl_seoul_archive_photos(on_progress=on_progress)
        _jobs[jid]["collected"] = len(docs)
        if docs:
            _jobs[jid]["phase"] = "DB 저장 중"
            _finish_job(jid, await ingest_documents(docs))
        else:
            _finish_job(jid, 0)
    except Exception as e:
        _fail_job(jid, str(e))


@router.get("/magazines")
async def list_magazines():
    return [{"id": k, "name": v} for k, v in MAGAZINE_ITEMS.items()]


@router.post("/fetch-magazine")
async def ingest_magazine(req: MagazineRequest, background_tasks: BackgroundTasks):
    name = MAGAZINE_ITEMS.get(req.mag_level_id, req.mag_level_id)
    year_str = f" ({req.year_filter[0]}~{req.year_filter[-1]}년)" if req.year_filter else ""
    job_id = _new_job(f"{name}{year_str}", req.max_docs)
    background_tasks.add_task(_do_ingest_magazine, req.mag_level_id, req.year_filter, req.max_docs, job_id)
    return {"message": f"'{name}' 수집을 시작합니다. 최대 {req.max_docs}건.", "job_id": job_id}


async def _do_ingest_magazine(mag_level_id: str, year_filter: list[str] | None, max_docs: int, job_id: str):
    def on_progress(n): _jobs[job_id]["collected"] = n
    try:
        _jobs[job_id]["phase"] = "크롤링 중"
        docs = await crawl_magazine(mag_level_id=mag_level_id, max_docs=max_docs, year_filter=year_filter, on_progress=on_progress)
        _jobs[job_id]["collected"] = len(docs)
        if docs:
            _jobs[job_id]["phase"] = "DB 저장 중"
            count = await ingest_documents(docs)
            _finish_job(job_id, count)
        else:
            _finish_job(job_id, 0)
    except Exception as e:
        _fail_job(job_id, str(e))
