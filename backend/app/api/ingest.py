from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.services.public_api import fetch_korean_wikipedia
from app.services.rag import ingest_documents
import uuid

router = APIRouter()


class IngestRequest(BaseModel):
    keyword: str
    sources: list[str] = ["wikipedia"]


@router.post("/fetch")
async def ingest_from_api(req: IngestRequest, background_tasks: BackgroundTasks):
    """공개 API에서 데이터를 가져와 ChromaDB에 저장"""
    background_tasks.add_task(_do_ingest, req.keyword, req.sources)
    return {"message": f"'{req.keyword}' 데이터 수집을 시작합니다. 잠시 후 검색 가능합니다."}


async def _do_ingest(keyword: str, sources: list[str]):
    documents = []

    if "wikipedia" in sources:
        try:
            items = await fetch_korean_wikipedia(keyword, limit=5)
            for item in items:
                item["id"] = f"wiki_{uuid.uuid4().hex[:8]}"
                documents.append(item)
        except Exception as e:
            print(f"위키백과 수집 실패: {e}")

    if documents:
        count = await ingest_documents(documents)
        print(f"✅ {count}개 문서 ChromaDB 저장 완료")
    else:
        print("⚠ 수집된 문서가 없습니다.")


@router.post("/manual")
async def ingest_manual(documents: list[dict]):
    """직접 JSON으로 문서 업로드"""
    count = await ingest_documents(documents)
    return {"ingested": count}
